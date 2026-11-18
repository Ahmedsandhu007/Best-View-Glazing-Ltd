"""The Amazon card's page and its settings endpoint, on the fake GitHub (the Amazon runs carry the REAL logs of tests/amazon_data.py)."""
from datetime import timedelta

from amazon_data import CENSUS_LOG, MAKSTORE_LOG, NEGATIVE_BALANCE_LOG, ONE_ROW_LOG, YRA_FAILED_LOG
from conftest import AMAZON_WORKFLOW_TEXT, NOW, make_run

from app import amazon

GOOD, FAILED, SMALL, CENSUS = 70, 71, 72, 80


def add_runs(fake, newest_failed=False):
    """A big good sync 2 h ago, one that ran out of Keepa tokens 8 h ago (or 1 h ago when `newest_failed`), a manual sync of ONE row 30 minutes ago, and a seller count."""
    failed_at = NOW - timedelta(hours=1 if newest_failed else 8)
    fake.runs["org/gtv"] = [make_run(SMALL, "run_amazon.yml", "Amazon Sync (Keepa)", NOW - timedelta(minutes=30), event="workflow_dispatch"),
                            make_run(GOOD, "run_amazon.yml", "Amazon Sync (Keepa)", NOW - timedelta(hours=2)),
                            make_run(FAILED, "run_amazon.yml", "Amazon Sync (Keepa)", failed_at, conclusion="failure"),
                            make_run(CENSUS, "amazon_seller_census.yml", "Amazon Seller Census (read-only)", NOW - timedelta(days=1), event="workflow_dispatch")] + fake.runs["org/gtv"]
    fake.logs.update({GOOD: MAKSTORE_LOG, FAILED: YRA_FAILED_LOG, SMALL: ONE_ROW_LOG, CENSUS: CENSUS_LOG})


def page(web):
    r = web.get("/amazon?store=gtv")
    assert r.status_code == 200
    return r.text


def save(web, values=None, **kw):
    return web.post("/api/store/gtv/amazon/settings", json={"values": values or {}, **kw})


# ---- the page ---------------------------------------------------------------------------------------------------------------------
def test_the_page_shows_the_last_good_sync_its_keepa_tokens_and_what_the_guards_did(web, fake):
    add_runs(fake)
    text = page(web)
    assert "last good sync" in text and "1,941 tokens used (about 1.21 per product)" in text and "waited 38 min for the refill" in text
    assert "Priced from the usual level" in text and ">467<" in text and "Priced from the Buy Box" in text and "Second looks at the Buy Box" in text
    assert "Read as unavailable: only Amazon's own, unbuyable offer" in text and "B08PL4XKKR" in text and "Delayed (Amazon&#39;s own offer only)" in text
    assert '195 <span class="muted">updated</span>' in text and "43 brand-blocked rows were flagged, not pushed" in text           # the OnBuy pushes of the run
    assert '<span class="pill quiet" title="GitHub often starts a scheduled run a few hours late">13 0-20/4 * * *</span>' in text   # the schedule pill


def test_the_last_good_sync_is_a_real_one_not_a_manual_run_for_a_single_row(web, fake):
    add_runs(fake)                                    # the newest finished run is a manual sync of one row (1 token); the big one ran 2 h ago
    text = page(web)
    assert "1,941 tokens used" in text and "1 tokens used" not in text.replace("1,941 tokens used", "")
    history = text.split("The last syncs")[-1]
    assert history.count("manual") >= 1 and ">1<" in history                                              # the one-row run is still in the table of runs
    fake.runs["org/gtv"] = []
    add_runs(fake, newest_failed=True)
    assert "ran out of Keepa tokens</strong> and left 2,216 Amazon rows" in page(web)                    # a one-row success after a failure does not make up for it


def test_a_sync_that_ended_overdrawn_on_keepa_is_still_the_last_good_sync(web, fake):
    add_runs(fake)
    fake.logs[GOOD] = NEGATIVE_BALANCE_LOG                                              # YRA's real log: the balance went to -108 and the run ended at -12
    text = page(web)
    assert "2,786 tokens used" in text and "-12 left at the end" in text and "last good sync" in text and "1,941 tokens used" not in text


def test_the_biggest_price_falls_are_listed_and_a_big_one_is_marked(web, fake):
    add_runs(fake)
    text = page(web)
    assert "Prices the last sync lowered" in text and "327210340093" in text and "£227.65" in text and "£117.22" in text and "-48.5%" in text
    assert "1 fell by 25% or more" in text and 'class="bad-text">-48.5%' in text
    assert "The sync writes a line only for a fall" in text


def test_a_sync_that_ran_out_of_tokens_is_a_banner_only_while_no_good_sync_came_after_it(web, fake):
    add_runs(fake)                                    # the failure is 8 h old, a good sync ran 2 h ago
    text = page(web)
    assert "ran out of Keepa tokens</strong>" not in text and "out of tokens: 2,216 rows left as they were" in text      # still in the table of runs
    fake.runs["org/gtv"] = []
    add_runs(fake, newest_failed=True)                # now the failure is the newest
    text = page(web)
    assert "ran out of Keepa tokens</strong> and left 2,216 Amazon rows exactly as they were" in text


def test_the_settings_start_at_the_syncs_own_defaults(web, fake):
    text = page(web)
    for phrase in ("default 40", "default on", "default off", "default 100", "default 300", 'id="amz_drop_hold"', 'id="amz_own_only"', "Hold a price that falls below this share of the usual level",
                   "Only Amazon&#39;s own offer counts as in stock"):
        assert phrase in text, phrase
    assert ">strict stock rule ON</span>" not in text and "stock rule: Amazon or any seller" in text


def test_a_strict_rule_that_is_on_is_shown_in_the_pill_and_a_set_value_is_marked(web, fake):
    fake.variables["org/gtv"] += [{"name": "AMAZON_OWN_OFFER_ONLY", "value": "yes"}, {"name": "KEEPA_DROP_HOLD_PERCENT", "value": "25"}, {"name": "KEEPA_REAL_PRICE_MAX", "value": "lots"}]
    text = page(web)
    assert ">strict stock rule ON</span>" in text and 'value="25"' in text and ('stored text "lots" is unreadable' in text or "stored text &#34;lots&#34; is unreadable" in text)


def test_a_setting_the_stores_workflow_does_not_pass_on_is_locked(web, fake):
    fake.files[("org/gtv", ".github/workflows/run_amazon.yml")] = AMAZON_WORKFLOW_TEXT.replace("KEEPA_BUYBOX: ${{ vars.KEEPA_BUYBOX }}", "")
    text = page(web)
    assert "not read by this store's sync" in text and text.count("not read by this store's sync") == 1
    writes = save(web, {"buybox": True}, confirm=True)
    assert writes.status_code == 200 and writes.json()["written"] == {} and fake.variables["org/gtv"] == [v for v in fake.variables["org/gtv"] if v["name"] != "KEEPA_BUYBOX"]


def test_the_seller_count_is_shown_with_what_the_strict_rule_would_do(web, fake):
    add_runs(fake)
    text = page(web)
    assert "Count the sellers" in text and "3rd party (lowest New)" in text and "2,236" in text and "2,793" in text and "80.1%" in text
    assert "Your last seller count: 2,236 of 2,793 live rows (80.1%) would go to stock 0." in text


def test_the_seller_count_button_starts_a_read_only_run_and_its_result_is_parsed(web, fake):
    add_runs(fake)

    def finish(f, repo, workflow, inputs, run):
        f.logs[run["id"]] = CENSUS_LOG
        f.script[run["id"]] = [{"status": "completed", "conclusion": "success"}]           # the run is finished the first time anybody looks at it
    fake.on_dispatch = finish
    r = web.post("/api/store/gtv/run", json={"workflow": "amazon_seller_census.yml", "inputs": {"sample": "15"}})
    assert r.status_code == 200 and r.json()["live"] is False and fake.dispatched[-1][1] == "amazon_seller_census.yml"
    facts = web.get(f"/api/store/gtv/run/{r.json()['run']['id']}").json()["facts"]
    assert facts["would_zero"] == 2236 and facts["would_zero_share"] == 80.1 and facts["sellers"][1]["seller"] == "Amazon"


def test_a_store_without_the_amazon_workflow_says_so(web, fake):
    for name in ("run_amazon.yml", "amazon_seller_census.yml"):
        fake.definitions.pop(name)
    assert "has no Amazon sync workflow" in page(web)


# ---- saving -----------------------------------------------------------------------------------------------------------------------
def test_a_save_needs_the_box_and_writes_nothing_without_it(web, fake):
    r = save(web, {"drop_hold": "25"})
    assert r.status_code == 400 and "confirmation box" in r.json()["error"]
    assert not any(v["name"] == "KEEPA_DROP_HOLD_PERCENT" for v in fake.variables["org/gtv"])


def test_a_save_writes_only_the_values_that_changed_and_is_logged(web, fake, db):
    r = save(web, {"drop_hold": "25", "real_lookup": True, "own_only": False, "real_max": "100", "max_products": "1600"}, confirm=True)
    body = r.json()
    assert r.status_code == 200 and body["written"] == {"KEEPA_DROP_HOLD_PERCENT": "25", "AMAZON_MAX_PRODUCTS_PER_RUN": "1600"}
    stored = {v["name"]: v["value"] for v in fake.variables["org/gtv"]}
    assert stored["KEEPA_DROP_HOLD_PERCENT"] == "25" and stored["AMAZON_MAX_PRODUCTS_PER_RUN"] == "1600" and "KEEPA_REAL_PRICE_LOOKUP" not in stored and "AMAZON_OWN_OFFER_ONLY" not in stored
    by_key = {s["key"]: s for s in body["settings"]}
    assert by_key["drop_hold"]["value"] == 25.0 and by_key["drop_hold"]["set"] and by_key["max_products"]["value"] == 1600
    assert [a["action"] for a in db.recent_audit(store="gtv")][0] == "amazon_settings"
    again = save(web, {"drop_hold": "25", "max_products": "1600"}, confirm=True).json()
    assert again["written"] == {} and "Nothing changed" in again["note"]


def test_an_unreadable_value_is_refused_with_the_name_of_the_setting(web, fake):
    for key, bad in (("drop_hold", "95"), ("real_max", "0"), ("max_products", "100000"), ("own_only", "perhaps")):
        r = save(web, {key: bad}, confirm=True)
        assert r.status_code == 400 and amazon.BY_KEY[key]["label"] in r.json()["error"], (key, bad)
    assert fake.variables["org/gtv"] == [v for v in fake.variables["org/gtv"] if v["name"] in ("FEE_MODE", "ONBUY_API_PUSH_ENABLED")]


def test_switching_the_strict_stock_rule_on_needs_its_own_second_box(web, fake):
    refused = save(web, {"own_only": True}, confirm=True)
    assert refused.status_code == 400 and "second box" in refused.json()["error"] and not any(v["name"] == "AMAZON_OWN_OFFER_ONLY" for v in fake.variables["org/gtv"])
    ok = save(web, {"own_only": True}, confirm=True, confirm_strict=True)
    assert ok.status_code == 200 and ok.json()["written"] == {"AMAZON_OWN_OFFER_ONLY": "yes"}
    off = save(web, {"own_only": False}, confirm=True)                 # switching it OFF is the safe direction: one box is enough
    assert off.status_code == 200 and off.json()["written"] == {"AMAZON_OWN_OFFER_ONLY": "no"}


def test_a_github_error_on_save_is_a_502_not_a_crash(web, fake):
    fake.fail_repo = "org/gtv"
    r = save(web, {"drop_hold": "25"}, confirm=True)
    assert r.status_code == 502 and web.post("/api/store/nope/amazon/settings", json={}).status_code == 404


# ---- the Keepa plan card (2026-10-29) ----------------------------------------------------------------------------------------------------
def test_the_keepa_plan_card_shows_every_store_and_the_fleet_line(web, fake):
    add_runs(fake)
    text = page(web)
    assert 'id="keepaPlan"' in text and "The Keepa plan" in text
    assert text.index("keepaPlan") < text.index("GTV</strong>") and "YRA" in text[text.index("keepaPlan"):]
    assert "Across the" in text and "minutes a day spent waiting" in text                 # GTV's MAKSTORE_LOG sync gives the fleet line data
    assert "under 100 rows a run - no refill waiting worth counting" in text               # YRA has no amazon runs wired in this fixture
    assert "At double the rate" in text and "if the syncs never overlapped" in text
