"""The To do card: what needs a person today, store by store - the "check the logs and give todos" as a list.

Pure functions: the page gathers the facts a store's runs, logs, variables and files give (the same ones the other cards parse) and hands them in as one dict; this turns them into items, each with a
severity, a plain sentence, the page that deals with it and (where it helps) the GitHub run. Nothing here talks to GitHub.

severity: act  = something is wrong or late right now (an order past its date, a sync that failed, updates switched off)
          look = worth a look today (a sale ending, borderline listings waiting for a call, a big price fall, tables that changed)
          fyi  = what the nightly did, no action

The facts (all optional) one store hands in:
  orders      {"count", "overdue", "due_today", "orders": [{"order_id", "due", "overdue", "due_today"}], "age_hours"}   - from the latest orders lookup (None = there is none)
  newest      {workflow path: {"run": the newest finished run, "facts": its parsed log or {}}}                        - only workflows of WATCHED
  stale       [{"name", "hours", "limit"}]                                                                            - scheduled jobs that did not run for too long
  stuck       [{"name", "created_at", "url"}]                                                                          - runs queued for days (a GitHub ghost)
  ci          the newest finished CI run (tests.yml) or None
  falls       {"alerts": n, "alert_percent": 25.0, "worst": {"row", "sku", "old", "new", "percent"}}                   - the last real Amazon sync's biggest price falls
  nightly     {"run", "facts", "age_hours"}                                                                           - the last nightly (digest.parse_nightly facts)
  frozen      [{"sku", "since"}]                                                                                      - listings frozen by the nightly in the last FROZEN_DAYS days (the hold files), not yet judged "same product"
  sale        {"active": bool, "ends": "YYYY-MM-DD", "percent": ..}                                                    - the running store sale
  push        True / False / None (ONBUY_API_PUSH_ENABLED is true / something else / not asked), push_value = its text
  fees        {"tables": "differ" | "unchanged" | "committed", "note", "run", "age_days"}                              - the latest commission-table refresh
  dead_rows   {"count", "most_nights", "reason"}                                                                       - rows the nightly's price fix refused last night AND on earlier nights (the Daily check's "rows that keep failing")
  suspended   {"waiting", "new"}                                                                                       - suspended listings waiting for a hand-delete (the Delete page's ticklist); new = reported in the last 2 days
"""
from datetime import date, datetime, timezone

ORDERS_FRESH_HOURS = 36
SOON_DAYS = 2
SALE_WARN_DAYS = 2
FEES_RECENT_DAYS = 21
FROZEN_DAYS = 7
SEVERITY_ORDER = {"act": 0, "look": 1, "fyi": 2}
SEVERITY_WORDS = {"act": "Act now", "look": "Look today", "fyi": "For your information"}

# the workflows whose newest run is checked, with the label a person knows and whether a failure needs acting on (the syncs) or only a look
WATCHED = {
    "run.yml": ("eBay sync", "act"),
    "run_amazon.yml": ("Amazon sync", "act"),
    "backfill_onbuy_status.yml": ("backfill of the OnBuy status", "act"),
    "nightly_reconcile.yml": ("nightly check", "act"),
    "buybox_defense.yml": ("Buy Box defense", "look"),
    "scan_content_mismatch.yml": ("content scan", "look"),
}


def _plural(n, one, many=None):
    return f"{n} {one if n == 1 else (many or one + 's')}"


def _ids(orders, limit=6):
    shown = [o["order_id"] + (f" (due {o['due']})" if o.get("due") else "") for o in orders[:limit]]
    return ", ".join(shown) + (f" and {len(orders) - limit} more" if len(orders) > limit else "")


def _hours_ago(run, now):
    try:
        then = datetime.fromisoformat(str(run.get("created_at")).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return max(0.0, (now - then).total_seconds() / 3600.0)


def _ago(hours):
    if hours is None:
        return "recently"
    return f"{hours:.0f} h ago" if hours < 48 else f"{hours / 24:.0f} days ago"


def _days_until(iso_day, today):
    try:
        return (date.fromisoformat(str(iso_day)[:10]) - today).days
    except ValueError:
        return None


def items_for(store_id, name, facts, now=None):
    """The items of one store, most urgent first."""
    now = now or datetime.now(timezone.utc)
    today = now.date()
    out = []

    def add(key, severity, title, detail="", link="", url="", since=None):
        out.append({"id": f"{store_id}:{key}", "store": store_id, "store_name": name, "severity": severity, "title": title, "detail": detail,
                    "link": link.replace("{s}", store_id), "url": url, "since": since})

    # ---- orders -------------------------------------------------------------------------------------------------------------
    orders = facts.get("orders")
    if "orders" not in facts:
        pass                                                                                    # not gathered: say nothing rather than guess
    elif orders is None:
        add("orders-none", "look", "No orders list yet", "Press Refresh on the Orders page: it reads what is waiting to be dispatched.", "/orders")
    else:
        lines = orders.get("orders") or []
        overdue = [o for o in lines if o.get("overdue")]
        today_lines = [o for o in lines if o.get("due_today")]
        soon = [o for o in lines if not o.get("overdue") and not o.get("due_today") and o.get("due") and 0 < (_days_until(o["due"], today) or 99) <= SOON_DAYS]
        if overdue:
            add("orders-overdue", "act", f"{_plural(len(overdue), 'order is', 'orders are')} past the dispatch date", _ids(overdue), "/orders")
        if today_lines:
            add("orders-today", "act", f"{_plural(len(today_lines), 'order')} must be dispatched today", _ids(today_lines), "/orders")
        if soon:
            add("orders-soon", "look", f"{_plural(len(soon), 'order')} due in the next {SOON_DAYS} days", _ids(soon), "/orders")
        age = orders.get("age_hours")
        if age is not None and age > ORDERS_FRESH_HOURS:
            add("orders-old", "look", f"The orders list is {age:.0f} hours old", "Refresh it on the Orders page: orders that came in since are not on it.", "/orders")

    # ---- the syncs and the other scheduled jobs --------------------------------------------------------------------------------
    for path, (label, severity) in WATCHED.items():
        entry = (facts.get("newest") or {}).get(path)
        if not entry or entry["run"].get("conclusion") != "failure":
            continue
        run, run_facts = entry["run"], entry.get("facts") or {}
        hours = _hours_ago(run, now)
        if path == "run_amazon.yml" and run_facts.get("keepa_failed"):
            failed = run_facts["keepa_failed"]
            add("amazon-tokens", "act", "The Amazon sync ran out of Keepa tokens",
                f"{failed['asins']:,} Amazon rows were left exactly as they were ({_ago(hours)}). Lower the rows per sync on the Amazon page, or get more tokens; the next good sync catches them up.",
                "/amazon?store={s}", run.get("url", ""), run.get("created_at"))
            continue
        add(f"failed-{path}", severity if run.get("event") == "schedule" else "look", f"The {label} failed {_ago(hours)}" + ("" if run.get("event") == "schedule" else " (a run started by hand)"), "Open the run for the reason; the next scheduled run may already have put it right.",
            "/store/{s}", run.get("url", ""), run.get("created_at"))
    for item in facts.get("stale") or []:
        add(f"stale-{item['name']}", "look", f"{item['name']} has not run for {item['hours']:.0f} hours", f"It should run at least every {item['limit']} hours; GitHub sometimes delays scheduled runs by hours.", "/store/{s}")
    for ghost in facts.get("stuck") or []:
        add(f"stuck-{ghost.get('url') or ghost.get('name')}", "look", f"A run of '{ghost['name']}' has been queued since {str(ghost.get('created_at'))[:10]}",
            "It will never start (a GitHub ghost). Cancel it on GitHub so it stops looking like a waiting run.", "/store/{s}", ghost.get("url", ""), ghost.get("created_at"))
    ci = facts.get("ci")
    if ci and ci.get("conclusion") == "failure":
        add("ci", "look", f"The automated tests of this store's code are failing ({_ago(_hours_ago(ci, now))})", "The last push to the repository broke a test; the syncs keep running the code that is there.",
            "/store/{s}", ci.get("url", ""), ci.get("created_at"))
    if facts.get("push") is False:
        value = facts.get("push_value")
        shown = f'"{value}"' if value else "not set"
        add("push-off", "look", "OnBuy updates are switched off for this store", f"ONBUY_API_PUSH_ENABLED is {shown}, not true: prices and stock are worked out but not sent to OnBuy.", "/settings")

    # ---- Amazon prices ----------------------------------------------------------------------------------------------------------
    falls = facts.get("falls")
    if falls and falls.get("alerts"):
        worst = falls.get("worst") or {}
        detail = ""
        if worst:
            detail = f"The biggest: row {worst['row']} (SKU {worst['sku']}) from £{worst['old']:.2f} to £{worst['new']:.2f} ({worst['percent']:g}%). A price that falls this far in one step is worth a minute on Amazon."
        add("amazon-falls", "look", f"{_plural(falls['alerts'], 'price')} fell by {falls.get('alert_percent', 25):g}% or more in the last Amazon sync", detail, "/amazon?store={s}")

    # ---- the nightly -------------------------------------------------------------------------------------------------------------
    nightly = facts.get("nightly")
    if nightly:
        n = nightly.get("facts") or {}
        bits = []
        if n.get("zeroed"):
            bits.append(f"{n['zeroed']} listing(s) zeroed for showing another product")
        if n.get("rows_deleted"):
            bits.append(f"{n['rows_deleted']} row(s) deleted")
        if n.get("corrected"):
            bits.append(f"{n['corrected']} price(s) corrected on OnBuy" + (f" ({n['fix_failed']} could not be)" if n.get("fix_failed") else ""))
        if bits:
            add("nightly", "fyi", "The nightly check " + ", ".join(bits), "", "/daily", nightly["run"].get("url", ""), nightly["run"].get("created_at"))

    frozen = facts.get("frozen") or []
    if frozen:
        shown = ", ".join(f["sku"] for f in frozen[:4]) + (f" and {len(frozen) - 4} more" if len(frozen) > 4 else "")
        add("frozen", "fyi", f"{_plural(len(frozen), 'listing')} frozen in the last {FROZEN_DAYS} days because the OnBuy page shows another product",
            f"{shown}. They stay at stock 0 until you release them - routine nightly work. If one should be selling, open the Catalogue page: it may be the same product after all (mark it), fixed (release it) or wrong (delete it).", "/catalogue?store={s}")

    # ---- sale and fees -------------------------------------------------------------------------------------------------------------
    sale = facts.get("sale")
    if sale and sale.get("active"):
        left = _days_until(sale.get("ends"), today)
        if left is not None and left <= SALE_WARN_DAYS:
            when = "today" if left <= 0 else ("tomorrow" if left == 1 else f"in {left} days")
            add("sale-ends", "look", f"The store sale ends {when} ({sale['ends']})",
                "After the last day the nightly puts the normal prices back: look at the Sale page the day after to see that it did.", "/sale?store={s}")
    fees = facts.get("fees")
    if fees and fees.get("tables") == "differ" and (fees.get("age_days") is None or fees["age_days"] <= FEES_RECENT_DAYS):
        add("fees-differ", "look", "OnBuy's commission tables have changed", ((fees.get("note") or "").rstrip(". ") + ". " if fees.get("note") else "") + "Compare them and commit them on the Fees page if they are right.", "/fees?store={s}", fees["run"].get("url", "") if fees.get("run") else "")

    # ---- dead rows and suspended listings (the Daily check's and the Delete page's finds) -------------------------------------------
    dead = facts.get("dead_rows")
    if dead and dead.get("count"):
        reason = f' - OnBuy answers "{dead["reason"]}"' if dead.get("reason") else ""
        add("dead-rows", "look", f"{_plural(dead['count'], 'row')} failed the nightly's price fix again last night",
            f"The same SKUs are refused night after night (up to {dead['most_nights']} nights running){reason}: dead rows that will not heal. "
            "The Daily check page shows them; the Delete page removes them properly (row backed up first).", "/delete?store={s}")
    susp = facts.get("suspended")
    if susp and susp.get("waiting"):
        add("suspended", "look" if susp.get("new") else "fyi", f"{_plural(susp['waiting'], 'suspended listing waits', 'suspended listings wait')} for your hand-delete",
            (f"{_plural(susp['new'], 'was', 'were')} reported in the last two days. " if susp.get("new") else "") +
            "OnBuy's API cannot delete a suspended listing; the Delete page keeps the ticklist, and none of them can sell meanwhile.", "/delete?store={s}")

    out.sort(key=lambda i: (SEVERITY_ORDER[i["severity"]], i["id"]))
    return out


def summarize(items):
    """{"act": n, "look": n, "fyi": n, "total": n} over any list of items."""
    counts = {key: 0 for key in SEVERITY_ORDER}
    for i in items:
        counts[i["severity"]] += 1
    counts["total"] = len(items)
    return counts


def grouped(items):
    """[(severity, heading, [items])] for the severities that have items, most urgent first; the items keep their order (store, then id)."""
    out = []
    for key in sorted(SEVERITY_ORDER, key=SEVERITY_ORDER.get):
        mine = [i for i in items if i["severity"] == key]
        if mine:
            out.append((key, SEVERITY_WORDS[key], mine))
    return out
