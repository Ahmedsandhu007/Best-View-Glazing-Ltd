from datetime import timedelta

from conftest import IN_3_DAYS, NIGHTLY_LOG, NOW, ORDERS_LOG, TODAY, iso, make_run

from app import digest


def test_parse_orders_counts_due_today_and_overdue():
    out = digest.parse_orders(ORDERS_LOG, today=TODAY)
    assert out["count"] == 3 and out["due_today"] == 1 and out["overdue"] == 1
    first = out["orders"][0]                      # sorted by dispatch-by date: the overdue August order first
    assert first["order_id"] == "T6N77VB" and first["overdue"] and first["skus"] == ["304285306230"]
    assert out["orders"][1]["order_id"] == "T6QPP5J" and out["orders"][1]["due_today"]
    assert out["orders"][2]["due"] == IN_3_DAYS


def test_parse_nightly_headline_numbers():
    facts = digest.parse_nightly(NIGHTLY_LOG)
    assert facts["mismatched"] == 3 and facts["zeroed"] == 1 and facts["held"] == 3
    assert facts["rows_deleted"] == 1 and facts["underpriced"] == 589
    assert facts["corrected"] == 1234 and facts["fix_failed"] == 6
    assert facts["on_sale"] == 0 and facts["listings"] == 7938
    assert facts["zeroed_skus"] == [{"sku": "203648462166", "kind": "shift+1", "row": 1149}]
    assert facts["borderlines"] == [{"sku": "Ama-B0BRHJTQZ6-5", "overlap": 0.44}]


def test_key_lines_drop_noise_and_keep_decisions():
    lines = digest.key_lines(NIGHTLY_LOG)
    assert any("ZEROED 203648462166" in l for l in lines)
    assert any("FIX done" in l for l in lines)
    assert not any("Requirement already satisfied" in l for l in lines)


def test_parse_budget_keepa_and_sync_summary():
    assert digest.parse_ebay_budget("buy/Browse/buy.browse: limit 5000 remaining 3920 window 86400s") == {"limit": 5000, "remaining": 3920}
    keepa = digest.parse_keepa("INFO Keepa: 127 token(s) used, 805 left, refill 20/min\nINFO Keepa: 120 token(s) used, 554 left, refill 20/min")
    assert keepa == {"tokens_left": 554, "last_batch_used": 120, "batches": 2}
    s = digest.parse_sync_summary("INFO Updated rows: 2271\nINFO OnBuy: 0 created, 197 updated, 1 deferred (awaiting go-live), 0 postponed, 0 failed")
    assert s["updated_rows"] == 2271 and s["onbuy_updated"] == 197 and s["deferred"] == 1 and s["failed"] == 0


def test_summarize_runs_counts_and_stale():
    runs = [
        make_run(3, "run.yml", "Sync", NOW - timedelta(hours=1)),
        make_run(2, "run.yml", "Sync", NOW - timedelta(hours=3), conclusion="cancelled"),
        make_run(1, "backfill_onbuy_status.yml", "Backfill", NOW - timedelta(hours=40)),
        make_run(0, "daily_digest.yml", "Weekly Fleet Digest", NOW - timedelta(days=5)),
    ]
    out = digest.summarize_runs(runs, iso(NOW - timedelta(hours=24)), now=NOW)
    assert out["count"] == 2 and out["cancels"] == 1 and out["failures"] == 0
    assert out["by_workflow"]["Sync"] == {"success": 1, "cancelled": 1}
    stale_paths = {s["path"] for s in out["stale"]}
    assert "backfill_onbuy_status.yml" in stale_paths          # 40 h > its 8 h cadence
    assert "daily_digest.yml" not in stale_paths                # weekly: 5 days is fine
    assert "run.yml" not in stale_paths
