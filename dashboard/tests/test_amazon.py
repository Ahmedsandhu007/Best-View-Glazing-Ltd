"""The Amazon card's pure parts: the sync-log parser (on REAL logs), the biggest price falls, the seller census, the settings."""
from amazon_data import CENSUS_LOG, MAKSTORE_LOG, NEGATIVE_BALANCE_LOG, OPENMAAL_LOG, YRA_FAILED_LOG

from app import amazon

WORKFLOW = """
      - name: Run script
        env:
          KEEPA_BUYBOX: ${{ vars.KEEPA_BUYBOX }}
          AMAZON_OWN_OFFER_ONLY: ${{ vars.AMAZON_OWN_OFFER_ONLY }}
          KEEPA_DROP_HOLD_PERCENT: ${{ vars.KEEPA_DROP_HOLD_PERCENT }}
          MAX_PRODUCTS_PER_RUN: ${{ vars.AMAZON_MAX_PRODUCTS_PER_RUN || '300' }}
"""


def view(variables=(), wired=None):
    return amazon.settings_view([{"name": k, "value": v} for k, v in dict(variables).items()], wired if wired is not None else {s["variable"] for s in amazon.SETTINGS})


# ---- the log ----------------------------------------------------------------------------------------------------------------------
def test_a_two_job_sync_log_gives_the_keepa_numbers_the_guards_and_the_onbuy_summary():
    f = amazon.parse_sync(MAKSTORE_LOG)
    assert f["processing"] == 1600 and f["answered"] == 1600 and f["asked"] == 1600 and f["rows_in_sheet"] == 3205
    # Keepa: 17 batches (16 of the main request + the second looks), the plan refills 20 a minute, the run waited for it 7 times and ended with 39 tokens
    assert f["tokens_used"] == 1941 and f["batches"] == 17 and f["refill"] == 20 and f["waits"] == 7 and f["wait_seconds"] == 2294 and f["tokens_left"] == 39
    assert f["fetched_live"] == 1600 and f["per_asin"] == 1.21
    assert f["looked_up_flagged"] == 17 and f["looked_up"] == 17                               # the second look at the Buy Box
    assert f["buybox_priced"] == 8 and f["usual_level"] == 467 and f["by_hand"] == 9
    assert f["own_offer_only"] == 9 and f["no_offer"] == 1 and len(f["unavailable"]) == 10      # guard 1: Amazon's own unbuyable offer is not a third-party source
    assert {"asin": "B08PL4XKKR", "why": "Delayed (Amazon's own offer only)"} in f["unavailable"]
    assert f["onbuy"] == {"created": 0, "updated": 195, "deferred": 2, "postponed": 0, "failed": 0, "brand_blocked": 43, "protected": 1, "suspended": 0}
    assert f["zeroed"] == 3 and f["bounced"] == 0
    assert "keepa_failed" not in f and "held" not in f and len(f["moves"]) == 12 and f["moves"][0]["sku"]


def test_a_run_that_ran_out_of_keepa_tokens_says_so_and_changed_nothing():
    f = amazon.parse_sync(YRA_FAILED_LOG)
    assert f["keepa_failed"] == {"asins": 2216, "reason": "keepa product: out of tokens"}
    assert f["processing"] == 2275 and f["waits"] == 14 and f["tokens_used"] == 2617 and f["tokens_left"] == -34 and f["refill"] == 20          # it ended 34 tokens overdrawn
    assert f["onbuy"]["updated"] == 0 and "moves" not in f


def test_a_one_job_log_of_a_store_without_a_prefetch_reads_the_same_way():
    f = amazon.parse_sync(OPENMAAL_LOG)
    assert f["processing"] == 49 and f["answered"] == 44 and f["asked"] == 44 and f["tokens_used"] == 49 and f["tokens_left"] == 1151 and "waits" not in f
    assert f["usual_level"] == 15 and f["no_offer"] == 3 and f["own_offer_only"] == 0 and f["onbuy"]["updated"] == 43 and f["onbuy"]["deferred"] == 1


def test_a_run_whose_keepa_balance_goes_negative_is_read_like_any_other():
    """YRA and Arden end most syncs overdrawn ("-108 left"): the lines carry a minus sign, and a parser that skipped them showed a 25-hour-old sync as the last good one (2026-10-28)."""
    f = amazon.parse_sync(NEGATIVE_BALANCE_LOG)
    assert f["answered"] == 2275 and f["asked"] == 2275 and f["processing"] == 2275 and f["tokens_used"] == 2786 and f["batches"] == 35 and f["refill"] == 20
    assert f["tokens_left"] == -12 and f["waits"] == 16 and f["wait_seconds"] == 6920 and f["per_asin"] == 1.22
    assert f["looked_up_flagged"] == 8 and f["looked_up"] == 0 and f["own_offer_only"] == 8 and f["no_offer"] == 5          # no token left for the second looks: the 8 flagged rows stay held
    assert amazon.token_note(f).endswith("-12 left at the end.")
    waiting = amazon.parse_sync("2026-10-27 21:00:00,000 INFO Keepa: -37 token(s) left, 100 needed - waiting 2850s for the refill (20/min)\n")
    assert waiting["waits"] == 1 and waiting["wait_seconds"] == 2850


def test_the_price_drop_guard_lines_are_read():
    text = ("2026-10-27 12:00:00,100 INFO PRICE DROP HELD: B0FB2L7CCX is at 31% of its usual level - treated as unavailable until it recovers\n"
            "2026-10-27 12:00:00,200 INFO PRICE DROP HELD: B000000001 is at 12% of its usual level - treated as unavailable until it recovers\n"
            "2026-10-27 12:09:00,000 INFO Amazon offers held because their price fell below 40% of the usual level (error price / glitch), read as unavailable: 2\n")
    f = amazon.parse_sync(text)
    assert f["held"] == [{"asin": "B0FB2L7CCX", "percent": 31}, {"asin": "B000000001", "percent": 12}] and f["drop_held"] == 2 and f["drop_hold_percent"] == 40


def test_a_sku_with_a_space_or_a_dash_suffix_is_kept_whole_in_a_price_line():
    text = "2026-10-27 12:00:00,100 INFO Row 598 (SKU 0000069168437 -Messam): Amazon price re-derived from current cost: 47.78 -> 19.73\n"
    assert amazon.parse_sync(text)["moves"] == [{"row": 598, "sku": "0000069168437 -Messam", "old": 47.78, "new": 19.73}]


def test_the_token_note_is_one_plain_sentence():
    note = amazon.token_note(amazon.parse_sync(MAKSTORE_LOG))
    assert note == "1,941 tokens used (about 1.21 per product), the plan refills 20 a minute, the run waited 38 min for the refill, 39 left at the end."
    assert amazon.token_note({}) == "" and amazon.waited_minutes({"wait_seconds": 2294}) == 38


# ---- the biggest falls ------------------------------------------------------------------------------------------------------------
def test_the_biggest_price_falls_come_first_and_big_ones_are_counted_as_alerts():
    moves = amazon.parse_sync(MAKSTORE_LOG)["moves"]
    pm = amazon.price_moves(moves, top=3)
    assert pm["falls"][0] == {"row": 89, "sku": "327210340093", "old": 227.65, "new": 117.22, "percent": -48.5}
    assert [f["percent"] for f in pm["falls"]] == sorted(f["percent"] for f in pm["falls"]) and len(pm["falls"]) == 3
    assert pm["alerts"] == 1 and pm["alert_percent"] == 25.0 and pm["count"] == 12 and pm["average"] > 0


def test_a_rise_a_tie_and_a_zero_old_price_are_not_falls():
    pm = amazon.price_moves([{"row": 1, "sku": "a", "old": 10.0, "new": 12.0}, {"row": 2, "sku": "b", "old": 10.0, "new": 10.0}, {"row": 3, "sku": "c", "old": 0.0, "new": 5.0},
                             {"row": 4, "sku": "d", "old": 20.0, "new": 10.0}])
    assert pm["count"] == 1 and pm["falls"][0]["sku"] == "d" and pm["falls"][0]["percent"] == -50.0 and pm["alerts"] == 1
    assert amazon.price_moves([])["count"] == 0 and amazon.price_moves(None)["falls"] == []


# ---- the seller census ------------------------------------------------------------------------------------------------------------
def test_the_census_counts_rows_by_seller_and_what_the_strict_rule_would_zero():
    f = amazon.parse_census(CENSUS_LOG)
    assert f["tab"] == "Amazon" and f["rows"] == 3028
    assert f["sellers"] == [{"seller": "3rd party (lowest New)", "all": 2236, "live": 2236}, {"seller": "Amazon", "all": 557, "live": 557}, {"seller": "(none recorded)", "all": 235, "live": 0}]
    assert f["would_zero"] == 2236 and f["live"] == 2793 and f["would_zero_share"] == 80.1
    assert amazon.parse_census("nothing here") == {}


# ---- the settings -----------------------------------------------------------------------------------------------------------------
def test_with_no_variables_every_setting_is_its_default_and_none_is_set():
    rows = {r["key"]: r for r in view()}
    assert rows["drop_hold"]["value"] == 40.0 and rows["real_lookup"]["value"] is True and rows["real_max"]["value"] == 100 and rows["regular_price"]["value"] is True
    assert rows["buybox"]["value"] is False and rows["own_only"]["value"] is False and rows["max_products"]["value"] == 300
    assert not any(r["set"] or r["changed"] or r["unreadable"] for r in rows.values()) and all(r["wired"] for r in rows.values())


def test_a_value_is_read_the_way_the_sync_reads_it():
    rows = {r["key"]: r for r in view({"KEEPA_DROP_HOLD_PERCENT": "25", "KEEPA_REAL_PRICE_LOOKUP": "off", "KEEPA_REGULAR_PRICE": "maybe", "AMAZON_OWN_OFFER_ONLY": "TRUE",
                                       "KEEPA_BUYBOX": "no", "KEEPA_REAL_PRICE_MAX": "lots", "AMAZON_MAX_PRODUCTS_PER_RUN": "2275"})}
    assert rows["drop_hold"]["value"] == 25.0 and rows["drop_hold"]["set"] and rows["drop_hold"]["changed"]
    assert rows["real_lookup"]["value"] is False                      # no / 0 / false / off switch a "default on" setting off
    assert rows["regular_price"]["value"] is True                     # anything else leaves it on
    assert rows["own_only"]["value"] is True and rows["buybox"]["value"] is False
    assert rows["real_max"]["value"] == 100 and rows["real_max"]["unreadable"] and rows["real_max"]["set"]      # unreadable text = the default, and the page says so
    assert rows["max_products"]["value"] == 2275 and rows["max_products"]["changed"]
    assert view({"KEEPA_DROP_HOLD_PERCENT": "0"})[1]["value"] == 0.0 and view({"KEEPA_DROP_HOLD_PERCENT": "0"})[1]["changed"]       # 0 = the guard is off, not "unset"


def test_the_workflow_file_tells_which_variables_the_sync_really_reads():
    wired = amazon.read_wiring(WORKFLOW)
    assert wired == {"KEEPA_BUYBOX", "AMAZON_OWN_OFFER_ONLY", "KEEPA_DROP_HOLD_PERCENT", "AMAZON_MAX_PRODUCTS_PER_RUN"}
    rows = {r["key"]: r for r in view(wired=wired)}
    assert rows["own_only"]["wired"] and rows["max_products"]["wired"] and not rows["real_lookup"]["wired"] and not rows["real_max"]["wired"]


def test_a_save_writes_only_what_changed_and_never_creates_a_variable_for_a_default():
    rows = view()
    writes, error = amazon.changes_from(rows, {"drop_hold": "40", "own_only": True, "real_lookup": True, "real_max": "100", "max_products": "1600"})
    assert error == "" and writes == {"AMAZON_OWN_OFFER_ONLY": "yes", "AMAZON_MAX_PRODUCTS_PER_RUN": "1600"}
    stored = view({"AMAZON_OWN_OFFER_ONLY": "yes", "KEEPA_DROP_HOLD_PERCENT": "25"})
    writes, _ = amazon.changes_from(stored, {"own_only": True, "drop_hold": "25"})
    assert writes == {}                                                # the same text as stored: nothing to write
    writes, _ = amazon.changes_from(stored, {"own_only": False, "drop_hold": "40"})
    assert writes == {"AMAZON_OWN_OFFER_ONLY": "no", "KEEPA_DROP_HOLD_PERCENT": "40"}      # a variable that is set is overwritten even by the default's value


def test_an_unreadable_new_value_stops_the_save_and_says_which_setting():
    for key, bad in (("drop_hold", "95"), ("drop_hold", "abc"), ("real_max", "0"), ("real_max", "1.5"), ("max_products", "99999"), ("own_only", "perhaps")):
        writes, error = amazon.changes_from(view(), {key: bad})
        assert writes == {} and error and amazon.BY_KEY[key]["label"] in error, (key, bad, error)


def test_a_setting_the_workflow_does_not_pass_is_never_written():
    rows = view(wired={"AMAZON_OWN_OFFER_ONLY"})
    writes, error = amazon.changes_from(rows, {"own_only": True, "drop_hold": "10"})
    assert error == "" and writes == {"AMAZON_OWN_OFFER_ONLY": "yes"}


def test_the_text_written_is_what_the_sync_reads_back():
    assert amazon.canonical(amazon.BY_KEY["own_only"], True) == "yes" and amazon.canonical(amazon.BY_KEY["real_lookup"], False) == "no"
    assert amazon.canonical(amazon.BY_KEY["drop_hold"], 40.0) == "40" and amazon.canonical(amazon.BY_KEY["drop_hold"], 27.5) == "27.5" and amazon.canonical(amazon.BY_KEY["real_max"], 100) == "100"
    for key, value in (("own_only", True), ("own_only", False), ("real_lookup", True), ("real_lookup", False), ("regular_price", False), ("drop_hold", 0.0), ("drop_hold", 27.5), ("max_products", 1600)):
        spec = amazon.BY_KEY[key]
        assert amazon.in_effect(spec, amazon.canonical(spec, value)) == (value, False)             # round trip through the variable


# ---- the Keepa plan (2026-10-29) ---------------------------------------------------------------------------------------------------------
def sync_row(run_id, created, asked=1600, tokens=1900, waits=7, wait_seconds=2294, left=39, rate=20):
    return {"run": {"id": run_id, "created_at": created, "conclusion": "success"},
            "facts": {"asked": asked, "tokens_used": tokens, "waits": waits, "wait_seconds": wait_seconds, "tokens_left": left, "refill": rate}}


def test_one_row_fixes_are_left_out_of_the_economics():
    rows = [sync_row(1, "2026-10-29T02:00:00Z"), {"run": {"id": 2, "created_at": "2026-10-29T03:00:00Z", "conclusion": "success"},
                                                  "facts": {"asked": 1, "tokens_used": 2, "waits": 0, "wait_seconds": 0}}]
    assert len(amazon.real_syncs(rows)) == 1


def test_the_economics_average_the_real_syncs_and_price_the_two_options():
    now = amazon.parse_iso("2026-10-29T12:00:00Z")
    rows = [sync_row(1, "2026-10-29T02:00:00Z", tokens=2400, wait_seconds=3600, left=-25),
            sync_row(2, "2026-10-28T20:00:00Z", tokens=2800, wait_seconds=4800, left=14),
            sync_row(3, "2026-10-26T20:00:00Z", tokens=2600, wait_seconds=4200)]                     # older than 2 days: counts in the averages, not in per-day
    eco = amazon.economics(rows, now=now)
    assert eco["runs"] == 3 and eco["per_day"] == 1.0 and eco["tokens"] == 2600
    assert eco["wait_minutes"] == 70 and eco["lowest_left"] == -25 and eco["rate"] == 20
    assert eco["wait_now"] == amazon.wait_at(2600, 20) == 70                                          # (2600 - 1200) / 20
    assert eco["wait_double"] == amazon.wait_at(2600, 40) == 5 and eco["wait_shared60"] == 0          # a 60/min bucket holds 3,600
    assert amazon.economics([]) is None


def test_the_fleet_totals_multiply_by_syncs_per_day_and_skip_stores_without_data():
    stores = [{"store": {"id": "a"}, "eco": {"tokens": 2600, "per_day": 3.0, "wait_minutes": 70, "wait_double": 5, "wait_shared60": 0}},
              {"store": {"id": "b"}, "eco": None}]
    t = amazon.plan_totals(stores)
    assert t == {"stores": 1, "tokens_day": 7800, "wait_day": 210, "wait_day_double": 15, "wait_day_shared60": 0}
    assert amazon.plan_totals([{"store": {"id": "b"}, "eco": None}]) is None
