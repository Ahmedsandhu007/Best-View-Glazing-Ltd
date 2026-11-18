"""The fees card's brain: OnBuy's commission tables as committed in a store, the fee model its price formula deducts, and the numbers in the
fee tools' logs (order fee probe, observed fee feedback, category census, relabel, table refresh, price impact).

Pure functions - the page fetches the variables, the files and the logs and hands them in; the tests feed them real log excerpts.
"""
import csv
import io
import re
from collections import Counter

VAT_PERCENT = 20.0


def _num(value):
    try:
        v = float(str(value).replace("£", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return v


def effective(pct, vat=VAT_PERCENT):
    """The share of the price OnBuy really deducts for a listed commission: the rate plus the VAT on it (15 -> 18)."""
    return round(float(pct) * (1 + float(vat) / 100.0), 2)


# ---- the tables and the model -------------------------------------------------------------------------------------------------------
def parse_tiers_csv(text, vat=VAT_PERCENT):
    """onbuy_commission_tiers.csv -> one dict per tier, by name: the nominal rates, the threshold, the minimum fee and the VAT-inclusive rates."""
    out = []
    for r in csv.DictReader(io.StringIO((text or "").lstrip("﻿"))):
        lower = _num(r.get("Lower %"))
        if lower is None or not (r.get("Tier ID") or "").strip():
            continue
        upper, threshold, min_fee = _num(r.get("Upper %")), _num(r.get("Threshold (£)")), _num(r.get("Min Fee (£)"))
        if upper is not None and threshold:
            rule = f"{lower:g}% up to £{threshold:g}, {upper:g}% above"
        elif upper is not None:
            rule = f"{lower:g}% ({upper:g}% upper rate, no threshold given)"
        else:
            rule = f"{lower:g}%"
        out.append({"tier_id": r["Tier ID"].strip(), "name": (r.get("Name") or "").strip(), "lower": lower, "upper": upper,
                    "threshold": threshold, "min_fee": min_fee or 0.0, "effective_lower": effective(lower, vat),
                    "effective_upper": effective(upper, vat) if upper is not None else None, "rule": rule})
    return sorted(out, key=lambda t: (t["name"].lower(), t["lower"]))


def summarize_category_tiers(text):
    """onbuy_category_tiers.csv -> how many categories the table maps, per tier name, and how many map to no tier."""
    rows, by_tier, without = 0, Counter(), 0
    for r in csv.DictReader(io.StringIO((text or "").lstrip("﻿"))):
        if not (r.get("Category ID") or "").strip():
            continue
        rows += 1
        name = (r.get("Tier Name") or "").strip()
        if name:
            by_tier[name] += 1
        else:
            without += 1
    return {"categories": rows, "by_tier": dict(by_tier.most_common()), "without_tier": without}


def fee_model(variables, code=None):
    """What the store's formula deducts: category tables or the flat rate (FEE_MODE), how a two-rate tier applies (FEE_TIER_MODE), the flat
    rate from pricing.py and its VAT-inclusive value. `variables` is the list the GitHub client returns, or a plain dict."""
    if isinstance(variables, list):
        variables = {v["name"]: v["value"] for v in variables}
    variables = variables or {}
    mode = (variables.get("FEE_MODE") or "flat").strip().lower()
    tier_mode = (variables.get("FEE_TIER_MODE") or "marginal").strip().lower()
    flat = float((code or {}).get("platform_fee") or 20)
    vat = float((code or {}).get("fee_vat") or VAT_PERCENT)
    return {"mode": "category" if mode == "category" else "flat", "mode_raw": variables.get("FEE_MODE", ""),
            "tier_mode": "step" if tier_mode == "step" else "marginal", "flat": flat, "vat": vat, "flat_effective": effective(flat, vat)}


def default_rules(source):
    """The relabel tool's built-in rules (its DEFAULT_RULES string), one '<title regex> => <category path>' per line."""
    m = re.search(r'DEFAULT_RULES\s*=\s*r?"""(.*?)"""', source or "", re.S)
    return "\n".join(line.strip() for line in m.group(1).splitlines() if line.strip()) if m else ""


# ---- the logs ----------------------------------------------------------------------------------------------------------------------
def _clean(text):
    for raw in (text or "").splitlines():
        yield re.sub(r"\x1b\[[0-9;]*m", "", raw).rstrip()


def _int(s):
    return int(str(s).replace(",", ""))


_FB_ROW = re.compile(r"^\s+(\S+) \| (.+?) row (\d+) \| (.*?) \| sheet tier (.+?) \| OnBuy charged ([\d.]+)% ex VAT "
                     r"\((\d+) order\(s\), (\d+) kept; e\.g\. (.*?)\) \| Fee % (\S+)(?: -> (\S+))? \| price (\S+)(?: \| stock (\S+))?")


def parse_fee_feedback(text):
    """An observed-fee-feedback run: the plan (under-charged rows -> Fee % overrides), the over-charged rows, and what was written."""
    facts, section, rows = {"rows": []}, None, []
    for line in _clean(text):
        m = re.match(r"^(DRY RUN|APPLY) \| (\d+) days \| SKUs with usable orders: (\d+) \| sheet rows: (\d+)", line)
        if m:
            facts.update(mode="dry run" if m.group(1) == "DRY RUN" else "apply", days=int(m.group(2)),
                         skus_with_orders=int(m.group(3)), sheet_rows=int(m.group(4)))
            continue
        m = re.match(r"^UNDER-CHARGED - .*?: (\d+) row\(s\) to override(?: \(\+(\d+) already overridden\))?", line)
        if m:
            facts["under"], facts["already"], section = int(m.group(1)), int(m.group(2) or 0), "under"
            continue
        m = re.match(r"^\s+extra commission already paid on the kept orders of these SKUs: GBP ([\d.]+) ex VAT \(GBP ([\d.]+) inc VAT\)", line)
        if m:
            facts["extra_ex"], facts["extra_inc"] = float(m.group(1)), float(m.group(2))
            continue
        m = re.match(r"^OVER-CHARGED by the sheet - .*?: (\d+) row\(s\)", line)
        if m:
            facts["over"], section = int(m.group(1)), "over"
            continue
        m = re.match(r"^TIERED categories \(two rates; not compared\): (\d+)", line)
        if m:
            facts["tiered"], section = int(m.group(1)), "tiered"
            continue
        m = re.match(r"^NO TIER on the row \(category missing or unknown\): (\d+)", line)
        if m:
            facts["no_tier"], section = int(m.group(1)), "no tier"
            continue
        m = re.match(r"^rows matching their tier: (\d+) \| ordered SKUs not in the sheet \(team / legacy listings\): (\d+)", line)
        if m:
            facts["matching"], facts["not_in_sheet"], section = int(m.group(1)), int(m.group(2)), None
            continue
        m = re.match(r"^backup tab '(.+?)': (\d+) row", line)
        if m:
            facts["backup_tab"], facts["backup_rows"] = m.group(1), int(m.group(2))
            continue
        m = re.match(r"^WRITTEN: (\d+) Fee % override\(s\), (\d+) skipped", line)
        if m:
            facts["written"], facts["skipped"] = int(m.group(1)), int(m.group(2))
            continue
        if line.startswith("nothing to write"):
            facts["nothing_to_write"] = True
            continue
        m = _FB_ROW.match(line)
        if m and section:
            rows.append({"kind": section, "sku": m.group(1), "tab": m.group(2), "row": int(m.group(3)), "category": m.group(4),
                         "sheet_tier": m.group(5), "charged": float(m.group(6)), "orders": int(m.group(7)), "kept": int(m.group(8)),
                         "examples": m.group(9), "fee_cell": m.group(10), "target": m.group(11) or "", "price": m.group(12),
                         "stock": m.group(13) or ""})
    facts["rows"] = rows
    return facts


def parse_order_fee_probe(text):
    """An order-fee-probe run: per flat tier what OnBuy charged against the nominal rate, and the orders charged another rate than the
    sheet's tier, grouped by category."""
    facts, tiers, groups, last = {}, [], [], None
    for line in _clean(text):
        m = re.match(r"^\s+nominal ([\d.]+)%: (\d+) order\(s\) \| ex-VAT median ([\d.]+)% \(min ([\d.]+), max ([\d.]+)\) ratio to nominal ([\d.]+)"
                     r"(?: \| inc-VAT median ([\d.]+)% ratio ([\d.]+))?", line)
        if m:
            last = {"nominal": float(m.group(1)), "orders": int(m.group(2)), "median": float(m.group(3)), "min": float(m.group(4)),
                    "max": float(m.group(5)), "ratio": float(m.group(6)), "median_inc_vat": float(m.group(7)) if m.group(7) else None,
                    "charged": ""}
            tiers.append(last)
            continue
        m = re.match(r"^\s+charged: (.+)$", line)
        if m and last is not None:
            last["charged"] = m.group(1).strip()
            continue
        m = re.match(r"^MISMATCHES: (\d+) single-line order\(s\) .*?extra commission paid on the kept orders: GBP ([\d.]+) ex VAT "
                     r"\(x1\.2 inc VAT = GBP ([\d.]+)\)", line)
        if m:
            facts.update(mismatches=int(m.group(1)), extra_ex=float(m.group(2)), extra_inc=float(m.group(3)))
            continue
        m = re.match(r"^\s+(\d+) order\(s\) \| sheet tier ([\d.]+)% \| charged \[([\d, ]+)\] \| (.*?) \| e\.g\. (.*)$", line)
        if m:
            groups.append({"orders": int(m.group(1)), "sheet_tier": float(m.group(2)),
                           "charged": [int(x) for x in m.group(3).replace(" ", "").split(",") if x], "category": m.group(4),
                           "examples": m.group(5).strip()})
            continue
        m = re.match(r"^DONE: scanned (\d+) order\(s\), (\d+) line\(s\) listed, oldest (.+)$", line)
        if m:
            facts.update(scanned=int(m.group(1)), lines=int(m.group(2)), oldest=m.group(3).strip())
    facts["tiers"], facts["by_category"] = tiers, groups
    facts.setdefault("mismatches", 0 if tiers else None)
    return facts


_CENSUS_HIT = re.compile(r"^\s+(\S+) \| (.+?) row (\d+) \| cat (.*?) \[(.*?)\] \| Fee % (\S+) \| price (\S+) \| stock (\S+) \| (.*?) \| (.*)$")
_CENSUS_EXPO = re.compile(r"^\s+(.+?)\s+\| (.+?)\s+\| nominal (.+?)\s+\| Fee % cell (\S+)\s+\|\s+(\d+) rows \|\s+(\d+) in stock \| GBP ([\d,]+)")


def _pairs(text):
    """'a: 3; b: 4' -> [{'name': 'a', 'rows': 3}, ...]"""
    out = []
    for part in (text or "").split(";"):
        part = part.strip()
        m = re.match(r"^(.*): (\d+)$", part)
        if m:
            out.append({"name": m.group(1).strip() or "-", "rows": int(m.group(2))})
    return out


def parse_census(text):
    """A category-keyword-census run: the keyword rows, the exposure census (priced rows by tab / tier / Fee % cell) and the categories
    the tables map to no tier. A run whose tier column is empty on every row predates the fix of 2026-10-22: `tiers_empty` says so."""
    facts, hits, exposure = {}, [], []
    for line in _clean(text):
        m = re.match(r"^KEYWORD ROWS \((.*)\): (\d+)$", line)
        if m:
            facts["pattern"], facts["keyword_rows"] = m.group(1).strip("'\""), int(m.group(2))
            continue
        m = re.match(r"^\s+per category: (.*)$", line)
        if m:
            facts["per_category"] = _pairs(m.group(1))
            continue
        m = re.match(r"^CATEGORIES WITH NO TIER \(rows\): (.*)$", line)
        if m:
            facts["no_tier_categories"] = _pairs(m.group(1))
            continue
        m = _CENSUS_EXPO.match(line)
        if m:
            exposure.append({"tab": m.group(1), "tier": m.group(2).strip(), "nominal": m.group(3), "fee_cell": m.group(4),
                             "rows": int(m.group(5)), "in_stock": int(m.group(6)), "total": _int(m.group(7))})
            continue
        m = _CENSUS_HIT.match(line)
        if m:
            hits.append({"sku": m.group(1), "tab": m.group(2), "row": int(m.group(3)), "category": m.group(4), "category_id": m.group(5),
                         "fee_cell": m.group(6), "price": m.group(7), "stock": m.group(8), "sync": m.group(9), "title": m.group(10)})
    facts["hits"], facts["exposure"] = hits, exposure
    if exposure:
        facts["rows_priced"] = sum(e["rows"] for e in exposure)
        facts["rows_no_tier"] = sum(e["rows"] for e in exposure if e["tier"] == "(no tier)")
        facts["tiers_empty"] = facts["rows_no_tier"] == facts["rows_priced"]
        by_cell = Counter()
        for e in exposure:
            by_cell[e["fee_cell"]] += e["rows"]
        facts["by_fee_cell"] = [{"fee_cell": k, "rows": v} for k, v in sorted(by_cell.items(), key=lambda kv: -kv[1])]
        facts["flat_fallback_rows"] = by_cell.get("24.00", 0)
    return facts


_RELABEL_ROW = re.compile(r"^\s+(\S+) \| (.+?) row (\d+) \| (.*?) \[(.*?)\] \((.*?)\) -> (.*?) \[(\d+)\] \((.*?)\) \| Fee % (\S+) \| "
                          r"price (\S+) \| stock (\S+) \| (.*)$")


def parse_relabel(text):
    """A set-category-by-keyword run: the rules, the rows to relabel (old category and tier -> new leaf and tier) and what was written."""
    facts, rows = {"rows": []}, []
    for line in _clean(text):
        m = re.match(r"^(DRY RUN|APPLY) \| (\d+) rule\(s\): (.*)$", line)
        if m:
            facts.update(mode="dry run" if m.group(1) == "DRY RUN" else "apply", rules=int(m.group(2)), rules_text=m.group(3))
            continue
        m = re.match(r"^ROWS TO RELABEL: (\d+) \(already on the target path: (\d+)\)", line)
        if m:
            facts["to_relabel"], facts["already"] = int(m.group(1)), int(m.group(2))
            continue
        m = re.match(r"^backup tab '(.+?)': (\d+) row", line)
        if m:
            facts["backup_tab"], facts["backup_rows"] = m.group(1), int(m.group(2))
            continue
        m = re.match(r"^WRITTEN: (\d+) row\(s\) relabelled, (\d+) skipped", line)
        if m:
            facts["written"], facts["skipped"] = int(m.group(1)), int(m.group(2))
            continue
        if line.startswith("nothing to write"):
            facts["nothing_to_write"] = True
            continue
        m = _RELABEL_ROW.match(line)
        if m:
            rows.append({"sku": m.group(1), "tab": m.group(2), "row": int(m.group(3)), "old_category": m.group(4), "old_id": m.group(5),
                         "old_tier": m.group(6), "new_leaf": m.group(7), "new_id": m.group(8), "new_tier": m.group(9),
                         "fee_cell": m.group(10), "price": m.group(11), "stock": m.group(12), "title": m.group(13)})
    facts["rows"] = rows
    if rows:
        facts["tier_changes"] = sum(1 for r in rows if r["old_tier"] != r["new_tier"])
    return facts


def parse_refresh_fees(text):
    """A refresh-commission-tables run: what OnBuy answered, how the listable categories spread, and (since 2026-10-24) whether the fresh
    tables differ from the committed ones and whether they were committed."""
    facts, tiers, spread, gone, section = {}, [], [], [], None
    for line in _clean(text):
        m = re.match(r"^commission tiers: (\d+)", line)
        if m:
            facts["tiers"], section = int(m.group(1)), "tiers"
            continue
        m = re.match(r"^categories fetched: (\d+) \| with a tier: (\d+)", line)
        if m:
            facts["categories"], facts["categories_with_tier"], section = int(m.group(1)), int(m.group(2)), None
            continue
        if line.startswith("listable categories by tier:"):
            section = "spread"
            continue
        m = re.match(r"^listable categories with NO tier: (\d+)", line)
        if m:
            facts["listable_without_tier"], section = int(m.group(1)), "gone"
            continue
        m = re.match(r"^TABLES (UNCHANGED|DIFFER|COMMITTED)\b:?\s*(.*)$", line)
        if m:
            if m.group(1) != "COMMITTED" or "tables" not in facts:
                facts["tables"], facts["tables_note"] = m.group(1).lower(), m.group(2).strip()
            else:
                facts["tables"], facts["commit"] = "committed", m.group(2).strip()
            counts = re.search(r"(\d+) gone, (\d+) new, (\d+) changed tier", m.group(2))
            if counts:
                facts.update(gone=int(counts.group(1)), new=int(counts.group(2)), changed_tier=int(counts.group(3)))
            continue
        if section == "tiers":
            m = re.match(r"^\s{3}(\S.*?)\s{2,}([\d.]+)%(.*?)\s{2}min £([\d.]+)$", line)
            if m:
                tiers.append({"name": m.group(1).strip(), "lower": float(m.group(2)), "extra": m.group(3).strip(", "), "min_fee": float(m.group(4))})
                continue
        if section == "spread":
            m = re.match(r"^\s+(\d+)\s{2}(.+)$", line)
            if m:
                spread.append({"name": m.group(2).strip(), "categories": int(m.group(1))})
                continue
        if section == "gone":
            m = re.match(r"^\s+(\d+) (.+)$", line)
            if m and not line.startswith("TABLES"):
                gone.append({"category_id": m.group(1), "path": m.group(2).strip()})
                continue
        if line.startswith("sample category record"):
            section = None
    facts.update(tier_lines=tiers, listable_by_tier=spread, listable_no_tier=gone)
    return facts


def parse_price_impact(text):
    """A price-impact-of-category-fees run: what category pricing would do to the priced rows, per tier."""
    facts, tiers, in_table = {}, [], False
    for line in _clean(text):
        m = re.match(r"^rows priced: (\d+) \| would LOWER: (\d+) \| would RAISE: (\d+) \| KEEP: (\d+)", line)
        if m:
            facts.update(rows=int(m.group(1)), lower=int(m.group(2)), raise_=int(m.group(3)), keep=int(m.group(4)))
            continue
        m = re.match(r"^skipped: no cost (\d+) \| no category (\d+) \| category without a tier (\d+)", line)
        if m:
            facts.update(no_cost=int(m.group(1)), no_category=int(m.group(2)), no_tier=int(m.group(3)))
            continue
        m = re.match(r"^tier mode: (\w+)", line)
        if m:
            facts["tier_mode"] = m.group(1)
            continue
        if line.startswith("tier ") and "rows" in line and "lower" in line:
            in_table = True
            continue
        if in_table:
            m = re.match(r"^(\S.*?)\s{2,}(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)$", line)
            if m:
                tiers.append({"tier": m.group(1).strip(), "rows": int(m.group(2)), "lower": int(m.group(3)), "raise_": int(m.group(4)),
                              "keep": int(m.group(5)), "avg_flat": float(m.group(6)), "avg_tier": float(m.group(7)), "avg_cell": float(m.group(8))})
                continue
            if line.strip() == "" or line.startswith("examples"):
                in_table = False
    facts["tiers"] = tiers
    return facts


PARSERS = {
    "order_fee_probe.yml": parse_order_fee_probe,
    "observed_fee_feedback.yml": parse_fee_feedback,
    "category_keyword_census.yml": parse_census,
    "set_category_by_keyword.yml": parse_relabel,
    "refresh_fees.yml": parse_refresh_fees,
    "price_impact_report.yml": parse_price_impact,
}

# the page's short names for the latest run of each fee tool
LATEST = {"probe": "order_fee_probe.yml", "feedback": "observed_fee_feedback.yml", "census": "category_keyword_census.yml",
          "relabel": "set_category_by_keyword.yml", "refresh": "refresh_fees.yml", "impact": "price_impact_report.yml"}
