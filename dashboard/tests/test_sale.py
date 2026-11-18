"""The sale card's pure functions: price ranges, the workflow's inputs, the running sale's state file, and the numbers in the store sale logs (new and old format)."""
import json
from datetime import date

from conftest import SALE_CANCEL_LOG, SALE_PLAN_LOG, SALE_STATE_LEGACY, SALE_V2_APPLY_LOG, SALE_V2_TEST_LOG

from app import sale

TODAY = date(2026, 10, 26)


def test_clean_ranges_reads_the_pages_rows_and_refuses_nonsense():
    rows = [["0", "4.99", "5"], ["5", "9.99", ""], ["10", "20", "0"], ["20.01", "", "3"], ["", "", "2.5"]]
    ranges, error = sale.clean_ranges(rows)
    assert error == "" and ranges == [[0.0, 4.99, 5.0], [5.0, 9.99, 0.0], [10.0, 20.0, 0.0], [20.01, None, 3.0], [None, None, 2.5]]
    assert sale.clean_ranges([["£1,000", "2,000.5", "10"]])[0] == [[1000.0, 2000.5, 10.0]]
    for bad, text in (([], "at least one"), (None, "at least one"), ([["a", "5", "3"]], "numbers"), ([["5", "1", "3"]], "below the low"), ([["-1", "5", "3"]], "negative"),
                      ([["0", "5", "95"]], "1 to 90"), ([["0", "5", "0.5"]], "1 to 90"), ([["0", "5", "x"]], "numbers"), ([["0", "5"]], "a low price"),
                      ([["0", "5", ""], ["6", "9", "0"]], "nothing would go on sale"), ([["0", "1", "5"]] * 21, "At most")):
        ranges, error = sale.clean_ranges(bad)
        assert ranges is None and text in error, (bad, error)
    assert sale.ranges_text([[0.0, 4.99, 5.0], [20.01, None, 3.0]]) == "[[0.0,4.99,5.0],[20.01,null,3.0]]"
    assert sale.describe_ranges([[0.0, 4.99, 5.0], [10.0, 20.0, 0.0], [20.01, None, 3.0]]) == "5% off £0 to £4.99; no sale on £10 to £20; 3% off £20.01 and above"


def test_the_usual_brackets_leave_no_gap_and_no_overlap():
    brackets = sale.BRACKETS
    assert brackets[0][0] == 0 and brackets[-1][1] is None
    for (lo1, hi1), (lo2, hi2) in zip(brackets, brackets[1:]):
        assert round(lo2 - hi1, 2) in (0.01, 0.0) and (hi1 is not None)          # 4.99 -> 5, 9.99 -> 10, 20 -> 20.01: pence-exact, the 10-20 bracket holds both ends


def test_the_last_day_must_be_a_real_day_from_today_to_a_year_ahead():
    assert sale.clean_end("2026-10-28", TODAY) == ("2026-10-28", "") and sale.clean_end("2026-10-26", TODAY)[1] == ""
    assert "past" in sale.clean_end("2026-10-25", TODAY)[1] and "year" in sale.clean_end("2027-10-27", TODAY)[1]
    assert sale.clean_end("2027-10-26", TODAY)[1] == "" and "last day" in sale.clean_end("28-10-2026", TODAY)[1] and "last day" in sale.clean_end("", TODAY)[1]


def test_build_inputs_for_each_mode():
    body = {"ranges": [["0", "9.99", "5"], ["10", "20", ""], ["20.01", "", "3"]], "sale_end": "2026-10-28", "min_profit": "12", "floor_mode": "cap", "scope": "in_stock"}
    inputs, error = sale.build_inputs(body, "plan", TODAY)
    assert error == "" and inputs == {"mode": "plan", "price_ranges": "[[0.0,9.99,5.0],[10.0,20.0,0.0],[20.01,null,3.0]]", "sale_end": "2026-10-28", "min_profit": "12",
                                       "floor_mode": "cap", "scope": "in_stock"}
    applied, _ = sale.build_inputs(body, "apply", TODAY)
    assert applied["mode"] == "apply" and applied["max_changes"] == "20000"
    tested, error = sale.build_inputs(dict(body, test_sku=" 738516204215 "), "test", TODAY)
    assert tested["test_sku"] == "738516204215" and "SKU" in sale.build_inputs(body, "test", TODAY)[1]
    assert sale.build_inputs({}, "cancel", TODAY) == ({"mode": "cancel"}, "")
    assert sale.build_inputs(dict(body, floor_off=True), "plan", TODAY)[0]["min_profit"] == "off"
    assert sale.build_inputs({k: v for k, v in body.items() if k != "min_profit"}, "plan", TODAY)[0]["min_profit"] == "10"
    for change, text in (({"ranges": []}, "at least one"), ({"sale_end": "2026-10-01"}, "past"), ({"min_profit": "900"}, "margin floor"), ({"min_profit": "x"}, "margin floor"),
                         ({"floor_mode": "wild"}, "Unknown"), ({"scope": "some"}, "Unknown")):
        assert text in sale.build_inputs(dict(body, **change), "plan", TODAY)[1], change


def test_state_view_reads_a_new_state_and_the_one_gtvs_first_sale_wrote():
    legacy = sale.state_view(json.dumps(SALE_STATE_LEGACY), today=date.fromisoformat(SALE_STATE_LEGACY["sale_end_date"][:10]))
    assert legacy["active"] and legacy["summary"] == "3% off every listing except £10 to £20" and legacy["listings"] == 7938 and legacy["ranges"] == []
    assert legacy["floor"] == "10.0% profit on cost + shipping after the fee, skip" and legacy["exclude"] == [10.0, 20.0]
    assert not sale.state_view(json.dumps(SALE_STATE_LEGACY), today=date(2099, 1, 1))["active"]
    new = {"percent": 5, "summary": "5% off GBP 0 to GBP 9.99; no sale on GBP 10 to GBP 20", "price_ranges": [[0.0, 9.99, 5.0], [10.0, 20.0, 0.0]], "sale_start_date": "2026-10-25 00:00:00",
           "sale_end_date": "2026-10-28 23:59:59", "min_profit_percent": "off", "scope": "in_stock", "listings": 10}
    view = sale.state_view(json.dumps(new), today=TODAY)
    assert view["summary"] == "5% off £0 to £9.99; no sale on £10 to £20" and view["floor"] == "none" and view["scope"] == "in_stock" and view["ends"] == "2026-10-28"
    assert [r["label"] for r in view["ranges"]] == ["£0 to £9.99", "£10 to £20"] and view["ranges"][1]["percent"] == 0.0
    assert sale.state_view("not json") is None and sale.state_view("[1]") is None and sale.state_view("") is None


def test_parse_a_plan_with_price_ranges():
    f = sale.parse_store_sale(SALE_PLAN_LOG)
    assert f["mode"] == "plan" and f["sale"].startswith("5% off GBP 0 to GBP 9.99; no sale on") and f["window_end"] == "2026-10-28 23:59:59" and f["scope"] == "all"
    assert f["floor"].startswith("10.0% profit") and f["state_before"] == "none" and f["listings"] == 8936 and f["sales_now"] == 0
    assert f["updates"] == 7500 and f["requests"] == 15 and f["on_sale_after"] == 7500 and f["discount"] == 26112.5 and f["nothing_changed"] is True
    assert f["actions"][0] == {"action": "sale on", "listings": 7500} and {"action": "skip: price in the excluded range", "listings": 656} in f["actions"]
    assert f["ranges"][0] == {"range": 1, "prices": "£0 to £9.99", "sale": "5%", "listings": 900, "on_sale": 800, "no_cost": 60, "below_floor": 30, "other": 10, "discount": 112.5, "ended": 0}
    assert f["ranges"][1]["sale"] == "kept out" and f["ranges"][2]["discount"] == 26000.0 and f["ranges"][2]["ended"] == 3 and f["outside"] == 0


def test_parse_the_first_runs_in_the_old_format_with_masked_braces():
    f = sale.parse_store_sale(SALE_V2_APPLY_LOG)
    assert f["mode"] == "apply" and f["sale"] == "3.0% off every listing except GBP 10 to GBP 20 (both included)" and f["window_end"] == "2026-11-25 23:59:59"
    assert f["sales_now"] == 0 and f["listings"] == 8936 and f["updates"] == 7938 and f["requests"] == 16
    assert {"action": "sale on", "listings": 7938} in f["actions"] and {"action": "skip: below the margin floor", "listings": 38} in f["actions"]
    assert f["on_sale_after"] == 7938 and f["discount"] == 26593.01 and f["applied_ok"] == 7938 and f["applied_failed"] == 0 and f["readback"] == "8 of 8"
    assert f["state_written"].startswith("3.0% until 2026-11-25")
    t = sale.parse_store_sale(SALE_V2_TEST_LOG)
    assert t["mode"] == "test" and t["test_sku"] == "738516204215" and t["test_plan"] == "sale on at 26.32" and t["test_on"] == "visible after 15s" and t["test_off"] == "gone after 60s"


def test_parse_a_cancel_and_a_listing_that_would_not_go_on_sale():
    f = sale.parse_store_sale(SALE_CANCEL_LOG)
    assert f["mode"] == "cancel" and f["sales_now"] == 7938 and f["sales_end_dates"] == "2026-10-28 (7938)" and f["to_end"] == 7938
    assert f["cancelled_ok"] == 7938 and f["cancelled_failed"] == 0 and f["state_removed"] is True and f["readback"] == "8 of 8"
    assert f["state_before"].startswith("ACTIVE 3% off every listing")
    nothing = sale.parse_store_sale("MODE test | sale 3% off every listing | window a b .. c d | scope all | margin floor OFF | state: none\nRESULT: nothing sent - this listing would not be put on sale (see the reason above)")
    assert nothing["test_on"].startswith("nothing sent")
    assert sale.parse_store_sale("") == {}
