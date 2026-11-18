"""The Delivery card: the template ids (validation, where they come from), the numbers in the delivery tool's log, and the page with its two endpoints."""
from conftest import (DELIVERY_APPLY_LOG, DELIVERY_NIGHTLY_LOG, DELIVERY_PLAN_LOG, DELIVERY_TEST_LOG, DELIVERY_WORKFLOW_BARE, DELIVERY_WORKFLOW_FALLBACKS, NOW, make_run)

from app import delivery

GTV_WORKFLOW = ("org/gtv", ".github/workflows/delivery_templates.yml")


def test_a_template_id_is_a_whole_number_without_a_leading_zero():
    assert delivery.clean_id("54810") == ("54810", "") and delivery.clean_id(" 7 ") == ("7", "") and delivery.clean_id(123456789) == ("123456789", "")
    for bad in ("0123", "1234567890", "abc", "", None, "-5", "5.5", "5 6"):
        value, error = delivery.clean_id(bad)
        assert value is None and "digits only" in error, bad


def test_the_apply_limit_defaults_and_stays_inside_its_range():
    assert delivery.clean_max_changes("") == (3000, "") and delivery.clean_max_changes(None) == (3000, "") and delivery.clean_max_changes("100") == (100, "")
    assert delivery.clean_max_changes("20000") == (20000, "") and delivery.clean_max_changes("1") == (1, "")
    for bad in ("0", "20001", "x", "-1", "1.5"):
        value, error = delivery.clean_max_changes(bad)
        assert value is None and "whole number from 1 to 20,000" in error, bad


def test_the_workflow_file_says_which_suppliers_it_takes_and_what_it_falls_back_to():
    full = delivery.read_wiring(DELIVERY_WORKFLOW_FALLBACKS)
    assert full == {"ebay": {"variable_read": True, "fallback": "54810"}, "amazon": {"variable_read": True, "fallback": "54809"}, "ali": {"variable_read": True, "fallback": "43190"}}
    assert delivery.read_wiring(DELIVERY_WORKFLOW_BARE)["ebay"] == {"variable_read": True, "fallback": ""}
    old = delivery.read_wiring("          TEMPLATE_EBAY: ${{ inputs.template_ebay }}\n          TEMPLATE_AMAZON: ${{ inputs.template_amazon }}\n")
    assert old == {"ebay": {"variable_read": False, "fallback": ""}, "amazon": {"variable_read": False, "fallback": ""}} and delivery.read_wiring("") == {}


def test_a_supplier_uses_the_saved_id_else_the_built_in_one_else_nothing():
    wiring = delivery.read_wiring(DELIVERY_WORKFLOW_FALLBACKS)
    variables = [{"name": "DELIVERY_TEMPLATE_EBAY", "value": "60001"}, {"name": "DELIVERY_TEMPLATE_AMAZON", "value": "oops"}, {"name": "FEE_MODE", "value": "flat"}]
    ids = {i["key"]: (i["id"], i["source"], i["wired"]) for i in delivery.effective_ids(variables, wiring)}
    assert ids == {"ebay": ("60001", "variable", True), "amazon": ("54809", "built in", True), "ali": ("43190", "built in", True)}       # an id that is not a number is ignored
    bare = delivery.effective_ids([], delivery.read_wiring(DELIVERY_WORKFLOW_BARE))
    assert [(i["key"], i["id"], i["source"]) for i in bare] == [("ebay", "", "none"), ("amazon", "", "none"), ("ali", "", "none")]
    two = delivery.effective_ids([], delivery.read_wiring(DELIVERY_WORKFLOW_FALLBACKS.replace("TEMPLATE_ALI", "SOMETHING_ELSE")))
    assert [i["key"] for i in two] == ["ebay", "amazon"]                                                 # a workflow without an AliExpress input has no AliExpress setting


def test_parse_templates_reads_a_plan_with_its_census_and_what_would_move():
    f = delivery.parse_templates(DELIVERY_PLAN_LOG)
    assert f["mode"] == "plan" and f["ids"] == {"ebay": "54810", "amazon": "54809", "ali": ""} and f["sheet_skus"] == {"ebay": 7508, "amazon": 2159, "none": 148}
    assert (f["swept"], f["listings"]) == (12130, 12130) and f["templates"] == {"54810": 7342, "52506": 2682, "54809": 2106} and f["handling"] == {"0": 12129, "5": 1}
    assert f["classes"]["ebay"] == {"listings": 7410, "templates": {"54810": 7340, "52506": 70}, "handling": {"0": 7410}} and set(f["classes"]) == {"ebay", "amazon", "legacy"}
    assert f["to_move"] == 75 and f["moves"] == [{"supplier": "ebay", "from": "52506", "to": "54810", "n": 70}, {"supplier": "amazon", "from": "52506", "to": "54809", "n": 5}]
    assert f["plan_only"] is True and "applied_ok" not in f and "handling_cleared" not in f
    assert delivery.headline(f) == {"state": "moves", "to_move": 75, "movable": 75, "priceless": 0, "exact": False}              # a plan cannot tell the never-live ones


def test_parse_templates_reads_the_nightlys_step_and_how_many_listings_no_run_can_move():
    f = delivery.parse_templates(DELIVERY_NIGHTLY_LOG)
    assert f["mode"] == "apply" and f["clear_handling"] is True and f["ids"] == {"ebay": "35109", "amazon": "22069", "ali": "43190"}
    assert f["semi"] == {"sheet": "Makstore_Feed_Master", "skus": 2374, "added": 2374} and f["swept"] == 12405 and f["own_handling"] == 212
    assert f["to_move"] == 158 and f["handling_cleared"] == 1 and f["priceless"] == 158 and f["nothing_to_send"] is True and "applied_ok" not in f
    assert f["moves"] == [{"supplier": "ebay", "from": "22069", "to": "35109", "n": 157}, {"supplier": "ali", "from": "22069", "to": "43190", "n": 1}]
    assert delivery.headline(f) == {"state": "ok", "to_move": 158, "movable": 0, "priceless": 158, "exact": True}                  # everything that can be moved is where it should be
    rows = {r["label"]: r for r in delivery.census_rows(f)}
    assert (rows["eBay"]["id"], rows["eBay"]["listings"], rows["eBay"]["right"], rows["eBay"]["off"]) == ("35109", 6624, 6467, 157) and rows["eBay"]["sits"] == [("35109", 6467), ("22069", 157)]
    assert (rows["AliExpress"]["right"], rows["AliExpress"]["off"]) == (1975, 1) and rows["Amazon"]["off"] == 0
    assert rows["No sheet row (legacy)"]["right"] is None and rows["No sheet row (legacy)"]["listings"] == 999
    assert [r["label"] for r in delivery.census_rows(f)] == ["eBay", "Amazon", "AliExpress", "No sheet row (legacy)"]


def test_the_census_uses_the_ids_of_the_run_and_the_settings_only_where_the_run_has_none():
    f = delivery.parse_templates(DELIVERY_PLAN_LOG)                      # this run had no AliExpress id and sheet rows of none
    settings = [{"key": "ebay", "id": "99999"}, {"key": "ali", "id": "43190"}]
    rows = delivery.census_rows(f, settings)
    assert rows[0]["id"] == "54810" and rows[0]["right"] == 7340 and len(rows) == 3                         # eBay: the run's own id wins over the setting
    assert delivery.census_rows({"classes": {"ebay": {"listings": 5, "templates": {"1": 5}, "handling": {}}}})[0]["right"] is None      # no id at all: nothing is "on" or "off"


def test_parse_templates_reads_an_apply_batch_by_batch_and_its_read_back():
    f = delivery.parse_templates(DELIVERY_APPLY_LOG)
    assert f["mode"] == "apply" and f["to_move"] == 8750 and len(f["moves"]) == 4 and f["moves"][2] == {"supplier": "ebay", "from": "54809", "to": "54810", "n": 4}
    assert f["batches"] == [{"n": 1, "http": 200, "ok": 499, "of": 499}, {"n": 2, "http": 500, "ok": 0, "of": 500}, {"n": 3, "http": 200, "ok": 498, "of": 498}]
    assert (f["applied_ok"], f["applied_failed"], f["applied_errors"]) == (7675, 1000, "'error: HTTP 500': 1000") and f["readback"] == {"ok": 11, "of": 12}
    assert "plan_only" not in f and delivery.headline(f)["state"] == "moves"


def test_parse_templates_reads_the_one_listing_test_and_a_refusal():
    f = delivery.parse_templates(DELIVERY_TEST_LOG)
    assert f["mode"] == "test" and f["test"] == {"sku": "283826373354", "supplier": "ebay", "before": "52506", "want": "54810", "after": "54810"}
    assert f["result"] == "the API accepts delivery_template_id - the template moved" and "classes" not in f and delivery.headline(f) == {"state": "unknown"}
    newer = delivery.parse_templates("283826373354: class ebay | before: template 52506 handling 0 price 9.99 stock 1 | want template 54810, handling unchanged\n")
    assert newer["test"]["want"] == "54810"
    refused = delivery.parse_templates("8751 moves exceed MAX_CHANGES=3000 - refusing\n")
    assert refused["refused"] == {"moves": 8751, "max": 3000} and delivery.parse_templates("") == {}
    assert delivery.parse_templates("WARNING: semi sheet 'X' not read (no access) - AliExpress-sourced listings cannot be recognised this run\n")["semi_warning"].startswith("semi sheet 'X' not read")


def test_older_logs_without_the_handling_part_still_parse():
    f = delivery.parse_templates("MODE plan | templates: eBay 54810, Amazon - | sheet SKUs by supplier: ***'ebay': 3***\nTO MOVE: 0 listing(s):  | handling time cleared on 0\n")
    assert f["ids"] == {"ebay": "54810", "amazon": "", "ali": ""} and f["to_move"] == 0 and "moves" not in f and f["handling_cleared"] == 0
    assert delivery.headline(f)["state"] == "ok"
    no_ids = delivery.parse_templates("MODE plan | templates: eBay -, Amazon - | sheet SKUs by supplier: ***'ebay': 3***\nTO MOVE: 0 listing(s):  | handling time cleared on 0\n")
    assert no_ids["ids"] == {"ebay": "", "amazon": "", "ali": ""} and delivery.headline(no_ids) == {"state": "noids"}      # no id = nothing was checked: not an all-clear
    assert delivery.kind_label({"path": "nightly_reconcile.yml"}, f) == "nightly" and delivery.kind_label({"path": "delivery_templates.yml"}, f) == "plan" and delivery.kind_label({}, {}) == "manual"


# ---- the page and its endpoints --------------------------------------------------------------------------------------------------------
def variable(fake, repo, name):
    return next((v["value"] for v in fake.variables.get(repo, []) if v["name"] == name), None)


def test_delivery_page_shows_the_ids_where_the_listings_sit_the_last_checks_and_the_run_forms(web):
    r = web.get("/delivery?store=gtv")
    assert r.status_code == 200
    assert 'class="brief"' in r.text and "Delivery templates" in r.text and "75 listing(s) are off their supplier's template" in r.text and "no run can move" in r.text
    assert '<strong class="warn-text">70</strong>' in r.text and "<code>54810</code>" in r.text and "ebay</code> 52506 &rarr; 54810: <strong>70</strong>" in r.text
    assert 'data-key="ebay"' in r.text and 'value="54810"' in r.text and 'value="43190"' in r.text and r.text.count(">built in<") == 3
    assert "Plan now" in r.text and "Save the ids" in r.text and 'id="dtTestSku"' in r.text and 'id="dtMax"' in r.text and "Apply</button>" in r.text
    assert "<td>plan</td>" in r.text and "<td>apply</td>" in r.text and "<td>test</td>" in r.text and "7675" in r.text and "1000 failed" in r.text
    assert "Every night this store's nightly run" not in r.text and "<td>nightly</td>" not in r.text                     # GTV has no nightly step
    yra = web.get("/delivery?store=yra")
    assert yra.status_code == 200 and r.text != yra.text and "No finished run with a census yet" in yra.text and yra.text.count(">none<") == 3 and "No run yet" in yra.text


def test_delivery_page_adds_the_nightlys_step_to_the_checks_for_stores_that_run_it(web, monkeypatch):
    monkeypatch.setattr(delivery, "IN_NIGHTLY", ("gtv",))
    r = web.get("/delivery?store=gtv")
    assert "<td>nightly</td>" in r.text and "Every night this store's nightly run also moves" in r.text and "tonight's nightly" in r.text and "manual runs and the nightly's step" in r.text


def test_delivery_page_warns_when_the_workflow_does_not_read_the_saved_ids_or_is_missing(web, fake):
    fake.files[GTV_WORKFLOW] = "          TEMPLATE_EBAY: ${{ inputs.template_ebay }}\n          TEMPLATE_AMAZON: ${{ inputs.template_amazon }}\n"
    r = web.get("/delivery?store=gtv")
    assert "does not read the saved ids yet" in r.text and 'data-key="ali"' not in r.text
    del fake.definitions["delivery_templates.yml"]
    gone = web.get("/delivery?store=gtv")
    assert gone.status_code == 200 and "has no delivery templates workflow" in gone.text and "Plan now" not in gone.text


def test_saving_ids_needs_numbers_and_the_box_then_sets_only_the_filled_variables(web, fake, db):
    body = {"ebay": "60001", "amazon": "", "ali": " 70003 "}
    for bad, text in (({"ebay": "abc"}, "eBay: A template id is the template's number"), ({"ali": "007"}, "AliExpress: A template id"), ({"ebay": "", "ali": ""}, "at least one template id"), ({}, "confirmation")):
        r = web.post("/api/store/gtv/delivery/settings", json={**body, **bad})
        assert r.status_code == 400 and text in r.json()["error"], (bad, r.json())
    assert variable(fake, "org/gtv", "DELIVERY_TEMPLATE_EBAY") is None
    ok = web.post("/api/store/gtv/delivery/settings", json={**body, "confirm": True})
    assert ok.status_code == 200
    assert variable(fake, "org/gtv", "DELIVERY_TEMPLATE_EBAY") == "60001" and variable(fake, "org/gtv", "DELIVERY_TEMPLATE_ALI") == "70003" and variable(fake, "org/gtv", "DELIVERY_TEMPLATE_AMAZON") is None
    assert ok.json()["ids"] == [{"label": "eBay", "id": "60001", "source": "variable"}, {"label": "Amazon", "id": "54809", "source": "built in"}, {"label": "AliExpress", "id": "70003", "source": "variable"}]
    assert db.recent_audit()[0]["action"] == "delivery_settings"
    assert web.post("/api/store/zzz/delivery/settings", json=body).status_code == 404


def test_a_supplier_the_workflow_has_no_input_for_cannot_be_saved(web, fake):
    fake.files[GTV_WORKFLOW] = DELIVERY_WORKFLOW_FALLBACKS.replace("TEMPLATE_ALI", "SOMETHING_ELSE")
    r = web.post("/api/store/gtv/delivery/settings", json={"ali": "70003", "confirm": True})
    assert r.status_code == 400 and "at least one template id" in r.json()["error"] and variable(fake, "org/gtv", "DELIVERY_TEMPLATE_ALI") is None
    ok = web.post("/api/store/gtv/delivery/settings", json={"ebay": "60001", "ali": "70003", "confirm": True})
    assert ok.status_code == 200 and variable(fake, "org/gtv", "DELIVERY_TEMPLATE_ALI") is None and variable(fake, "org/gtv", "DELIVERY_TEMPLATE_EBAY") == "60001"


def test_a_plan_needs_no_box_and_always_carries_the_ids_in_force(web, fake):
    r = web.post("/api/store/gtv/delivery/run", json={"mode": "plan"})
    assert r.status_code == 200 and r.json()["live"] is False
    repo, workflow, inputs, ref = fake.dispatched[-1]
    assert (repo, workflow, ref) == ("org/gtv", "delivery_templates.yml", "main") and inputs == {"mode": "plan", "template_ebay": "54810", "template_amazon": "54809", "template_ali": "43190"}
    fake.variables["org/gtv"].append({"name": "DELIVERY_TEMPLATE_EBAY", "value": "60001", "updated_at": ""})
    web.post("/api/store/gtv/delivery/run", json={"mode": "plan"})
    assert fake.dispatched[-1][2]["template_ebay"] == "60001"                                           # the saved id beats the built-in one, as in the nightly
    yra = web.post("/api/store/yra/delivery/run", json={"mode": "plan"})
    assert yra.status_code == 200 and fake.dispatched[-1][2] == {"mode": "plan"}                       # no id set: the census still runs
    assert web.post("/api/store/gtv/delivery/run", json={"mode": "bogus"}).status_code == 400


def test_a_test_moves_one_listing_and_an_apply_moves_all_both_behind_the_box(web, fake):
    count = len(fake.dispatched)
    for mode in ("test", "apply"):
        refused = web.post("/api/store/gtv/delivery/run", json={"mode": mode, "test_sku": "E1"})
        assert refused.status_code == 400 and "confirmation" in refused.json()["error"]
    assert len(fake.dispatched) == count
    for bad in ("", "E1 E2", "a#b"):
        r = web.post("/api/store/gtv/delivery/run", json={"mode": "test", "test_sku": bad, "confirm": True})
        assert r.status_code == 400 and "one SKU" in r.json()["error"], bad
    ok = web.post("/api/store/gtv/delivery/run", json={"mode": "test", "test_sku": "E1", "confirm": True})
    assert ok.status_code == 200 and ok.json()["live"] is True
    assert fake.dispatched[-1][2] == {"mode": "test", "template_ebay": "54810", "template_amazon": "54809", "template_ali": "43190", "clear_handling": "no", "test_sku": "E1"}
    apply = web.post("/api/store/gtv/delivery/run", json={"mode": "apply", "confirm": True, "max_changes": "500", "clear_handling": True})
    assert apply.status_code == 200 and apply.json()["live"] is True
    assert fake.dispatched[-1][2] == {"mode": "apply", "template_ebay": "54810", "template_amazon": "54809", "template_ali": "43190", "clear_handling": "yes", "max_changes": "500"}
    default = web.post("/api/store/gtv/delivery/run", json={"mode": "apply", "confirm": True})
    assert fake.dispatched[-1][2]["max_changes"] == "3000" and fake.dispatched[-1][2]["clear_handling"] == "no"
    for bad in ("0", "99999", "many"):
        r = web.post("/api/store/gtv/delivery/run", json={"mode": "apply", "confirm": True, "max_changes": bad})
        assert r.status_code == 400 and "whole number from 1 to 20,000" in r.json()["error"], bad


def test_a_test_or_an_apply_refuses_while_no_template_id_is_set(web, fake):
    count = len(fake.dispatched)
    for mode in ("test", "apply"):
        r = web.post("/api/store/yra/delivery/run", json={"mode": mode, "test_sku": "E1", "confirm": True})
        assert r.status_code == 400 and "No template id is set" in r.json()["error"]
    assert len(fake.dispatched) == count


def test_a_run_waits_its_turn_behind_the_slot_rule(web, fake):
    fake.pending["org/gtv"] = [make_run(500, "run.yml", "Generate OnBuy Feed", NOW, status="queued", conclusion="")]
    r = web.post("/api/store/gtv/delivery/run", json={"mode": "apply", "confirm": True})
    assert r.status_code == 400 and "waiting for the store's slot" in r.json()["error"]


def test_run_status_parses_the_delivery_logs(web):
    plan = web.get("/api/store/gtv/run/60").json()["facts"]
    assert plan["mode"] == "plan" and plan["to_move"] == 75 and plan["classes"]["amazon"]["listings"] == 2102
    apply = web.get("/api/store/gtv/run/61").json()["facts"]
    assert apply["applied_ok"] == 7675 and apply["batches"][1]["http"] == 500
    assert web.get("/api/store/gtv/run/62").json()["facts"]["test"]["after"] == "54810"


def test_delivery_page_does_not_call_a_run_without_ids_an_all_clear(web, fake):
    fake.logs[60] = DELIVERY_PLAN_LOG.replace("eBay 54810, Amazon 54809", "eBay -, Amazon -").replace("TO MOVE: 75 listing(s): ebay 52506->54810: 70, amazon 52506->54809: 5", "TO MOVE: 0 listing(s):  | handling time cleared on 0")
    r = web.get("/delivery?store=gtv")
    assert r.status_code == 200 and "That run had no template id, so it checked nothing" in r.text and "Every listing that can be moved sits" not in r.text
