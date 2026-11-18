"""Orphans on the Catalogue page (2026-11-02): the live listings on no sheet row - Arden 2,782, Makstore 3,353,
OpenMaal 4,962 at the 19th log check, stable night over night (the manual/import era). They get no price fix, no stock
sync and no purge, so the card puts the in-stock ones first and hands the SKUs over paste-ready."""
from datetime import timedelta

from conftest import NOW, make_run

from app import orphans

# lines exactly as Arden's 2026-11-01 nightly printed them (the scan prints the block; the log can carry it twice)
REAL_SCAN_LOG = """
2026-11-01T10:21:33.1Z ORPHANS (live on OnBuy, on no product tab): 3
2026-11-01T10:21:33.2Z ORPHAN|0000016945579-manual|price=205.00|stock=1|created=2026-10-28 09:43|ZVOX Dialogue Clarifying Sound Bar with Patented Hearing Tec
2026-11-01T10:21:33.2Z ORPHAN|0000061733886-Chef1(MH***|price=7.85|stock=0|created=2026-04-09 13:00|NKS Radar Key Disabled Toilet Bathroom Door Access Braille E
2026-11-01T10:21:33.3Z ORPHAN|0000126758953-zplus|price=419.99|stock=1|created=2026-10-31 10:54|Sharp 50 Inch 4T-C50JH6425KB Smart Roku 4K UHD HDR Mini LED
2026-11-01T10:21:40.0Z ORPHANS (live on OnBuy, on no product tab): 3
2026-11-01T10:21:40.1Z ORPHAN|0000016945579-manual|price=205.00|stock=1|created=2026-10-28 09:43|ZVOX Dialogue Clarifying Sound Bar with Patented Hearing Tec
"""


def test_parse_reads_the_count_and_the_rows_and_dedupes_the_repeated_block():
    parsed = orphans.parse_orphans(REAL_SCAN_LOG)
    assert parsed["count"] == 3 and len(parsed["rows"]) == 3
    first = parsed["rows"][0]
    assert first == {"sku": "0000016945579-manual", "price": 205.00, "stock": 1,
                     "created": "2026-10-28 09:43", "title": "ZVOX Dialogue Clarifying Sound Bar with Patented Hearing Tec"}
    assert parsed["rows"][1]["sku"] == "0000061733886-Chef1(MH***"                       # odd characters in a SKU survive
    assert orphans.parse_orphans("no such lines") == {"count": None, "rows": []}


def test_display_puts_the_in_stock_ones_first_and_the_newest_of_those_on_top():
    rows = orphans.display_rows(orphans.parse_orphans(REAL_SCAN_LOG)["rows"])
    assert [r["sku"] for r in rows] == ["0000126758953-zplus", "0000016945579-manual", "0000061733886-Chef1(MH***"]


def test_the_api_reads_the_latest_scan_and_the_csv_carries_every_row(web, fake):
    fake.runs["org/yra"].append(make_run(601, "scan_content_mismatch.yml", "Scan Content Mismatch (read-only)", NOW - timedelta(hours=2)))
    fake.logs[601] = REAL_SCAN_LOG
    data = web.get("/api/store/yra/orphans").json()
    assert data["count"] == 3 and data["in_stock"] == 2 and not data["truncated"]
    assert data["rows"][0]["sku"] == "0000126758953-zplus" and data["run"]["url"]

    resp = web.get("/api/store/yra/orphans.csv")
    assert resp.status_code == 200 and "text/csv" in resp.headers["content-type"]
    assert "attachment" in resp.headers["content-disposition"]
    text = resp.text
    assert text.splitlines()[0] == "sku,price,stock,created,title" and "0000061733886-Chef1(MH***" in text

    assert web.get("/api/store/nope/orphans").status_code == 404
    assert web.get("/api/store/nope/orphans.csv").status_code == 404


def test_without_a_scan_run_the_nightly_carries_the_same_lines(web, fake):
    fake.logs[10] = REAL_SCAN_LOG                                                        # gtv's canned nightly_reconcile run
    data = web.get("/api/store/gtv/orphans").json()
    assert data["count"] == 3 and data["in_stock"] == 2


def test_the_catalogue_page_carries_the_card_and_the_script_fills_it(web):
    text = web.get("/catalogue?store=gtv").text
    assert 'id="orphansCard"' in text and 'id="orphans"' in text
    assert "loadOrphans" in web.get("/static/app.js?v=1").text
