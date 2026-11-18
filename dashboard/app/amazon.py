"""The Amazon card: what the Amazon sync did (Keepa tokens, rows looked at, what the guards caught, the prices that moved most), the settings that decide what counts as in stock and which
price to believe, and the seller census that helps with the strict stock rule.

The Amazon sync (run_amazon.yml, six times a day) asks Keepa about each Amazon row's product and sets the row's price and stock from the offer a customer could really buy: Amazon's own offer,
else a third-party seller's. Keepa's price arrays are noisy - Amazon's own "Delayed" offer sits in the lowest-New price, a glitch can drop a price to a third of its level - so the sync carries
guards (2026-10-27, after Arden row 598 took an order at GBP 19.73 for a product that sells at about 40) and a second Keepa look at the Buy Box for the few products they flag.

Pure functions: the page reads the repository variables, the workflow file and the logs and hands them in; the tests feed the parsers REAL logs (Makstore 2026-10-27, a YRA run that ran out of
Keepa tokens, OpenMaal's single-job run, the seller census).
"""
import re
from datetime import datetime, timezone


def parse_iso(text):
    return datetime.fromisoformat(str(text).replace("Z", "+00:00"))


def utcnow():
    return datetime.now(timezone.utc)

from .catalogue import clean_lines

WORKFLOW = "run_amazon.yml"
CENSUS_WORKFLOW = "amazon_seller_census.yml"
OFF_WORDS = ("0", "no", "false", "off")
ON_WORDS = ("1", "yes", "true")
FALL_ALERT_PERCENT = 25.0            # a price that fell by this much or more in one sync step is marked on the page

# the settings: key, repository variable, kind, default, range, label, what it does (plain words). The meaning of an empty / unreadable value is the code's own (keepa_client.py):
# a percent or a count falls back to the default, a "default on" switch is on unless it says no / 0 / false / off, a "default off" switch is on only when it says yes / 1 / true.
SETTINGS = (
    {"key": "own_only", "variable": "AMAZON_OWN_OFFER_ONLY", "kind": "switch", "default": False, "label": "Only Amazon's own offer counts as in stock",
     "brief": "Off: a product is in stock when Amazon sells it OR any third-party seller does (the cheapest New offer). On: only Amazon's own offer counts - a row that is live on a third-party offer alone "
              "goes to stock 0 on OnBuy at the next sync. Stricter means fewer orders for products Amazon stopped selling, and far fewer live listings: the seller count below shows how many."},
    {"key": "drop_hold", "variable": "KEEPA_DROP_HOLD_PERCENT", "kind": "percent", "default": 40.0, "low": 0.0, "high": 90.0, "label": "Hold a price that falls below this share of the usual level (%)",
     "brief": "A price far under what the product normally sells at is usually a glitch or an error price (the jump starter that took an order at £19.73 instead of about £40). The row reads as out of "
              "stock until the price recovers. 40 = below 40% of the usual level; 0 switches the guard off."},
    {"key": "real_lookup", "variable": "KEEPA_REAL_PRICE_LOOKUP", "kind": "switch", "default": True, "label": "Take a second look before a held row goes out of stock",
     "brief": "For the few products the guards flag, Keepa is asked again with the Buy Box detail (about 2 extra tokens each). A product that really sells at its usual price (one Prime seller holds the box) "
              "keeps its listing at that price instead of going out of stock."},
    {"key": "real_max", "variable": "KEEPA_REAL_PRICE_MAX", "kind": "count", "default": 100, "low": 1, "high": 1000, "label": "Most second looks per run",
     "brief": "A cap on the second looks of one run (tokens). Products flagged beyond it stay held until the next run."},
    {"key": "regular_price", "variable": "KEEPA_REGULAR_PRICE", "kind": "switch", "default": True, "label": "Price from the usual level, not from a deal",
     "brief": "A lightning deal, a voucher or a short sale on Amazon would pull your OnBuy price down with it - and the order arrives after the deal has ended. On: the price comes from the level the "
              "product normally sells at (never below the current price, lifted by at most 35%)."},
    {"key": "buybox", "variable": "KEEPA_BUYBOX", "kind": "switch", "default": False, "label": "Read the Buy Box on every row (more Keepa tokens)",
     "brief": "Off: the sync uses the cheapest New offer Keepa lists and looks at the Buy Box only for flagged products. On: it asks for the Buy Box detail on every row (about 2 extra tokens per product) - "
              "the price a customer really pays. Your Keepa plan's tokens are the limit."},
    {"key": "max_products", "variable": "AMAZON_MAX_PRODUCTS_PER_RUN", "kind": "count", "default": 300, "low": 1, "high": 5000, "label": "Amazon rows each sync refreshes",
     "brief": "More rows = fresher prices, but each product costs about 1.2 Keepa tokens. When the tokens run out the run fails and every Amazon row stays as it was (YRA, 26 October). "
              "A store with a 20 tokens-a-minute plan can refresh roughly 1,500-2,000 rows an hour of waiting."},
)
BY_KEY = {s["key"]: s for s in SETTINGS}


# ---- settings -------------------------------------------------------------------------------------------------------------------
def clean_percent(value, low, high):
    text = str(value if value is not None else "").strip().replace("%", "").replace(",", ".")
    try:
        number = float(text)
    except ValueError:
        return None, f"A number between {low:g} and {high:g} (percent)."
    if not low <= number <= high:
        return None, f"The number must be between {low:g} and {high:g} (percent)."
    return round(number, 2), ""


def clean_count(value, low, high):
    text = str(value if value is not None else "").strip()
    if not re.fullmatch(r"\d{1,5}", text) or not low <= int(text) <= high:
        return None, f"A whole number between {low:g} and {high:g}."
    return int(text), ""


def clean_switch(value):
    if isinstance(value, bool):
        return value, ""
    text = str(value if value is not None else "").strip().lower()
    if text in ON_WORDS + ("on",):
        return True, ""
    if text in OFF_WORDS:
        return False, ""
    return None, "Yes or no."


def clean_value(spec, value):
    """One setting's new value -> (value, "") or (None, why)."""
    if spec["kind"] == "switch":
        return clean_switch(value)
    if spec["kind"] == "percent":
        return clean_percent(value, spec["low"], spec["high"])
    return clean_count(value, spec["low"], spec["high"])


def canonical(spec, value):
    """The text written into the repository variable (what keepa_client / the workflow read back the same way)."""
    if spec["kind"] == "switch":
        return "yes" if value else "no"
    return f"{value:g}" if spec["kind"] == "percent" else str(int(value))


def in_effect(spec, raw):
    """(the value the sync uses, True when the stored text could not be read and the default is used) - the same rules as the code that reads the variable."""
    text = str(raw or "").strip()
    if spec["kind"] == "switch":
        low = text.lower()
        if spec["default"]:
            return (low not in OFF_WORDS), False
        return (low in ON_WORDS), False
    if text == "":
        return spec["default"], False
    try:
        number = float(text) if spec["kind"] == "percent" else int(text)
    except ValueError:
        return spec["default"], True
    return number, False


def read_wiring(workflow_text):
    """The repository variables this store's Amazon sync workflow passes to the script (a variable it does not pass changes nothing when edited)."""
    return set(re.findall(r"vars\.([A-Z][A-Z0-9_]*)", workflow_text or ""))


def settings_view(variables, wired):
    """The settings as the page shows them: value in force, whether it was set explicitly, whether the sync reads it, and a note when the stored text is unreadable."""
    stored = {v["name"]: str(v.get("value") or "").strip() for v in variables}
    out = []
    for spec in SETTINGS:
        raw = stored.get(spec["variable"], "")
        value, unreadable = in_effect(spec, raw)
        out.append({**spec, "raw": raw, "value": value, "set": raw != "", "unreadable": unreadable, "wired": spec["variable"] in wired,
                    "changed": value != spec["default"]})
    return out


def changes_from(view, body):
    """What a save would write: {variable: text} for the settings whose new value differs from the one in force (nothing is created for a value that equals the default and is not set), or
    ({}, why) for the first value that cannot be read. `body` = {key: value} of the form."""
    writes = {}
    for row in view:
        if row["key"] not in body:
            continue
        value, error = clean_value(row, body[row["key"]])
        if error:
            return {}, f"{row['label']}: {error}"
        text = canonical(row, value)
        if not row["wired"]:
            continue
        if row["set"]:
            if text != row["raw"]:
                writes[row["variable"]] = text
        elif value != row["default"]:
            writes[row["variable"]] = text
    return writes, ""


# ---- the Amazon sync's log --------------------------------------------------------------------------------------------------------
_STAMP = re.compile(r"^\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d[.,]\d+ (?:DEBUG|INFO|WARNING|ERROR|CRITICAL) ")
_ONBUY_COUNTS = (("created", r"(\d+) created"), ("updated", r"(\d+) updated"), ("deferred", r"(\d+) deferred"), ("postponed", r"(\d+) postponed"), ("failed", r"(\d+) failed"),
                 ("brand_blocked", r"(\d+) brand-blocked"), ("protected", r"(\d+) protected"), ("suspended", r"(\d+) suspended-locked"))


def strip_stamp(raw):
    """A sync log line without its logger prefix ('2026-10-27 09:22:21,686 INFO ') -> the message (the eBay sync's log has the same prefix)."""
    return _STAMP.sub("", raw).strip()


def onbuy_summary(msg):
    """The closing line of every sync, 'OnBuy: 0 created, 195 updated, 2 deferred (...), ...' -> {created, updated, deferred, postponed, failed, brand_blocked, protected, suspended}, else None."""
    if not re.match(r"^OnBuy: (\d+) created, (\d+) updated, (\d+) deferred", msg):
        return None
    return {name: int(g.group(1)) for name, pat in _ONBUY_COUNTS for g in [re.search(pat, msg)] if g}


def _int(text):
    return int(str(text).replace(",", ""))


def parse_sync(text):
    """The numbers of one Amazon sync run (the prefetch job and the sync job, or the one job of the stores without a prefetch): rows, Keepa (answers, tokens, refill rate, waiting), the second looks,
    what the guards caught (Amazon's own unbuyable offer, a price far below its usual level), how prices were chosen, every price that moved, and what was pushed to OnBuy. A run that ran out of
    Keepa tokens says so (keepa_failed) and left every Amazon row as it was."""
    facts = {"moves": [], "unavailable": [], "held": [], "waits": 0, "wait_seconds": 0, "tokens_used": 0, "batches": 0}
    for raw in clean_lines(text):
        msg = _STAMP.sub("", raw).strip()
        # the balance is NEGATIVE when a run overdraws what the plan has stored ("-108 left": YRA and Arden end most syncs there); the sync then waits for the refill
        m = re.match(r"^Keepa: (\d+) token\(s\) used, (-?\d+) left, refill (\d+)/min$", msg)
        if m:
            facts["batches"] += 1
            facts["tokens_used"] += int(m.group(1))
            facts["tokens_left"], facts["refill"] = int(m.group(2)), int(m.group(3))
            continue
        m = re.match(r"^Keepa: (-?\d+) token\(s\) left, (\d+) needed - waiting (\d+)s for the refill \((\d+)/min\)$", msg)
        if m:
            facts["waits"] += 1
            facts["wait_seconds"] += int(m.group(3))
            facts["refill"] = int(m.group(4))
            continue
        m = re.match(r"^Keepa: (\d+) of (\d+) ASIN\(s\) answered, (\d+) token\(s\) used, (-?\d+|None) left", msg)
        if m:
            facts["answered"], facts["asked"] = max(facts.get("answered", 0), int(m.group(1))), max(facts.get("asked", 0), int(m.group(2)))
            continue
        m = re.match(r"^Keepa cache: (\d+) of (\d+) ASIN\(s\) answered from the cache, (\d+) fetched live", msg)
        if m:
            # the prefetch job fetches live, the sync job that follows reads the cache: the larger live count is the run's
            facts["fetched_live"] = max(facts.get("fetched_live", 0), int(m.group(3)))
            continue
        m = re.match(r"^Keepa real-price lookup: (\d+) product\(s\) flagged, (\d+) looked up", msg)
        if m:
            facts["looked_up_flagged"], facts["looked_up"] = int(m.group(1)), int(m.group(2))
            continue
        m = re.match(r"^Keepa fetch failed for (\d+) ASIN\(s\) - [^:]*: (.*)$", msg)
        if m:
            facts["keepa_failed"] = {"asins": int(m.group(1)), "reason": m.group(2).strip()}
            continue
        m = re.match(r"^UNAVAILABLE: (\S+) \((.*)\)$", msg)
        if m:
            facts["unavailable"].append({"asin": m.group(1), "why": m.group(2)})
            continue
        m = re.match(r"^PRICE DROP HELD: (\S+) is at (\d+)% of its usual level", msg)
        if m:
            facts["held"].append({"asin": m.group(1), "percent": int(m.group(2))})
            continue
        m = re.match(r"^Amazon offers held because their price fell below (\d+)% of the usual level .*: (\d+)$", msg)
        if m:
            facts["drop_hold_percent"], facts["drop_held"] = int(m.group(1)), int(m.group(2))
            continue
        m = re.match(r"^Amazon prices taken from the Buy Box .*: (\d+)$", msg)
        if m:
            facts["buybox_priced"] = int(m.group(1))
            continue
        m = re.match(r"^Amazon prices taken from the usual level .*: (\d+)$", msg)
        if m:
            facts["usual_level"] = int(m.group(1))
            continue
        m = re.match(r"^Amazon prices kept above the formula \(set by hand\): (\d+)$", msg)
        if m:
            facts["by_hand"] = int(m.group(1))
            continue
        m = re.match(r"^Row (\d+) \(SKU (.+?)\): Amazon price re-derived from current cost: ([\d.]+) -> ([\d.]+)$", msg)
        if m:
            facts["moves"].append({"row": int(m.group(1)), "sku": m.group(2), "old": float(m.group(3)), "new": float(m.group(4))})
            continue
        counts = onbuy_summary(msg)
        if counts:
            facts["onbuy"] = counts
            continue
        m = re.match(r"^OOS pass: (\d+) zeroed on OnBuy, (\d+) bounced", msg)
        if m:
            facts["zeroed"], facts["bounced"] = int(m.group(1)), int(m.group(2))
            continue
        m = re.match(r"^Processing (\d+) products", msg)
        if m:
            facts["processing"] = max(facts.get("processing", 0), int(m.group(1)))
            continue
        m = re.match(r"^TOTAL ROWS IN SHEET: (\d+)", msg)
        if m:
            facts["rows_in_sheet"] = int(m.group(1))
            continue
        m = re.match(r"^Activation pass: (\d+) activated", msg)
        if m:
            facts["activated"] = int(m.group(1))
    own = [u for u in facts["unavailable"] if "Amazon's own offer only" in u["why"]]
    facts["own_offer_only"] = len(own)
    facts["no_offer"] = len([u for u in facts["unavailable"] if u["why"].startswith("No Amazon offer")])
    asked = facts.get("fetched_live") if facts.get("fetched_live") else facts.get("answered")
    if facts["tokens_used"] and asked:
        facts["per_asin"] = round(facts["tokens_used"] / asked, 2)
    for key in ("held", "unavailable", "moves"):
        if not facts[key]:
            facts.pop(key)
    for key in ("waits", "wait_seconds", "batches", "tokens_used"):
        if not facts[key]:
            facts.pop(key)
    return facts


def price_moves(moves, top=10, alert=FALL_ALERT_PERCENT):
    """The prices a sync LOWERED -> {count, falls: the biggest ones, alerts: falls of `alert` % or more, average}. The sync logs a price only when the new one is lower than the one on the row
    ('Amazon price re-derived from current cost: old -> new', more than a penny lower); a rise is applied without a line, so the log can only show falls - which are the ones to look at."""
    rows = []
    for m in moves or []:
        if m["old"] <= 0 or m["new"] >= m["old"]:
            continue
        rows.append({**m, "percent": round(100.0 * (m["new"] - m["old"]) / m["old"], 1), "_ratio": (m["new"] - m["old"]) / m["old"]})
    rows.sort(key=lambda r: r["_ratio"])
    for r in rows:
        r.pop("_ratio")
    alerts = [r for r in rows if -r["percent"] >= alert]
    average = round(sum(-r["percent"] for r in rows) / len(rows), 1) if rows else 0.0
    return {"count": len(rows), "falls": rows[:top], "alerts": len(alerts), "alert_percent": alert, "average": average}


def trigger_label(run):
    """How a run started: 'scheduled' or 'manual'."""
    return "scheduled" if run.get("event") == "schedule" else "manual"


def waited_minutes(facts):
    return round((facts.get("wait_seconds") or 0) / 60.0)


def token_note(facts):
    """One plain sentence about the Keepa tokens of a run, or ''."""
    if "tokens_used" not in facts:
        return ""
    bits = [f"{facts['tokens_used']:,} tokens used"]
    if facts.get("per_asin"):
        bits[0] += f" (about {facts['per_asin']:g} per product)"
    if facts.get("refill"):
        bits.append(f"the plan refills {facts['refill']} a minute")
    if facts.get("waits"):
        bits.append(f"the run waited {waited_minutes(facts)} min for the refill")
    if facts.get("tokens_left") is not None:
        bits.append(f"{facts['tokens_left']:,} left at the end")
    return ", ".join(bits) + "."


# ---- the seller census --------------------------------------------------------------------------------------------------------------
def parse_census(text):
    """amazon_seller_census.py's printout: the Amazon-sourced rows by the seller Keepa last reported (all / with stock above 0) and how many rows AMAZON_OWN_OFFER_ONLY=1 would send to stock 0."""
    facts = {"sellers": []}
    in_table = False
    for line in clean_lines(text):
        m = re.match(r"^tab '([^']*)': (\d+) Amazon-sourced rows", line)
        if m:
            facts["tab"], facts["rows"] = m.group(1), int(m.group(2))
            continue
        if line.startswith("Amazon-sourced rows by the seller"):
            in_table = True
            continue
        m = re.match(r"^\s{2}(.+?)\s+(\d+) /\s+(\d+)\s*$", line)
        if in_table and m:
            facts["sellers"].append({"seller": m.group(1).strip(), "all": int(m.group(2)), "live": int(m.group(3))})
            continue
        m = re.match(r"^Would go to stock 0 under AMAZON_OWN_OFFER_ONLY=1 \(live on a third-party offer only\): (\d+)", line)
        if m:
            facts["would_zero"] = int(m.group(1))
            in_table = False
    if not facts["sellers"]:
        facts.pop("sellers")
    live = sum(s["live"] for s in facts.get("sellers", []))
    if live and "would_zero" in facts:
        facts["live"] = live
        facts["would_zero_share"] = round(100.0 * facts["would_zero"] / live, 1)
    return facts


# ---- the Keepa plan (2026-10-29): the numbers behind "keep the five 20/min keys, raise two, or share one bigger one" --------------------
BUCKET_MINUTES = 60                  # a Keepa key stores up to 60 minutes of refill: a 20/min key holds at most 1,200 tokens


def real_syncs(rows):
    """The full syncs out of a store's parsed runs ([{run, facts}]): a one-row fix asks for a handful of ASINs and would make the averages lie."""
    return [r for r in rows if (r.get("facts") or {}).get("asked") and r["facts"]["asked"] >= 100 and r["facts"].get("tokens_used")]


def per_day(rows, now):
    """Real syncs per day, counted over the last two days of runs (GitHub delivers only some of the scheduled ones - this counts what really ran)."""
    recent = [r for r in real_syncs(rows) if (now - parse_iso(r["run"]["created_at"])).total_seconds() <= 48 * 3600]
    return round(len(recent) / 2, 1)


def wait_at(tokens, rate):
    """Minutes a sync needing `tokens` spends waiting for refills at `rate` tokens a minute, starting from a full bucket (rate x 60). The measured waits
    sit a little above this (the bucket is rarely full when a sync starts), so it compares plans fairly rather than promising exact minutes."""
    need = tokens - rate * BUCKET_MINUTES
    return 0 if need <= 0 else round(need / rate)


def economics(rows, now=None):
    """What a store's real syncs actually use, averaged -> {runs, per_day, asked, tokens, waits, wait_minutes, rate, lowest_left, wait_now/double/shared60} or None."""
    syncs = real_syncs(rows)
    if not syncs:
        return None
    facts = [r["facts"] for r in syncs]
    n = len(facts)
    avg = lambda key: round(sum(f.get(key) or 0 for f in facts) / n)
    lows = [f.get("tokens_left") for f in facts if f.get("tokens_left") is not None]
    rate = next((f.get("refill") for f in facts if f.get("refill")), 20)
    tokens = avg("tokens_used")
    return {"runs": n, "per_day": per_day(rows, now or utcnow()), "asked": avg("asked"), "tokens": tokens, "waits": avg("waits"),
            "wait_minutes": round(avg("wait_seconds") / 60), "rate": rate, "lowest_left": min(lows) if lows else None,
            "wait_now": wait_at(tokens, rate), "wait_double": wait_at(tokens, rate * 2), "wait_shared60": wait_at(tokens, 60)}


def plan_totals(stores):
    """The fleet line under the table: tokens a day across the stores with data, and the waiting minutes a day now vs the two options."""
    with_data = [s for s in stores if s.get("eco")]
    if not with_data:
        return None
    daily = lambda key: round(sum(s["eco"][key] * s["eco"]["per_day"] for s in with_data))
    return {"stores": len(with_data), "tokens_day": daily("tokens"), "wait_day": daily("wait_minutes"),
            "wait_day_double": daily("wait_double"), "wait_day_shared60": daily("wait_shared60")}
