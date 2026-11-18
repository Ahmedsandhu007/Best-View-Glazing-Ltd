"""Sheet health: what the sheet itself holds back from the sync (2026-11-02).

Kidoomi's first fill made the gap visible: rows with a Supplier URL but no SKU wait silently ("left out of the batch
until a SKU is added"), two rows sharing one supplier link fight (one listing per supplier product - only the first
lists), and a half-filled tab looks done from the outside. The sync logs already say all of it, every run; this parses
the sheet-side lines of the latest eBay and Amazon runs so the owner sees the gaps without opening a log:

    TOTAL ROWS IN SHEET: 30
    Skipping 592 row(s) with no eBay/Amazon Supplier URL yet (not counted against this run's batch)
    Manual run: limited to 30 unfilled row(s) of 30 processable - ...
    WARNING 30 row(s) have a Supplier URL but no SKU yet (sheet rows 2, 3, 4, ...) - left out of the batch ...
    WARNING Row 13 (SKU 808221610721): Failed: supplier link already used on row 11 (eBay) - one listing per supplier product
    OnBuy: 196 created, ... 0 failed, ... 0 brand-blocked (flagged), 4 skipped (dead eBay link), 0 awaiting category ...
"""
import re

ROWS = re.compile(r"TOTAL ROWS IN SHEET: ([\d,]+)")
NO_URL = re.compile(r"Skipping ([\d,]+) row\(s\) with no eBay/Amazon Supplier URL yet")
PROCESSABLE = re.compile(r"([\d,]+) unfilled row\(s\) of ([\d,]+) processable")
NO_SKU = re.compile(r"([\d,]+) row\(s\) have a Supplier URL but no SKU yet \(sheet rows ([^)]*)\)")
DUP = re.compile(r"Row (\d+) \(SKU ([^)]+?)\): Failed: supplier link already used on row (\d+)")
CREATED = re.compile(r"OnBuy: ([\d,]+) created")
FAILED = re.compile(r"OnBuy: [^\n]*?, ([\d,]+) failed,")
BRAND = re.compile(r"([\d,]+) brand-blocked \(flagged\)")
DEAD = re.compile(r"([\d,]+) skipped \(dead eBay link\)")
AWAITING_CAT = re.compile(r"([\d,]+) awaiting category")


def _int(s):
    return int(str(s).replace(",", ""))


def parse_sheet(text):
    """The sheet-side facts of one sync log; a key is absent when its line is (an old log, or a run that died early)."""
    t = text or ""
    out = {}
    for key, rx in (("rows", ROWS), ("no_url", NO_URL), ("created", CREATED), ("failed", FAILED),
                    ("brand_blocked", BRAND), ("dead_links", DEAD), ("awaiting_category", AWAITING_CAT)):
        m = rx.search(t)
        if m:
            out[key] = _int(m.group(1))
    m = PROCESSABLE.search(t)
    if m:
        out["unfilled"], out["processable"] = _int(m.group(1)), _int(m.group(2))
    m = NO_SKU.search(t)
    if m:
        sample = [r.strip() for r in m.group(2).replace("...", " ").split(",") if r.strip().isdigit()]
        out["no_sku"] = {"count": _int(m.group(1)), "sample_rows": sample[:12]}
    dups = []
    seen = set()
    for m in DUP.finditer(t):
        key = (m.group(1), m.group(3))
        if key in seen:
            continue
        seen.add(key)
        dups.append({"row": int(m.group(1)), "sku": m.group(2).strip(), "original_row": int(m.group(3))})
    if dups:
        out["duplicate_links"] = dups
    return out


def issues(parsed):
    """The numbers worth a colored pill, in the order they should be fixed: a missing SKU and a duplicate link are the
    owner's edits; missing URLs are simply rows not yet filled."""
    out = []
    if parsed.get("no_sku", {}).get("count"):
        out.append(("no SKU yet", parsed["no_sku"]["count"], "warn"))
    if parsed.get("duplicate_links"):
        out.append(("duplicate supplier links", len(parsed["duplicate_links"]), "bad"))
    if parsed.get("no_url"):
        out.append(("no supplier URL yet", parsed["no_url"], "quiet"))
    if parsed.get("failed"):
        out.append(("failed last run", parsed["failed"], "bad"))
    if parsed.get("dead_links"):
        out.append(("dead supplier links", parsed["dead_links"], "warn"))
    if parsed.get("awaiting_category"):
        out.append(("awaiting category", parsed["awaiting_category"], "warn"))
    return out
