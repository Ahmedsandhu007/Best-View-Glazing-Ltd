"""The eBay page on the fake GitHub: the eBay syncs carry the REAL logs of tests/ebay_data.py."""
import html
from datetime import timedelta

from conftest import NOW, make_run
from ebay_data import MAKSTORE_LOG, YRA_LOG

NEWEST, SIX_H, FOURTEEN_H, FAILED, CANCELLED = 90, 91, 92, 93, 94


def add_runs(fake, newest_log=YRA_LOG):
    """Three good syncs (1 h, 6 h and 14 h ago), a failed one and a cancelled one; the newest first."""
    fake.runs["org/gtv"] = [make_run(NEWEST, "run.yml", "Generate OnBuy Feed", NOW - timedelta(hours=1)),
                            make_run(CANCELLED, "run.yml", "Generate OnBuy Feed", NOW - timedelta(hours=3), conclusion="cancelled"),
                            make_run(SIX_H, "run.yml", "Generate OnBuy Feed", NOW - timedelta(hours=6)),
                            make_run(FOURTEEN_H, "run.yml", "Generate OnBuy Feed", NOW - timedelta(hours=14)),
                            make_run(FAILED, "run.yml", "Generate OnBuy Feed", NOW - timedelta(hours=20), conclusion="failure")] + fake.runs["org/gtv"]
    fake.logs.update({NEWEST: newest_log, SIX_H: YRA_LOG, FOURTEEN_H: MAKSTORE_LOG, FAILED: "", CANCELLED: ""})


def page(web):
    r = web.get("/ebay?store=gtv")
    assert r.status_code == 200
    return html.unescape(r.text)


def test_the_page_shows_the_last_good_sync_the_allowance_and_the_rows_that_are_never_refreshed(web, fake):
    add_runs(fake)
    text = page(web)
    assert "last good sync" in text and "1,690 eBay calls left" in text and "7,001" in text
    assert "No supplier link" in text and "672" in text and "6,069 / 2 / 229" in text
    assert "Refreshed on eBay" in text and "1,499" in text and "(batch 1,499)" in text and "the batch took 38 min" in text
    assert "Dead rows removed" in text and "(16 out of stock)" in text and "1,496" in text and "7 followed a price down" in text
    assert "1,471 free" in text and "9 paid" in text and "3 not stated" in text


def test_how_long_the_whole_sheet_takes_comes_from_what_the_syncs_really_did(web, fake):
    add_runs(fake)
    text = page(web)
    # the newest three good syncs: 1,499 + 1,499 + 560 rows in 24 hours against 7,001 - 672 = 6,329 rows that are due
    assert "whole sheet every ~42.7 h" in text and "The whole sheet comes round about every 42.7 hours." in text
    assert "3,558" in text and "(about 1,186 a sync)" in text and "6,329" in text
    assert "The whole sheet takes about" not in text


def test_a_slow_cycle_is_a_warning(web, fake):
    slow = YRA_LOG.replace("Updated rows: 1499", "Updated rows: 100")
    add_runs(fake, newest_log=slow)
    fake.logs[SIX_H] = slow
    fake.logs[FOURTEEN_H] = slow
    text = page(web)
    assert "The whole sheet takes about 506.3 hours to come round" in text and 'class="pill failed"' in text


def test_a_batch_cut_to_fit_ebays_allowance_and_suspended_listings_are_shown(web, fake):
    add_runs(fake, newest_log=MAKSTORE_LOG)
    text = page(web)
    assert "Batch cut" in text and "1,091 to 560" in text
    assert "9 purged listing(s) are suspended on OnBuy" in text and "385476307274" in text and "delete them by hand" in text


def test_the_table_of_syncs_shows_failed_and_cancelled_runs_too(web, fake):
    add_runs(fake)
    table = page(web).split("The last syncs")[-1]
    assert table.count("<tr>") >= 6 and "cancelled" in table and "failure" in table and "success" in table
    assert "(cut)" in table                                                           # the Makstore log's run in the table was cut
    assert "1,690" in table and "16" in table


def test_the_budget_variables_are_shown_not_edited(web, fake):
    add_runs(fake)
    fake.variables["org/gtv"] += [{"name": "EBAY_DAILY_CALL_BUDGET", "value": "4500", "updated_at": "2026-10-01T00:00:00Z"}]
    text = page(web)
    assert "variable EBAY_DAILY_CALL_BUDGET = 4500" in text and "4,800" in text and "These are repository variables: change them on the Settings page" in text
    assert web.post("/ebay").status_code in (404, 405)


def test_a_store_with_no_finished_sync_says_so_and_one_without_the_workflow_says_that(web, fake):
    assert "No finished sync with numbers yet" in page(web)                          # the default fake's only run carries the purge's lines, no sync numbers
    fake.definitions.pop("run.yml")
    assert "has no eBay sync workflow" in page(web)


def test_the_menu_has_the_page(web):
    text = web.get("/ebay?store=gtv").text
    assert 'class="on">eBay</a>' in text and 'href="/ebay' in text
