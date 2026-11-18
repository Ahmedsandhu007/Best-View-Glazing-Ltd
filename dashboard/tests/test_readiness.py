"""Store readiness on Settings (2026-11-02): one answer for "what does this store still need" - the usual secrets that are
missing, the secret/variable names most of the fleet carries that this store lacks, and the parked workflows with an
enable/park button. Built for the moment right after "Add a store": Kidoomi arrived with six secrets, no variables and
eight workflows parked, and every card failed in its own quiet way."""
from app import readiness


def test_majority_rule_keeps_one_store_oddities_quiet():
    others = {"a": {"EUR_PER_GBP"}, "b": set(), "c": set(), "d": set()}
    assert readiness.gaps(set(), others) == []                                            # 1 of 4 siblings is no expectation
    others["b"].add("EUR_PER_GBP")
    assert readiness.gaps(set(), others) == [{"name": "EUR_PER_GBP", "held_by": 2}]       # half of 4 = expected
    assert readiness.gaps({"EUR_PER_GBP"}, others) == []                                  # already carried = no gap


def test_fleet_value_is_offered_only_on_exact_agreement():
    others = {"a": {"KEEPA_DROP_HOLD_PERCENT": "40"}, "b": {"KEEPA_DROP_HOLD_PERCENT": "40"},
              "c": {"SHEET_NAME": "A_Master"}, "d": {"SHEET_NAME": "B_Master"}}
    assert readiness.fleet_value("KEEPA_DROP_HOLD_PERCENT", others) == "40"
    assert readiness.fleet_value("SHEET_NAME", others) == ""                              # per-store values are typed, never copied


def test_report_splits_expected_secrets_from_fleet_gaps_and_sorts_parked_first():
    mine = {"secrets": {"ONBUY_CONSUMER_KEY"}, "variables": {},
            "workflows": [{"path": "run.yml", "name": "Sync", "state": "active"},
                          {"path": "buybox_defense.yml", "name": "Buy Box", "state": "disabled_manually"}]}
    others = {"a": {"secrets": {"ONBUY_CONSUMER_KEY", "EBAY_CLIENT_ID"}, "variables": {"PURGE_DEAD_ROWS": "1"}}}
    out = readiness.report(mine, others, ("ONBUY_CONSUMER_KEY", "KEEPA_API_KEY"))
    assert out["secrets_missing"] == ["KEEPA_API_KEY"]                                    # the fixed list, in its own box
    assert out["secret_gaps"] == [{"name": "EBAY_CLIENT_ID", "held_by": 1}]               # the fleet's extras separately
    assert out["variable_gaps"] == [{"name": "PURGE_DEAD_ROWS", "held_by": 1, "value": "1"}]
    assert [w["path"] for w in out["workflows"]][0] == "buybox_defense.yml"               # parked first
    assert out["parked"][0]["path"] == "buybox_defense.yml" and not out["ready"]


def test_the_readiness_api_compares_a_store_against_its_siblings(web, fake):
    fake.variables["org/gtv"].append({"name": "KEEPA_DROP_HOLD_PERCENT", "value": "40", "updated_at": "2026-10-27T00:00:00Z"})
    fake.workflow_states[("org/yra", "buybox_defense.yml")] = "disabled_manually"
    data = web.get("/api/stores/yra/readiness").json()
    assert data["repo"] == "org/yra" and data["compared_against"] == ["gtv"]
    assert "ONBUY_CONSUMER_KEY" in data["secrets_missing"]                                # yra's fake repo has no secrets at all
    assert {"name": "KEEPA_DROP_HOLD_PERCENT", "held_by": 1, "value": "40"} in data["variable_gaps"]
    assert [w["path"] for w in data["parked"]] == ["buybox_defense.yml"] and not data["ready"]
    assert web.get("/api/stores/nope/readiness").status_code == 404


def test_the_workflow_switch_needs_the_confirmation_and_flips_the_state(web, fake):
    fake.workflow_states[("org/yra", "buybox_defense.yml")] = "disabled_manually"
    refused = web.post("/api/stores/yra/workflows", json={"path": "buybox_defense.yml", "action": "enable"})
    assert refused.status_code == 400 and "confirmation" in refused.json()["error"]
    assert fake.workflow_states[("org/yra", "buybox_defense.yml")] == "disabled_manually"

    ok = web.post("/api/stores/yra/workflows", json={"path": "buybox_defense.yml", "action": "enable", "confirm": True}).json()
    assert ok == {"ok": True, "path": "buybox_defense.yml", "state": "active"}
    assert fake.workflow_states[("org/yra", "buybox_defense.yml")] == "active"
    parked = web.post("/api/stores/yra/workflows", json={"path": "buybox_defense.yml", "action": "disable", "confirm": True}).json()
    assert parked["state"] == "disabled_manually"

    assert web.post("/api/stores/yra/workflows", json={"path": "../evil.yml", "action": "enable", "confirm": True}).status_code == 400
    assert web.post("/api/stores/yra/workflows", json={"path": "nope.yml", "action": "enable", "confirm": True}).status_code == 400
    assert web.post("/api/stores/yra/workflows", json={"path": "run.yml", "action": "pause", "confirm": True}).status_code == 400


def test_the_settings_page_carries_the_card_and_the_script_drives_it(web):
    text = web.get("/settings").text
    assert "Store readiness" in text and 'id="readiness"' in text
    js = web.get("/static/app.js?v=1").text
    assert "loadReadiness" in js and "rdWorkflow" in js
