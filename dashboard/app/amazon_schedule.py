"""The dynamic Amazon schedule, as the dashboard shows it (2026-11-02).

Each store's `amazon_dispatch.yml` runs every hour, reads the number of Amazon products and its Keepa budget, and prints one line:

    AMAZON_PLAN|n=2719|runs=6|slice=1632|cycles=3.6|daily=9792|tokens_day=12240|share=12240|key_tokens_day=28800|stores_on_key=2|interval_h=4.0|limited_by=budget|elapsed_h=2.0|due=no|dispatched=no|reason=2.0 h since the last sync, the next is due after 4 h

This parses the LAST such line of a dispatcher log, and turns it into the figures the Amazon page's schedule card needs: how many products a
day the account refreshes, how often a single product is refreshed, and how much of its Keepa share that spends."""
import re

LINE = re.compile(r"AMAZON_PLAN\|([^\r\n]*)")
WARNING = re.compile(r"^WARNING (.+)$", re.M)
INTS = ("n", "runs", "slice", "daily", "tokens_day", "share", "key_tokens_day", "stores_on_key")
FLOATS = ("cycles", "interval_h", "elapsed_h")
FLAGS = ("due", "dispatched")


def parse_plan(text):
    """The newest AMAZON_PLAN line of a dispatcher log as a dict (numbers parsed, due/dispatched as booleans, warnings listed), or None."""
    last = None
    for m in LINE.finditer(text or ""):
        last = m.group(1)
    if last is None:
        return None
    out = {}
    for part in last.split("|"):
        key, _, value = part.partition("=")
        key = key.strip()
        if not key:
            continue
        try:
            if key in INTS:
                out[key] = int(float(value))
            elif key in FLOATS:
                out[key] = float(value)
            elif key in FLAGS:
                out[key] = value.strip().lower() == "yes"
            else:
                out[key] = value.strip()
        except ValueError:
            out[key] = value.strip()
    warnings = [w.strip() for w in WARNING.findall(text or "")]
    if warnings:
        out["warnings"] = warnings
    return out


def refresh_every_hours(plan):
    """Hours between two refreshes of one product (24 / passes a day), or None when the plan has no passes."""
    cycles = (plan or {}).get("cycles") or 0
    return round(24.0 / cycles, 1) if cycles else None


def share_used_percent(plan):
    """How much of its Keepa share the plan spends, in percent (the rest is headroom for lookups and bursts)."""
    share = (plan or {}).get("share") or 0
    return round(100.0 * (plan.get("tokens_day") or 0) / share) if share else None


def card_row(store, plan, syncs_24h, last_sync=None, last_tick=None):
    """One account's line in the schedule card. plan = parse_plan(...) or None (not on the dynamic schedule yet)."""
    row = {"store": store, "on_plan": bool(plan and plan.get("runs") is not None and plan.get("n") is not None),
           "syncs_24h": syncs_24h, "last_sync": last_sync, "last_tick": last_tick}
    if row["on_plan"]:
        row.update(n=plan.get("n"), runs=plan.get("runs"), slice=plan.get("slice"), daily=plan.get("daily"), cycles=plan.get("cycles"),
                   refresh_hours=refresh_every_hours(plan), tokens_day=plan.get("tokens_day"), share=plan.get("share"),
                   share_percent=share_used_percent(plan), limited_by=plan.get("limited_by"), stores_on_key=plan.get("stores_on_key"),
                   decision=plan.get("reason"), note=plan.get("note"), warnings=plan.get("warnings") or [],
                   due=plan.get("due"), dispatched=plan.get("dispatched"))
    elif plan:
        row.update(note=plan.get("note") or "the old fixed cadence", decision=plan.get("reason"))
    return row
