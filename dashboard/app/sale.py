"""The sale card's brain: price ranges with a sale % each, the running sale (store_sale.json), the inputs of a store_sale.yml run, and the numbers in its logs.

Pure functions - the page fetches the state file and the logs and hands them in; the tests feed them real log excerpts. The validation here mirrors store_sale.py's own
(the tool refuses nonsense too), so a mistake is caught before a run is queued.
"""
import json
import re
from datetime import date, datetime, timedelta

# the brackets the user thinks in (GTV: under 5 / 5-10 / 10-20 / 20-50 / 50+), pence-exact so no price falls in a gap and none sits in two
BRACKETS = [(0, 4.99), (5, 9.99), (10, 20), (20.01, 50), (50.01, None)]
MAX_RANGES = 20
MAX_DAYS = 365
ACTIVE_MODES = ("apply", "cancel", "test", "refresh")


def _num(v):
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(str(v).replace("£", "").replace(",", "").strip())
    except ValueError:
        return None


def _blank(v):
    return v is None or str(v).strip() == ""


def money(n):
    return f"{n:.2f}".rstrip("0").rstrip(".")


def pct_text(p):
    return f"{p:g}"


def label_range(lo, hi):
    if lo is None and hi is None:
        return "every price"
    if lo is None:
        return f"up to £{money(hi)}"
    if hi is None:
        return f"£{money(lo)} and above"
    return f"£{money(lo)} to £{money(hi)}"


# ---- ranges ---------------------------------------------------------------------------------------------------------------------
def clean_ranges(rows):
    """The page's rows [[from, to, percent], ...] -> ([[low|None, high|None, percent], ...], error). A blank percent is 0 (that range is kept out of the sale);
    from / to blank = open ended. At least one range must carry a sale."""
    if not isinstance(rows, (list, tuple)) or not rows:
        return None, "Give at least one price range."
    if len(rows) > MAX_RANGES:
        return None, f"At most {MAX_RANGES} price ranges."
    out = []
    for n, row in enumerate(rows, 1):
        if not isinstance(row, (list, tuple)) or len(row) != 3:
            return None, f"Range {n}: a range is a low price, a high price and a sale %."
        lo = None if _blank(row[0]) else _num(row[0])
        hi = None if _blank(row[1]) else _num(row[1])
        pct = 0.0 if _blank(row[2]) else _num(row[2])
        if (not _blank(row[0]) and lo is None) or (not _blank(row[1]) and hi is None) or pct is None:
            return None, f"Range {n}: prices and the sale % must be numbers."
        if (lo is not None and lo < 0) or (hi is not None and hi < 0):
            return None, f"Range {n}: a price cannot be negative."
        if lo is not None and hi is not None and hi < lo:
            return None, f"Range {n}: the high price is below the low price."
        if not (pct == 0 or 1 <= pct <= 90):
            return None, f"Range {n}: the sale % is 1 to 90 (leave it empty or 0 to keep that range out)."
        out.append([lo, hi, pct])
    if not any(r[2] > 0 for r in out):
        return None, "No range has a sale % - nothing would go on sale."
    return out, ""


def ranges_text(ranges):
    """The PRICE_RANGES input of the workflow: compact JSON the tool parses."""
    return json.dumps([[r[0], r[1], r[2]] for r in ranges], separators=(",", ":"))


def describe_ranges(ranges):
    return "; ".join(f"{pct_text(p)}% off {label_range(lo, hi)}" if p else f"no sale on {label_range(lo, hi)}" for lo, hi, p in ranges)


def clean_end(text, today=None):
    """The sale's last day: YYYY-MM-DD, today or later, at most a year ahead -> (text, error)."""
    today = today or date.today()
    s = str(text or "").strip()
    try:
        d = datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None, "Pick the sale's last day."
    if d < today:
        return None, "The last day is in the past."
    if d > today + timedelta(days=MAX_DAYS):
        return None, "The last day is more than a year away."
    return s, ""


def build_inputs(body, mode, today=None):
    """The store_sale.yml inputs for a mode from the page's body -> (inputs, error). plan / apply need the ranges, the last day and the floor; test also a SKU; cancel nothing."""
    if mode == "cancel":
        return {"mode": "cancel"}, ""
    ranges, error = clean_ranges(body.get("ranges"))
    if error:
        return None, error
    end, error = clean_end(body.get("sale_end"), today)
    if error:
        return None, error
    floor_off = bool(body.get("floor_off"))
    if floor_off:
        min_profit = "off"
    else:
        mp = _num(body.get("min_profit") if not _blank(body.get("min_profit")) else 10)
        if mp is None or not 0 <= mp <= 500:
            return None, "The margin floor is a profit % from 0 to 500."
        min_profit = f"{mp:g}"
    floor_mode = str(body.get("floor_mode") or "skip").strip().lower()
    scope = str(body.get("scope") or "all").strip().lower()
    if floor_mode not in ("skip", "cap") or scope not in ("all", "in_stock"):
        return None, "Unknown floor mode or scope."
    inputs = {"mode": mode, "price_ranges": ranges_text(ranges), "sale_end": end, "min_profit": min_profit, "floor_mode": floor_mode, "scope": scope}
    if mode == "apply":
        inputs["max_changes"] = "20000"                              # a runaway plan stops here; the biggest store has about 12,000 listings
    if mode == "test":
        sku = str(body.get("test_sku") or "").strip()
        if not sku:
            return None, "Give the SKU to try."
        inputs["test_sku"] = sku
    return inputs, ""


# ---- the state file -------------------------------------------------------------------------------------------------------------
def describe_state(state):
    """The running sale in words: its own summary, else (a state written before price ranges existed) a percentage and an optional excluded range."""
    if state.get("summary"):
        return str(state["summary"]).replace("GBP ", "£")
    p = _num(state.get("percent"))
    text = f"{pct_text(p)}% off every listing" if p else "a sale"
    lo, hi = _num(state.get("exclude_price_from")), _num(state.get("exclude_price_to"))
    if lo is not None and hi is not None:
        text += f" except {label_range(lo, hi)}"
    return text


def state_view(text, today=None):
    """store_sale.json text -> what the page shows, or None when there is no sale file / it cannot be read."""
    try:
        state = json.loads(text or "")
    except ValueError:
        return None
    if not isinstance(state, dict):
        return None
    today = (today or date.today()).isoformat()
    end = str(state.get("sale_end_date") or "")[:10]
    ranges = []
    for item in state.get("price_ranges") or []:
        try:
            ranges.append({"low": item[0], "high": item[1], "percent": item[2], "label": label_range(item[0], item[1])})
        except (TypeError, IndexError):
            continue
    floor = state.get("min_profit_percent")
    return {"active": bool(end) and end >= today, "summary": describe_state(state), "ends": end, "starts": str(state.get("sale_start_date") or "")[:10],
            "applied_at": state.get("applied_at") or "", "listings": state.get("listings"), "ranges": ranges, "scope": state.get("scope") or "all",
            "floor": "none" if str(floor).lower() == "off" else (f"{floor}% profit on cost + shipping after the fee, {state.get('floor_mode') or 'skip'}" if floor is not None else ""),
            "exclude": [state.get("exclude_price_from"), state.get("exclude_price_to")] if state.get("exclude_price_from") is not None else None}


# ---- the logs ---------------------------------------------------------------------------------------------------------------------
def _clean(text):
    for raw in (text or "").splitlines():
        yield re.sub(r"\x1b\[[0-9;]*m", "", raw).rstrip()


def _int(s):
    return int(str(s).replace(",", ""))


_MODE3 = re.compile(r"^MODE (\w+) \| sale (.*?) \| window (\S+ \S+) \.\. (\S+ \S+) \| scope (\w+) \| margin floor (.*?) \| state: (.*)$")
_MODE2 = re.compile(r"^MODE (\w+) \| percent ([\d.]+|-) \| window (\S+ \S+) \.\. (\S+ \S+) \| scope (\w+)(?: \| excluded prices (.*?))? \| margin floor (.*?) \| state: (.*)$")
_RANGE = re.compile(r"^RANGE (\d+) \| (.+?) \| (kept out|[\d.]+%) \| (\d+) listings \| (\d+) on sale \| (\d+) no cost \| (\d+) below the floor \| (\d+) other \| "
                    r"GBP ([\d,.]+) off \| (\d+) sale\(s\) ended$")


def parse_store_sale(text):
    """The numbers of a store_sale run (plan, test, apply, cancel or refresh). Reads the v3 format (price ranges, no braces) and the v2 one GTV's first runs wrote."""
    facts = {"actions": [], "ranges": []}
    for line in _clean(text):
        m = _MODE3.match(line)
        if m:
            facts.update(mode=m.group(1), sale=m.group(2), window_start=m.group(3), window_end=m.group(4), scope=m.group(5), floor=m.group(6), state_before=m.group(7))
            continue
        m = _MODE2.match(line)
        if m:
            sale = f"{m.group(2)}% off every listing" if m.group(2) != "-" else "-"
            if m.group(6) and m.group(6) != "none":
                sale += f" except {m.group(6)}"
            facts.update(mode=m.group(1), sale=sale, window_start=m.group(3), window_end=m.group(4), scope=m.group(5), floor=m.group(7), state_before=m.group(8))
            continue
        m = re.match(r"^sweep: (\d+) listings in (\d+) page", line) or re.match(r"^shared sweep: (\d+) listings", line)
        if m:
            facts["listings"] = _int(m.group(1))
            continue
        m = re.match(r"^sales on the account now: (\d+) of (\d+) listings(?: \| end dates (.*))?", line)
        if m:
            facts["sales_now"], facts["listings"] = _int(m.group(1)), _int(m.group(2))
            ends = m.group(3) or ""
            facts["sales_end_dates"] = ", ".join(f"{k} ({v})" for k, v in re.findall(r"(\d{4}-\d{2}-\d{2})(?:=|'?: ?)(\d+)", ends))
            continue
        m = re.match(r"^PLAN (.+?) \| (\d+) update\(s\) in (\d+) request\(s\)$", line)
        if m:
            facts.update(plan=m.group(1), updates=int(m.group(2)), requests=int(m.group(3)))
            continue
        m = re.match(r"^PLAN ([\d.]+% off): (.*) -> (\d+) update\(s\) in (\d+) request\(s\)$", line)          # the first runs of 2026-10-26: counts inside masked braces
        if m:
            facts.update(plan=m.group(1), updates=int(m.group(3)), requests=int(m.group(4)))
            facts["actions"] = [{"action": k, "listings": int(v)} for k, v in re.findall(r"'([^']+)': (\d+)", m.group(2))]
            continue
        m = re.match(r"^ACTIONS (.+)$", line)
        if m and m.group(1) != "none":
            facts["actions"] = [{"action": a.rsplit("=", 1)[0], "listings": int(a.rsplit("=", 1)[1])} for a in m.group(1).split("; ") if "=" in a]
            continue
        m = _RANGE.match(line)
        if m:
            facts["ranges"].append({"range": int(m.group(1)), "prices": m.group(2).replace("GBP ", "£"), "sale": m.group(3), "listings": int(m.group(4)),
                                    "on_sale": int(m.group(5)), "no_cost": int(m.group(6)), "below_floor": int(m.group(7)), "other": int(m.group(8)),
                                    "discount": float(m.group(9).replace(",", "")), "ended": int(m.group(10))})
            continue
        m = re.match(r"^RANGE other \| outside every selected range \| (\d+) listings", line)
        if m:
            facts["outside"] = int(m.group(1))
            continue
        m = re.match(r"^after this run (\d+) of (\d+) listings carry the sale, GBP ([\d,.]+) off in total", line)
        if m:
            facts.update(on_sale_after=_int(m.group(1)), listings=_int(m.group(2)), discount=float(m.group(3).replace(",", "")))
            continue
        if line.startswith("PLAN ONLY - nothing changed"):
            facts["nothing_changed"] = True
            continue
        m = re.match(r"^store_sale\.json written \((.*)\)$", line)
        if m:
            facts["state_written"] = m.group(1)
            continue
        m = re.match(r"^APPLIED: (\d+) ok, (\d+) failed", line)
        if m:
            facts["applied_ok"], facts["applied_failed"] = int(m.group(1)), int(m.group(2))
            continue
        m = re.match(r"^read-back after \d+s: (\d+) of (\d+) already show (?:the sale|no sale)", line)
        if m:
            facts["readback"] = f"{m.group(1)} of {m.group(2)}"
            continue
        m = re.match(r"^TO END: (\d+) sale\(s\)", line)
        if m:
            facts["to_end"] = int(m.group(1))
            continue
        m = re.match(r"^CANCELLED: (\d+) ok, (\d+) failed", line)
        if m:
            facts["cancelled_ok"], facts["cancelled_failed"] = int(m.group(1)), int(m.group(2))
            facts["state_removed"] = "store_sale.json removed" in line
            continue
        m = re.match(r"^(\S+): before .* -> (.+)$", line)
        if m and facts.get("mode") == "test":
            facts["test_sku"], facts["test_plan"] = m.group(1), m.group(2)
            continue
        m = re.match(r"^RESULT sale on: (.+)$", line)
        if m:
            facts["test_on"] = m.group(1)
            continue
        m = re.match(r"^RESULT sale off: (.+)$", line)
        if m:
            facts["test_off"] = m.group(1)
            continue
        if line.startswith("RESULT: nothing sent"):
            facts["test_on"] = "nothing sent - this listing would not be put on sale"
    if not facts["actions"]:
        facts.pop("actions")
    if not facts["ranges"]:
        facts.pop("ranges")
    return facts
