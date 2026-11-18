"""The pages and the JSON endpoints against the fake GitHub client - the house rules above all."""
import json

from app.config import Settings
from app.db import Database
from app.main import create_app


def test_home_lists_stores_and_tiles(web):
    r = web.get("/")
    assert r.status_code == 200
    assert "GTV" in r.text and "YRA" in r.text and "eBay sync" in r.text and "queue empty" in r.text


def test_store_page_shows_runs_and_run_now(web):
    r = web.get("/store/gtv")
    assert r.status_code == 200
    assert "Run now" in r.text and "Amazon Sync (Keepa)" in r.text and "failure" in r.text
    assert "stale" in r.text                      # the backfill is 40 h old
    assert "Nightly (in backfill)" in r.text      # GTV's nightly lives in its backfill run; the tile says so
    assert "Purge dead eBay rows" in r.text and "Content mismatch scan" not in r.text   # only workflows the store has
    assert web.get("/store/nope", follow_redirects=False).status_code == 303


def test_run_refused_while_a_run_is_waiting(web, fake):
    fake.pending["org/gtv"] = [{"name": "Watch Recovery", "path": "watch_recovery.yml", "status": "pending"}]
    r = web.post("/api/store/gtv/run", json={"workflow": "run.yml", "inputs": {}})
    assert r.status_code == 400 and "waiting for the store's slot" in r.json()["error"]
    assert fake.dispatched == []


def test_a_run_stuck_in_the_queue_for_days_does_not_block_the_store(web, fake):
    from conftest import NOW, iso
    from datetime import timedelta
    ghost = {"name": "Makstore Full-Auto Sync", "path": "run.yml", "status": "queued", "created_at": iso(NOW - timedelta(days=66))}
    fake.pending["org/gtv"] = [ghost]
    page = web.get("/store/gtv")
    assert "stuck since" in page.text and "waiting for the slot" not in page.text
    r = web.post("/api/store/gtv/run", json={"workflow": "run.yml", "inputs": {}})
    assert r.status_code == 200 and fake.dispatched[-1][1] == "run.yml"
    fake.pending["org/gtv"] = [dict(ghost, created_at=iso(NOW - timedelta(hours=1)))]
    assert web.post("/api/store/gtv/run", json={"workflow": "run.yml", "inputs": {}}).status_code == 400


def test_a_queued_ci_run_is_not_a_run_waiting_for_the_slot(web, fake):
    """The CI tests every push starts have no concurrency group: they sit 'queued' for seconds while GitHub finds a runner. That used to refuse the sheet read that follows a list file
    the dashboard commits (GTV 2026-10-27: 'A run is already waiting for the store's slot (Tests)')."""
    from conftest import NOW, make_run
    fake.pending["org/gtv"] = [make_run(900, "tests.yml", "Tests", NOW, status="queued", conclusion="")]
    fake.in_progress["org/gtv"] = [make_run(901, "tests.yml", "Tests", NOW, status="in_progress", conclusion="")]
    page = web.get("/store/gtv")
    assert "waiting for the slot" not in page.text and "Tests" not in page.text.split("Recent runs")[0]
    r = web.post("/api/store/gtv/run", json={"workflow": "run.yml", "inputs": {}})
    assert r.status_code == 200 and fake.dispatched[-1][1] == "run.yml" and not r.json().get("warning")
    fake.pending["org/gtv"] = [make_run(902, "tests.yml", "Tests", NOW, status="queued", conclusion=""), make_run(903, "run.yml", "Generate OnBuy Feed", NOW, status="queued", conclusion="")]
    refused = web.post("/api/store/gtv/run", json={"workflow": "run.yml", "inputs": {}})
    assert refused.status_code == 400 and "Generate OnBuy Feed" in refused.json()["error"] and "Tests" not in refused.json()["error"]       # a real waiting run still blocks


def test_dangerous_live_run_needs_the_confirmation_box(web, fake):
    r = web.post("/api/store/gtv/run", json={"workflow": "purge_dead_rows.yml", "inputs": {"dry_run": "no"}})
    assert r.status_code == 400 and "confirmation box" in r.json()["error"]
    assert fake.dispatched == []
    ok = web.post("/api/store/gtv/run", json={"workflow": "purge_dead_rows.yml", "inputs": {"dry_run": "yes"}})
    assert ok.status_code == 200 and ok.json()["live"] is False         # a dry run needs no box
    live = web.post("/api/store/gtv/run", json={"workflow": "purge_dead_rows.yml", "inputs": {"dry_run": "no"}, "confirm": True})
    assert live.status_code == 200 and live.json()["live"] is True
    assert [d[1] for d in fake.dispatched] == ["purge_dead_rows.yml", "purge_dead_rows.yml"]


def test_run_warns_when_it_queues_behind_a_running_sync(web, fake, db):
    fake.in_progress["org/gtv"] = [{"name": "Generate OnBuy Feed", "path": "run.yml", "status": "in_progress"}]
    r = web.post("/api/store/gtv/run", json={"workflow": "orders_lookup.yml", "inputs": {"sku": "NONE", "list_all": "yes", "unknown": "x"}})
    body = r.json()
    assert r.status_code == 200 and "wait behind Generate OnBuy Feed" in body["warning"]
    assert body["run"]["path"] == "orders_lookup.yml"
    assert fake.dispatched[-1][2] == {"sku": "NONE", "list_all": "yes"}        # unknown inputs dropped
    recorded = db.recent_dispatches("gtv")[0]
    assert recorded["workflow"] == "orders_lookup.yml" and recorded["run_id"] == body["run"]["id"]
    assert db.recent_audit()[0]["action"] == "run"


def test_required_input_missing_is_refused(web):
    r = web.post("/api/store/gtv/run", json={"workflow": "orders_lookup.yml", "inputs": {}})
    assert r.status_code == 400 and "'sku' is required" in r.json()["error"]


def test_run_status_returns_facts_for_a_finished_orders_lookup(web):
    r = web.get("/api/store/gtv/run/8")
    body = r.json()
    assert r.status_code == 200 and body["run"]["id"] == 8
    assert body["facts"]["count"] == 3 and body["facts"]["due_today"] == 1
    assert any("ORDER-LINE" in l or "DONE" in l for l in body["lines"])


def test_daily_check_page(web):
    r = web.get("/daily?hours=24")
    assert r.status_code == 200
    assert "Daily check" in r.text and "Not green" in r.text and "Amazon Sync (Keepa)" in r.text
    assert "ZEROED 203648462166" in r.text or "203648462166" in r.text
    assert "Ama-B0BRHJTQZ6-5" in r.text                 # the borderline left for a decision
    assert "T6QPP5J" in r.text                          # orders from the fresh lookup


def test_orders_page_and_refresh_form(web):
    r = web.get("/orders")
    assert r.status_code == 200 and "T6N77VB" in r.text and "overdue" in r.text and "Refresh" in r.text


def test_tools_page_groups_by_area_and_serves_definitions(web):
    r = web.get("/tools?store=gtv")
    assert r.status_code == 200 and "Catalogue hygiene" in r.text and "Purge dead eBay rows" in r.text
    d = web.get("/api/store/gtv/workflow/purge_dead_rows.yml").json()
    assert d["risk"] == "danger" and d["apply_input"] == "dry_run" and d["inputs"]["dry_run"]["default"] == "yes"
    assert web.get("/api/store/gtv/workflow/missing.yml").status_code == 502


def test_settings_and_variables(web, fake, db):
    r = web.get("/settings")
    assert r.status_code == 200 and "tester" in r.text and "org/gtv" in r.text
    assert web.get("/api/store/gtv/variables").json()["variables"][0]["name"] == "FEE_MODE"
    refused = web.post("/api/store/gtv/variables", json={"name": "FEE_MODE", "value": "flat"})
    assert refused.status_code == 400
    ok = web.post("/api/store/gtv/variables", json={"name": "fee_mode", "value": "flat", "confirm": True})
    assert ok.status_code == 200 and fake.variables["org/gtv"][0]["value"] == "flat"
    assert db.recent_audit()[0]["action"] == "set_variable"
    bad = web.post("/api/store/gtv/variables", json={"name": "bad name!", "value": "x", "confirm": True})
    assert bad.status_code == 400


def test_github_errors_become_messages_not_crashes(web, fake):
    fake.fail_repo = "org/yra"
    r = web.get("/")
    assert r.status_code == 200 and "Bad credentials" in r.text
    assert web.get("/daily").status_code == 200
    assert web.get("/api/store/yra/variables").status_code == 502


def test_pricing_page_shows_the_code_schedule_and_the_window(web):
    r = web.get("/pricing?store=gtv")
    assert r.status_code == 200
    assert "code constants" in r.text and "under £5" in r.text and "above £50" in r.text
    assert "£10 to £20" in r.text and "Profit % by price range" in r.text           # GTV's range (10-20 -> 15%), editable
    assert 'id="windows"' in r.text and "Add a price range" in r.text and "/sale?store=gtv" in r.text
    flat = web.get("/pricing?store=yra")                                             # the mechanism is on every store now, empty until a range is set
    assert flat.status_code == 200 and "above £30" in flat.text and 'id="windows"' in flat.text and "No price range has its own profit" in flat.text


def test_pricing_page_prefers_the_setting_when_set(web, fake):
    fake.variables["org/gtv"].append({"name": "PROFIT_SCHEDULE", "value": '{"bands": [[5, 60], [null, 30]]}', "updated_at": ""})
    r = web.get("/pricing?store=gtv")
    assert "dashboard setting" in r.text and "under £5" in r.text and "above £5" in r.text and "60" in r.text


def test_pricing_preview_runs_a_dry_run_with_the_proposed_schedule(web, fake):
    r = web.post("/api/store/gtv/pricing/preview", json={"bands": [[5, 60], [None, 30]], "overrides": [[10, 20, 15]]})
    body = r.json()
    assert r.status_code == 200 and body["run"]["path"] == "even_margins.yml" and body["live"] is False
    repo, workflow, inputs, _ = fake.dispatched[-1]
    assert workflow == "even_margins.yml" and inputs["apply"] == "no" and inputs["max_changes"] == "20000"
    sent = json.loads(inputs["schedule_json"])
    assert sent["bands"] == [[5.0, 60.0], [None, 30.0]] and sent["sell_price_overrides"] == [[10.0, 20.0, 15.0]]
    assert sent["superseded"][-1] == [[5.0, 100.0], [10.0, 80.0], [50.0, 40.0], [None, 20.0]]     # the outgoing code schedule
    assert fake.variables["org/gtv"][-1]["name"] != "PROFIT_SCHEDULE"                             # a preview sets nothing
    bad = web.post("/api/store/gtv/pricing/preview", json={"bands": [[5, 60], [3, 30]]})
    assert bad.status_code == 400 and "last band" in bad.json()["error"]


def test_pricing_apply_needs_the_box_then_sets_the_variable_and_runs_apply(web, fake, db):
    refused = web.post("/api/store/gtv/pricing/apply", json={"bands": [[5, 60], [None, 30]]})
    assert refused.status_code == 400 and "confirmation box" in refused.json()["error"]
    fake.pending["org/gtv"] = [{"name": "Amazon Sync (Keepa)", "path": "run_amazon.yml", "status": "pending"}]
    waiting = web.post("/api/store/gtv/pricing/apply", json={"bands": [[5, 60], [None, 30]], "confirm": True})
    assert waiting.status_code == 400 and "waiting" in waiting.json()["error"]
    fake.pending["org/gtv"] = []
    ok = web.post("/api/store/gtv/pricing/apply", json={"bands": [[5, 60], [None, 30]], "confirm": True})
    body = ok.json()
    assert ok.status_code == 200 and body["live"] is True and body["run"]["path"] == "even_margins.yml"
    setting = next(v for v in fake.variables["org/gtv"] if v["name"] == "PROFIT_SCHEDULE")
    assert json.loads(setting["value"])["bands"] == [[5.0, 60.0], [None, 30.0]]
    assert fake.dispatched[-1][2]["apply"] == "yes" and fake.dispatched[-1][2]["schedule_json"] == setting["value"]
    actions = [a["action"] for a in db.recent_audit()]
    assert "set_variable" in actions and "run" in actions
    # the page now shows the setting, and a second change keeps the first one as superseded
    assert "dashboard setting" in web.get("/pricing?store=gtv").text
    web.post("/api/store/gtv/pricing/apply", json={"bands": [[5, 70], [None, 35]], "confirm": True})
    latest = json.loads(next(v for v in fake.variables["org/gtv"] if v["name"] == "PROFIT_SCHEDULE")["value"])
    assert [[5.0, 60.0], [None, 30.0]] in latest["superseded"]


def test_even_margins_facts_in_the_run_status(web, fake):
    from conftest import NOW, make_run
    run = make_run(99, "even_margins.yml", "Even Margins (dry run / apply)", NOW, event="workflow_dispatch")
    fake.runs["org/gtv"].insert(0, run)
    fake.logs[99] = "DRY RUN | top band profit 20%\n=== Sheet1 (eBay pricing): 10 rows with a SKU | lower 2, ok 8\nTOTAL: 2 price(s) to change, 0 held for review\n"
    body = web.get("/api/store/gtv/run/99").json()
    assert body["facts"]["to_change"] == 2 and body["facts"]["lower"] == 2 and body["facts"]["mode"] == "dry run"


def test_fees_page_shows_the_model_the_tables_and_the_latest_runs(web):
    r = web.get("/fees?store=gtv")
    assert r.status_code == 200
    assert "category tables" in r.text                                   # FEE_MODE=category in the fake variables
    assert "Consumer Electronics" in r.text and "8.4%" in r.text         # the committed tiers with the VAT-inclusive rate
    assert "refresh_fees run 34346220435" in r.text and "09 Sep 11:40Z" in r.text   # the commit that holds the tables
    assert "612227390835" in r.text and "18.00" in r.text                # the under-charged row and its target Fee %
    assert "7549" in r.text and "tables differ" in r.text and "462 categories gone" in r.text
    assert "15% x56" in r.text                                           # the probe's per-tier summary
    assert "Baby &amp; Toddler" in r.text and "8/15 above 10" in r.text   # the census exposure table
    assert "Never run on this store" in r.text                           # the relabel has no run yet
    assert "3D Printer Filament" in r.text                               # the built-in relabel rules
    assert 'name="commit"' in r.text and 'name="apply"' in r.text
    yra = web.get("/fees?store=yra")
    assert yra.status_code == 200 and "flat 20%" in yra.text and "could not be read" in yra.text


def test_fee_mode_endpoint_validates_and_sets_both_variables(web, fake, db):
    bad = web.post("/api/store/gtv/fees/mode", json={"mode": "cheap", "tier_mode": "marginal", "confirm": True})
    assert bad.status_code == 400
    refused = web.post("/api/store/gtv/fees/mode", json={"mode": "flat", "tier_mode": "step"})
    assert refused.status_code == 400 and "confirmation box" in refused.json()["error"]
    ok = web.post("/api/store/gtv/fees/mode", json={"mode": "flat", "tier_mode": "step", "confirm": True})
    assert ok.status_code == 200
    values = {v["name"]: v["value"] for v in fake.variables["org/gtv"]}
    assert values["FEE_MODE"] == "flat" and values["FEE_TIER_MODE"] == "step"
    assert db.recent_audit()[0]["action"] == "set_variable"
    assert "flat 20%" in web.get("/fees?store=gtv").text


def test_fee_runs_need_the_box_only_when_they_write(web, fake):
    dry = web.post("/api/store/gtv/run", json={"workflow": "observed_fee_feedback.yml", "inputs": {"apply": "no", "days": "90"}})
    assert dry.status_code == 200 and dry.json()["live"] is False
    live = web.post("/api/store/gtv/run", json={"workflow": "observed_fee_feedback.yml", "inputs": {"apply": "yes"}})
    assert live.status_code == 400 and "confirmation box" in live.json()["error"]
    compare = web.post("/api/store/gtv/run", json={"workflow": "refresh_fees.yml", "inputs": {"commit": "no"}})
    assert compare.status_code == 200 and compare.json()["live"] is False
    commit = web.post("/api/store/gtv/run", json={"workflow": "refresh_fees.yml", "inputs": {"commit": "yes"}})
    assert commit.status_code == 400
    facts = web.get("/api/store/gtv/run/31").json()["facts"]              # the finished feedback dry run, parsed for the result box
    assert facts["under"] == 2 and facts["rows"][0]["target"] == "18.00"


def sale_body(**change):
    from conftest import IN_3_DAYS
    body = {"ranges": [["0", "9.99", "5"], ["10", "20", ""], ["20.01", "", "3"]], "sale_end": IN_3_DAYS, "min_profit": "10", "floor_mode": "skip", "scope": "all"}
    body.update(change)
    return body


def test_sale_page_shows_the_running_sale_the_last_run_and_the_range_editor(web):
    r = web.get("/sale?store=gtv")
    assert r.status_code == 200
    assert "running" in r.text and "3% off every listing except £10 to £20" in r.text and "7938" in r.text            # GTV's own state file, written before price ranges existed
    assert "Cancel the sale" in r.text and 'id="sranges"' in r.text and r.text.count('class="srow"') == 5            # the usual brackets, ready to type a % into
    assert 'id="saleEnd"' in r.text and "Preview" in r.text and "Apply the sale" in r.text
    assert "£0 to £9.99" in r.text and "kept out" in r.text and "26,000.00" in r.text and "Under floor" in r.text      # the last run's per-range table
    yra = web.get("/sale?store=yra")
    assert yra.status_code == 200 and "No store sale is running" in yra.text and "Nothing has run on this store yet" in yra.text and "Cancel the sale" not in yra.text


def test_a_newer_failed_sale_run_is_named_but_the_last_good_numbers_stay(web, fake):
    from datetime import timedelta
    from conftest import NOW, make_run
    fake.runs["org/gtv"].insert(0, make_run(36, "store_sale.yml", "Store Sale (one click on / off)", NOW - timedelta(minutes=5), conclusion="failure", event="workflow_dispatch"))
    text = web.get("/sale?store=gtv").text
    assert "A newer run ended with" in text and "failure" in text and "£0 to £9.99" in text and "26,000.00" in text


def test_started_from_here_catches_up_with_runs_that_finished_after_the_page_was_left(web, fake, db):
    from conftest import NOW
    web.post("/api/store/gtv/sale/plan", json=sale_body())
    first = db.recent_dispatches("gtv")[0]
    assert first["status"] == "queued"                                  # the page that started it was closed before the run finished
    fake.runs["org/gtv"][0].update(status="completed", conclusion="success")
    assert "success" in web.get("/sale?store=gtv").text
    assert db.recent_dispatches("gtv")[0]["status"] == "success" and db.dispatch(first["id"])["status"] == "success"
    assert "success" in web.get("/store/gtv").text


def test_sale_preview_runs_a_plan_with_the_ranges_and_changes_nothing(web, fake, db):
    r = web.post("/api/store/gtv/sale/plan", json=sale_body())
    body = r.json()
    assert r.status_code == 200 and body["live"] is False and body["run"]["path"] == "store_sale.yml"
    repo, workflow, inputs, _ = fake.dispatched[-1]
    assert workflow == "store_sale.yml" and inputs["mode"] == "plan" and inputs["price_ranges"] == "[[0.0,9.99,5.0],[10.0,20.0,0.0],[20.01,null,3.0]]"
    assert inputs["min_profit"] == "10" and inputs["floor_mode"] == "skip" and inputs["scope"] == "all" and "max_changes" not in inputs
    assert db.recent_dispatches("gtv")[0]["inputs"]["mode"] == "plan"


def test_sale_apply_needs_the_box_and_an_empty_slot_then_records_who_pressed_it(web, fake, db):
    refused = web.post("/api/store/gtv/sale/apply", json=sale_body())
    assert refused.status_code == 400 and "confirmation box" in refused.json()["error"] and fake.dispatched == []
    fake.pending["org/gtv"] = [{"name": "Amazon Sync (Keepa)", "path": "run_amazon.yml", "status": "pending"}]
    waiting = web.post("/api/store/gtv/sale/apply", json=sale_body(confirm=True))
    assert waiting.status_code == 400 and "waiting for the store's slot" in waiting.json()["error"] and fake.dispatched == []
    fake.pending["org/gtv"] = []
    ok = web.post("/api/store/gtv/sale/apply", json=sale_body(confirm=True, floor_mode="cap", scope="in_stock"))
    assert ok.status_code == 200 and ok.json()["live"] is True
    _, _, inputs, _ = fake.dispatched[-1]
    assert inputs["mode"] == "apply" and inputs["max_changes"] == "20000" and inputs["floor_mode"] == "cap" and inputs["scope"] == "in_stock"
    assert [a["action"] for a in db.recent_audit()][0] == "run"


def test_sale_cancel_and_test_need_the_box(web, fake):
    assert web.post("/api/store/gtv/sale/cancel", json={}).status_code == 400
    cancel = web.post("/api/store/gtv/sale/cancel", json={"confirm": True})
    assert cancel.status_code == 200 and fake.dispatched[-1][2] == {"mode": "cancel"}
    assert web.post("/api/store/gtv/sale/test", json=sale_body(test_sku="123")).status_code == 400
    tested = web.post("/api/store/gtv/sale/test", json=sale_body(test_sku="123", confirm=True))
    assert tested.status_code == 200 and fake.dispatched[-1][2]["test_sku"] == "123" and fake.dispatched[-1][2]["mode"] == "test"
    assert web.post("/api/store/nope/sale/plan", json=sale_body()).status_code == 404


def test_sale_refuses_bad_ranges_and_dates_before_anything_is_queued(web, fake):
    for change, text in (({"ranges": []}, "at least one"), ({"ranges": [["0", "9", ""]]}, "nothing would go on sale"), ({"ranges": [["5", "1", "3"]]}, "below the low"),
                         ({"sale_end": "2020-01-01"}, "past"), ({"sale_end": ""}, "last day"), ({"min_profit": "900"}, "margin floor")):
        r = web.post("/api/store/gtv/sale/plan", json=sale_body(**change))
        assert r.status_code == 400 and text in r.json()["error"], (change, r.json())
    assert fake.dispatched == []


def test_the_running_sale_shows_on_the_home_and_store_pages_and_the_run_facts_are_parsed(web):
    assert "sale until" in web.get("/").text and "sale until" in web.get("/store/gtv").text
    facts = web.get("/api/store/gtv/run/35").json()["facts"]
    assert facts["mode"] == "plan" and facts["ranges"][1]["sale"] == "kept out" and facts["on_sale_after"] == 7500
    d = web.get("/api/store/gtv/workflow/store_sale.yml").json()
    assert d["risk"] == "danger" and d["apply_input"] == "mode"
    from app import catalog
    assert [catalog.is_live_request("mode", {"mode": m}) for m in ("plan", "test", "apply", "cancel", "refresh")] == [False, True, True, True, True]


def test_password_gate_when_configured(stores, fake, tmp_path):
    from fastapi.testclient import TestClient
    settings = Settings(github_token="t", stores=stores, data_dir=tmp_path, dashboard_password="secret-pass")
    client = TestClient(create_app(settings=settings, client=fake, database=Database(":memory:")))
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/login")
    assert client.post("/api/store/gtv/run", json={"workflow": "run.yml"}, headers={"Accept": "application/json"}).status_code == 401
    assert client.get("/healthz").status_code == 200
    wrong = client.post("/login", data={"password": "nope", "next": "/"})
    assert "not the password" in wrong.text
    good = client.post("/login", data={"password": "secret-pass", "next": "/store/gtv"}, follow_redirects=False)
    assert good.status_code == 303 and good.headers["location"] == "/store/gtv"
    assert client.get("/store/gtv").status_code == 200
    client.get("/logout")
    assert client.get("/", follow_redirects=False).status_code == 303
