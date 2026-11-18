"""The Delete card: the pasted list, what is kept out of it, the file and inputs the removal tool gets, the plan that must come first, and the numbers in the tool's log."""
from datetime import datetime, timedelta, timezone

from conftest import GUARDED_LIVE_LOG, GUARDED_PLAN_LOG, NOW, TODAY, make_run

from app import deletion

ORDER_SKUS = ["0145936976019", "303553980790", "304285306230"]            # the three orders of the canned orders lookup
HELD_SKU = "856689732127"                                                  # on GTV's hold lists in the canned files


# ---- the list ---------------------------------------------------------------------------------------------------------------------------
def test_parse_pasted_reads_lines_commas_and_spaces_and_counts_the_repeats():
    skus, pasted, error = deletion.parse_pasted("a1, b2\nc3  a1\n\n")
    assert (skus, pasted, error) == (["a1", "b2", "c3"], 4, "")
    assert deletion.parse_pasted(["x", "y", "x"]) == (["x", "y"], 3, "")
    for bad, text in (("", "at least one"), (None, "at least one"), ("ok # note", "not a SKU"), (",".join(f"s{i}" for i in range(2001)), "At most 2,000")):
        skus, pasted, error = deletion.parse_pasted(bad)
        assert skus is None and pasted == 0 and text in error, (bad, error)
    assert deletion.parse_pasted(",".join(f"s{i}" for i in range(2000)))[2] == ""


def test_keep_out_removes_hold_list_skus_and_open_orders_whatever_their_leading_zeros():
    skus = ["111", HELD_SKU, "0145936976019", "222", "303553980790"]
    keep, held, orders = deletion.keep_out(skus, [HELD_SKU, "Ebay-1-1"], ORDER_SKUS)
    assert keep == ["111", "222"] and held == [HELD_SKU] and orders == ["0145936976019", "303553980790"]
    keep, held, orders = deletion.keep_out(["145936976019", "0856689732127"], [HELD_SKU], ["0145936976019"])         # the order says 0145..., the list 145...: the same SKU
    assert keep == [] and held == ["0856689732127"] and orders == ["145936976019"]
    both = deletion.keep_out(["x"], ["x"], ["x"])
    assert both == ([], ["x"], [])                                                                    # counted once, as held
    assert deletion.keep_out([], [], []) == ([], [], [])


def test_the_fingerprint_names_the_list_not_its_order_and_the_path_carries_it():
    a, b = deletion.fingerprint(["1", "2", "3"]), deletion.fingerprint(["3", "1", "2"])
    assert a == b and len(a) == 10 and a != deletion.fingerprint(["1", "2"])
    path = deletion.list_path("gtv", "2026-10-26", a)
    assert path == f"cleanup/dashboard/gtv_delete_2026-10-26_{a}.txt" and deletion.path_fingerprint(path) == a
    assert deletion.path_fingerprint("cleanup/other_list.txt") == "" and deletion.path_fingerprint(None) == ""
    text = deletion.list_text("GTV", ["b", "a"], "2026-10-26")
    assert text.splitlines()[0].startswith("# GTV: 2 SKU(s) to remove") and text.splitlines()[1:] == ["a", "b"] and text.endswith("\n")


def test_backup_tab_names_are_cleaned_for_google_sheets():
    assert deletion.clean_backup_tab("", "2026-10-26") == "Removed 2026-10-26"
    assert deletion.clean_backup_tab("  Removed [brand] 10/26: x?* ", "2026-10-26") == "Removed brand 1026 x"
    assert len(deletion.clean_backup_tab("x" * 100, "2026-10-26")) == 60
    assert deletion.clean_backup_tab("[]*?:/\\", "2026-10-26") == "Removed 2026-10-26"


def test_the_inputs_ask_for_the_list_only_and_cap_the_plan_at_its_size():
    plan = deletion.build_inputs("cleanup/dashboard/x_0123456789.txt", 12, "Removed 2026-10-26", False, True)
    assert plan == {"oos_list_file": "cleanup/dashboard/x_0123456789.txt", "allow_in_stock": "no", "remove_live_dups": "no", "remove_dead_copies": "no",
                    "require_keeper_synced": "yes", "max_remove": "12", "backup_tab": "Removed 2026-10-26", "dry_run": "yes"}
    real = deletion.build_inputs("p_0123456789.txt", 0, "T", True, False)
    assert real["dry_run"] == "no" and real["allow_in_stock"] == "yes" and real["max_remove"] == "1"


def test_find_plan_wants_a_finished_dry_run_of_this_list_with_these_options_from_the_last_day():
    now = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
    fp = deletion.fingerprint(["1", "2"])

    def row(**kw):
        inputs = {"oos_list_file": f"cleanup/dashboard/gtv_delete_2026-10-26_{fp}.txt", "dry_run": "yes", "backup_tab": "Removed 2026-10-26", "allow_in_stock": "no"}
        inputs.update(kw.pop("inputs", {}))
        return {"workflow": "dup_removal.yml", "status": "success", "at": "2026-10-26T06:00:00Z", "inputs": inputs, **kw}

    assert deletion.find_plan([row()], fp, "Removed 2026-10-26", False, now)["status"] == "success"
    assert deletion.find_plan([row(status="queued")], fp, "Removed 2026-10-26", False, now) is None              # not finished
    assert deletion.find_plan([row(status="failure")], fp, "Removed 2026-10-26", False, now) is None
    assert deletion.find_plan([row(inputs={"dry_run": "no"})], fp, "Removed 2026-10-26", False, now) is None     # a real run is not a plan
    assert deletion.find_plan([row()], deletion.fingerprint(["1"]), "Removed 2026-10-26", False, now) is None    # another list
    assert deletion.find_plan([row()], fp, "Removed other", False, now) is None                                  # another backup tab
    assert deletion.find_plan([row()], fp, "Removed 2026-10-26", True, now) is None                              # planned without the in-stock switch
    assert deletion.find_plan([row(inputs={"allow_in_stock": "yes"})], fp, "Removed 2026-10-26", True, now) is not None
    assert deletion.find_plan([row(at="2026-10-25T11:00:00Z")], fp, "Removed 2026-10-26", False, now) is None    # 25 h old
    assert deletion.find_plan([row(at="2026-10-25T13:00:00Z")], fp, "Removed 2026-10-26", False, now) is not None  # 23 h old
    assert deletion.find_plan([row(workflow="remove_wrong_content.yml")], fp, "Removed 2026-10-26", False, now) is None
    assert deletion.find_plan([], fp, "x", False, now) is None


# ---- the tool's log ---------------------------------------------------------------------------------------------------------------------
def test_parse_guarded_reads_a_plan_with_held_rows_and_unlisted_skus():
    f = deletion.parse_guarded(GUARDED_PLAN_LOG)
    assert (f["listed"], f["mode"], f["in_stock_ok"], f["never"], f["tabs"]) == (8, "dry run", False, 26, {"Sheet1": 5153, "Amazon": 3629})
    assert f["planned"] == 5 and f["will_remove"] == [{"n": 1, "tab": "Amazon", "reason": "listed (out of stock)"}, {"n": 4, "tab": "Sheet1", "reason": "listed (out of stock)"}]
    assert (f["live"], f["in_stock"], f["held"], f["absent"], f["onbuy_list"]) == (4, 0, 2, 1, 6)
    assert f["held_reasons"][0] == {"n": 1, "tab": "Sheet1", "why": "back in stock  since the list was made"}
    assert f["held_rows"][0] == {"tab": "Sheet1", "row": 262, "sku": "634439213559", "stock": "52", "created": True, "why": "back in stock (stock 52) since the list was made"}
    assert f["held_rows"][1]["why"].startswith("excluded (open order / protected SKU)") and f["nothing_changed"]
    assert len(f["held_rows"]) == 2                                                                   # the "kept:" lines after the plan are not held rows
    assert "deleted" not in f and "onbuy" not in f and "suspended" not in f


def test_parse_guarded_reads_a_real_run_its_backup_and_what_onbuy_answered():
    f = deletion.parse_guarded(GUARDED_LIVE_LOG)
    assert f["mode"] == "live" and (f["listed"], f["planned"], f["deleted"], f["still_on_sheet"]) == (3, 3, 3, 0) and "in_stock_ok" not in f
    assert f["backup"] == {"rows": 3, "tab": "Removed 2026-10-26"} and f["will_remove"][1] == {"n": 2, "tab": "Sheet1", "reason": "listed (out of stock)"}
    assert f["onbuy"] == {"gone": 1, "ok": 1, "suspended": 1, "other error": 2} and f["suspended"] == ["305812347721"]
    assert f["already_gone"] == ["772793799866"] and f["errors"] == [{"sku": "859123422103", "why": "HTTP 500 the platform went away"}]      # "already removed" is not an error
    assert "held_rows" not in f and "nothing_changed" not in f


def test_parse_guarded_reads_the_explicit_order_header_and_a_refusal():
    header = "listed SKUs: 930 | in-stock rows of the list: REMOVED too (explicit order) | live duplicates: off | dead copies: off | LIVE RUN"
    f = deletion.parse_guarded(header + "\nWILL REMOVE 930 row(s):\n    930  Sheet1  | listed (in stock - explicit order)\n")
    assert f["in_stock_ok"] is True and f["listed"] == 930 and f["will_remove"][0]["reason"] == "listed (in stock - explicit order)"
    yra = deletion.parse_guarded("listed SKUs: 1 | live duplicates: off | LIVE RUN\n")                  # YRA's older header has no dead-copies part
    assert yra["listed"] == 1 and yra["mode"] == "live"
    refused = deletion.parse_guarded("plan removes 5 rows, above MAX_REMOVE=3 - refusing\n")
    assert refused["refused"] == {"rows": 5, "max": 3}
    assert deletion.parse_guarded("nothing to remove\n") == {"nothing": True} and deletion.parse_guarded("") == {}


def test_parse_guarded_reads_the_stores_real_logs_of_the_explicit_list_runs():
    """The 2026-10-08 GTV run that removed 742 rows (cut down: the lines the parser reads, as the runner printed them)."""
    real = """
listed SKUs: 742 | live duplicates: off | dead copies: off | LIVE RUN
product rows: ***'Sheet1': 5153, 'Amazon': 3629***
never removed (open orders / protected): 26 SKU(s) | keeper must be Synced: yes

WILL REMOVE 742 row(s):
    123  Amazon  | listed (out of stock)
    619  Sheet1  | listed (out of stock)
  of which live on OnBuy (created=TRUE): 727 | in stock at this moment: 0

HELD BACK 0 row(s):

listed SKUs not on the sheet (OnBuy may still hold them): 0
OnBuy delete list: 742 SKU(s) -> onbuy_delete_list.txt
backup verified: 742 row(s) written to 'Removed 2026-10-08'
DELETED 742 of 742 planned row(s) from the sheet
VERIFY: 0 removed SKU(s) still on the sheet
INFO DONE in 11 request(s): 58 gone, 682 ok, 2 other error
WARNING ERROR 772793799866: Listing is already removed
WARNING ERROR 859123422103: Listing is already removed
"""
    f = deletion.parse_guarded(real)
    assert (f["listed"], f["planned"], f["deleted"], f["live"], f["held"], f["absent"]) == (742, 742, 742, 727, 0, 0)
    assert f["onbuy"] == {"gone": 58, "ok": 682, "other error": 2} and f["already_gone"] == ["772793799866", "859123422103"] and "errors" not in f


# ---- the page and its endpoints --------------------------------------------------------------------------------------------------------
def post(web, path, **body):
    return web.post(f"/api/store/gtv/delete/{path}", json=body)


def test_delete_page_shows_the_list_form_the_open_orders_and_the_hold_lists(web):
    r = web.get("/delete?store=gtv")
    assert r.status_code == 200
    assert "Delete by list" in r.text and 'id="delSkus"' in r.text and "Plan (dry run)" in r.text and 'id="delApply"' in r.text and " disabled>Delete for real" in r.text
    assert f"Removed {TODAY}" in r.text and "3 order(s) awaiting dispatch (3 SKUs)" in r.text and "Hold lists: 5 SKUs" in r.text
    assert "Started from here" not in r.text and "more than a day old" not in r.text
    yra = web.get("/delete?store=yra")
    assert yra.status_code == 200 and "No orders lookup has finished on this store yet" in yra.text and "Hold lists: 0 SKUs" in yra.text


def test_delete_page_explains_a_store_whose_tool_cannot_take_a_list(web, fake):
    for key in ("oos_list_file", "allow_in_stock"):
        del fake.definitions["dup_removal.yml"]["inputs"][key]
    r = web.get("/delete?store=gtv")
    assert r.status_code == 200 and "no oos_list_file / allow_in_stock input yet" in r.text and 'id="delSkus"' not in r.text
    plan = post(web, "plan", skus="111")
    assert plan.status_code == 400 and "removes duplicates only" in plan.json()["error"] and not fake.dispatched


def test_delete_page_warns_when_the_open_order_data_is_too_old(web, fake):
    for r in fake.runs["org/gtv"]:
        if r["path"] == "orders_lookup.yml":
            r["created_at"] = (NOW - timedelta(hours=30)).isoformat().replace("+00:00", "Z")
    assert "more than a day old" in web.get("/delete?store=gtv").text


def test_check_keeps_hold_list_skus_and_open_orders_out_and_counts_the_repeats(web, fake):
    r = post(web, "check", skus=f"111, 222\n{HELD_SKU} 303553980790 111 0145936976019")
    assert r.status_code == 200
    body = r.json()
    assert (body["count"], body["unique"], body["pasted"]) == (2, 5, 6)
    assert body["held"] == [HELD_SKU] and body["on_orders"] == ["303553980790", "0145936976019"] and body["held_count"] == 1 and body["on_orders_count"] == 2
    assert body["orders_count"] == 3 and body["orders_hours"] is not None and body["orders_hours"] < 3 and body["backup_tab"] == f"Removed {TODAY}"
    assert not fake.edits and not fake.dispatched                                                    # checking writes nothing and starts nothing


def test_check_refuses_an_empty_list_a_bad_sku_and_a_list_with_nothing_left(web):
    for skus, text in (("", "at least one"), ("a#b", "not a SKU"), (f"{HELD_SKU} 303553980790", "Nothing is left to delete")):
        r = post(web, "check", skus=skus)
        assert r.status_code == 400 and text in r.json()["error"], (skus, r.json())
    assert web.post("/api/store/zzz/delete/check", json={"skus": "a"}).status_code == 404


def test_plan_commits_the_list_and_starts_a_dry_run_of_exactly_it(web, fake, db):
    r = post(web, "plan", skus="222\n111\n" + HELD_SKU, backup_tab="")
    assert r.status_code == 200
    body = r.json()
    fp = deletion.fingerprint(["111", "222"])
    path = f"cleanup/dashboard/gtv_delete_{TODAY}_{fp}.txt"
    assert body["list"]["path"] == path and body["list"]["changed"] is True and body["list"]["url"] == f"https://github.com/org/gtv/blob/main/{path}"
    assert fake.files[("org/gtv", path)].splitlines()[1:] == ["111", "222"] and fake.edits[0][:2] == ("org/gtv", path)
    assert body["count"] == 2 and body["held_count"] == 1 and body["live"] is False and body["run"]
    repo, workflow, inputs, ref = fake.dispatched[-1]
    assert (repo, workflow, ref) == ("org/gtv", "dup_removal.yml", "main")
    assert inputs == {"oos_list_file": path, "allow_in_stock": "no", "remove_live_dups": "no", "remove_dead_copies": "no", "require_keeper_synced": "yes", "max_remove": "2",
                      "backup_tab": f"Removed {TODAY}", "dry_run": "yes"}
    assert db.recent_audit()[0]["action"] == "delete_plan" and "delete plan" in db.recent_dispatches("gtv")[0]["note"]
    again = post(web, "plan", skus="111 222")
    assert again.status_code == 200 and again.json()["list"]["changed"] is False and len(fake.edits) == 1          # the same list is the same file


def test_plan_passes_the_in_stock_switch_and_the_backup_tab_on(web, fake):
    r = post(web, "plan", skus="111", backup_tab="Removed brand ban", allow_in_stock=True)
    assert r.status_code == 200
    inputs = fake.dispatched[-1][2]
    assert inputs["allow_in_stock"] == "yes" and inputs["backup_tab"] == "Removed brand ban" and inputs["max_remove"] == "1"


def test_plan_refuses_while_a_run_waits_for_the_slot_but_keeps_the_saved_list(web, fake):
    fake.pending["org/gtv"] = [make_run(500, "run.yml", "Generate OnBuy Feed", NOW, status="queued", conclusion="")]
    r = post(web, "plan", skus="111")
    assert r.status_code == 400 and "waiting for the store's slot" in r.json()["error"] and not fake.dispatched
    assert len(fake.edits) == 1                                                                      # the list file is harmless: the next plan finds it unchanged


def finish_last_run(fake, conclusion="success"):
    run = fake.runs["org/gtv"][0]
    run["status"], run["conclusion"] = "completed", conclusion
    return run


def test_delete_for_real_needs_the_box_a_finished_plan_of_this_list_and_fresh_orders(web, fake, db):
    body = {"skus": "111 222", "backup_tab": ""}
    no_box = post(web, "apply", **body)
    assert no_box.status_code == 400 and "confirmation" in no_box.json()["error"]
    no_plan = post(web, "apply", **body, confirm=True)
    assert no_plan.status_code == 400 and "no finished plan" in no_plan.json()["error"]
    assert post(web, "plan", **body).status_code == 200
    still_queued = post(web, "apply", **body, confirm=True)                                           # the plan has not finished yet
    assert still_queued.status_code == 400 and "no finished plan" in still_queued.json()["error"]
    finish_last_run(fake, "failure")
    assert "no finished plan" in post(web, "apply", **body, confirm=True).json()["error"]              # a plan that failed is no plan
    count = len(fake.dispatched)
    assert post(web, "plan", **body).status_code == 200
    finish_last_run(fake)
    other_list = post(web, "apply", skus="111 222 333", confirm=True)
    assert other_list.status_code == 400 and "no finished plan" in other_list.json()["error"]
    other_option = post(web, "apply", **body, confirm=True, allow_in_stock=True)
    assert other_option.status_code == 400 and "no finished plan" in other_option.json()["error"]
    assert len(fake.dispatched) == count + 1                                                          # nothing real was started by any of these
    ok = post(web, "apply", **body, confirm=True)
    assert ok.status_code == 200 and ok.json()["live"] is True and ok.json()["list"]["path"].endswith(f"_{deletion.fingerprint(['111', '222'])}.txt")
    inputs = fake.dispatched[-1][2]
    assert inputs["dry_run"] == "no" and inputs["oos_list_file"] == fake.dispatched[-2][2]["oos_list_file"] and inputs["max_remove"] == "2" and inputs["remove_live_dups"] == "no"
    assert db.recent_audit()[0]["action"] == "delete_apply" and "delete for real" in db.recent_dispatches("gtv")[0]["note"]


def test_delete_for_real_is_refused_when_the_open_order_data_is_too_old(web, fake):
    assert post(web, "plan", skus="111").status_code == 200
    finish_last_run(fake)
    for r in fake.runs["org/gtv"]:
        if r["path"] == "orders_lookup.yml":
            r["created_at"] = (NOW - timedelta(hours=30)).isoformat().replace("+00:00", "Z")
    count = len(fake.dispatched)
    r = post(web, "apply", skus="111", confirm=True)
    assert r.status_code == 400 and "more than a day old" in r.json()["error"] and len(fake.dispatched) == count


def test_delete_for_real_is_refused_when_an_order_arrived_for_a_listed_sku_after_the_plan(web, fake):
    assert post(web, "plan", skus="111 303553980790x").status_code == 200                              # 303553980790x is not an ordered SKU: it stays in the list
    finish_last_run(fake)
    fake.runs["org/gtv"].insert(0, make_run(90, "orders_lookup.yml", "Orders Lookup (read-only)", NOW, event="workflow_dispatch"))          # a newer lookup that shows the new order
    fake.logs[90] = fake.logs[8] + "ORDER-LINE T6QZZZZ | Awaiting Dispatch | 2026-10-26 09:00:00 | SKUs ['303553980790x'] | dispatch by ['" + TODAY + " 22:59:59']\n"
    r = post(web, "apply", skus="111 303553980790x", confirm=True)                                     # now the SKU is on an open order: the list changes, so the plan no longer fits
    assert r.status_code == 400 and "no finished plan" in r.json()["error"]


def test_run_status_parses_the_removal_tools_logs(web):
    plan = web.get("/api/store/gtv/run/40").json()["facts"]
    assert plan["mode"] == "dry run" and plan["planned"] == 5 and plan["held"] == 2 and plan["absent"] == 1
    live = web.get("/api/store/gtv/run/41").json()["facts"]
    assert live["deleted"] == 3 and live["suspended"] == ["305812347721"] and live["backup"]["tab"] == "Removed 2026-10-26"


def test_started_from_here_lists_the_plans_and_runs_with_their_lists(web, fake):
    assert post(web, "plan", skus="111 222").status_code == 200
    page = web.get("/delete?store=gtv").text
    assert "Started from here" in page and "plan (dry run)" in page and f"gtv_delete_{TODAY}_{deletion.fingerprint(['111', '222'])}.txt" in page and f"github.com/org/gtv/blob/main/cleanup/dashboard/" in page
