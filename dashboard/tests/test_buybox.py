"""The Buy Box card: the three settings (validation, what the repository variables mean), the numbers in the engine's log, and the page and its two endpoints."""
from conftest import BUYBOX_DRY_LOG, BUYBOX_LIVE_LOG, BUYBOX_LIVE_LOG_2, BUYBOX_OFF_LOG

from app import buybox


def test_the_undercut_is_a_whole_number_of_pence_from_0_to_20():
    assert buybox.clean_undercut("1") == (1, "") and buybox.clean_undercut(" 0 ") == (0, "") and buybox.clean_undercut(20) == (20, "") and buybox.clean_undercut("07") == (7, "")
    for bad in ("21", "-1", "1.5", "", "abc", None, "100"):
        value, error = buybox.clean_undercut(bad)
        assert value is None and "whole number of pence" in error, bad


def test_the_profit_floor_is_a_percent_of_the_selling_price_from_1_to_50():
    assert buybox.clean_profit("15") == (15.0, "") and buybox.clean_profit("12,5") == (12.5, "") and buybox.clean_profit("12.5%") == (12.5, "") and buybox.clean_profit(1) == (1.0, "")
    assert buybox.clean_profit("14.999") == (15.0, "") and buybox.clean_profit("50") == (50.0, "")
    for bad in ("0.5", "51", "x", "", None, "-3"):
        value, error = buybox.clean_profit(bad)
        assert value is None and "between 1 and 50" in error or "number between" in error, bad


def test_settings_in_force_come_from_the_variables_and_fall_back_to_the_old_numbers():
    default = buybox.settings_view([])
    assert default == {"enabled": True, "undercut": 1, "profit": 15.0, "set": {"enabled": False, "undercut": False, "profit": False}, "push": False, "push_value": ""}
    variables = [{"name": "BUYBOX_DEFENSE_ENABLED", "value": "no"}, {"name": "BUYBOX_DEFENSE_UNDERCUT_PENCE", "value": "2"}, {"name": "BUYBOX_DEFENSE_PROFIT_PERCENT", "value": "12.5"},
                 {"name": "ONBUY_API_PUSH_ENABLED", "value": "TRUE"}, {"name": "FEE_MODE", "value": "category"}]
    mine = buybox.settings_view(variables)
    assert mine["enabled"] is False and mine["undercut"] == 2 and mine["profit"] == 12.5 and mine["push"] is True and all(mine["set"].values())
    for word in ("No", "0", "false", "OFF"):
        assert buybox.settings_view([{"name": "BUYBOX_DEFENSE_ENABLED", "value": word}])["enabled"] is False
    assert buybox.settings_view([{"name": "BUYBOX_DEFENSE_ENABLED", "value": "yes"}])["enabled"] is True
    broken = buybox.settings_view([{"name": "BUYBOX_DEFENSE_UNDERCUT_PENCE", "value": "lots"}, {"name": "BUYBOX_DEFENSE_PROFIT_PERCENT", "value": "200"}, {"name": "ONBUY_API_PUSH_ENABLED", "value": "maybe"}])
    assert broken["undercut"] == 1 and broken["profit"] == 15.0 and broken["set"] == {"enabled": False, "undercut": False, "profit": False} and broken["push"] is False and broken["push_value"] == "maybe"


def test_describe_cron_reads_a_daily_schedule_and_leaves_other_ones_alone():
    assert buybox.describe_cron("17 4 * * *") == "daily at 04:17 UTC" and buybox.describe_cron("26 5 * * *") == "daily at 05:26 UTC"
    assert buybox.describe_cron("0 */6 * * *") == "0 */6 * * *"


def test_parse_defense_reads_a_live_run():
    f = buybox.parse_defense(BUYBOX_LIVE_LOG)
    assert (f["with_cost"], f["protected"], f["push_enabled"], f["dry_run"]) == (4035, 13, True, False)
    assert (f["live"], f["candidates"], f["calls"], f["answers"]) == (8936, 8695, 87, 8695)
    assert f["counts"] == {"winning": 7465, "no data": 525, "cheaper-not-winning": 107, "no cost": 419, "reprice": 48, "held": 131, "restored": 3}
    assert f["pushes"][0] == {"sku": "473302857618", "price": 30.97} and f["pushes"][-1] == {"sku": "Ebay-126172742134-11", "price": 18.18} and len(f["pushes"]) == 3
    assert f["restores"] == [{"sku": "733653967719", "price": 24.44}, {"sku": "797581478891", "price": 79.45}]
    assert (f["pushed"], f["failed"], f["contested"], f["share"]) == (52, 0, 705, 85.9) and "waits" not in f and "off" not in f and "nothing_pushed" not in f


def test_parse_defense_counts_the_rate_limit_waits_and_failed_pushes():
    f = buybox.parse_defense(BUYBOX_LIVE_LOG_2)
    assert f["waits"] == 2 and (f["pushed"], f["failed"]) == (70, 2) and f["counts"]["reprice"] == 65 and f["share"] == 86.3 and "restores" not in f


def test_parse_defense_reads_a_dry_run_and_a_switched_off_run():
    dry = buybox.parse_defense(BUYBOX_DRY_LOG)
    assert dry["dry_run"] is True and dry["nothing_pushed"] is True and "pushed" not in dry and dry["counts"]["reprice"] == 70
    assert buybox.parse_defense(BUYBOX_OFF_LOG) == {"off": True}
    assert buybox.parse_defense("") == {} and buybox.winning_share({}) is None and buybox.winning_share({"candidates": 0, "counts": {"winning": 0}}) is None


def test_parse_defense_reads_the_stores_real_summary_lines():
    """The three stores' summary lines of 2026-10-26, as the runner printed them."""
    arden = buybox.parse_defense("summary: winning: 8962 | no data: 1903 | cheaper-not-winning: 26 | no cost: 273 | reprice: 6 | held: 223 | restored: 0\nlive listings: 11955 | in-stock unprotected candidates: 11393\n")
    assert arden["counts"]["winning"] == 8962 and arden["counts"]["restored"] == 0 and arden["share"] == 78.7
    yra = buybox.parse_defense("live listings: 8035 | in-stock unprotected candidates: 7953\nsummary: winning: 7118 | no data: 398 | cheaper-not-winning: 116 | no cost: 155 | reprice: 47 | held: 119 | restored: 9\npushed: 56 | failed: 0\n")
    assert yra["counts"]["held"] == 119 and yra["pushed"] == 56 and yra["share"] == 89.5


# ---- the page and its endpoints --------------------------------------------------------------------------------------------------------
def test_buybox_page_shows_the_settings_the_last_result_the_history_and_a_running_sale(web):
    r = web.get("/buybox?store=gtv")
    assert r.status_code == 200
    assert 'class="brief"' in r.text and "Buy Box defense" in r.text and "daily run: ON" in r.text and "daily at 04:17 UTC" in r.text and "prices are pushed to OnBuy" in r.text
    assert "<strong>85.9%</strong> of the 8695 listings checked" in r.text and "Lowered to win it" in r.text and "Put back after a contest" in r.text and "Cheaper, still not winning" in r.text
    assert "Prices lowered (3)" in r.text and "473302857618" in r.text and "£30.97" in r.text
    assert r.text.count("<td>daily</td>") == 4 and r.text.count("<td>manual</td>") == 1 and "switched off" in r.text and 'class="pill failed">failure' in r.text         # the five finished runs
    assert "A store sale is running until" in r.text and 'id="bbUndercut"' in r.text and 'id="bbProfit"' in r.text and "Save the settings" in r.text and "Run live now" in r.text
    assert 'value="1"' in r.text and 'value="15"' in r.text and "does not read these settings yet" not in r.text


def test_buybox_page_for_a_store_without_runs_or_the_push_switch(web):
    r = web.get("/buybox?store=yra")
    assert r.status_code == 200 and "NOT pushed (dry runs only)" in r.text and "ONBUY_API_PUSH_ENABLED</code> is not set" in r.text
    assert "No finished run with numbers yet" in r.text and "No finished run yet" in r.text and "A store sale is running" not in r.text


def test_buybox_page_warns_when_the_workflow_does_not_read_the_settings_or_is_missing(web, fake):
    del fake.definitions["buybox_defense.yml"]["inputs"]["profit_percent"]
    assert "does not read these settings yet" in web.get("/buybox?store=gtv").text
    del fake.definitions["buybox_defense.yml"]
    r = web.get("/buybox?store=gtv")
    assert r.status_code == 200 and "has no Buy Box defense workflow" in r.text and 'id="bbUndercut"' not in r.text


def variable(fake, name):
    return next((v["value"] for v in fake.variables["org/gtv"] if v["name"] == name), None)


def test_saving_the_settings_needs_valid_numbers_and_the_box_then_sets_the_three_variables(web, fake, db):
    body = {"enabled": True, "undercut_pence": "2", "profit_percent": "12.5"}
    for bad, text in (({"undercut_pence": "x"}, "whole number of pence"), ({"profit_percent": "99"}, "between 1 and 50"), ({}, "confirmation")):
        r = web.post("/api/store/gtv/buybox/settings", json={**body, **bad})
        assert r.status_code == 400 and text in r.json()["error"], (bad, r.json())
    assert variable(fake, "BUYBOX_DEFENSE_ENABLED") is None
    ok = web.post("/api/store/gtv/buybox/settings", json={**body, "enabled": False, "confirm": True})
    assert ok.status_code == 200
    assert (variable(fake, "BUYBOX_DEFENSE_ENABLED"), variable(fake, "BUYBOX_DEFENSE_UNDERCUT_PENCE"), variable(fake, "BUYBOX_DEFENSE_PROFIT_PERCENT")) == ("no", "2", "12.5")
    assert ok.json()["settings"]["enabled"] is False and ok.json()["settings"]["undercut"] == 2 and ok.json()["settings"]["profit"] == 12.5 and ok.json()["settings"]["push"] is True
    assert db.recent_audit()[0]["action"] == "buybox_settings"
    again = web.post("/api/store/gtv/buybox/settings", json={**body, "enabled": True, "profit_percent": "15", "undercut_pence": "1", "confirm": True})
    assert again.status_code == 200 and variable(fake, "BUYBOX_DEFENSE_ENABLED") == "yes" and variable(fake, "BUYBOX_DEFENSE_PROFIT_PERCENT") == "15"          # 15, not 15.0
    page = web.get("/buybox?store=gtv").text
    assert "daily run: ON" in page and 'class="pill quiet">set' in page
    assert web.post("/api/store/zzz/buybox/settings", json=body).status_code == 404


def test_a_preview_is_a_dry_run_that_can_try_other_values_for_one_run(web, fake):
    r = web.post("/api/store/gtv/buybox/run", json={"mode": "preview"})
    assert r.status_code == 200 and r.json()["live"] is False
    repo, workflow, inputs, ref = fake.dispatched[-1]
    assert (repo, workflow, inputs, ref) == ("org/gtv", "buybox_defense.yml", {"dry_run": "yes"}, "main")
    trial = web.post("/api/store/gtv/buybox/run", json={"mode": "preview", "undercut_pence": "2", "profit_percent": "12,5"})
    assert trial.status_code == 200 and fake.dispatched[-1][2] == {"dry_run": "yes", "undercut_pence": "2", "profit_percent": "12.5"}
    for bad, text in (({"undercut_pence": "50"}, "whole number of pence"), ({"profit_percent": "0"}, "between 1 and 50")):
        refused = web.post("/api/store/gtv/buybox/run", json={"mode": "preview", **bad})
        assert refused.status_code == 400 and text in refused.json()["error"]
    del fake.definitions["buybox_defense.yml"]["inputs"]["profit_percent"]
    old = web.post("/api/store/gtv/buybox/run", json={"mode": "preview", "profit_percent": "12"})
    assert old.status_code == 400 and "does not take a trial profit percent yet" in old.json()["error"]


def test_a_live_run_needs_the_box_the_push_switch_and_uses_only_the_saved_settings(web, fake):
    count = len(fake.dispatched)
    no_box = web.post("/api/store/gtv/buybox/run", json={"mode": "live"})
    assert no_box.status_code == 400 and "confirmation" in no_box.json()["error"] and len(fake.dispatched) == count
    no_push = web.post("/api/store/yra/buybox/run", json={"mode": "live", "confirm": True})                       # YRA's fake repo has no ONBUY_API_PUSH_ENABLED
    assert no_push.status_code == 400 and "ONBUY_API_PUSH_ENABLED is not true" in no_push.json()["error"] and len(fake.dispatched) == count
    ok = web.post("/api/store/gtv/buybox/run", json={"mode": "live", "confirm": True, "undercut_pence": "5", "profit_percent": "5"})
    assert ok.status_code == 200 and ok.json()["live"] is True
    assert fake.dispatched[-1][2] == {"dry_run": "no"}                                                           # trial values are for previews only
    assert web.post("/api/store/zzz/buybox/run", json={"mode": "live"}).status_code == 404


def test_run_status_parses_the_buy_box_log(web):
    facts = web.get("/api/store/gtv/run/50").json()["facts"]
    assert facts["counts"]["reprice"] == 48 and facts["share"] == 85.9 and facts["pushed"] == 52
    assert web.get("/api/store/gtv/run/53").json()["facts"] == {"off": True}
