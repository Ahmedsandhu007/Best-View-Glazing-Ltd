"""The suspended to-do on the Delete page (2026-10-29): every tool's "SUSPENDED" reports in one list, ticked off as the user deletes them by hand.

The day it was built, deleting the dead rows surfaced 243 suspended listings in one afternoon (OnBuy's API refuses to delete them); the
reports lived in run logs and Downloads files, and nothing remembered which were already handled.
"""
from datetime import timedelta

from conftest import NOW, PURGE_SUSPENDED_LOG, make_run

from app import suspended

# the delete-by-list answer exactly as 2026-10-29's real Arden run printed it
DELETE_SUSPENDED_LOG = """
INFO batch 1 (10 SKUs) -> HTTP 400: {"error":{"message":"No listings were deleted."}}
INFO DONE in 2 request(s): 3 suspended
INFO SUSPENDED (needs OnBuy): 275381389406
INFO SUSPENDED (needs OnBuy): 275713042528
INFO SUSPENDED (needs OnBuy): 305812347721
"""


def test_merge_makes_one_row_per_sku_keeps_the_title_and_sorts_the_waiting_first():
    reports = [
        suspended.report("275381389406", "2026-10-29", "delete by list", "u2"),
        suspended.report("305812347721", "2026-10-27", "dead-row purge", "u1", title="Women Waterproof Walking Shoes"),
        suspended.report("0305812347721", "2026-10-29", "delete by list", "u2"),          # the same listing, a leading zero on the sheet
    ]
    rows = suspended.merge(reports)
    assert len(rows) == 2
    shoe = next(r for r in rows if r["title"])
    assert shoe["sku"] == "305812347721" and shoe["first"] == "2026-10-27" and shoe["last"] == "2026-10-29" and shoe["source"] == "delete by list"
    assert suspended.counts(rows) == {"waiting": 2, "done": 0, "total": 2}
    assert suspended.waiting_skus(rows) == [r["sku"] for r in rows]


def test_merge_lays_the_done_marks_over_and_sinks_the_done_rows():
    reports = [suspended.report("111", "2026-10-29", "nightly"), suspended.report("222", "2026-10-28", "nightly")]
    rows = suspended.merge(reports, {"111": {"actor": "sadia", "at": "2026-10-29T15:00:00Z"}})
    assert [r["sku"] for r in rows] == ["222", "111"]                                     # the done one sinks below the waiting one
    assert rows[1]["done"] and rows[1]["by"] == "sadia" and not rows[0]["done"]
    assert suspended.waiting_skus(rows) == ["222"] and suspended.counts(rows) == {"waiting": 1, "done": 1, "total": 2}


def test_the_api_merges_the_tools_reports_and_the_marks_survive_a_fresh_read(web, fake):
    fake.runs["org/yra"].append(make_run(301, "dup_removal.yml", "Duplicate Removal (sheet rows + OnBuy listings)", NOW - timedelta(hours=3), event="workflow_dispatch"))
    fake.runs["org/yra"].append(make_run(302, "purge_dead_rows.yml", "Purge Dead eBay Rows (dry run / live)", NOW - timedelta(hours=30), event="workflow_dispatch"))
    fake.logs[301] = DELETE_SUSPENDED_LOG
    fake.logs[302] = PURGE_SUSPENDED_LOG
    data = web.get("/api/store/yra/suspended").json()
    assert data["counts"] == {"waiting": 4, "done": 0, "total": 4}
    by_sku = {r["sku"]: r for r in data["rows"]}
    assert by_sku["305812347721"]["title"].startswith("Women Waterproof")                 # the purge knew the title, the delete run did not
    assert by_sku["305812347721"]["source"] == "delete by list"                           # ... but the delete run reported it last
    assert by_sku["Ebay-174409866283-2"]["source"] == "dead-row purge"

    marked = web.post("/api/store/yra/suspended/mark", json={"sku": "275381389406", "done": True}).json()
    assert marked == {"ok": True, "sku": "275381389406", "done": True}
    again = web.get("/api/store/yra/suspended").json()
    row = next(r for r in again["rows"] if r["sku"] == "275381389406")
    assert row["done"] and row["by"] == "owner" and again["counts"]["waiting"] == 3
    assert "275381389406" not in again["waiting_skus"] and again["rows"][-1]["sku"] == "275381389406"

    web.post("/api/store/yra/suspended/mark", json={"sku": "275381389406", "done": False})
    assert web.get("/api/store/yra/suspended").json()["counts"] == {"waiting": 4, "done": 0, "total": 4}


def test_a_yra_removal_wipes_suspended_refusals_reach_the_list_too(web, fake):
    fake.runs["org/yra"].append(make_run(303, "yra_removal.yml", "YRA Removal (sheet rows + OnBuy listings)", NOW - timedelta(hours=2), event="workflow_dispatch"))
    fake.logs[303] = "INFO DONE in 3 request(s): 1 suspended\nINFO SUSPENDED (needs OnBuy): 883399112233\n"
    data = web.get("/api/store/yra/suspended").json()
    row = next((r for r in data["rows"] if r["sku"] == "883399112233"), None)
    assert row and row["source"] == "delete by list" and not row["done"]


def test_the_mark_endpoint_refuses_an_empty_sku_and_an_unknown_store(web):
    assert web.post("/api/store/yra/suspended/mark", json={"sku": " ", "done": True}).status_code == 400
    assert web.post("/api/store/nope/suspended/mark", json={"sku": "1", "done": True}).status_code == 404
    assert web.get("/api/store/nope/suspended").status_code == 404


def test_the_delete_page_carries_the_card_and_the_script_fills_it(web):
    text = web.get("/delete?store=gtv").text
    assert 'id="suspCard"' in text and 'id="suspBody"' in text
    assert "suspMark" in web.get("/static/app.js?v=1").text
