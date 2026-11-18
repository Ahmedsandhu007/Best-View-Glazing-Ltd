"""The dynamic Amazon schedule on the Amazon page (2026-11-02): each account's hourly dispatcher prints one AMAZON_PLAN line, the dashboard shows
what it decided - products synced a day, runs, slice, how often a product is refreshed, the Keepa tokens spent - and a sync the dispatcher launched
still counts as SCHEDULED (it arrives as a workflow_dispatch; failure severity and staleness depend on 'schedule')."""
from datetime import timedelta

from conftest import NOW, make_run

from app import amazon_schedule, github_client

# the line Kidoomi's first dispatcher tick printed on 2026-11-02 (525 Amazon products), then a quiet tick of the same store
KIDOOMI_TICK = """
2026-11-02T13:41:30.1Z AMAZON_PLAN|n=525|runs=12|slice=525|cycles=12.0|daily=6300|tokens_day=7875|share=12240|key_tokens_day=28800|stores_on_key=2|interval_h=2.0|limited_by=cadence|due=yes|dispatched=yes|reason=no earlier planned sync on record
"""
QUIET_TICK = """
2026-11-02T14:41:30.1Z AMAZON_PLAN|n=525|runs=12|slice=525|cycles=12.0|daily=6300|tokens_day=7875|share=12240|key_tokens_day=28800|stores_on_key=2|interval_h=2.0|limited_by=cadence|elapsed_h=1.0|due=no|dispatched=no|reason=1.0 h since the last sync, the next is due after 2 h
"""
BIG_TICK = """
AMAZON_PLAN|n=20000|runs=6|slice=1632|cycles=0.49|daily=9792|tokens_day=12240|share=12240|key_tokens_day=28800|stores_on_key=2|interval_h=4.0|limited_by=budget|due=no|dispatched=no|reason=x
WARNING each product is refreshed only every 49 hours - the Keepa share is too small for 20,000 products
"""


def test_the_plan_line_parses_into_numbers_and_flags():
    p = amazon_schedule.parse_plan(KIDOOMI_TICK)
    assert (p["n"], p["runs"], p["slice"], p["daily"], p["tokens_day"], p["share"]) == (525, 12, 525, 6300, 7875, 12240)
    assert p["cycles"] == 12.0 and p["interval_h"] == 2.0 and p["due"] is True and p["dispatched"] is True
    assert p["limited_by"] == "cadence" and p["reason"] == "no earlier planned sync on record"
    assert amazon_schedule.parse_plan("nothing here") is None and amazon_schedule.parse_plan("") is None


def test_the_newest_line_wins_and_warnings_are_kept():
    assert amazon_schedule.parse_plan(KIDOOMI_TICK + QUIET_TICK)["dispatched"] is False
    big = amazon_schedule.parse_plan(BIG_TICK)
    assert big["warnings"] == ["each product is refreshed only every 49 hours - the Keepa share is too small for 20,000 products"]
    assert amazon_schedule.refresh_every_hours(big) == 49.0 and amazon_schedule.share_used_percent(big) == 100


def test_a_legacy_tick_is_not_a_plan():
    legacy = amazon_schedule.parse_plan("AMAZON_PLAN|runs=6|interval_h=4.0|limited_by=legacy|due=no|dispatched=no|reason=x|note=AMAZON_DYNAMIC is off - the old cadence")
    row = amazon_schedule.card_row({"id": "x"}, legacy, 3)
    assert row["on_plan"] is False and "old cadence" in row["note"]
    assert amazon_schedule.card_row({"id": "x"}, None, 0)["on_plan"] is False


def test_a_sync_the_dispatcher_launched_counts_as_scheduled_and_a_hand_run_does_not():
    planned = github_client._run_view({"id": 1, "event": "workflow_dispatch", "display_title": "Amazon Sync (Keepa) · plan", "path": ".github/workflows/run_amazon.yml"})
    assert planned["event"] == "schedule" and planned["planned"] is True
    hand = github_client._run_view({"id": 2, "event": "workflow_dispatch", "display_title": "Amazon Sync (Keepa)", "path": ".github/workflows/run_amazon.yml"})
    assert hand["event"] == "workflow_dispatch" and hand["planned"] is False
    cron = github_client._run_view({"id": 3, "event": "schedule", "display_title": "Amazon Sync (Keepa)"})
    assert cron["event"] == "schedule" and cron["planned"] is False


def test_the_api_shows_the_plan_of_a_store_on_the_dispatcher_and_an_honest_row_for_the_rest(web, fake):
    fake.runs["org/yra"].insert(0, make_run(901, "amazon_dispatch.yml", "Amazon Dispatcher (dynamic schedule)", NOW - timedelta(minutes=20)))
    fake.logs[901] = KIDOOMI_TICK + QUIET_TICK
    fake.runs["org/yra"].insert(1, make_run(902, "run_amazon.yml", "Amazon Sync (Keepa)", NOW - timedelta(hours=1), event="schedule"))
    data = web.get("/api/amazon/schedule").json()
    yra = next(s for s in data["stores"] if s["store"]["id"] == "yra")
    assert yra["on_plan"] and yra["runs"] == 12 and yra["daily"] == 6300 and yra["refresh_hours"] == 2.0
    assert yra["share_percent"] == 64 and yra["syncs_24h"] >= 1 and yra["last_tick"]["url"] and yra["last_sync"]["state"] == "success"
    gtv = next(s for s in data["stores"] if s["store"]["id"] == "gtv")
    assert gtv["on_plan"] is False                                                     # no dispatcher run in gtv's fake repository yet


def test_the_amazon_page_carries_the_card_and_the_script_fills_it(web):
    text = web.get("/amazon?store=gtv").text
    assert 'id="schedCard"' in text and 'id="schedBody"' in text and "five keys" not in text
    assert "loadSchedule" in web.get("/static/app.js?v=1").text
