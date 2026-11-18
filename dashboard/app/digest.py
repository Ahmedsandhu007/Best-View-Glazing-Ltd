"""The daily check, as pure functions: run summaries, stale crons, and the numbers hidden in the workflows' logs.

Nothing here talks to GitHub; the pages fetch runs and logs and hand them in, which is also what the tests do.
"""
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

from . import catalog

KEY = re.compile(
    r"zeroed|held at zero|DELETED|deleted|wrong|TO MOVE|APPLIED|Purg|purge|corrected|SELLABLE|UNDERPRICED|orphan|sale price|Traceback|"
    r"ERROR|WARNING|skipped|frozen|calls left|allowance|remaining|halt|429|guard|protected|nothing to|no listings|removed|backup|suspended|"
    r"not found|mismatch|flag|token\(s\) used|DONE|Updated rows|MATCHED|^TABLES |UNDER-CHARGED|OVER-CHARGED|ROWS TO RELABEL|WRITTEN:|"
    r"KEYWORD ROWS|rows priced:|commission tiers:|categories fetched:", re.I)
NOISE = re.compile(
    r"DeprecationWarning|punycode|Node\.js 20|trace-deprecation|##\[|Download action|Complete job|pip |Collecting|Installing|"
    r"Requirement already|Successfully installed|git config|hint:|warning: in the working copy|Cleaning up orphan|GITHUB_TOKEN|"
    r"token: \*\*\*|^\s*$|raw response", re.I)


def parse_iso(text):
    return datetime.fromisoformat(str(text).replace("Z", "+00:00"))


def age_hours(iso, now=None):
    now = now or datetime.now(timezone.utc)
    try:
        return (now - parse_iso(iso)).total_seconds() / 3600
    except (ValueError, TypeError):
        return None


def summarize_runs(runs, since_iso, now=None):
    """Per-workflow outcome counts since `since_iso`, the non-success runs, and the last scheduled run per workflow (with staleness)."""
    now = now or datetime.now(timezone.utc)
    recent = [r for r in runs if r["created_at"] >= since_iso]
    by_wf = defaultdict(Counter)
    for r in recent:
        by_wf[r["name"]][r["conclusion"] or r["status"]] += 1
    not_ok = [r for r in recent if (r["conclusion"] or r["status"]) not in ("success",)]
    last_scheduled = {}
    for r in runs:                                   # newest first
        if r["event"] == "schedule" and r["path"] not in last_scheduled:
            last_scheduled[r["path"]] = r
    stale = []
    for path, r in last_scheduled.items():
        hours = age_hours(r["created_at"], now)
        limit = catalog.STALE_HOURS.get(path, catalog.STALE_DEFAULT_HOURS)
        if hours is not None and hours > limit:
            stale.append({"path": path, "name": r["name"], "hours": round(hours, 1), "limit": limit, "run": r})
    return {
        "count": len(recent),
        "by_workflow": {k: dict(v) for k, v in sorted(by_wf.items(), key=lambda kv: -sum(kv[1].values()))},
        "not_ok": sorted(not_ok, key=lambda r: r["created_at"]),
        "last_scheduled": last_scheduled,
        "stale": stale,
        "failures": sum(1 for r in not_ok if r["conclusion"] == "failure"),
        "cancels": sum(1 for r in not_ok if r["conclusion"] == "cancelled"),
    }


def key_lines(text, limit=80):
    """The lines of a log worth a person's eye, timestamps already stripped."""
    out = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or NOISE.search(line) or not KEY.search(line):
            continue
        line = re.sub(r"\x1b\[[0-9;]*m", "", line)
        if line not in out:
            out.append(line[:220])
        if len(out) >= limit:
            break
    return out


_NUM = r"(\d[\d,]*)"


def parse_nightly(text):
    """Headline numbers of a nightly reconcile (or a GTV backfill that embeds it)."""
    t = text or ""
    facts = {}
    m = re.findall(r"MISMATCHED: " + _NUM, t)
    if m:
        facts["mismatched"] = sum(int(x.replace(",", "")) for x in m)
    zeroed = re.findall(r"DONE: " + _NUM + r" zeroed", t)
    if zeroed:
        facts["zeroed"] = sum(int(x.replace(",", "")) for x in zeroed)
    held = re.findall(r"held at zero for the audit: " + _NUM, t)
    if held:
        facts["held"] = max(int(x.replace(",", "")) for x in held)
    m = re.search(r"DELETED " + _NUM + r" of " + _NUM + r" planned row", t)
    if m:
        facts["rows_deleted"] = int(m.group(1).replace(",", ""))
    m = re.search(r"UNDERPRICED on OnBuy \(listing below sheet\): " + _NUM, t)
    if m:
        facts["underpriced"] = int(m.group(1).replace(",", ""))
    m = re.search(r"FIX done: " + _NUM + r" corrected, " + _NUM + r" failed", t)
    if m:
        facts["corrected"], facts["fix_failed"] = int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
    m = re.search(r"sale guard: " + _NUM + r" of " + _NUM + r" listings carry a sale price", t)
    if m:
        facts["on_sale"], facts["listings"] = int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
    m = re.search(r"re-zeroed " + _NUM + r" listing", t)
    if m:
        facts["oversell_rezeroed"] = int(m.group(1).replace(",", ""))
    borderlines = re.findall(r"^(\S+) - borderline \(word overlap ([\d.]+)", t, re.M)
    if borderlines:
        facts["borderlines"] = [{"sku": s, "overlap": float(o)} for s, o in borderlines]
    deleted = re.findall(r"ZEROED (\S+) \((shift[+-]?\d+|collision), row (\d+)\)", t)
    if deleted:
        facts["zeroed_skus"] = [{"sku": s, "kind": k, "row": int(r)} for s, k, r in deleted]
    return facts


def parse_orders(text, today=None):
    """ORDER-LINE rows of an orders lookup -> orders with their dispatch-by date, plus counts."""
    today = today or datetime.now(timezone.utc).date().isoformat()
    orders = []
    for line in (text or "").splitlines():
        if "ORDER-LINE" not in line:
            continue
        body = line.split("ORDER-LINE", 1)[1].strip()
        parts = [p.strip() for p in body.split("|")]
        if len(parts) < 3:
            continue
        skus = re.findall(r"'([^']+)'", parts[3]) if len(parts) > 3 else []
        due = ""
        m = re.search(r"dispatch by \[?'?(\d{4}-\d{2}-\d{2})", body)
        if m:
            due = m.group(1)
        orders.append({"order_id": parts[0], "status": parts[1], "date": parts[2][:16], "skus": skus, "due": due,
                       "overdue": bool(due) and due < today, "due_today": due == today})
    orders.sort(key=lambda o: (o["due"] or "9999", o["date"]))
    return {"orders": orders, "count": len(orders), "overdue": sum(o["overdue"] for o in orders),
            "due_today": sum(o["due_today"] for o in orders)}


def parse_ebay_budget(text):
    m = re.search(r"buy/Browse/buy\.browse: limit (\d+) remaining (\d+)", text or "")
    return {"limit": int(m.group(1)), "remaining": int(m.group(2))} if m else {}


def parse_keepa(text):
    """The last 'Keepa: N token(s) used, M left' line of an Amazon sync."""
    found = re.findall(r"Keepa: (\d+) token\(s\) used, (\d+) left", text or "")
    if not found:
        return {}
    used, left = found[-1]
    return {"tokens_left": int(left), "last_batch_used": int(used), "batches": len(found)}


def parse_sync_summary(text):
    """The DONE block of an eBay / Amazon sync."""
    t = text or ""
    out = {}
    m = re.search(r"Updated rows: (\d+)", t)
    if m:
        out["updated_rows"] = int(m.group(1))
    m = re.search(r"OnBuy: (\d+) created, (\d+) updated, (\d+) deferred", t)
    if m:
        out["created"], out["onbuy_updated"], out["deferred"] = int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = re.search(r"(\d+) failed", t)
    if m:
        out["failed"] = int(m.group(1))
    return out
