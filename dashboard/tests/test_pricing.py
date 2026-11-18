"""The pricing card's pure functions: reading a store's constants, validating and building the setting, the formula, the run numbers."""
import json

from app import pricing

MAKSTORE_SOURCE = '''
import os
MIN_PROFIT_PERCENT = 20
PLATFORM_FEE_PERCENT = 20
FEE_VAT_PERCENT = 20.0
STANDARD_TOP_BAND_PROFIT = 20.0
PREVIOUS_STANDARD_TOP_BAND_PROFIT = 13.0
FLAT_PROFIT = 20.0
TOP_BAND_FROM = 30.0
PREVIOUS_TOP_BAND_FROM = 50.0
PREVIOUS_TOP_BAND_PROFIT = 25.0


def _top_band_profit():
    return float(os.getenv("X") or STANDARD_TOP_BAND_PROFIT)


TOP_BAND_PROFIT = _top_band_profit()
PROFIT_BANDS = (
    (5.0, FLAT_PROFIT),
    (10.0, FLAT_PROFIT),
    (TOP_BAND_FROM, FLAT_PROFIT),
    (None, TOP_BAND_PROFIT),
)
_SUPERSEDED_PROFIT_BANDS = (
    ((5.0, 80), (10.0, 80), (30.0, 40), (100.0, 40), (None, 30)),
) + (
    ((5.0, 100), (10.0, 80), (PREVIOUS_TOP_BAND_FROM, 40), (None, PREVIOUS_TOP_BAND_PROFIT)),
)
FEE_TIER_MODE = (os.getenv("FEE_TIER_MODE") or "marginal").strip().lower()
'''

GTV_SOURCE = '''
PLATFORM_FEE_PERCENT = 20
PROFIT_BANDS = (
    (5.0, 100),
    (10.0, 80),
    (50.0, 40),
    (None, 20),
)
SELL_PRICE_OVERRIDES = (
    (10.0, 20.0, 15),
)
_SUPERSEDED_PROFIT_BANDS = (
    ((5.0, 80), (10.0, 80), (30.0, 40), (100.0, 40), (None, 30)),
)
'''


def test_code_schedule_reads_makstore_style_constants_and_the_knob():
    code = pricing.code_schedule(MAKSTORE_SOURCE)
    assert code["bands"] == [[5.0, 20.0], [10.0, 20.0], [30.0, 20.0], [None, 20.0]]
    assert code["overrides"] is None and code["platform_fee"] == 20 and code["top_band_from"] == 30.0
    assert len(code["superseded"]) == 2 and code["superseded"][1] == [[5.0, 100.0], [10.0, 80.0], [50.0, 40.0], [None, 25.0]]
    with_knob = pricing.code_schedule(MAKSTORE_SOURCE, knob="13")
    assert with_knob["bands"][-1] == [None, 13.0] and with_knob["knob_used"]


def test_code_schedule_reads_gtv_style_constants_with_the_window():
    code = pricing.code_schedule(GTV_SOURCE)
    assert code["bands"] == [[5.0, 100.0], [10.0, 80.0], [50.0, 40.0], [None, 20.0]]
    assert code["overrides"] == [[10.0, 20.0, 15.0]]
    assert pricing.code_schedule("def f():\n    pass\n") is None
    assert pricing.code_schedule("this is not python (") is None


def test_check_bands_rules():
    assert pricing.check_bands([[5, 100], [10, 80], [None, 20]]) == ""
    assert "at least one" in pricing.check_bands([])
    assert "last band" in pricing.check_bands([[5, 100], [10, 80]])
    assert "Only the last" in pricing.check_bands([[5, 100], [None, 80], [None, 20]])
    assert "rise" in pricing.check_bands([[10, 100], [5, 80], [None, 20]])
    assert "between 0 and 1000" in pricing.check_bands([[5, 2000], [None, 20]])
    assert "above 0" in pricing.check_bands([[0, 20], [None, 20]])
    assert "numbers" in pricing.check_bands([["x", 20], [None, 20]])
    assert pricing.check_overrides(None) == "" and pricing.check_overrides([[10, 20, 15]]) == ""
    assert pricing.check_overrides([[20, 10, 15]]) and pricing.check_overrides([[10, 20]])


def test_validate_setting_matches_the_stores_parser():
    raw = json.dumps({"bands": [[5, 50], [None, 50]], "superseded": [[[5, 100], [None, 20]], [[5, 1]]], "sell_price_overrides": [[10, 20, 15]]})
    s = pricing.validate_setting(raw)
    assert s["bands"] == [[5.0, 50.0], [None, 50.0]] and s["overrides"] == [[10.0, 20.0, 15.0]]
    assert s["superseded"] == [[[5.0, 100.0], [None, 20.0]]]          # the entry with a bounded last band is dropped, as the stores drop it
    assert pricing.validate_setting("") is None and pricing.validate_setting("{") is None
    assert pricing.validate_setting(json.dumps({"bands": [[5, 20], [10, 20]]})) is None


def test_effective_schedule_prefers_a_valid_setting():
    code = pricing.code_schedule(GTV_SOURCE)
    assert pricing.effective_schedule("", code)["source"] == "code"
    eff = pricing.effective_schedule(json.dumps({"bands": [[5, 60], [None, 30]]}), code)
    assert eff["source"] == "setting" and eff["bands"] == [[5.0, 60.0], [None, 30.0]]
    assert eff["overrides"] == [[10.0, 20.0, 15.0]]          # the window is kept from the code when the setting says nothing about it
    assert pricing.effective_schedule("not json", code)["source"] == "code"
    assert pricing.effective_schedule("", None) is None


def test_build_setting_keeps_the_outgoing_schedule_as_superseded():
    current = pricing.effective_schedule("", pricing.code_schedule(GTV_SOURCE))
    text = pricing.build_setting(current, [[5.0, 60.0], [None, 30.0]], current["overrides"])
    data = json.loads(text)
    assert data["bands"] == [[5.0, 60.0], [None, 30.0]] and data["sell_price_overrides"] == [[10.0, 20.0, 15.0]]
    assert data["superseded"][-1] == [[5.0, 100.0], [10.0, 80.0], [50.0, 40.0], [None, 20.0]]
    assert len(data["superseded"]) == 2
    # the same schedule again adds nothing
    again = json.loads(pricing.build_setting(pricing.validate_setting(text) | {"source": "setting"}, [[5.0, 60.0], [None, 30.0]]))
    assert len(again["superseded"]) == 2 and "sell_price_overrides" not in again


def test_describe_bands_band_profit_and_price():
    bands = [[5.0, 100.0], [10.0, 80.0], [50.0, 40.0], [None, 20.0]]
    assert pricing.describe_bands(bands) == [("under £5", 100.0), ("£5 to £10", 80.0), ("£10 to £50", 40.0), ("above £50", 20.0)]
    assert pricing.band_profit(bands, 4.99) == 100 and pricing.band_profit(bands, 5) == 80 and pricing.band_profit(bands, 10) == 80
    assert pricing.band_profit(bands, 10.01) == 40 and pricing.band_profit(bands, 50) == 40 and pricing.band_profit(bands, 51) == 20
    assert pricing.price_for(20.0, 20, 18.0) == 29.27        # 24 / 0.82


def test_parse_even_margins_dry_run_and_apply():
    dry = """
DRY RUN | top band profit 20% | outlier ratio 2 | cap 20000 | fee mode category
=== Sheet1 (eBay pricing): 4648 rows with a SKU | lower 120, ok 4400, raise 30, skip 98
  LOWER: 120 rows (100 in stock, 3 Buy Box-defended) | median lower 12.3%, biggest x1.9
  RAISE: 30 rows (28 in stock, 0 Buy Box-defended) | median raise 4.0%, biggest x0.8
=== Amazon (Amazon pricing): 5205 rows with a SKU | lower 10, ok 5100, skip 95
TOTAL: 160 price(s) to change, 2 held for review
DRY RUN - nothing written. Re-run with apply=yes to write the prices.
"""
    f = pricing.parse_even_margins(dry)
    assert f["mode"] == "dry run" and f["to_change"] == 160 and f["held"] == 2
    assert f["lower"] == 130 and f["raise"] == 30 and f["ok"] == 9500
    assert f["tabs"][0]["median_lower_pct"] == 12.3 and f["tabs"][0]["lower_defended"] == 3 and f["tabs"][1]["kind"] == "Amazon"
    applied = pricing.parse_even_margins("APPLY | top band profit 20%\nbackup tab 'Prices evened 2026-10-24': 160 row(s)\nDONE: 158 row(s) put on the schedule, 2 skipped (edited meanwhile), 2 held for review.")
    assert applied["mode"] == "apply" and applied["written"] == 158 and applied["skipped"] == 2 and applied["backup_tab"] == "Prices evened 2026-10-24"
    stopped = pricing.parse_even_margins("STOP: 9001 changes exceed the cap of 800 - re-run with a higher max_changes if that is intended.")
    assert "9001 changes exceed the cap of 800" in stopped["cap_stop"]
