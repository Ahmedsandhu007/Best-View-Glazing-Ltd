"""The catalogue card: the hold lists (read, merge, edit) and the numbers in the purge and removal logs - the pure functions on the stores' own file excerpts."""
from conftest import (HOLD_TEXT, NOW, PROTECTED_TEXT, PURGE_DRY_LOG, PURGE_LOG, PURGE_SUSPENDED_LOG, REMOVAL_LIVE_LOG, REMOVAL_LOG, SAME_TEXT, TODAY, make_run)

from app import catalogue
from app.github_client import GitHubError

AMA = "Ama-B0BRHJTQZ6-5"
AMA_LINE = f"{AMA}  # Amazon row 772: row = zoerbufan Toe Separators, 3 Pairs, Soft Silic | page = Toe Separators [3 Pair], Toe Stretcher for Ov"


def test_split_skus_reads_commas_spaces_and_lines_and_refuses_junk():
    assert catalogue.split_skus("a1, b2\nc3  a1") == (["a1", "b2", "c3"], "")
    assert catalogue.split_skus(["x", " y ", "x"]) == (["x", "y"], "")
    for bad, text in (("", "at least one"), (None, "at least one"), ("ok # note", "not a SKU"), ("x" * 81, "not a SKU"), (",".join(f"s{i}" for i in range(101)), "At most")):
        skus, error = catalogue.split_skus(bad)
        assert skus is None and text in error, (bad, error)


def test_skus_match_with_or_without_leading_zeros():
    assert catalogue.same_sku("0145936976019", "145936976019") and catalogue.same_sku("Ama-B0BRHJTQZ6-5", " Ama-B0BRHJTQZ6-5 ")
    assert not catalogue.same_sku("0000049897678-Messam", "49897678") and not catalogue.same_sku("", "") and not catalogue.same_sku("a", "b")


def test_parse_list_dates_each_line_from_the_header_above_it_or_from_its_own_note():
    entries = {e["sku"]: e for e in catalogue.parse_list(PROTECTED_TEXT)}
    assert list(entries) == ["773086105845", "Ebay-125275026740-13", "653709952448", "856689732127", AMA]
    assert entries["773086105845"]["since"] == "" and entries["773086105845"]["note"] == ""            # under the file's opening comments: no date
    assert entries["653709952448"]["since"] == "2026-09-22" and entries["653709952448"]["reason"].startswith("source OOS on page")      # its own date beats the 2026-09-04 header
    assert entries["856689732127"]["since"] == "2026-10-16" and "ANOTHER product" in entries["856689732127"]["reason"]
    assert entries[AMA]["since"] == "2026-10-22"                                                       # the nearest dated comment above, not the one before it
    assert catalogue.parse_list("") == [] and catalogue.parse_list("# only comments\n\n# 2026-10-01 here\n") == []


def test_split_note_reads_where_the_row_and_the_page():
    note = "Amazon row 772: row = zoerbufan Toe Separators, 3 Pairs, Soft Silic | page = Toe Separators [3 Pair], Toe Stretcher for Ov"
    assert catalogue.split_note(note) == {"where": "Amazon row 772", "row": "zoerbufan Toe Separators, 3 Pairs, Soft Silic", "page": "Toe Separators [3 Pair], Toe Stretcher for Ov"}
    assert catalogue.split_note("2026-09-22 source OOS on page") == catalogue.split_note("") == {"where": "", "row": "", "page": ""}


def test_merge_holds_lists_every_frozen_listing_once_newest_first_with_what_holds_it():
    merged = catalogue.merge_holds(HOLD_TEXT, PROTECTED_TEXT, SAME_TEXT, overlaps={AMA: 0.44})
    assert [m["sku"] for m in merged] == [AMA, "856689732127", "653709952448", "Ebay-125275026740-13", "773086105845"]
    ama = merged[0]
    assert ama["in_hold"] and ama["in_protected"] and not ama["same_listed"] and ama["overlap"] == 0.44 and ama["since"] == "2026-10-22"
    assert (ama["where"], ama["row"][:9], ama["page"][:9]) == ("Amazon row 772", "zoerbufan", "Toe Separ")
    old = merged[-1]
    assert not old["in_hold"] and old["in_protected"] and old["since"] == "" and old["overlap"] is None and old["row"] == ""
    listed = catalogue.merge_holds(HOLD_TEXT, PROTECTED_TEXT, SAME_TEXT + AMA + "\n")
    assert next(m for m in listed if m["sku"] == AMA)["same_listed"]
    assert catalogue.merge_holds("", "") == []


def test_merge_holds_treats_a_leading_zero_as_the_same_listing():
    merged = catalogue.merge_holds("0145936976019  # Sheet1 row 5: row = a | page = b\n", "145936976019\n")
    assert len(merged) == 1 and merged[0]["in_hold"] and merged[0]["in_protected"] and merged[0]["row"] == "a"


def test_remove_skus_drops_only_the_named_lines_and_keeps_every_comment():
    new, removed = catalogue.remove_skus(HOLD_TEXT, [AMA])
    assert removed == [AMA] and AMA not in new and "856689732127" in new
    assert [line for line in HOLD_TEXT.splitlines() if line not in new.splitlines()] == [AMA_LINE]
    assert new.endswith("\n") and new.count("\n") == HOLD_TEXT.count("\n") - 1
    same, none = catalogue.remove_skus(PROTECTED_TEXT, ["757763636464"])                                # only named in a comment: nothing to drop
    assert same == PROTECTED_TEXT and none == []
    zeros, got = catalogue.remove_skus("0145936976019  # note\nx1\n", ["145936976019"])
    assert zeros == "x1\n" and got == ["0145936976019"]
    assert catalogue.remove_skus("", ["a"]) == ("", [])


def test_add_skus_appends_a_dated_block_skips_what_is_listed_and_parses_back():
    header = catalogue.freeze_header("2026-10-26", "supplier out of stock")
    new, added = catalogue.add_skus(HOLD_TEXT, [AMA, "0000049897678-Messam", "111"], header, {"111": "a note"})
    assert added == ["0000049897678-Messam", "111"]                                                      # Ama is already on the list
    assert new.startswith(HOLD_TEXT) and new.endswith(f"# {header}\n0000049897678-Messam\n111  # a note\n")
    assert catalogue.add_skus(new, ["111", "0000049897678-Messam"], header) == (new, [])
    parsed = {e["sku"]: e for e in catalogue.parse_list(new)}
    assert parsed["111"]["since"] == "2026-10-26" and parsed["111"]["note"] == "a note" and "supplier out of stock" in parsed["111"]["reason"]
    assert catalogue.add_skus("# only a comment", ["x"], "h") == ("# only a comment\n# h\nx\n", ["x"])
    assert catalogue.add_skus("", ["x"], "h") == ("# h\nx\n", ["x"])
    title = "A row title that is longer than fifty characters, really it is"
    same, _ = catalogue.add_skus(SAME_TEXT, ["y"], catalogue.same_header("2026-10-26"), {"y": catalogue.same_note({"row": title, "note": "n"})})
    assert same.endswith(f"\ny  # {title[:50]}\n") and catalogue.same_note({"note": "kept"}) == "kept"


def test_parse_purge_reads_the_last_syncs_numbers():
    f = catalogue.parse_purge(PURGE_LOG)
    assert (f["mode"], f["tab"], f["max_rows"], f["max_checks"]) == ("live", "eBay", 200, 40)
    assert (f["rows"], f["brand"], f["oos"], f["held_back"]) == (4210, 3, 17, 4)
    assert f["held"] == [{"rows": 3, "why": "protected listing (protected_skus.txt)"}, {"rows": 1, "why": "open order (awaiting dispatch)"}]
    assert (f["ebay_gone"], f["ebay_alive"], f["ebay_unknown"]) == (12, 2, 3) and f["to_delete"] == 15 and f["deleted"] == 15
    assert (f["done"], f["done_brand"], f["done_oos"], f["suspended_count"], f["onbuy_errors"]) == (15, 3, 12, 1, 0)
    assert f["suspended"] == [{"sku": "305812347721", "title": "Women Waterproof Walking Shoes Lightweight Sneakers"}]            # printed once, not twice
    tail = catalogue.parse_purge("PURGE DONE: 4 row(s) removed (brand 1, out of stock 3); suspended on OnBuy 2; OnBuy errors 1\n")
    assert tail == {"done": 4, "done_brand": 1, "done_oos": 3, "suspended_count": 2, "onbuy_errors": 1}


def test_parse_purge_dry_runs_the_suspended_list_and_an_empty_sync():
    dry = catalogue.parse_purge(PURGE_DRY_LOG)
    assert dry["mode"] == "dry run" and dry["to_delete"] == 15 and dry["nothing_changed"] and "done" not in dry and "deleted" not in dry
    listed = catalogue.parse_purge(PURGE_SUSPENDED_LOG)
    assert listed["suspended_total"] == 2 and [s["sku"] for s in listed["suspended"]] == ["305812347721", "Ebay-174409866283-2"]
    empty = catalogue.parse_purge("DRY RUN | tab 'eBay' | kinds brand,oos | max 200 rows, 250 eBay checks\neBay tab: 900 rows | looking dead: brand-blocked 0, out of stock 0 | held back 0\nnothing to purge\n")
    assert empty["nothing"] and empty["rows"] == 900 and "suspended" not in empty and "held" not in empty
    assert catalogue.parse_purge("") == {}


def test_parse_removal_reads_the_plan_the_held_back_and_the_dry_run():
    f = catalogue.parse_removal(REMOVAL_LOG)
    assert (f["asked"], f["mode"], f["planned"], f["nothing_changed"]) == (2, "dry run", 1, True)
    assert f["will_remove"] == [{"tab": "Amazon", "row": 772, "sku": AMA, "sheet_stock": "5", "onbuy_stock": "0", "opc": "1234567890", "overlap": 0.44,
                                 "row_title": "zoerbufan Toe Separators, 3 Pairs, Soft Silic", "page_name": "Toe Separators [3 Pair], Toe Stretcher for Ov"}]
    assert f["held_back"] == [{"sku": "856689732127", "why": "the OnBuy page now matches the row (word overlap 0.80) - not wrong content"}]
    assert catalogue.deleted_skus(f) == []                                                               # a dry run deleted nothing


def test_parse_removal_reads_a_live_run_with_its_suspended_listing():
    f = catalogue.parse_removal(REMOVAL_LIVE_LOG)
    assert f["mode"] == "live" and (f["deleted"], f["planned"], f["still_on_sheet"], f["hold_lines_dropped"]) == (1, 1, 0, 2)
    assert f["onbuy"] == {"suspended": 1} and f["suspended"] == ["856689732127"] and "held_back" not in f and "errors" not in f
    assert catalogue.deleted_skus(f) == ["856689732127"]
    tally = catalogue.parse_removal("INFO DONE in 3 request(s): 28 ok, 2 gone, 1 suspended, 4 other error\nWARNING ERROR s9: error: HTTP 500 server went away\n")
    assert tally["onbuy"] == {"ok": 28, "gone": 2, "suspended": 1, "other error": 4} and tally["errors"] == [{"sku": "s9", "why": "error: HTTP 500 server went away"}]
    assert catalogue.parse_removal("nothing to remove\n") == {"nothing": True}


def test_a_partial_removal_proves_nothing_about_which_listings_are_gone():
    partial = catalogue.parse_removal(REMOVAL_LIVE_LOG.replace("DELETED 1 of 1 planned", "DELETED 0 of 1 planned"))
    assert catalogue.deleted_skus(partial) == []
    left = catalogue.parse_removal(REMOVAL_LIVE_LOG.replace("VERIFY: 0 removed", "VERIFY: 1 removed"))
    assert catalogue.deleted_skus(left) == []


def test_mark_deleted_flags_holds_a_finished_removal_deleted_but_not_a_newer_listing_under_the_same_sku():
    merged = catalogue.merge_holds(HOLD_TEXT, PROTECTED_TEXT)
    run = {"id": 38, "number": 38, "url": "https://github.com/x/y/actions/runs/38"}
    marked = catalogue.mark_deleted(merged, [{"sku": "856689732127", "day": "2026-10-26", "run": run}, {"sku": AMA, "day": "2026-10-20", "run": run}])
    by_sku = {m["sku"]: m for m in marked}
    assert by_sku["856689732127"]["deleted_by"] == run                                                   # frozen 2026-10-16, deleted 2026-10-26
    assert by_sku[AMA]["deleted_by"] is None                                                             # frozen 2026-10-22, AFTER the 2026-10-20 deletion: a new listing
    assert by_sku["773086105845"]["deleted_by"] is None
    assert catalogue.mark_deleted(catalogue.merge_holds("0145936976019\n", ""), [{"sku": "145936976019", "day": "2026-01-01", "run": run}])[0]["deleted_by"] == run   # undated old fence


# ---- the page and its endpoints --------------------------------------------------------------------------------------------------------
def test_catalogue_page_lists_the_frozen_listings_the_nightly_facts_and_the_purge(web):
    r = web.get("/catalogue?store=gtv")
    assert r.status_code == 200
    assert r.text.count('class="cksel"') == 5 and AMA in r.text and "856689732127" in r.text and "773086105845" in r.text
    assert "zoerbufan Toe Separators" in r.text and "Toe Separators [3 Pair]" in r.text and "borderline 44%" in r.text            # the row next to the page, the nightly's overlap
    assert "Same product" in r.text and "Dash.catRelease(false)" in r.text and "Check the delete (dry run)" in r.text and "Delete for real" in r.text
    assert "Freeze listings" in r.text and "also take the stock off OnBuy now" in r.text
    assert "Left frozen for your decision" in r.text and "Dead-row purge" in r.text and "<strong>15</strong> row(s) removed (brand 3, out of stock 12)" in r.text
    assert "305812347721" in r.text and "Delete these by hand on OnBuy" in r.text and "Dry run now" in r.text and "List the suspended listings" in r.text
    assert "deleted by run" not in r.text and "goneBox" not in r.text
    yra = web.get("/catalogue?store=yra")
    assert yra.status_code == 200 and "Nothing is frozen on YRA" in yra.text and "No finished eBay sync yet" not in yra.text
    assert 'class="cksel"' not in yra.text and "Check the delete" not in yra.text                         # nothing to tick, so none of the buttons for ticked listings


def test_catalogue_page_shows_a_github_error_not_a_crash(web, fake):
    fake.fail_repo = "org/gtv"
    r = web.get("/catalogue?store=gtv")
    assert r.status_code == 200 and "Bad credentials" in r.text


def test_release_needs_the_box_and_known_listings_then_edits_both_lists(web, fake, db):
    refused = web.post("/api/store/gtv/catalogue/release", json={"skus": ["856689732127"]})
    assert refused.status_code == 400 and "confirmation" in refused.json()["error"] and not fake.edits
    unknown = web.post("/api/store/gtv/catalogue/release", json={"skus": ["856689732127", "nope"], "confirm": True})
    assert unknown.status_code == 400 and "Not on any hold list: nope" in unknown.json()["error"] and not fake.edits
    assert web.post("/api/store/gtv/catalogue/release", json={"skus": [], "confirm": True}).status_code == 400
    assert web.post("/api/store/zzz/catalogue/release", json={"skus": ["a"], "confirm": True}).status_code == 404
    ok = web.post("/api/store/gtv/catalogue/release", json={"skus": ["856689732127"], "confirm": True})
    assert ok.status_code == 200 and ok.json()["released"] == ["856689732127"] and not ok.json()["same_product"]
    assert [(d["file"], d["changed"]) for d in ok.json()["files"]] == [("protected_skus.txt", True), ("hold_at_zero_skus.txt", True)]
    assert [e[1] for e in fake.edits] == ["protected_skus.txt", "hold_at_zero_skus.txt"]                 # protected first: a half-way failure leaves it on the hold list, the safe side
    assert "856689732127" not in fake.files[("org/gtv", "hold_at_zero_skus.txt")] and "856689732127" not in fake.files[("org/gtv", "protected_skus.txt")]
    assert fake.files[("org/gtv", "same_product_skus.txt")] == SAME_TEXT
    assert db.recent_audit()[0]["action"] == "release"
    assert web.get("/catalogue?store=gtv").text.count('class="cksel"') == 4                                # the page re-reads the lists: one listing fewer


def test_same_product_goes_on_its_list_first_and_never_comes_back_as_a_borderline(web, fake):
    ok = web.post("/api/store/gtv/catalogue/release", json={"skus": [AMA], "same_product": True, "confirm": True})
    assert ok.status_code == 200 and ok.json()["same_product"]
    assert [e[1] for e in fake.edits] == ["same_product_skus.txt", "protected_skus.txt", "hold_at_zero_skus.txt"]            # the list that protects it from the nightly first
    same = fake.files[("org/gtv", "same_product_skus.txt")]
    assert same.startswith(SAME_TEXT) and "checked by hand in the dashboard" in same and f"\n{AMA}  # zoerbufan Toe Separators, 3 Pairs, Soft Silic\n" in same
    assert AMA not in fake.files[("org/gtv", "hold_at_zero_skus.txt")] and AMA not in fake.files[("org/gtv", "protected_skus.txt")]
    again = web.post("/api/store/gtv/catalogue/release", json={"skus": [AMA], "same_product": True, "confirm": True})
    assert again.status_code == 400 and "Not on any hold list" in again.json()["error"] and len(fake.edits) == 3


def test_a_github_failure_half_way_is_reported_and_leaves_the_listing_frozen_on_the_lists_not_yet_edited(web, fake):
    real = fake.update_file

    def flaky(repo, path, transform, message, ref="main", attempts=3):
        if path == "hold_at_zero_skus.txt":
            raise GitHubError("GitHub answered 409: conflict", 409)
        return real(repo, path, transform, message, ref, attempts)

    fake.update_file = flaky
    r = web.post("/api/store/gtv/catalogue/release", json={"skus": ["856689732127"], "confirm": True})
    assert r.status_code == 502 and "409" in r.json()["error"] and "reload" in r.json()["error"]
    assert "856689732127" in fake.files[("org/gtv", "hold_at_zero_skus.txt")]                              # still on the list the nightly zeroes from: nothing was restocked


def test_freeze_validates_then_writes_both_lists_and_can_take_the_stock_off_now(web, fake, db):
    base = {"skus": "999111, 999222", "reason": "supplier out of stock, two orders came in", "confirm": True}
    for bad, text in (({"skus": ""}, "at least one"), ({"skus": "a#b"}, "not a SKU"), ({"reason": "x"}, "Say why"), ({"confirm": False}, "confirmation")):
        r = web.post("/api/store/gtv/catalogue/freeze", json={**base, **bad})
        assert r.status_code == 400 and text in r.json()["error"], (bad, r.json())
    assert not fake.edits and not fake.dispatched
    ok = web.post("/api/store/gtv/catalogue/freeze", json={**base, "zero_now": True})
    assert ok.status_code == 200 and ok.json()["frozen"] == ["999111", "999222"] and ok.json()["zero"]["run"] and ok.json()["zero_error"] == ""
    assert [e[1] for e in fake.edits] == ["hold_at_zero_skus.txt", "protected_skus.txt"]
    for path in ("hold_at_zero_skus.txt", "protected_skus.txt"):
        text = fake.files[("org/gtv", path)]
        assert f"{TODAY} frozen from the dashboard: supplier out of stock, two orders came in" in text and "\n999111  # supplier out of stock, two orders came in\n999222  # " in text
    assert fake.dispatched[-1][:3] == ("org/gtv", "zero_listings.yml", {"skus": "999111,999222", "dry_run": "no"})
    assert [a["action"] for a in db.recent_audit()][:2] == ["freeze", "run"]
    assert "999111" in web.get("/catalogue?store=gtv").text
    again = web.post("/api/store/gtv/catalogue/freeze", json=base)                                         # no zero_now this time, and nothing new to write
    assert again.status_code == 200 and not any(f["changed"] for f in again.json()["files"]) and again.json()["zero"] is None and len(fake.dispatched) == 1


def test_freeze_keeps_the_lists_when_the_stock_cannot_be_taken_off_now(web, fake):
    fake.pending["org/gtv"] = [make_run(500, "run.yml", "Generate OnBuy Feed", NOW, status="queued", conclusion="")]            # a run is waiting for the store's slot
    r = web.post("/api/store/gtv/catalogue/freeze", json={"skus": "999111", "reason": "page shows a different model", "confirm": True, "zero_now": True})
    assert r.status_code == 200 and r.json()["zero"] is None and "waiting for the store's slot" in r.json()["zero_error"]
    assert "999111" in fake.files[("org/gtv", "hold_at_zero_skus.txt")] and not fake.dispatched          # frozen on the lists; the nightly takes the stock off


def test_delete_is_a_dry_run_by_default_and_a_real_one_needs_the_box(web, fake):
    dry = web.post("/api/store/gtv/catalogue/delete", json={"skus": [AMA], "dry_run": "yes"})
    assert dry.status_code == 200 and dry.json()["live"] is False
    store, workflow, inputs, _ = fake.dispatched[-1]
    assert workflow == "remove_wrong_content.yml" and inputs == {"skus": AMA, "backup_tab": f"Removed {TODAY}", "max_remove": "40", "keep_at": "0.5", "dry_run": "yes"}
    blank = web.post("/api/store/gtv/catalogue/delete", json={"skus": [AMA]})                              # nothing said = a dry run
    assert blank.status_code == 200 and blank.json()["live"] is False
    count = len(fake.dispatched)
    refused = web.post("/api/store/gtv/catalogue/delete", json={"skus": [AMA], "dry_run": "no"})
    assert refused.status_code == 400 and "confirmation" in refused.json()["error"] and len(fake.dispatched) == count
    live = web.post("/api/store/gtv/catalogue/delete", json={"skus": [AMA], "dry_run": "no", "confirm": True})
    assert live.status_code == 200 and live.json()["live"] is True and fake.dispatched[-1][2]["dry_run"] == "no"
    assert web.post("/api/store/gtv/catalogue/delete", json={"skus": [], "dry_run": "yes"}).status_code == 400


def test_purge_dry_run_and_the_suspended_list_are_read_only(web, fake):
    dry = web.post("/api/store/gtv/catalogue/purge", json={})
    assert dry.status_code == 200 and dry.json()["live"] is False and fake.dispatched[-1][2] == {"dry_run": "yes"}
    listed = web.post("/api/store/gtv/catalogue/purge", json={"suspended": True})
    assert listed.status_code == 200 and listed.json()["live"] is False and fake.dispatched[-1][2] == {"dry_run": "yes", "list_suspended": "yes"}


def test_run_status_parses_the_removal_and_the_purge_logs(web, fake):
    removal = web.get("/api/store/gtv/run/36").json()["facts"]
    assert removal["planned"] == 1 and removal["will_remove"][0]["sku"] == AMA and removal["held_back"][0]["sku"] == "856689732127"
    purge = web.get("/api/store/gtv/run/37").json()["facts"]
    assert purge["mode"] == "dry run" and purge["to_delete"] == 15 and purge["brand"] == 3
    fake.runs["org/gtv"].insert(0, make_run(39, "purge_dead_rows.yml", "Purge Dead eBay Rows (dry run / live)", NOW, event="workflow_dispatch"))
    assert web.get("/api/store/gtv/run/39").json()["facts"]["suspended_total"] == 2


def test_listings_a_finished_removal_deleted_are_flagged_and_forget_drops_only_those(web, fake, db):
    fake.runs["org/gtv"].insert(0, make_run(38, "remove_wrong_content.yml", "Remove Wrong-Content Listings", NOW, event="workflow_dispatch"))
    page = web.get("/catalogue?store=gtv").text
    assert "deleted by run 38" in page and 'id="goneBox"' in page and "1 of these listing(s) were deleted" in page and "Drop their lines" in page
    assert page.count('class="cksel"') == 5 and page.count(" disabled>") == 1                              # still listed, but not selectable
    forgot = web.post("/api/store/gtv/catalogue/forget", json={})
    assert forgot.status_code == 200 and forgot.json()["forgotten"] == ["856689732127"]
    assert [e[1] for e in fake.edits] == ["protected_skus.txt", "hold_at_zero_skus.txt"]
    assert "856689732127" not in fake.files[("org/gtv", "hold_at_zero_skus.txt")] and AMA in fake.files[("org/gtv", "hold_at_zero_skus.txt")]
    assert db.recent_audit()[0]["action"] == "forget"
    after = web.get("/catalogue?store=gtv").text
    assert "goneBox" not in after and after.count('class="cksel"') == 4
    nothing = web.post("/api/store/gtv/catalogue/forget", json={})                                         # nothing deleted is left to drop: nothing is written
    assert nothing.status_code == 200 and nothing.json()["forgotten"] == [] and len(fake.edits) == 2


def test_forget_never_drops_a_listing_no_run_deleted(web, fake):
    nothing = web.post("/api/store/gtv/catalogue/forget", json={"skus": [AMA]})                            # whatever the body says, the server decides from the run logs
    assert nothing.status_code == 200 and nothing.json()["forgotten"] == [] and not fake.edits
    assert AMA in fake.files[("org/gtv", "hold_at_zero_skus.txt")]
