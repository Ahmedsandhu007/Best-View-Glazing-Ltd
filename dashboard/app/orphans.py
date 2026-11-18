"""Orphans: listings live on OnBuy that sit on NO sheet row (2026-11-02).

The 19th log check made the populations visible - Arden 2,782, Makstore 3,353, OpenMaal 4,962 live listings outside the
sheets, stable night over night: the manual and import era. They live outside every guard a sheet row gets - no price
fix, no stock sync, no purge - so an in-stock orphan sells at whatever price it was left with. The content scan
(scan_content_mismatch.py, which the nightly also runs) prints every one:

    ORPHANS (live on OnBuy, on no product tab): 2782
    ORPHAN|0000016945579-manual|price=205.00|stock=1|created=2026-10-28 09:43|ZVOX Dialogue Clarifying Sound Bar wi

This parses those lines for the Catalogue page's card: the count, the in-stock slice (the risk), the rows in-stock-first
and newest-first, and the SKUs paste-ready for the Delete page's delete-by-list the day the owner retires a batch."""
import re

COUNT = re.compile(r"ORPHANS \(live on OnBuy, on no product tab\): (\d+)")
LINE = re.compile(r"ORPHAN\|([^|]+)\|price=([0-9.]+)\|stock=(\d+)\|created=([^|]*?)\|(.*)")


def parse_orphans(text):
    """{'count': int or None, 'rows': [{sku, price, stock, created, title}]} - rows deduped by SKU (the log can carry
    the block twice), the log's own order kept."""
    m = COUNT.search(text or "")
    count = int(m.group(1)) if m else None
    rows, seen = [], set()
    for m in LINE.finditer(text or ""):
        sku = m.group(1).strip()
        if not sku or sku in seen:
            continue
        seen.add(sku)
        rows.append({"sku": sku, "price": float(m.group(2)), "stock": int(m.group(3)),
                     "created": m.group(4).strip()[:16], "title": m.group(5).strip()})
    return {"count": count, "rows": rows}


def display_rows(rows):
    """In-stock first (they are the risk), newest created first within each half; stable so equal rows keep log order."""
    newest_first = sorted(rows, key=lambda r: r["created"], reverse=True)
    return sorted(newest_first, key=lambda r: r["stock"] <= 0)
