"""The fees card's pure functions on real log excerpts: the tables, the model, and the six fee tools' outputs."""
from conftest import (CATEGORY_TIERS_CSV, CENSUS_LOG, FEEDBACK_APPLY_LOG, FEEDBACK_DRY_LOG, IMPACT_LOG, PROBE_LOG, REFRESH_LOG,
                      RELABEL_APPLY_LOG, RELABEL_LOG, RELABEL_SOURCE, STALE_CENSUS_LOG, TIERS_CSV)

from app import fees


def test_tiers_csv_gives_the_vat_inclusive_rates_and_the_rule_text():
    tiers = fees.parse_tiers_csv(TIERS_CSV)
    assert [t["name"] for t in tiers] == ["Baby & Toddler", "Consumer Electronics", "Jewellery", "Standard Selling Fee"]
    baby, electronics, jewellery, standard = tiers
    assert baby["rule"] == "8% up to £10, 15% above" and baby["effective_lower"] == 9.6 and baby["effective_upper"] == 18.0
    assert electronics["rule"] == "7%" and electronics["effective_lower"] == 8.4 and electronics["effective_upper"] is None
    assert jewellery["rule"] == "20% (5% upper rate, no threshold given)" and standard["min_fee"] == 0.25
    summary = fees.summarize_category_tiers(CATEGORY_TIERS_CSV)
    assert summary == {"categories": 5, "by_tier": {"Standard Selling Fee": 2, "Baby & Toddler": 1, "Consumer Electronics": 1}, "without_tier": 1}


def test_fee_model_from_variables_and_code():
    model = fees.fee_model([{"name": "FEE_MODE", "value": "category"}], {"platform_fee": 20})
    assert model["mode"] == "category" and model["tier_mode"] == "marginal" and model["flat_effective"] == 24.0
    flat = fees.fee_model({"FEE_TIER_MODE": "step"}, None)
    assert flat["mode"] == "flat" and flat["tier_mode"] == "step" and flat["flat"] == 20 and flat["vat"] == 20
    assert fees.fee_model({"FEE_MODE": "Category "}, {})["mode"] == "category"


def test_default_rules_come_out_of_the_relabel_source():
    rules = fees.default_rules(RELABEL_SOURCE)
    assert rules.splitlines()[-1] == "filament => Arts, Crafts & Sewing > Other Crafts > 3D Printing > 3D Printer Filament"
    assert len(rules.splitlines()) == 2 and fees.default_rules("x = 1") == ""


def test_parse_fee_feedback_dry_run_and_apply():
    f = fees.parse_fee_feedback(FEEDBACK_DRY_LOG)
    assert f["mode"] == "dry run" and f["days"] == 90 and f["skus_with_orders"] == 171 and f["sheet_rows"] == 9463
    assert f["under"] == 2 and f["already"] == 0 and f["over"] == 7 and f["tiered"] == 1 and f["matching"] == 67 and f["not_in_sheet"] == 95
    assert f["extra_ex"] == 8.83 and f["extra_inc"] == 10.6 and "written" not in f
    kinds = [r["kind"] for r in f["rows"]]
    assert kinds == ["under", "under", "over", "tiered"]
    first = f["rows"][0]
    assert first["sku"] == "612227390835" and first["tab"] == "Sheet1" and first["row"] == 1568
    assert first["sheet_tier"] == "Large Appliances 7%" and first["charged"] == 15.0 and first["orders"] == 2 and first["kept"] == 2
    assert first["fee_cell"] == "8.40" and first["target"] == "18.00" and first["price"] == "55.67" and first["stock"] == "5"
    assert f["rows"][2]["target"] == "" and f["rows"][3]["sheet_tier"] == "Baby & Toddler 8%/15% above 10"
    a = fees.parse_fee_feedback(FEEDBACK_APPLY_LOG)
    assert a["mode"] == "apply" and a["written"] == 2 and a["skipped"] == 0 and a["backup_tab"] == "Fee overrides 2026-10-22"
    assert fees.parse_fee_feedback("")["rows"] == []


def test_parse_order_fee_probe():
    f = fees.parse_order_fee_probe(PROBE_LOG)
    assert [t["nominal"] for t in f["tiers"]] == [7.0, 13.0, 15.0]
    assert f["tiers"][0]["orders"] == 19 and f["tiers"][0]["median"] == 7.0 and f["tiers"][0]["max"] == 15.0 and f["tiers"][0]["charged"] == "7% x15, 15% x4"
    assert f["tiers"][2]["median_inc_vat"] == 18.0
    assert f["mismatches"] == 11 and f["extra_ex"] == 8.83 and f["extra_inc"] == 10.6
    assert f["by_category"][1] == {"orders": 2, "sheet_tier": 7.0, "charged": [15], "category": "Electronics & Technology > Computing & Gaming > iPads, Tablets & eBook Readers > Tablets", "examples": "Ama-B0BCK4K9ZC-6"}
    assert f["scanned"] == 200 and f["lines"] == 200 and f["oldest"] == "2026-06-13 21:59:11"
    assert fees.parse_order_fee_probe("DONE: scanned 0 order(s), 0 line(s) listed, oldest -")["mismatches"] is None


def test_parse_census_fixed_and_stale():
    f = fees.parse_census(CENSUS_LOG)
    assert f["pattern"] == "3d[ -]?print|filament|3d pen|resin printer" and f["keyword_rows"] == 2
    assert f["hits"][0]["sku"] == "4020740160723-zzz" and f["hits"][0]["row"] == 800 and f["hits"][0]["fee_cell"] == "8.40" and f["hits"][0]["title"].startswith("X-Maker")
    assert f["hits"][1]["stock"] == "None"
    assert f["per_category"][0]["rows"] == 1
    assert len(f["exposure"]) == 5 and f["exposure"][2]["nominal"] == "8/15 above 10" and f["exposure"][2]["tier"] == "Baby & Toddler"
    assert f["exposure"][0] == {"tab": "Amazon", "tier": "Standard Selling Fee", "nominal": "15", "fee_cell": "18.00", "rows": 2144, "in_stock": 2009, "total": 219356}
    assert f["rows_priced"] == 7402 and f["rows_no_tier"] == 28 and f["tiers_empty"] is False and f["flat_fallback_rows"] == 28
    assert f["by_fee_cell"][0] == {"fee_cell": "18.00", "rows": 6700}
    assert f["no_tier_categories"][0]["rows"] == 387
    stale = fees.parse_census(STALE_CENSUS_LOG)
    assert stale["tiers_empty"] is True and stale["rows_priced"] == 3704 and stale["flat_fallback_rows"] == 0


def test_parse_relabel_dry_run_and_apply():
    f = fees.parse_relabel(RELABEL_LOG)
    assert f["mode"] == "dry run" and f["rules"] == 3 and f["to_relabel"] == 2 and f["already"] == 17 and "written" not in f
    r = f["rows"][0]
    assert r["sku"] == "4020740160723-zzz" and r["tab"] == "Amazon" and r["row"] == 800
    assert r["old_tier"] == "Consumer Electronics 7%" and r["new_leaf"] == "3D Printers" and r["new_id"] == "10483" and r["new_tier"] == "Standard Selling Fee 15%"
    assert r["fee_cell"] == "8.40" and r["title"].startswith("X-Maker")
    assert f["tier_changes"] == 1                       # the enclosure row keeps its 15% tier
    a = fees.parse_relabel(RELABEL_APPLY_LOG)
    assert a["mode"] == "apply" and a["written"] == 43 and a["skipped"] == 0 and a["backup_tab"] == "Categories relabelled 2026-10-22"


def test_parse_refresh_fees_with_the_compare_step():
    f = fees.parse_refresh_fees(REFRESH_LOG)
    assert f["tiers"] == 29 and f["categories"] == 7549 and f["categories_with_tier"] == 7536 and f["listable_without_tier"] == 11
    assert f["tier_lines"][1] == {"name": "Baby & Toddler", "lower": 8.0, "extra": "15.00% above £10.00", "min_fee": 0.25}
    assert f["tier_lines"][2]["extra"] == "5.00% upper (no threshold given)"
    assert f["listable_by_tier"] == [{"name": "Standard Selling Fee", "categories": 5719}, {"name": "DIY & Tools", "categories": 548}]
    assert f["listable_no_tier"][0] == {"category_id": "38245", "path": "Appliances > Furniture, Furnishings & Decor > Lighting > Ceiling Lights"}
    assert f["tables"] == "differ" and f["gone"] == 462 and f["new"] == 11 and f["changed_tier"] == 0 and "commit=yes" in f["tables_note"]
    committed = fees.parse_refresh_fees(REFRESH_LOG + "TABLES COMMITTED: abc1234\n")
    assert committed["tables"] == "committed" and committed["commit"] == "abc1234" and committed["gone"] == 462
    assert fees.parse_refresh_fees(REFRESH_LOG.replace("TABLES DIFFER", "TABLES UNCHANGED"))["tables"] == "unchanged"
    assert "tables" not in fees.parse_refresh_fees("commission tiers: 29\n")


def test_parse_price_impact():
    f = fees.parse_price_impact(IMPACT_LOG)
    assert f["rows"] == 6652 and f["lower"] == 1 and f["raise_"] == 3217 and f["keep"] == 3434
    assert f["no_cost"] == 184 and f["no_category"] == 5 and f["no_tier"] == 97 and f["tier_mode"] == "marginal"
    assert f["tiers"][0] == {"tier": "Standard Selling Fee", "rows": 4944, "lower": 1, "raise_": 2562, "keep": 2381, "avg_flat": 63.02, "avg_tier": 59.25, "avg_cell": 60.87}
    assert len(f["tiers"]) == 2
