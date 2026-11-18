"""Sheet health on the store page (2026-11-02): the sheet-side facts of the latest sync logs. Kidoomi's first fill made
the gaps visible - 30 rows waited with a URL but no SKU, two rows shared one eBay item, 592 rows had no URL yet - and
every one of those facts lived only in run logs until this card."""
from datetime import timedelta

from conftest import NOW, make_run

from app import sheethealth

# lines exactly as Kidoomi's 2026-11-02 canary and first Amazon run printed them
EBAY_LOG = """
2026-11-02 08:15:38,400 INFO TOTAL ROWS IN SHEET: 30
2026-11-02 08:15:41,600 WARNING 30 row(s) have a Supplier URL but no SKU yet (sheet rows 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, ...) - left out of the batch until a SKU is added
2026-11-02 08:15:41,600 INFO Manual run: limited to 0 unfilled row(s) of 0 processable - filled rows refresh on scheduled runs; set refresh_all=yes for a full sweep
2026-11-02 10:00:51,759 WARNING Row 13 (SKU 808221610721): Failed: supplier link already used on row 11 (eBay) - one listing per supplier product
2026-11-02 10:00:51,760 WARNING Row 13 (SKU 808221610721): Failed: supplier link already used on row 11 (eBay) - one listing per supplier product
"""
AMAZON_LOG = """
2026-11-02 10:11:44,288 INFO TOTAL ROWS IN SHEET: 1000
2026-11-02 10:11:46,091 INFO Skipping 592 row(s) with no eBay/Amazon Supplier URL yet (not counted against this run's batch)
2026-11-02 10:11:46,091 INFO Manual run: limited to 408 unfilled row(s) of 408 processable - filled rows refresh on scheduled runs; set refresh_all=yes for a full sweep
2026-11-02 10:25:19,899 INFO OnBuy: 196 created, 0 updated, 0 deferred (awaiting go-live), 0 postponed (transient), 0 failed, 0 removed (brand rejected), 0 brand-blocked (flagged), 4 skipped (dead eBay link), 0 awaiting category (worklist), 0 suspended-locked, 0 no-price skipped, 0 protected (repair pending), 0 creates paused
"""


def test_parse_reads_the_sheet_side_lines_and_dedupes_repeated_warnings():
    d = sheethealth.parse_sheet(EBAY_LOG)
    assert d["rows"] == 30 and d["unfilled"] == 0 and d["processable"] == 0
    assert d["no_sku"]["count"] == 30 and d["no_sku"]["sample_rows"][:3] == ["2", "3", "4"]
    assert d["duplicate_links"] == [{"row": 13, "sku": "808221610721", "original_row": 11}]   # printed twice, kept once
    assert "created" not in d                                                                 # no tally line in this log


def test_parse_reads_the_tally_and_the_missing_url_count():
    d = sheethealth.parse_sheet(AMAZON_LOG)
    assert d["rows"] == 1000 and d["no_url"] == 592 and d["processable"] == 408
    assert d["created"] == 196 and d["failed"] == 0 and d["brand_blocked"] == 0 and d["dead_links"] == 4
    assert sheethealth.parse_sheet("") == {}


def test_issues_name_the_owner_fixes_first():
    d = sheethealth.parse_sheet(EBAY_LOG)
    named = [(name, n) for name, n, _cls in sheethealth.issues(d)]
    assert named[0] == ("no SKU yet", 30) and ("duplicate supplier links", 1) in named
    amazon = sheethealth.issues(sheethealth.parse_sheet(AMAZON_LOG))
    assert ("no supplier URL yet", 592, "quiet") in amazon and ("dead supplier links", 4, "warn") in amazon


def test_the_api_reads_the_latest_runs_and_the_store_page_carries_the_card(web, fake):
    fake.runs["org/yra"].insert(0, make_run(701, "run.yml", "YRA Full-Auto Sync", NOW - timedelta(hours=1)))
    fake.runs["org/yra"].insert(1, make_run(702, "run_amazon.yml", "Amazon Sync (Keepa)", NOW - timedelta(hours=2)))
    fake.logs[701] = EBAY_LOG
    fake.logs[702] = AMAZON_LOG
    data = web.get("/api/store/yra/sheet").json()
    assert data["ebay"]["no_sku"]["count"] == 30 and data["ebay"]["run"]["url"]
    assert data["amazon"]["created"] == 196 and data["amazon"]["no_url"] == 592
    assert ["no SKU yet", 30, "warn"] in data["ebay"]["issues"]
    assert web.get("/api/store/nope/sheet").status_code == 404

    text = web.get("/store/yra").text
    assert 'id="sheetCard"' in text and 'id="sheethealth"' in text
    assert "loadSheetHealth" in web.get("/static/app.js?v=1").text
