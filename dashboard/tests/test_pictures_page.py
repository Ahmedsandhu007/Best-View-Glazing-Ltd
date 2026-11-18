"""The Pictures card end to end: the ticket build as a background job (list committed, sheet read, OnBuy lookup, link check, files), the downloads, the resubmission in its three modes
and the guards (one build at a time, the sweep limit, a repair workflow that cannot be limited to the named SKUs)."""
import threading
from datetime import timedelta

from conftest import NOW, TODAY, make_run
from fastapi.testclient import TestClient
from pictures_data import ALL_FOUND, EXPORT_FILES, LOOKUP_LOG, MAIN, make_zip

from app import pictures
from app.jobs import Jobs
from app.main import create_app

SKU_LIST = "734381598114 734375635184 734375050444 735719813442 735739982043 999000111"
SHEET_ORDER = ["734375050444", "734375635184", "734381598114", "735719813442", "735739982043"]          # by row: 4909, 4910, 4911, 4992, 4993
EARLIER_DAY = (NOW - timedelta(days=20)).date().isoformat()
EARLIER_PATH = f"cleanup/image_ticket_skus_{EARLIER_DAY}.txt"
LIST_PATH = f"cleanup/image_ticket_skus_{TODAY}_{pictures.fingerprint(SKU_LIST.split())}.txt"


def wire(fake, files=None, fail=(), artifact=True):
    """The two runs a build starts, as GitHub would run them: each is looked at as in progress, then ends; the sheet read uploads its files, the lookup logs OnBuy's records."""
    def on_dispatch(f, repo, workflow, inputs, run):
        if workflow not in ("image_links_export.yml", "listing_lookup.yml"):
            return
        f.script[run["id"]] = [{"status": "in_progress"}, {"status": "completed", "conclusion": "failure" if workflow in fail else "success"}]
        if workflow == "image_links_export.yml" and artifact:
            f.artifacts[run["id"]] = [{"id": 900, "name": "image-links", "size": 4096, "expired": False}]
            f.artifact_zips[900] = make_zip(files or EXPORT_FILES)
        if workflow == "listing_lookup.yml":
            f.logs[run["id"]] = LOOKUP_LOG
    fake.on_dispatch = on_dispatch


# the same sheet read with only the three products whose OPC the sheet has: no lookup of OnBuy is needed
SHEET_ONLY = dict(EXPORT_FILES, **{"all_found_images.csv": "\n".join(ALL_FOUND.splitlines()[:4]) + "\n", "not_on_sheet.txt": "", "duplicates.csv": "SKU,Found at\n"})


def build(web, fake, skus=SKU_LIST, **kw):
    fake.files[("org/gtv", EARLIER_PATH)] = "# GTV: an earlier ticket\n734381598114\n281589222230\n"
    wire(fake, **kw)
    return web.post("/api/store/gtv/pictures/ticket", json={"skus": skus})


def repair_log(ok=(), failed=()):
    lines = ["INFO live listings: 6258", f"INFO shift-repairable: {len(ok) + len(failed)} (skipped incomplete: 0) | barcode-collision (report-only): 0"]
    lines += [f"INFO   target {s} (onbuy shows: Another product)" for s in [*ok, *failed]]
    lines += [f"INFO REPAIR {s}: submitted OK" for s in ok]
    lines += [f"WARNING REPAIR {s}: failed - HTTP 400" for s in failed]
    return "\n".join(lines + [f"INFO DONE: {len(ok)} submitted, {len(failed)} failed (content applies after OnBuy's queue processes)"])


def finish_last(fake, ok=(), failed=(), conclusion="success"):
    """The newest dispatched run of org/gtv ends, with the repair log."""
    run = fake.runs["org/gtv"][0]
    run.update(status="completed", conclusion=conclusion)
    fake.logs[run["id"]] = repair_log(ok, failed)
    return run


def recent_sweeps(fake, count):
    for i in range(count):
        fake.runs["org/gtv"].append(make_run(70 + i, "listing_lookup.yml", "Listing Lookup (read-only)", NOW - timedelta(minutes=10 * (i + 1)), event="workflow_dispatch"))


# ---- the page -------------------------------------------------------------------------------------------------------------------------
def test_the_page_opens_with_its_brief_and_says_a_ticket_comes_first(web):
    r = web.get("/pictures?store=gtv")
    assert r.status_code == 200 and '<details class="brief"><summary>What this page does</summary>' in r.text
    for phrase in ("Build the ticket", "Build a ticket first", "No list in the repository yet: the first build saves the first one.", 'id="pictures"'):
        assert phrase in r.text
    assert 'href="/pictures?store=gtv"' in r.text and web.get("/pictures?store=nowhere").status_code == 200          # an unknown store falls back to the first one


def test_the_page_says_so_when_github_cannot_be_read(web, fake):
    fake.fail_repo = "org/gtv"
    r = web.get("/pictures?store=gtv")
    assert r.status_code == 200 and "Bad credentials" in r.text


def test_a_store_without_the_tools_cannot_build_and_the_page_says_which_is_missing(web, fake):
    del fake.definitions["image_links_export.yml"]
    page = web.get("/pictures?store=gtv").text
    assert "has no image_links_export.yml, so the ticket cannot be built here" in page and "disabled" in page.split('id="picBuild"')[1].split(">")[0]
    refused = web.post("/api/store/gtv/pictures/ticket", json={"skus": "A1"})
    assert refused.status_code == 400 and "image_links_export.yml" in refused.json()["error"] and fake.dispatched == []


def test_every_function_of_a_page_with_a_ticket_has_its_hint(web, fake):
    build(web, fake)
    page = web.get("/pictures?store=gtv").text
    for phrase in ("Attach this to the ticket", "For us only, do not send", "The reply draft below as a text file", "Copy the reply", "paste it into the open OnBuy ticket yourself",
                   "Preview</strong> changes nothing", "Canary</strong> resubmits the first 3", "Resubmit the rest</strong> sends every product", "Each run reads all of the store's listings",
                   "Needs a look", '"In the attachment" = products with an OPC', "Rows whose category or main picture is missing on the sheet are skipped"):
        assert phrase in page, phrase


# ---- the ticket build -----------------------------------------------------------------------------------------------------------------
def test_a_build_saves_the_list_reads_the_sheet_asks_onbuy_opens_every_link_and_writes_the_files(web, fake, links, db):
    r = build(web, fake)
    job = r.json()["job"]
    assert r.status_code == 200 and job["state"] == "done", job
    assert [s["text"] for s in job["steps"]] == ["Saving the list in the repository", "Reading the earlier ticket lists", "Reading the sheet (the pictures and OPCs of these SKUs)",
                                                 "Asking OnBuy for the OPC of 3 SKU(s) the sheet has none for", "Opening 16 image links", "Writing the files"]
    # the list file holds the SKUs and nothing else: the stores' export takes every non-empty line for a SKU, a "# ..." header was counted as one
    assert [(e[0], e[1]) for e in fake.edits] == [("org/gtv", LIST_PATH)] and fake.files[("org/gtv", LIST_PATH)].splitlines() == SKU_LIST.split()
    assert [(d[1], d[2]) for d in fake.dispatched] == [("image_links_export.yml", {"sku_file": LIST_PATH}), ("listing_lookup.yml", {"skus": "735719813442,735739982043,999000111"})]
    assert len(links.opened) == 16 and MAIN["734381598114"] in links.opened
    rows = {(d["workflow"], d["status"]) for d in db.recent_dispatches("gtv")}
    assert rows == {("image_links_export.yml", "success"), ("listing_lookup.yml", "success")}                   # the dispatch rows end with the runs
    assert [a["action"] for a in db.recent_audit(store="gtv")] == ["pictures_ticket_built", "run", "run"]

    page = web.get("/pictures?store=gtv").text
    assert "The last ticket" in page and "<strong>5</strong><span>in the attachment</span>" in page and "<strong>1</strong><span>reported before</span>" in page
    assert "<strong>16 / 16</strong>" in page and "999000111" in page and "with no OPC" in page and "on the sheet more than once" in page
    assert f"GTV_stuck_loading_image_links_{TODAY}.csv" in page and "Reply draft" in page and "Hi Ash," in page
    assert f"Compared with the lists of 1 earlier day(s): {EARLIER_DAY}" in page


def test_the_attachment_the_reference_sheet_and_the_reply_download(web, fake):
    job = build(web, fake).json()["job"]
    base = f"/api/store/gtv/pictures/file/{job['result']['job_id']}"
    attachment = web.get(f"{base}/attachment")
    assert attachment.status_code == 200 and attachment.headers["content-type"].startswith("text/csv")
    assert f'filename="GTV_stuck_loading_image_links_{TODAY}.csv"' in attachment.headers["content-disposition"]
    lines = attachment.text.splitlines()
    assert lines[0] == "OPC,SKU,Main image link,Additional image links" and len(lines) == 6
    assert lines[1].startswith("PYQX8PQ,734375050444,") and all(line.split(",")[0] for line in lines[1:])                # new products first, the one reported before last
    assert lines[-1].startswith("PYQX8PS,734381598114,")
    reference = web.get(f"{base}/reference")
    assert reference.content.startswith(b"\xef\xbb\xbf") and "OPC source" in reference.text and "OnBuy" in reference.text and "999000111" in reference.text
    reply = web.get(f"{base}/reply")
    assert reply.headers["content-type"].startswith("text/plain") and "Hi Ash," in reply.text and "5 products" in reply.text and "4 new, 1 reported before" in reply.text
    assert "all of them open" in reply.text and reply.text.rstrip().endswith("Sadia")


def test_the_two_names_of_the_reply_are_the_ones_given(web, fake):
    fake.files[("org/gtv", EARLIER_PATH)] = "734381598114\n"
    wire(fake)
    job = web.post("/api/store/gtv/pictures/ticket", json={"skus": SKU_LIST, "agent": "Priya <b>", "signed_by": "  Mo  "}).json()["job"]
    reply = web.get(f"/api/store/gtv/pictures/file/{job['result']['job_id']}/reply").text
    assert "Hi Priya b," in reply and reply.rstrip().endswith("Mo")                                                  # only letters, spaces, dots, apostrophes and hyphens are kept


def test_a_product_with_a_dead_picture_link_is_left_out_of_the_attachment_and_listed(web, fake, links):
    links.dead.add(MAIN["734375635184"])
    job = build(web, fake).json()["job"]
    base = f"/api/store/gtv/pictures/file/{job['result']['job_id']}"
    assert job["result"]["ticket"] == 4 and "734375635184" not in web.get(f"{base}/attachment").text
    assert "15 of 16 open" in web.get(f"{base}/reply").text and "dead link: " in web.get(f"{base}/reference").text
    page = web.get("/pictures?store=gtv").text
    assert "<strong>15 / 16</strong>" in page and "with a picture link that does not open" in page and "404" in page


def test_nothing_is_asked_of_onbuy_when_the_sheet_has_every_opc(web, fake):
    job = build(web, fake, skus="734381598114 734375635184 734375050444", files=SHEET_ONLY).json()["job"]
    assert job["state"] == "done" and [d[1] for d in fake.dispatched] == ["image_links_export.yml"] and job["result"]["ticket"] == 3
    assert "Asking OnBuy" not in str(job["steps"])


def test_a_failed_sheet_read_stops_the_build_with_the_reason_and_leaves_no_ticket(web, fake, db):
    job = build(web, fake, fail=("image_links_export.yml",)).json()["job"]
    assert job["state"] == "failed" and "The sheet read ended with 'failure'" in job["error"] and "actions/runs" in job["error"] and job["result"] is None
    assert [d[1] for d in fake.dispatched] == ["image_links_export.yml"]
    assert db.recent_dispatches("gtv")[0]["status"] == "failure" and "The last ticket" not in web.get("/pictures?store=gtv").text


def test_a_failed_lookup_stops_the_build_too(web, fake):
    job = build(web, fake, fail=("listing_lookup.yml",)).json()["job"]
    assert job["state"] == "failed" and "The OnBuy lookup ended with 'failure'" in job["error"]


def test_a_sheet_read_without_its_files_is_reported(web, fake):
    job = build(web, fake, artifact=False).json()["job"]
    assert job["state"] == "failed" and "the artifact image-links" in job["error"]


def test_a_refused_dispatch_is_the_reason_of_the_failure(web, fake):
    fake.pending["org/gtv"] = [make_run(5, "run.yml", "Generate OnBuy Feed", NOW, status="queued", conclusion="")]
    job = build(web, fake).json()["job"]
    assert job["state"] == "failed" and "The sheet read: A run is already waiting for the store's slot" in job["error"] and fake.dispatched == []


def test_onbuy_is_not_asked_again_while_three_full_reads_started_in_the_last_hour(web, fake):
    recent_sweeps(fake, 3)
    job = build(web, fake).json()["job"]
    assert job["state"] == "failed" and "Build the ticket again in" in job["error"] and "minute(s). Nothing was changed." in job["error"]
    assert [d[1] for d in fake.dispatched] == ["image_links_export.yml"]                                       # the sheet read is cheap and went; the lookup did not
    recent_sweeps_ok = [r for r in fake.runs["org/gtv"] if r["path"] == "listing_lookup.yml"]
    assert len(recent_sweeps_ok) == 3


def test_a_bad_list_is_refused_before_anything_is_saved(web, fake):
    for body, why in (({"skus": ""}, "Give at least one SKU."), ({"skus": " ,, "}, "Give at least one SKU."), ({"skus": "A1 B#2"}, "is not a SKU"),
                      ({"skus": " ".join(f"S{n}" for n in range(1501))}, "At most 1,500 SKUs at a time.")):
        r = web.post("/api/store/gtv/pictures/ticket", json=body)
        assert r.status_code == 400 and why in r.json()["error"], body
    assert fake.edits == [] and fake.dispatched == [] and web.post("/api/store/nowhere/pictures/ticket", json={"skus": "A1"}).status_code == 404


def test_only_one_build_runs_at_a_time_per_store_and_the_page_follows_the_running_one(settings, fake, db, links):
    gate, jobs = threading.Event(), Jobs()
    client = TestClient(create_app(settings=settings, client=fake, database=db, jobs=jobs, link_fetch=links, sleep=lambda seconds: None))
    first = jobs.start("pictures", "gtv", lambda job: (job.set_step("Reading the sheet"), gate.wait(5)))
    try:
        refused = client.post("/api/store/gtv/pictures/ticket", json={"skus": "A1"})
        assert refused.status_code == 400 and "already running" in refused.json()["error"] and fake.edits == []
        assert f'data-job="{first.id}"' in client.get("/pictures?store=gtv").text and 'data-job=""' in client.get("/pictures?store=yra").text
        view = client.get(f"/api/store/gtv/pictures/job/{first.id}").json()
        assert view["state"] == "running" and view["step"] == "Reading the sheet" and client.get(f"/api/store/yra/pictures/job/{first.id}").status_code == 404
    finally:
        gate.set()
        jobs._threads[first.id].join(5)
    assert client.get(f"/api/store/gtv/pictures/job/{first.id}").json()["state"] == "done" and client.get("/api/store/gtv/pictures/job/unknown").status_code == 404


def test_only_the_three_files_of_a_build_can_be_downloaded(web, fake):
    job_id = build(web, fake).json()["job"]["result"]["job_id"]
    assert web.get(f"/api/store/gtv/pictures/file/{job_id}/result").status_code == 404                           # result.json is not one of the three
    assert web.get(f"/api/store/gtv/pictures/file/{job_id}/..").status_code == 404
    assert web.get("/api/store/gtv/pictures/file/..%2f..%2fdashboard/attachment").status_code == 404
    assert web.get("/api/store/gtv/pictures/file/0123456789ab/attachment").status_code == 404                    # no such build
    assert web.get(f"/api/store/yra/pictures/file/{job_id}/attachment").status_code == 404                       # another store's folder
    assert web.get(f"/api/store/nowhere/pictures/file/{job_id}/attachment").status_code == 404


def test_the_last_ten_builds_are_kept_and_the_latest_is_the_one_shown(web, fake, settings):
    ids = [build(web, fake, skus="734381598114 734375635184 734375050444", files=SHEET_ONLY).json()["job"]["result"]["job_id"] for _ in range(12)]
    folder = settings.data_dir / "pictures" / "gtv"
    assert sum(1 for p in folder.iterdir() if p.is_dir()) == 10 and (folder / "latest.txt").read_text() == ids[-1]
    assert f"/pictures/file/{ids[-1]}/attachment" in web.get("/pictures?store=gtv").text


# ---- the resubmission -----------------------------------------------------------------------------------------------------------------
def test_a_resubmission_needs_a_ticket_build_first(web, fake):
    r = web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Amazon", "mode": "preview"})
    assert r.status_code == 400 and "build the ticket first" in r.json()["error"]
    assert web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Amazon", "mode": "fix"}).status_code == 400


def test_a_preview_is_a_dry_run_limited_to_the_named_skus_in_sheet_order(web, fake):
    build(web, fake)
    before = len(fake.dispatched)
    r = web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Amazon", "mode": "preview"})
    assert r.status_code == 200 and r.json()["count"] == 5 and r.json()["live"] is False
    repo, workflow, inputs, ref = fake.dispatched[before]
    assert (repo, workflow) == ("org/gtv", "repair_shifted_content.yml")
    assert inputs == {"dry_run": "yes", "repair_skus": ",".join(SHEET_ORDER), "only_listed": "yes", "tab": "Amazon", "repair_limit": "0"}
    assert web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Nowhere", "mode": "preview"}).status_code == 400


def test_a_live_resubmission_needs_the_confirmation_box(web, fake):
    build(web, fake)
    before = len(fake.dispatched)
    for mode in ("canary", "rest"):
        r = web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Amazon", "mode": mode})
        assert r.status_code == 400 and "confirmation box" in r.json()["error"]
    assert len(fake.dispatched) == before


def test_the_canary_resubmits_the_first_three_then_the_rest_continues_with_what_is_left(web, fake, db):
    build(web, fake)
    start = len(fake.dispatched)
    canary = web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Amazon", "mode": "canary", "confirm": True})
    assert canary.status_code == 200 and canary.json()["live"] is True
    assert fake.dispatched[start][2] == {"dry_run": "no", "repair_skus": ",".join(SHEET_ORDER), "only_listed": "yes", "tab": "Amazon", "repair_limit": "3"}
    finish_last(fake, ok=SHEET_ORDER[:3])
    page = web.get("/pictures?store=gtv").text
    assert "<strong>Amazon</strong></td><td>5</td><td>3</td><td>0</td><td><strong>2</strong>" in page.replace("\n", "")                  # 5 products, 3 resubmitted OK, 2 to do
    rest = web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Amazon", "mode": "rest", "confirm": True})
    assert rest.status_code == 200 and rest.json()["count"] == 2
    assert fake.dispatched[start + 1][2] == {"dry_run": "no", "repair_skus": ",".join(SHEET_ORDER[3:]), "only_listed": "yes", "tab": "Amazon", "repair_limit": "0"}
    finish_last(fake, ok=SHEET_ORDER[3:])
    done = web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Amazon", "mode": "rest", "confirm": True})
    assert done.status_code == 400 and "already" in done.json()["error"] and "all done" in web.get("/pictures?store=gtv").text
    assert [a["action"] for a in db.recent_audit(store="gtv")][:2] == ["pictures_rest", "run"]


def test_a_product_that_failed_stays_on_the_list_and_a_run_that_was_cut_short_counts_what_it_did(web, fake):
    build(web, fake)
    web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Amazon", "mode": "rest", "confirm": True})
    finish_last(fake, ok=SHEET_ORDER[:2], failed=[SHEET_ORDER[2]], conclusion="failure")
    page = web.get("/pictures?store=gtv").text.replace("\n", "")
    assert "<td>5</td><td>2</td><td><span class=\"bad-text\">1</span></td><td><strong>3</strong>" in page
    again = web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Amazon", "mode": "rest", "confirm": True})
    assert again.json()["count"] == 3 and fake.dispatched[-1][2]["repair_skus"] == ",".join(SHEET_ORDER[2:])


def test_a_preview_changes_nothing_in_the_counts(web, fake):
    build(web, fake)
    web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Amazon", "mode": "preview"})
    finish_last(fake, ok=SHEET_ORDER)                                                                          # even a dry run's log naming targets must not count as done
    assert web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Amazon", "mode": "preview"}).json()["count"] == 5


def test_a_repair_workflow_that_cannot_be_limited_to_the_named_skus_is_never_started(web, fake):
    build(web, fake)
    before = len(fake.dispatched)
    del fake.definitions["repair_shifted_content.yml"]["inputs"]["only_listed"]
    r = web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Amazon", "mode": "preview"})
    assert r.status_code == 400 and "no only_listed input" in r.json()["error"] and len(fake.dispatched) == before
    del fake.definitions["repair_shifted_content.yml"]
    gone = web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Amazon", "mode": "preview"})
    assert gone.status_code == 400 and "has no repair_shifted_content.yml" in gone.json()["error"]


def test_a_resubmission_is_refused_while_three_full_reads_started_in_the_last_hour_and_while_a_run_waits(web, fake):
    build(web, fake)
    before = len(fake.dispatched)
    recent_sweeps(fake, 3)
    r = web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Amazon", "mode": "preview"})
    assert r.status_code == 400 and "Try again in" in r.json()["error"] and len(fake.dispatched) == before
    fake.runs["org/gtv"] = [run for run in fake.runs["org/gtv"] if run["path"] != "listing_lookup.yml" or run["id"] < 70]
    fake.pending["org/gtv"] = [make_run(5, "run.yml", "Generate OnBuy Feed", NOW, status="queued", conclusion="")]
    waiting = web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Amazon", "mode": "preview"})
    assert waiting.status_code == 400 and "already waiting for the store's slot" in waiting.json()["error"]


def test_the_log_of_a_resubmission_shows_its_numbers_on_the_run_endpoint(web, fake):
    build(web, fake)
    sent = web.post("/api/store/gtv/pictures/resubmit", json={"tab": "Amazon", "mode": "canary", "confirm": True}).json()
    run = finish_last(fake, ok=SHEET_ORDER[:3])
    facts = web.get(f"/api/store/gtv/run/{sent['run']['id']}").json()["facts"]
    assert run["id"] == sent["run"]["id"] and facts["ok"] == SHEET_ORDER[:3] and facts["submitted"] == 3 and facts["live"] == 6258
    started = web.get("/pictures?store=gtv").text
    assert "resubmission, tab Amazon: canary, the first 3" in started and "sheet read for a ticket" in started and "OnBuy lookup for a ticket" in started


# ---- the scan upload (2026-10-28) --------------------------------------------------------------------------------------------------------
def scan_text():
    header = '"sku","product_url","page_status","images_found","images_failed","first_image","first_status","all_statuses","note"'
    url = "https://www.onbuy.com/gb/p/thing~p1"
    rows = [f'"693428398370","{url}","200","2","0","img","ok","ok|ok",""',                 # fine
            f'"693436589647","{url}","404","0","0","","","","product page 404 (not found)"',
            f'"693500908381","{url}","200","2","1","img","error","error|ok",""',
            f'"693605925252","{url}","ERR","","","","","","gave up after repeated 429s"']
    return "\n".join([header, *rows])


def test_an_uploaded_scan_file_puts_only_the_stuck_products_in_the_box(web):
    data = web.post("/api/store/gtv/pictures/scan", json={"text": scan_text()}).json()
    assert data["scan"] is True and data["total"] == 4 and data["fine"] == 1
    assert data["stuck"] == ["693436589647", "693500908381"] and data["over"] is False
    assert data["why"] == {"page 404": 1, "pictures fail to load": 1}
    assert data["unclear"] == 1 and data["unclear_rows"] == [{"sku": "693605925252", "why": "gave up after repeated 429s"}]


def test_any_other_uploaded_file_is_read_as_before_first_column_header_dropped(web):
    data = web.post("/api/store/gtv/pictures/scan", json={"text": '"SKU","Tab"\n"693428398370","Amazon"\n693436589647,"x"\n'}).json()
    assert data == {"scan": False, "skus": ["693428398370", "693436589647"], "count": 2}
    bad = web.post("/api/store/gtv/pictures/scan", json={"text": "   \n\n"})
    assert bad.status_code == 400 and "at least one SKU" in bad.json()["error"]
    assert web.post("/api/store/nope/pictures/scan", json={"text": "1"}).status_code == 404


def test_the_page_says_the_scan_file_is_understood(web, fake):
    page = web.get("/pictures?store=gtv").text
    assert "onbuy_image_scan_" in page and 'id="picScanNote"' in page


# ---- earlier builds + start-from-last (2026-10-29) ---------------------------------------------------------------------------------------
def test_the_last_builds_full_list_fills_the_box_and_older_builds_keep_their_files(web, fake):
    build(web, fake)                                                                      # build 1: the six SKUs
    first_job = web.get("/pictures?store=gtv").text
    build(web, fake, skus=SKU_LIST + " 444555666777")                                     # build 2 replaces "the last ticket"
    last = web.get("/api/store/gtv/pictures/last_skus").json()
    assert last["asked"] == 7 and set(last["skus"]) == set(SKU_LIST.split()) and last["day"]   # the canned export defines the rows; asked counts the typed 7
    page = web.get("/pictures?store=gtv").text
    assert "Earlier builds and lists" in page and "Start from the last ticket" in page
    import re as _re
    jobs = _re.findall(r"/pictures/file/([0-9a-f]{12})/attachment", page)
    assert len(set(jobs)) == 2                                                            # the newest build's files above, the older build's in the earlier-builds table
    older = next(j for j in jobs if f"/pictures/file/{j}/reply" in first_job)
    assert web.get(f"/api/store/gtv/pictures/file/{older}/attachment").status_code == 200  # the older build's files still download


def test_without_a_build_the_button_and_endpoint_stay_quiet(web, fake):
    assert web.get("/api/store/gtv/pictures/last_skus").status_code == 404
    assert "Start from the last ticket" not in web.get("/pictures?store=gtv").text
