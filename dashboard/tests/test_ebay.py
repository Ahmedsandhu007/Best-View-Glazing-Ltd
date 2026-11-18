"""The eBay card's pure part: the eBay sync's log (the stores' REAL logs of 2026-10-28) and the estimate of how long the whole sheet takes to come round."""
from datetime import timedelta

from conftest import NOW, iso
from ebay_data import ARDEN_LOG, GTV_LOG, MAKSTORE_LOG, OPENMAAL_LOG, YRA_LOG

from app import ebay


def sync(facts, hours_ago):
    return {"created_at": iso(NOW - timedelta(hours=hours_ago)), "facts": facts}


# ---- the log ------------------------------------------------------------------------------------------------------------------------
def test_a_stores_sync_log_gives_rows_batch_allowance_prices_and_pushes():
    f = ebay.parse_sync(GTV_LOG)
    assert f["rows"] == 4440 and f["no_link"] == 475 and f["rotation"] == {"in_stock": 3798, "out_of_stock": 2, "flagged": 2}
    assert f["batch"] == 740 and f["budget"] == 4800 and f["runs_per_day"] == 24 and f["processing"] == 740 and f["updated_rows"] == 740 and f["minutes"] == 15
    assert f["allowance_left"] == 1780 and f["reserve"] == 150 and "batch_cut" not in f
    assert f["priced"] == 733 and f["followed_down"] == 5
    assert f["delivery"] == {"free": 714, "paid": 26, "mean": 4.65, "median": 3.99, "max": 19.99, "not_stated": 0, "cells_written": 1}
    assert f["onbuy"] == {"created": 0, "updated": 179, "deferred": 19, "postponed": 0, "failed": 0, "brand_blocked": 0, "protected": 1, "suspended": 0}
    assert f["purge"] == {"mode": "live", "held_back": 2, "suspended": []} and "warnings" not in f


def test_the_dead_rows_the_purge_removed_are_read_with_the_ones_eBay_confirmed_gone():
    f = ebay.parse_sync(YRA_LOG)
    assert f["rows"] == 7001 and f["no_link"] == 672 and f["batch"] == 1499 and f["updated_rows"] == 1499 and f["minutes"] == 38 and f["allowance_left"] == 1690
    assert f["purge"]["done"] == 16 and f["purge"]["done_oos"] == 16 and f["purge"]["done_brand"] == 0 and f["purge"]["ebay_gone"] == 16 and f["purge"]["suspended_count"] == 0
    assert f["delivery"]["not_stated"] == 3 and f["delivery"]["paid"] == 9


def test_a_batch_cut_to_fit_ebays_allowance_and_listings_suspended_on_onbuy_are_named():
    f = ebay.parse_sync(MAKSTORE_LOG)
    assert f["batch"] == 1091 and f["batch_cut"] == {"from": 1091, "to": 560} and f["updated_rows"] == 560 and f["allowance_left"] == 710
    assert f["purge"]["done"] == 9 and f["purge"]["suspended_count"] == 9 and len(f["purge"]["suspended"]) == 9 and "385476307274" in f["purge"]["suspended"]
    assert f["onbuy"]["created"] == 3 and f["onbuy"]["deferred"] == 13


def test_the_other_stores_read_the_same_way():
    arden, openmaal = ebay.parse_sync(ARDEN_LOG), ebay.parse_sync(OPENMAAL_LOG)
    assert arden["rows"] == 7143 and arden["processing"] == 738 and arden["no_link"] == 161 and arden["purge"]["done"] == 11 and arden["delivery"]["cells_written"] == 2
    assert openmaal["rows"] == 1232 and openmaal["processing"] == 1075 and openmaal["rotation"]["in_stock"] == 1230 and openmaal["delivery"]["not_stated"] == 12
    assert "done" not in openmaal["purge"] and openmaal["minutes"] == 24


def test_a_log_with_nothing_in_it_gives_nothing_and_a_run_that_stopped_early_counts_its_batch():
    assert ebay.parse_sync("") == {}
    assert ebay.processed({"updated_rows": 560, "processing": 1091}) == 560 and ebay.processed({"processing": 300}) == 300 and ebay.processed({}) == 0
    errors = ebay.parse_sync("2026-10-28 01:00:00,000 ERROR eBay call failed: HTTP 429 rate limit\n2026-10-28 01:00:01,000 INFO TOTAL ROWS IN SHEET: 10\n")
    assert errors["warnings"] == ["eBay call failed: HTTP 429 rate limit"] and errors["rows"] == 10


# ---- how often the whole sheet comes round ------------------------------------------------------------------------------------------------
def test_the_refresh_cycle_comes_from_the_rows_the_syncs_really_did_in_a_day():
    facts = ebay.parse_sync(YRA_LOG)                                                # 7,001 rows, 672 without a supplier link: 6,329 are due
    runs = [sync(facts, 1), sync(facts, 6), sync(facts, 14), sync(facts, 30)]       # three syncs inside the 24 hours before the newest, one older
    est = ebay.cycle_estimate(runs)
    assert est == {"hours": 33.8, "runs": 3, "per_run": 1499, "per_day": 4497, "eligible": 6329, "window_hours": 24.0, "slow": False}


def test_a_slow_cycle_is_marked_and_nothing_to_go_on_is_none():
    slow = ebay.cycle_estimate([sync({"rows": 7000, "no_link": 0, "updated_rows": 150}, 2)])
    assert slow["hours"] == 1120.0 and slow["slow"] is True and slow["runs"] == 1
    assert ebay.cycle_estimate([]) is None and ebay.cycle_estimate(None) is None
    assert ebay.cycle_estimate([sync({"rows": 7000}, 1)]) is None                   # a run that refreshed nothing says nothing
    assert ebay.cycle_estimate([{"created_at": "not a time", "facts": {"rows": 5, "updated_rows": 5}}]) is None


def test_one_good_sync_per_day_of_the_whole_sheet_is_a_24_hour_cycle():
    est = ebay.cycle_estimate([sync({"rows": 1232, "no_link": 2, "updated_rows": 1230}, 3)])
    assert est["hours"] == 24.0 and est["per_day"] == 1230 and est["slow"] is False
