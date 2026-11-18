"""The To do card's pure part: facts of one store -> items (what needs a person), their severity and their order."""
from datetime import timedelta

from conftest import NOW, iso

from app import todo


def order(order_id, days=None, **flags):
    due = (NOW.date() + timedelta(days=days)).isoformat() if days is not None else ""
    return {"order_id": order_id, "due": due, "overdue": flags.get("overdue", days is not None and days < 0), "due_today": flags.get("due_today", days == 0), "skus": ["x"]}


def orders(*lines, age=2.0):
    return {"count": len(lines), "overdue": sum(1 for o in lines if o["overdue"]), "due_today": sum(1 for o in lines if o["due_today"]), "orders": list(lines), "age_hours": age}


def failed(path, hours=3, facts=None, event="schedule"):
    return {path: {"run": {"path": path, "conclusion": "failure", "event": event, "created_at": iso(NOW - timedelta(hours=hours)), "url": f"https://github.com/x/y/actions/runs/{hours}"}, "facts": facts or {}}}


def items(facts, store="gtv"):
    return todo.items_for(store, store.upper(), facts, NOW)


def keys(found):
    return [i["id"] for i in found]


def test_a_store_with_nothing_to_do_has_no_items():
    assert items({"orders": orders(order("T1", 5)), "push": True, "newest": {"run.yml": {"run": {"conclusion": "success", "created_at": iso(NOW)}, "facts": {}}}}) == []


# ---- orders -----------------------------------------------------------------------------------------------------------------------
def test_orders_past_their_date_or_due_today_are_act_and_those_due_soon_are_look():
    found = items({"orders": orders(order("T-OLD", -2), order("T-TODAY", 0), order("T-SOON", 2), order("T-LATER", 6))})
    by_id = {i["id"]: i for i in found}
    assert by_id["gtv:orders-overdue"]["severity"] == "act" and "T-OLD (due" in by_id["gtv:orders-overdue"]["detail"] and by_id["gtv:orders-overdue"]["title"] == "1 order is past the dispatch date"
    assert by_id["gtv:orders-today"]["severity"] == "act" and by_id["gtv:orders-today"]["title"] == "1 order must be dispatched today"
    assert by_id["gtv:orders-soon"]["severity"] == "look" and "T-SOON" in by_id["gtv:orders-soon"]["detail"] and "T-LATER" not in by_id["gtv:orders-soon"]["detail"]
    assert keys(found) == ["gtv:orders-overdue", "gtv:orders-today", "gtv:orders-soon"]                  # the urgent ones first
    assert all(i["link"] == "/orders" for i in found)


def test_many_orders_are_named_up_to_six_and_the_rest_counted():
    found = items({"orders": orders(*[order(f"T{n}", -1) for n in range(9)])})
    assert found[0]["title"] == "9 orders are past the dispatch date" and "and 3 more" in found[0]["detail"] and found[0]["detail"].count("(due") == 6


def test_a_missing_or_old_orders_list_is_a_look_item_not_an_all_clear():
    assert [i["title"] for i in items({"orders": None})] == ["No orders list yet"]
    old = items({"orders": orders(order("T1", 9), age=60.0)})
    assert [i["id"] for i in old] == ["gtv:orders-old"] and "60 hours old" in old[0]["title"]
    assert items({"orders": orders(age=3.0)}) == []                                                   # a fresh list with nothing due


# ---- the syncs and the scheduled jobs ----------------------------------------------------------------------------------------------
def test_a_failed_sync_is_act_and_a_failed_content_scan_only_a_look():
    found = items({"newest": {**failed("run.yml"), **failed("scan_content_mismatch.yml", 30)}})
    by_id = {i["id"]: i for i in found}
    assert by_id["gtv:failed-run.yml"]["severity"] == "act" and by_id["gtv:failed-run.yml"]["title"] == "The eBay sync failed 3 h ago"
    assert by_id["gtv:failed-run.yml"]["url"].startswith("https://github.com/") and by_id["gtv:failed-run.yml"]["link"] == "/store/gtv"
    assert by_id["gtv:failed-scan_content_mismatch.yml"]["severity"] == "look" and by_id["gtv:failed-scan_content_mismatch.yml"]["title"] == "The content scan failed 30 h ago"


def test_a_failed_run_started_by_hand_is_only_a_look():
    found = items({"newest": failed("run_amazon.yml", 2, event="workflow_dispatch")})
    assert [(i["severity"], i["title"]) for i in found] == [("look", "The Amazon sync failed 2 h ago (a run started by hand)")]


def test_a_newest_run_that_succeeded_or_was_cancelled_is_not_a_failure():
    ok = {"run": {"conclusion": "success", "created_at": iso(NOW)}, "facts": {}}
    cancelled = {"run": {"conclusion": "cancelled", "created_at": iso(NOW)}, "facts": {}}
    assert items({"newest": {"run.yml": ok, "run_amazon.yml": cancelled}}) == []


def test_an_amazon_sync_that_ran_out_of_keepa_tokens_says_so_and_points_to_the_amazon_page():
    found = items({"newest": failed("run_amazon.yml", 5, {"keepa_failed": {"asins": 2216, "reason": "keepa product: out of tokens"}})}, store="yra")
    assert [i["id"] for i in found] == ["yra:amazon-tokens"] and found[0]["severity"] == "act" and found[0]["title"] == "The Amazon sync ran out of Keepa tokens"
    assert "2,216 Amazon rows were left exactly as they were (5 h ago)" in found[0]["detail"] and found[0]["link"] == "/amazon?store=yra"


def test_late_jobs_ghost_runs_failing_tests_and_switched_off_updates_are_look_items():
    found = items({"stale": [{"name": "Amazon Sync (Keepa)", "hours": 15.2, "limit": 12}],
                   "stuck": [{"name": "Makstore Full-Auto Sync", "created_at": "2026-08-19T01:00:00Z", "url": "https://github.com/x/y/actions/runs/32216976318"}],
                   "ci": {"conclusion": "failure", "created_at": iso(NOW - timedelta(hours=26)), "url": "https://github.com/x/y/actions/runs/9"},
                   "push": False, "push_value": "no"})
    by_title = {i["title"]: i for i in found}
    assert "Amazon Sync (Keepa) has not run for 15 hours" in by_title and "A run of 'Makstore Full-Auto Sync' has been queued since 2026-08-19" in by_title
    assert "The automated tests of this store's code are failing (26 h ago)" in by_title and "OnBuy updates are switched off for this store" in by_title
    assert 'ONBUY_API_PUSH_ENABLED is "no", not true' in by_title["OnBuy updates are switched off for this store"]["detail"]
    assert {i["severity"] for i in found} == {"look"}
    assert items({"push": False, "push_value": ""})[0]["detail"].startswith("ONBUY_API_PUSH_ENABLED is not set")
    assert items({"push": True}) == [] and items({"push": None}) == []


# ---- Amazon prices, the nightly, the sale, the fees -------------------------------------------------------------------------------------
def test_big_amazon_price_falls_are_a_look_item_naming_the_worst_row():
    found = items({"falls": {"alerts": 2, "alert_percent": 25.0, "worst": {"row": 89, "sku": "327210340093", "old": 227.65, "new": 117.22, "percent": -48.5}}}, store="makstore")
    assert found[0]["severity"] == "look" and found[0]["title"] == "2 prices fell by 25% or more in the last Amazon sync"
    assert "row 89 (SKU 327210340093) from £227.65 to £117.22 (-48.5%)" in found[0]["detail"] and found[0]["link"] == "/amazon?store=makstore"
    assert items({"falls": {"alerts": 0, "alert_percent": 25.0}}) == [] and items({"falls": None}) == []


def test_listings_frozen_in_the_last_days_and_what_the_nightly_did_are_for_information():
    found = items({"frozen": [{"sku": "Ama-B0BRHJTQZ6-5", "since": "2026-10-22"}, {"sku": "856689732127", "since": "2026-10-26"}]})
    assert [(i["id"], i["severity"], i["title"]) for i in found] == [("gtv:frozen", "fyi", "2 listings frozen in the last 7 days because the OnBuy page shows another product")]
    assert "Ama-B0BRHJTQZ6-5, 856689732127." in found[0]["detail"] and found[0]["link"] == "/catalogue?store=gtv"
    many = items({"frozen": [{"sku": f"S{n}", "since": "2026-10-26"} for n in range(6)]})
    assert "S0, S1, S2, S3 and 2 more." in many[0]["detail"] and items({"frozen": []}) == []
    nightly = {"run": {"created_at": iso(NOW - timedelta(hours=9)), "url": "https://github.com/x/y/actions/runs/7"}, "facts": {"zeroed": 4, "rows_deleted": 1, "corrected": 20, "fix_failed": 2}}
    found = items({"nightly": nightly})
    assert [(i["id"], i["severity"]) for i in found] == [("gtv:nightly", "fyi")]
    assert found[0]["title"] == "The nightly check 4 listing(s) zeroed for showing another product, 1 row(s) deleted, 20 price(s) corrected on OnBuy (2 could not be)"
    assert items({"nightly": {"run": nightly["run"], "facts": {"zeroed": 0, "held": 7}}}) == []


def test_a_sale_that_ends_within_two_days_is_a_look_item():
    today = NOW.date()
    for days, when in ((2, "in 2 days"), (1, "tomorrow"), (0, "today")):
        found = items({"sale": {"active": True, "ends": (today + timedelta(days=days)).isoformat(), "percent": 3}})
        assert len(found) == 1 and found[0]["title"] == f"The store sale ends {when} ({(today + timedelta(days=days)).isoformat()})" and found[0]["link"] == "/sale?store=gtv"
    assert items({"sale": {"active": True, "ends": (today + timedelta(days=9)).isoformat()}}) == [] and items({"sale": {"active": False, "ends": today.isoformat()}}) == [] and items({"sale": None}) == []


def test_changed_commission_tables_are_a_look_item_while_they_are_recent():
    differ = {"tables": "differ", "note": "3 gone, 20 new, 1 changed tier", "run": {"url": "https://github.com/x/y/actions/runs/34"}, "age_days": 3}
    found = items({"fees": differ})
    assert found[0]["id"] == "gtv:fees-differ" and found[0]["detail"] == "3 gone, 20 new, 1 changed tier. Compare them and commit them on the Fees page if they are right." and found[0]["url"].endswith("/34")
    assert items({"fees": {**differ, "age_days": 40}}) == [] and items({"fees": {**differ, "tables": "committed"}}) == [] and items({"fees": {**differ, "tables": "unchanged"}}) == []


# ---- putting it together -----------------------------------------------------------------------------------------------------------------
def test_the_summary_counts_and_the_groups_follow_the_urgency():
    found = items({"orders": orders(order("T1", -1)), "stale": [{"name": "Backfill", "hours": 9.0, "limit": 8}], "nightly": {"run": {"created_at": iso(NOW)}, "facts": {"zeroed": 2}}})
    assert todo.summarize(found) == {"act": 1, "look": 1, "fyi": 1, "total": 3}
    assert [(key, heading, len(rows)) for key, heading, rows in todo.grouped(found)] == [("act", "Act now", 1), ("look", "Look today", 1), ("fyi", "For your information", 1)]
    assert todo.grouped([]) == [] and todo.summarize([]) == {"act": 0, "look": 0, "fyi": 0, "total": 0}


# ---- dead rows and suspended listings (2026-10-29: the Daily check's and the Delete page's finds reach the To do flow) ---------------
def test_rows_that_keep_failing_are_a_look_item_with_the_reason_and_the_delete_page():
    found = items({"dead_rows": {"count": 75, "most_nights": 7, "reason": "SKU does not exist"}})
    assert keys(found) == ["gtv:dead-rows"] and found[0]["severity"] == "look"
    assert found[0]["title"] == "75 rows failed the nightly's price fix again last night"
    assert "7 nights running" in found[0]["detail"] and '"SKU does not exist"' in found[0]["detail"] and found[0]["link"] == "/delete?store=gtv"
    assert items({"dead_rows": {"count": 0, "most_nights": 0, "reason": ""}}) == []                   # healed = quiet


def test_waiting_suspended_listings_are_fyi_until_new_ones_arrive():
    standing = items({"suspended": {"waiting": 150, "new": 0}})
    assert keys(standing) == ["gtv:suspended"] and standing[0]["severity"] == "fyi"
    assert standing[0]["title"] == "150 suspended listings wait for your hand-delete" and "ticklist" in standing[0]["detail"]
    fresh = items({"suspended": {"waiting": 174, "new": 168}})
    assert fresh[0]["severity"] == "look" and "168 were reported in the last two days." in fresh[0]["detail"]
    one = items({"suspended": {"waiting": 1, "new": 1}})
    assert one[0]["title"] == "1 suspended listing waits for your hand-delete" and "1 was reported" in one[0]["detail"]
    assert items({"suspended": {"waiting": 0, "new": 0}}) == []
