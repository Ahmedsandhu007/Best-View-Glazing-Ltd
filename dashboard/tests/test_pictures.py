"""The Pictures card's pure part: the list, the artifact and lookup it reads, the rows, the link check, the ticket files and the reply draft, the resubmission logs."""
from datetime import datetime, timedelta, timezone

from pictures_data import EXPORT_FILES, LOOKUP_LOG, MAIN, REPAIR_DRY_LOG, REPAIR_LIVE_LOG, REPAIR_MIXED_LOG, fake_fetch, make_zip

from app import pictures

SKU_A, SKU_B, SKU_C = "734381598114", "734375635184", "734375050444"          # on the sheet with an OPC
SKU_D, SKU_E = "735719813442", "735739982043"                                    # on the sheet, no OPC (OnBuy has them)
GONE = "999000111"                                                                # nowhere


def export():
    return pictures.read_export(pictures.read_zip(make_zip(EXPORT_FILES)))


def rows(**kw):
    lookup, _ = pictures.read_lookup(LOOKUP_LOG)
    return pictures.build_rows(export(), lookup, kw.get("earlier", set()), kw.get("resubmitted"))


def test_sku_keys_ignore_commas_and_leading_zeros():
    assert pictures.norm("0123") == "123" and pictures.norm(" 1,234 ") == "1234" and pictures.norm("000") == "000" and pictures.norm(None) == ""
    assert pictures.norm("Ama-B0ABC12345-3") == "Ama-B0ABC12345-3"


def test_the_list_is_fingerprinted_by_its_skus_not_its_order_and_written_as_bare_skus():
    assert pictures.fingerprint([SKU_A, SKU_B]) == pictures.fingerprint([SKU_B, "0" + SKU_A]) and len(pictures.fingerprint([SKU_A])) == 10
    assert pictures.fingerprint([SKU_A]) != pictures.fingerprint([SKU_A, SKU_B])
    path = pictures.list_path("2026-10-26", "abcdef0123")
    assert path == "cleanup/image_ticket_skus_2026-10-26_abcdef0123.txt"
    text = pictures.list_text("GTV", [SKU_A, SKU_B], "2026-10-26")
    # the stores' export script takes EVERY non-empty line for a SKU, so the file carries nothing but SKUs (the first live build counted a "# ..." header as a fourth SKU)
    assert text == f"{SKU_A}\n{SKU_B}\n" and not any(line.startswith("#") for line in text.splitlines())
    assert pictures.read_list(text) == [SKU_A, SKU_B] and pictures.read_list("# c\n\n a \n#b\nc\n") == ["a", "c"]


def test_earlier_lists_are_found_by_name_oldest_first_and_the_new_one_is_left_out():
    entries = [{"name": "image_ticket_skus_2026-10-10.txt", "path": "cleanup/image_ticket_skus_2026-10-10.txt", "type": "file"},
               {"name": "image_ticket_skus_2026-10-03.txt", "path": "cleanup/image_ticket_skus_2026-10-03.txt", "type": "file"},
               {"name": "image_ticket_skus_2026-10-24_0123456789.txt", "path": "cleanup/image_ticket_skus_2026-10-24_0123456789.txt", "type": "file"},
               {"name": "image_ticket_skus_2026-10-15.txt", "path": "cleanup/sub/image_ticket_skus_2026-10-15.txt", "type": "dir"},
               {"name": "yra_delete_2026-10-10.txt", "path": "cleanup/yra_delete_2026-10-10.txt", "type": "file"}]
    assert [e["date"] for e in pictures.earlier_lists(entries)] == ["2026-10-03", "2026-10-10", "2026-10-24"]
    assert [e["date"] for e in pictures.earlier_lists(entries, exclude="cleanup/image_ticket_skus_2026-10-24_0123456789.txt")] == ["2026-10-03", "2026-10-10"]
    assert pictures.earlier_lists(None) == []
    assert [e["date"] for e in pictures.earlier_lists(entries, before="2026-10-24")] == ["2026-10-03", "2026-10-10"]          # only earlier days: a build of today is not "reported before"


def test_the_artifact_is_read_with_the_byte_order_mark_dropped():
    files = pictures.read_zip(make_zip(EXPORT_FILES))
    assert set(files) == set(EXPORT_FILES) and files["reference.csv"].startswith("SKU,Tab,Row") and not files["all_found_images.csv"].startswith("﻿")
    ex = export()
    assert [r["SKU"] for r in ex["found"]] == [SKU_A, SKU_B, SKU_C, SKU_D, SKU_E] and ex["found"][0]["Main image link"] == MAIN[SKU_A]
    assert set(ex["reference"]) == {SKU_A, SKU_B, SKU_C, SKU_D, SKU_E} and ex["reference"][SKU_A]["Tab"] == "Amazon"
    assert ex["not_on_sheet"] == [GONE] and ex["duplicates"] == [[SKU_C, "Amazon row 4909", "Sheet1 row 12"]]
    commented = pictures.read_export({**EXPORT_FILES, "not_on_sheet.txt": "# a list written by hand\n" + EXPORT_FILES["not_on_sheet.txt"]})
    assert commented["not_on_sheet"] == [GONE]                                      # a comment line is never a SKU (it made a whole sweep of OnBuy's listings for nothing)
    nested = pictures.read_zip(make_zip({"out/reference.csv": "SKU\n1\n"}))
    assert nested == {"reference.csv": "SKU\n1\n"} and pictures.read_export({})["found"] == []


def test_onbuys_own_records_are_read_even_when_the_runner_masked_the_braces():
    found, missing = pictures.read_lookup(LOOKUP_LOG)
    assert set(found) == {SKU_D, SKU_E, SKU_A} and found[SKU_D]["opc"] == "PYQX8T7" and found[SKU_D]["created_at"] == "2026-10-23 01:44:14" and missing == [GONE]
    masked, _ = pictures.read_lookup('LISTING|***"name": "X, with comma", "sku": "0555", "opc": "PYQ1234", "created_at": "2026-10-01 10:00:00", "price": "3.50"***\n')
    assert masked == {"555": {"name": "X, with comma", "sku": "0555", "opc": "PYQ1234", "created_at": "2026-10-01 10:00:00"}}
    assert pictures.read_lookup("") == ({}, []) and pictures.read_lookup("LISTING|***no sku here***\n") == ({}, [])


def test_only_the_skus_without_a_usable_opc_need_onbuys_record():
    assert pictures.missing_opc(export()) == [SKU_D, SKU_E, GONE]
    plain = {"found": [{"SKU": "1", "OPC": "PYQ1"}, {"SKU": "2", "OPC": "pending"}, {"SKU": "3", "OPC": " "}], "not_on_sheet": []}
    assert pictures.missing_opc(plain) == ["2", "3"]


def test_rows_take_the_opc_from_the_sheet_else_from_onbuy_and_mark_what_was_reported_before():
    rs = {r["sku"]: r for r in rows(earlier={SKU_C}, resubmitted={SKU_B: {"at": "2026-10-20T10:00:00Z", "ok": True}})}
    assert (rs[SKU_A]["opc"], rs[SKU_A]["source"], rs[SKU_D]["opc"], rs[SKU_D]["source"]) == ("PYQX8PS", "sheet", "PYQX8T7", "OnBuy") and rs[GONE]["source"] == "none" and rs[GONE]["opc"] == ""
    assert rs[SKU_A]["created"] == "2026-10-22" and rs[SKU_D]["created"] == "2026-10-23" and rs[SKU_B]["created"] == ""            # the sheet's TRUE is not a date
    assert rs[SKU_C]["repeat"] is True and rs[SKU_A]["repeat"] is False and rs[SKU_B]["resubmitted"]["at"].startswith("2026-10-20") and rs[SKU_A]["resubmitted"] is None
    assert rs[SKU_A]["tab"] == "Amazon" and rs[SKU_A]["row"] == "4911" and rs[SKU_A]["main"] == MAIN[SKU_A] and rs[GONE]["status"] == "not on the sheet" and rs[GONE]["tab"] == ""
    assert rs[SKU_A]["url"].startswith("https://www.onbuy.com/gb/p/hisense") and rs[SKU_B]["url"].startswith("https://onbuy.com/gb/p/hisense-3s") and rs[SKU_D]["title"].startswith("HP LaserJet")
    assert [r["sku"] for r in rows()][-1] == GONE                                                                                    # the ones not on the sheet come last


def test_every_link_of_a_listable_product_is_opened_and_a_dead_one_keeps_the_product_out_of_the_file():
    rs = rows()
    links = pictures.links_of(rs)
    assert len(links) == 16 and links[0] == (SKU_A, "main", MAIN[SKU_A]) and links[1][1] == "extra" and all(sku != GONE for sku, _, _ in links)
    dead_url = "https://m.media-amazon.com/images/I/71LTbhzTFzL.jpg"                                              # an extra link of SKU_C
    seen = []
    results = pictures.check_links(links, fake_fetch(dead={dead_url}, errors={MAIN[SKU_B]}), workers=3, progress=lambda done, total: seen.append((done, total)))
    assert [r[:3] for r in results] == links and seen[-1] == (16, 16) and len(results) == 16
    assert [(r[0], r[3]) for r in results if not pictures.link_ok(r)] == [(SKU_B, 0), (SKU_C, 404)]
    pictures.mark_links(rs, results)
    assert {r["sku"]: [d["status"] for d in r["dead"]] for r in rs if r["dead"]} == {SKU_B: [0], SKU_C: [404]}
    assert [r["sku"] for r in pictures.ticket_rows(rs)] == sorted([SKU_A, SKU_D, SKU_E])


def test_the_summary_counts_what_goes_in_the_file_and_what_needs_a_look():
    rs = rows(earlier={SKU_D}, resubmitted={SKU_A: {"at": "2026-10-20T10:00:00Z", "ok": True}})
    results = pictures.check_links(pictures.links_of(rs), fake_fetch(dead={MAIN[SKU_B]}))
    pictures.mark_links(rs, results)
    s = pictures.summarize(rs, 6, export(), results)
    assert (s["asked"], s["on_sheet"], s["rows_on_sheet"], s["ticket"], s["new"], s["repeat"], s["opc_from_onbuy"], s["resubmitted"]) == (6, 5, 5, 4, 3, 1, 2, 1)
    assert s["not_on_sheet"] == [GONE] and s["duplicates"] == [SKU_C] and s["no_opc"] == [GONE] and s["no_links"] == [] and s["tabs"] == {"Amazon": 5}
    assert s["dead"] == [{"sku": SKU_B, "links": [{"kind": "main", "url": MAIN[SKU_B], "status": 404, "info": "text/html"}]}]
    assert s["links"] == {"checked": 16, "ok": 15, "bad": 1} and s["created"] == {"first": "2026-10-22", "last": "2026-10-23"} and s["hosts"] == {"m.media-amazon.com": 13}      # the 4 products in the file
    assert s["extra_per_product"] == 2.2


def test_the_attachment_has_the_layout_of_every_earlier_file_and_the_reference_says_what_is_wrong_with_each_sku():
    rs = rows(earlier={SKU_C}, resubmitted={SKU_B: {"at": "2026-10-20T10:00:00Z", "ok": True}})
    dead_link = "https://m.media-amazon.com/images/I/61YK8lgvZhL.jpg"                                              # the first extra link of SKU_E (the two printers share their main image)
    pictures.mark_links(rs, pictures.check_links(pictures.links_of(rs), fake_fetch(dead={dead_link})))
    lines = pictures.attachment_csv(rs).splitlines()
    assert lines[0] == "OPC,SKU,Main image link,Additional image links" and len(lines) == 1 + 4                         # SKU_E has a dead link: left out
    assert lines[1].startswith(f"PYQX8PR,{SKU_B},{MAIN[SKU_B]},") and lines[2].startswith(f"PYQX8PS,{SKU_A},") and lines[-1].startswith(f"PYQX8PQ,{SKU_C},")      # by SKU, the repeat last
    ref = pictures.reference_csv(rs)
    assert ref.startswith("﻿SKU,Tab,Row,OPC,OPC source,Sync Status,Created on OnBuy,Reported before,Resubmitted,Problem,Product URL,Title")
    body = {r.split(",")[0]: r for r in ref.splitlines()[1:]}
    assert ",yes," in body[SKU_C] and ",2026-10-20," in body[SKU_B] and "dead link: " + dead_link in body[SKU_E] and "no OPC" in body[GONE] and ",OnBuy," in body[SKU_D]
    assert pictures.attachment_csv([]) == "OPC,SKU,Main image link,Additional image links\r\n"


def test_the_reply_draft_states_the_counts_the_link_check_the_dates_and_what_was_resubmitted():
    rs = rows()
    results = pictures.check_links(pictures.links_of(rs), fake_fetch())
    pictures.mark_links(rs, results)
    s = pictures.summarize(rs, 6, export(), results)
    earlier = [{"date": "2026-10-03"}, {"date": "2026-10-08"}, {"date": "2026-10-22"}]
    files = pictures.file_names("GTV", "2026-10-26")
    assert files == {"attachment": "GTV_stuck_loading_image_links_2026-10-26.csv", "reference": "GTV_image_ticket_reference_2026-10-26.csv", "reply": "GTV_ticket_additional_images_reply_2026-10-26.txt"}
    text = pictures.reply_text("GTV", s, files, earlier, 1500, agent="Ash", signed_by="Sadia")
    assert text.startswith("Reply to add to the ongoing GTV ticket (image processing) - a draft in Sadia's voice for GTV only\nAttach: GTV_stuck_loading_image_links_2026-10-26.csv   (5 products; same layout as the files of 3 October, 8 October and 22 October; 5 new)")
    assert "Hi Ash," in text and "We have found another 5 products with the same problem since our file of 22 October" in text and "None of them was in any of our earlier files." in text
    assert "re-checked every link today - all of them open." in text and "created between 22 October and 23 October 2026." in text and "at least 1500 different products" in text and text.rstrip().endswith("Sadia")
    assert "resubmitted through the products endpoint" not in text and "1 of them" not in text
    s2 = dict(s, repeat=2, new=3, resubmitted=2, links={"checked": 16, "ok": 14, "bad": 2}, created=None)
    again = pictures.reply_text("YRA", s2, files, [], 40, agent="Sam", signed_by="Priya")
    assert "2 of them were in our earlier files and are still not loading." in again and "14 of 16 open (the products with a link that does not open are left out)" in again
    assert "2 of these were also resubmitted through the products endpoint" in again and "Hi Sam," in again and "since our file" not in again and "the layout OnBuy asked for" in again and "The products were created" not in again
    one = pictures.reply_text("GTV", dict(s, repeat=1), files, [], 10)
    assert "One of them was in an earlier file and is still not loading." in one


def test_the_skus_to_resubmit_are_grouped_per_sheet_tab_in_sheet_order():
    assert pictures.resubmit_groups(rows()) == [{"tab": "Amazon", "skus": [SKU_C, SKU_B, SKU_A, SKU_D, SKU_E]}]                # not the SKU that is not on the sheet
    mixed = [{"sku": "1", "tab": "Sheet1", "row": "30"}, {"sku": "2", "tab": "Amazon", "row": "7"}, {"sku": "3", "tab": "Sheet1", "row": "9"}, {"sku": "4", "tab": "", "row": ""}, {"sku": "5", "tab": "Amazon", "row": "x"}]
    assert pictures.resubmit_groups(mixed) == [{"tab": "Sheet1", "skus": ["3", "1"]}, {"tab": "Amazon", "skus": ["5", "2"]}]


def test_parse_repair_reads_a_dry_run_with_its_collision_and_its_skipped_rows():
    f = pictures.parse_repair(REPAIR_DRY_LOG)
    assert (f["live"], f["worksheet"], f["repairable"], f["skipped_incomplete"], f["collision_count"]) == (8079, "Amazon", 4, 1, 1) and f["dry_run"] is True
    assert f["collisions"] == [{"row": 1288, "sku": "668580542916"}] and [t["sku"] for t in f["targets"]] == ["667770448984", "668159164105", "668196396682", "669347170304"]
    assert f["targets"][0]["shows"] == "Avio Carry-On Cabin Luggage 55x40x20cm | Hard Shell Suitcase" and "ok" not in f and "failed" not in f


def test_parse_repair_reads_a_canary_that_submitted_and_a_run_that_failed_and_hit_the_rate_limit():
    live = pictures.parse_repair(REPAIR_LIVE_LOG)
    assert live["ok"] == ["328989649226", "329020985778", "329026989923"] and live["limit"] == 3 and (live["submitted"], live["failed_count"]) == (3, 0) and "dry_run" not in live and live["worksheet"] == "Amazon"
    mixed = pictures.parse_repair(REPAIR_MIXED_LOG)
    assert mixed["ok"] == ["328989649226"] and mixed["failed"] == [{"sku": "329020985778", "why": 'HTTP 400 {"errors": ["image not reachable"]}'}] and mixed["rate_limited"] is True
    assert pictures.parse_repair("") == {}


def test_what_was_resubmitted_and_what_is_still_to_do_come_from_the_newest_runs():
    runs = [{"at": "2026-10-25T10:00:00Z", "run_url": "u2", "ok": ["2"], "failed": ["3"]}, {"at": "2026-10-20T10:00:00Z", "run_url": "u1", "ok": ["1", "3"], "failed": ["2"]}]
    history = pictures.resubmission_history(runs)
    assert history == {"2": {"at": "2026-10-25T10:00:00Z", "run_url": "u2", "ok": True}, "3": {"at": "2026-10-25T10:00:00Z", "run_url": "u2", "ok": False},
                       "1": {"at": "2026-10-20T10:00:00Z", "run_url": "u1", "ok": True}}                    # the newest word on a SKU stays
    state = pictures.group_state({"tab": "Amazon", "skus": ["1", "2", "3", "4"]}, history)
    assert state == {"tab": "Amazon", "total": 4, "done": 2, "failed": 1, "todo": ["3", "4"]}
    assert pictures.group_state({"tab": "X", "skus": ["0001"]}, history)["done"] == 1                          # leading zeros do not matter


def test_a_resubmission_is_started_with_only_the_named_skus_of_one_tab():
    skus = ["734375050444", "734375635184"]
    assert pictures.repair_inputs("preview", "Amazon", skus) == {"dry_run": "yes", "repair_skus": "734375050444,734375635184", "only_listed": "yes", "tab": "Amazon", "repair_limit": "0"}
    assert pictures.repair_inputs("canary", "Amazon", skus)["repair_limit"] == str(pictures.CANARY) and pictures.repair_inputs("canary", "Amazon", skus)["dry_run"] == "no"
    assert pictures.repair_inputs("rest", "eBay", skus)["repair_limit"] == "0" and pictures.repair_inputs("rest", "eBay", skus)["dry_run"] == "no"
    assert all(pictures.repair_inputs(mode, "Amazon", skus)["only_listed"] == "yes" for mode in ("preview", "canary", "rest"))        # never "every shifted listing of the store"
    assert set(pictures.repair_inputs("rest", "Amazon", skus)) == set(pictures.REPAIR_INPUTS)


def run_at(path, minutes_ago, now, conclusion="success"):
    return {"path": path, "created_at": (now - timedelta(minutes=minutes_ago)).isoformat().replace("+00:00", "Z"), "conclusion": conclusion}


def test_onbuy_is_not_read_in_full_more_than_three_times_an_hour_and_the_wait_says_how_long():
    now = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
    assert pictures.sweep_wait([], now) == 0
    two = [run_at("listing_lookup.yml", 5, now), run_at("repair_shifted_content.yml", 20, now)]
    assert pictures.sweep_wait(two, now) == 0
    three = two + [run_at("listing_lookup.yml", 40, now)]
    assert pictures.sweep_wait(three, now) == 20                                                          # the oldest of the three leaves the hour in 20 minutes
    four = three + [run_at("listing_lookup.yml", 50, now)]
    assert pictures.sweep_wait(four, now) == 20                                                           # the 3rd newest one decides, not the oldest
    assert pictures.sweep_wait(three + [run_at("listing_lookup.yml", 61, now)], now) == 20               # a run of more than an hour ago does not count
    assert pictures.sweep_wait([run_at("listing_lookup.yml", 1, now), run_at("listing_lookup.yml", 2, now), run_at("listing_lookup.yml", 3, now)], now) == 57


def test_cancelled_runs_and_other_workflows_do_not_count_as_full_reads():
    now = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)
    runs = [run_at("listing_lookup.yml", 5, now), run_at("listing_lookup.yml", 6, now, conclusion="cancelled"), run_at("orders_lookup.yml", 7, now), run_at("run.yml", 8, now)]
    assert pictures.sweep_wait(runs, now) == 0
    assert pictures.sweep_wait([{"path": "listing_lookup.yml", "created_at": "not a date", "conclusion": ""}] * 3, now) == 0


# ---- the scan upload (2026-10-28): the browser scan's CSV, read so only the stuck products go in the box --------------------------------
def scan_csv(*rows):
    """Exactly as onbuy_image_scan_<Store>.js downloads it: every value quoted, the fixed header."""
    header = ["sku", "product_url", "page_status", "images_found", "images_failed", "first_image", "first_status", "all_statuses", "note"]
    quoted = [",".join('"' + str(v).replace('"', '""') + '"' for v in row) for row in [header, *rows]]
    return "\n".join(quoted)


URL = "https://www.onbuy.com/gb/p/thing~p292247881"
FINE = ["693428398370", URL, 200, 2, 0, "https://cdn.onbuy.com/product/abc/500-500/x.jpg", "ok", "ok|ok", ""]
PAGE_404 = ["693436589647", URL, 404, 0, 0, "", "", "", "product page 404 (not found)"]
IMG_FAIL = ["693500908381", URL, 200, 2, 1, "https://cdn.onbuy.com/product/def/500-500/y.jpg", "error", "error|ok", ""]
PLACEHOLDER = ["693541506515", URL, 200, 0, 0, "", "", "", "placeholder only"]
NO_IMAGE = ["693586835151", URL, 200, 0, 0, "", "", "", "no image on page"]
GAVE_UP = ["693605925252", URL, "ERR", "", "", "", "", "", "gave up after repeated 429s"]
PAGE_500 = ["693614601062", URL, 500, "", "", "", "", "", "page error 500"]


def test_the_scan_file_is_recognised_and_read_with_one_row_per_sku():
    rows = pictures.read_scan("﻿" + scan_csv(FINE, PAGE_404, ["0" + FINE[0], URL, 404, 0, 0, "", "", "", "scanned twice"]))
    assert [r["sku"] for r in rows] == [FINE[0], PAGE_404[0]]                     # the BOM is dropped; the same SKU with a leading zero is the same listing, the first row wins
    assert rows[0]["page_status"] == "200" and rows[0]["images_failed"] == "0"


def test_files_that_are_not_the_scan_are_left_to_the_plain_reading():
    assert pictures.read_scan("SKU,Tab\n693428398370,Amazon\n") is None           # a SKU column alone is any of our CSVs
    assert pictures.read_scan("693428398370\n693436589647\n") is None and pictures.read_scan("") is None


def test_each_scanned_row_gets_its_verdict():
    verdicts = {row[0]: pictures.scan_verdict(dict(zip(("sku", "product_url", "page_status", "images_found", "images_failed", "first_image", "first_status", "all_statuses", "note"),
                                                       (str(v) for v in row)))) for row in (FINE, PAGE_404, IMG_FAIL, PLACEHOLDER, NO_IMAGE, GAVE_UP, PAGE_500)}
    assert verdicts[FINE[0]] == ("fine", "")
    assert verdicts[PAGE_404[0]] == ("stuck", "page 404")
    assert verdicts[IMG_FAIL[0]] == ("stuck", "1 of 2 picture(s) do not load")
    assert verdicts[PLACEHOLDER[0]] == ("stuck", "placeholder only") and verdicts[NO_IMAGE[0]] == ("stuck", "no image on page")
    assert verdicts[GAVE_UP[0]] == ("unclear", "gave up after repeated 429s") and verdicts[PAGE_500[0]] == ("unclear", "page error 500")


def test_the_report_counts_what_goes_in_the_box_and_what_the_scan_could_not_see():
    report = pictures.scan_report(pictures.read_scan(scan_csv(FINE, PAGE_404, IMG_FAIL, PLACEHOLDER, NO_IMAGE, GAVE_UP, PAGE_500)))
    assert report["total"] == 7 and report["fine"] == 1
    assert [r["sku"] for r in report["stuck"]] == [PAGE_404[0], IMG_FAIL[0], PLACEHOLDER[0], NO_IMAGE[0]]
    assert report["why"] == {"page 404": 1, "pictures fail to load": 1, "placeholder only": 1, "no image on page": 1}
    assert [r["sku"] for r in report["unclear"]] == [GAVE_UP[0], PAGE_500[0]] and report["unclear"][1]["why"] == "page error 500"


def test_any_other_file_keeps_the_old_reading_first_column_quotes_and_header_dropped():
    assert pictures.read_sku_file('"SKU",Found at\n"693428398370",Amazon row 5180\n693436589647,x\n\n') == ["693428398370", "693436589647"]
    assert pictures.read_sku_file("693428398370 extra words\n") == ["693428398370 extra words".split(",")[0]]
    assert pictures.read_sku_file("") == []
