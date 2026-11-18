"""The eBay card: how the hourly eBay sync did and how fresh the eBay rows are.

The eBay sync (run.yml, hourly) refreshes the store's eBay-sourced rows from eBay's Browse API: price, stock, shipping, then pushes the changes to OnBuy and ends with the dead-row purge. It can
only spend the eBay calls its allowance gives it (5,000 a day per key, the day resets at 07:00 UTC), so each run takes a batch of the rows that are due - oldest and riskiest first - and the
whole sheet comes round every day or two. How long that takes is the number that matters for overselling: an eBay seller who runs out of stock can keep selling on OnBuy until the row's turn comes.

Pure functions: the page hands in the runs' logs; the tests feed the parser the stores' REAL logs (GTV, YRA, Arden, Makstore, OpenMaal of 2026-10-28).
"""
import re
from datetime import datetime, timedelta

from .amazon import onbuy_summary, strip_stamp
from .catalogue import clean_lines, parse_purge

WORKFLOW = "run.yml"
SLOW_HOURS = 48.0                       # a refresh cycle longer than this is shown as a warning

_TIME = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),\d+ ")


def _when(raw):
    m = _TIME.match(raw)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def parse_sync(text):
    """The numbers of one eBay sync: rows on the sheet, rows without a supplier link (never refreshed), how the rotation sees the rest, the batch it took, the eBay allowance it had, a cut batch,
    the prices it changed, what eBay says delivery costs, what was pushed to OnBuy and what the purge removed."""
    facts = {"warnings": []}
    start = end = None
    for raw in clean_lines(text):
        msg = strip_stamp(raw)
        stamp = _when(raw)
        m = re.match(r"^TOTAL ROWS IN SHEET: (\d+)", msg)
        if m:
            facts["rows"] = int(m.group(1))
            continue
        m = re.match(r"^Batch size: (\d+) products/run \(budget (\d+) eBay calls/day over (\d+) runs/day\)", msg)
        if m:
            facts.update(batch=int(m.group(1)), budget=int(m.group(2)), runs_per_day=int(m.group(3)))
            continue
        m = re.match(r"^Skipping (\d+) row\(s\) with no eBay/Amazon Supplier URL", msg)
        if m:
            facts["no_link"] = int(m.group(1))
            continue
        m = re.match(r"^Rotation: scored by age x risk - (\d+) live in-stock row\(s\), (\d+) out of stock, (\d+) flagged and not live", msg)
        if m:
            facts["rotation"] = {"in_stock": int(m.group(1)), "out_of_stock": int(m.group(2)), "flagged": int(m.group(3))}
            continue
        m = re.match(r"^Processing (\d+) products", msg)
        if m:
            facts["processing"] = int(m.group(1))
            start = start or stamp
            continue
        m = re.match(r"^eBay allowance: (\d+) call\(s\) left in today's window \(reserve (\d+)\)", msg)
        if m:
            facts["allowance_left"], facts["reserve"] = int(m.group(1)), int(m.group(2))
            continue
        m = re.match(r"^Batch cut from (\d+) to (\d+) row\(s\) to stay inside eBay's daily allowance", msg)
        if m:
            facts["batch_cut"] = {"from": int(m.group(1)), "to": int(m.group(2))}
            continue
        m = re.match(r"^Updated rows: (\d+)", msg)
        if m:
            facts["updated_rows"] = int(m.group(1))
            end = stamp
            continue
        m = re.match(r"^Pricing: (\d+) row\(s\) priced with their category's commission, (\d+) formula price\(s\) followed it down", msg)
        if m:
            facts["priced"], facts["followed_down"] = int(m.group(1)), int(m.group(2))
            continue
        m = re.match(r"^eBay delivery cost: (\d+) free, (\d+) paid \(fee GBP mean ([\d.]+), median ([\d.]+), p90 ([\d.]+), max ([\d.]+)\), (\d+) not stated by eBay[^;]*; (\d+) Shipping Cost cell", msg)
        if m:
            facts["delivery"] = {"free": int(m.group(1)), "paid": int(m.group(2)), "mean": float(m.group(3)), "median": float(m.group(4)), "max": float(m.group(6)),
                                 "not_stated": int(m.group(7)), "cells_written": int(m.group(8))}
            continue
        counts = onbuy_summary(msg)
        if counts:
            facts["onbuy"] = counts
            continue
        if re.search(r"Traceback|eBay .*(failed|error|429|403|rate limit)", msg, re.I) and len(facts["warnings"]) < 5:
            facts["warnings"].append(msg[:200])
    if start and end and end >= start:
        facts["minutes"] = round((end - start).total_seconds() / 60.0)
    purge = parse_purge(text)
    if purge.get("done") is not None or purge.get("mode"):
        facts["purge"] = {k: purge[k] for k in ("mode", "done", "done_brand", "done_oos", "suspended_count", "onbuy_errors", "held_back", "ebay_gone", "ebay_alive") if k in purge}
        facts["purge"]["suspended"] = [s["sku"] for s in purge.get("suspended", [])]
    if not facts["warnings"]:
        facts.pop("warnings")
    return facts


def processed(facts):
    """The rows one sync refreshed ('Updated rows'; a run that did not get that far counts the batch it took)."""
    return facts.get("updated_rows") if facts.get("updated_rows") is not None else facts.get("processing", 0)


def cycle_estimate(runs, window_hours=24.0):
    """How long the whole sheet takes to come round, from what the syncs really did: `runs` = [{"created_at": ISO, "facts": parse_sync facts}] of the FINISHED GOOD syncs, newest first.
    The rows refreshed in the `window_hours` before the newest sync (and by it), against the rows that are due at all (the sheet's rows without those with no supplier link) ->
    {"hours", "runs", "per_run", "per_day", "eligible"} or None when there is nothing to go on. GitHub delivers only a few of the 24 scheduled runs a day, which is why this is not
    'rows / batch / runs a day' (the sync's own log line, which assumes every scheduled run comes)."""
    good = [r for r in runs or [] if r.get("facts") and processed(r["facts"]) and r["facts"].get("rows")]
    if not good:
        return None
    try:
        newest = datetime.fromisoformat(str(good[0]["created_at"]).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    floor = newest - timedelta(hours=window_hours)
    inside = []
    for r in good:
        try:
            when = datetime.fromisoformat(str(r["created_at"]).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if when > floor:
            inside.append(r)
    rows = sum(processed(r["facts"]) for r in inside)
    facts = good[0]["facts"]
    eligible = max(1, facts["rows"] - facts.get("no_link", 0))
    if not rows:
        return None
    return {"hours": round(eligible / rows * window_hours, 1), "runs": len(inside), "per_run": round(rows / len(inside)), "per_day": rows, "eligible": eligible,
            "window_hours": window_hours, "slow": eligible / rows * window_hours > SLOW_HOURS}


def trigger_label(run):
    return "scheduled" if run.get("event") == "schedule" else "manual"
