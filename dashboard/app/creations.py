"""Creations in flight: where the queued products stand (2026-11-02).

A create_product answers with a queue id, not a listing - OnBuy's queue assigns the OPC later, the backfill records it,
and only then can the activation pass set price, stock and the delivery template. Between those moments a store's new
products are invisible: Kidoomi queued 225 on its first day and the only trace was backfill log lines. This parses them:

    [eBay] 3 pending SKU(s)
    [Amazon] 196 pending SKU(s)
    [opc-import] listings swept: 222 OPC->SKU pairs
    [opc-fill] eBay: 26 blank OPC(s) filled from the listings, 0 row(s) OnBuy does not list
    Checking 199 pending SKU(s) against OnBuy's queue history...
    Found 199 of 199 pending SKU(s) in the queue history.
    795067034579: status=success, opc=PYSC6CG
    808397703623: status=failed, opc=None, reason=An error occurred: The supplied brand is owned by another seller.
    [Amazon] Updated 784 sheet cell(s).
"""
import re

PENDING = re.compile(r"\[(eBay|Amazon)\] ([\d,]+) pending SKU\(s\)")
SWEPT = re.compile(r"\[opc-import\] listings swept: ([\d,]+) OPC->SKU pairs")
FILLED = re.compile(r"\[opc-fill\] (eBay|Amazon): ([\d,]+) blank OPC\(s\) filled from the listings, ([\d,]+) row\(s\) OnBuy does not list")
FOUND = re.compile(r"Found ([\d,]+) of ([\d,]+) pending SKU\(s\) in the queue history")
STATUS = re.compile(r"([A-Za-z0-9._-]+): status=([a-z_]+), opc=([^,\s]+)(?:, reason=(.+))?")
UPDATED = re.compile(r"\[(eBay|Amazon)\] Updated ([\d,]+) sheet cell\(s\)")


def _int(s):
    return int(str(s).replace(",", ""))


def parse_creations(text):
    """The queue story of one backfill log; keys absent when their lines are."""
    t = text or ""
    out = {}
    pending = {m.group(1).lower(): _int(m.group(2)) for m in PENDING.finditer(t)}
    if pending:
        out["pending"] = pending
    m = SWEPT.search(t)
    if m:
        out["listings_live"] = _int(m.group(1))
    filled = [{"tab": m.group(1).lower(), "filled": _int(m.group(2)), "unlisted": _int(m.group(3))} for m in FILLED.finditer(t)]
    if filled:
        out["opc_fill"] = filled
    m = FOUND.search(t)
    if m:
        out["queue_found"], out["queue_checked"] = _int(m.group(1)), _int(m.group(2))
    outcomes, failures, seen = {}, [], set()
    for m in STATUS.finditer(t):
        sku = m.group(1)
        if sku in seen:
            continue
        seen.add(sku)
        status = m.group(2)
        outcomes[status] = outcomes.get(status, 0) + 1
        if status != "success" and len(failures) < 40:
            failures.append({"sku": sku, "status": status, "reason": (m.group(4) or "").strip()[:160]})
    if outcomes:
        out["outcomes"] = outcomes
    if failures:
        out["failures"] = failures
    updated = {m.group(1).lower(): _int(m.group(2)) for m in UPDATED.finditer(t)}
    if updated:
        out["sheet_cells_updated"] = updated
    return out
