"""The pricing card's brain: a store's profit schedule (the PROFIT_SCHEDULE setting, else the constants in its pricing.py), the setting
JSON for a change (the outgoing schedule kept as superseded), the price formula, and the numbers in an even-margins run.

Pure functions - the page fetches the variable, the source file and the logs and hands them in.
"""
import ast
import json
import re


class _Unresolvable(Exception):
    pass


def _evaluate(node, env):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in env:
            return env[node.id]
        raise _Unresolvable(node.id)
    if isinstance(node, (ast.Tuple, ast.List)):
        return tuple(_evaluate(e, env) for e in node.elts)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_evaluate(node.operand, env)
    if isinstance(node, ast.BinOp):
        a, b = _evaluate(node.left, env), _evaluate(node.right, env)
        if isinstance(node.op, ast.Add):
            return a + b
        if isinstance(node.op, ast.Sub):
            return a - b
        if isinstance(node.op, ast.Mult):
            return a * b
        if isinstance(node.op, ast.Div):
            return a / b
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_top_band_profit":
        # the top-band knob: the repository variable when set, else the standing value
        if "TOP_BAND_PROFIT_KNOB" in env:
            return env["TOP_BAND_PROFIT_KNOB"]
        if "STANDARD_TOP_BAND_PROFIT" in env:
            return env["STANDARD_TOP_BAND_PROFIT"]
    raise _Unresolvable(type(node).__name__)


def parse_pricing_source(text, knob=None):
    """The simple module-level constants of a pricing.py, evaluated in order (names, tuples, + on tuples, the top-band knob call)."""
    env = {}
    if knob not in (None, ""):
        try:
            env["TOP_BAND_PROFIT_KNOB"] = float(knob)
        except (TypeError, ValueError):
            pass
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return env
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                env[node.targets[0].id] = _evaluate(node.value, env)
            except (_Unresolvable, KeyError, TypeError, ZeroDivisionError):
                continue
    return env


def _bands_list(bands):
    return [[None if b is None else float(b), float(p)] for b, p in bands]


def code_schedule(text, knob=None):
    """What the constants of a pricing.py say: bands, the selling-price window (None when the store has no such mechanism),
    the superseded schedules and the fee constants."""
    env = parse_pricing_source(text, knob)
    bands = env.get("PROFIT_BANDS")
    if not bands:
        return None
    overrides = env.get("SELL_PRICE_OVERRIDES")
    return {
        "bands": _bands_list(bands),
        "overrides": [[float(a), float(b), float(c)] for a, b, c in overrides] if overrides is not None else None,
        "superseded": [_bands_list(b) for b in env.get("_SUPERSEDED_PROFIT_BANDS") or ()],
        "platform_fee": env.get("PLATFORM_FEE_PERCENT"),
        "fee_vat": env.get("FEE_VAT_PERCENT"),
        "top_band_from": env.get("TOP_BAND_FROM"),
        "knob_used": "TOP_BAND_PROFIT_KNOB" in env and "STANDARD_TOP_BAND_PROFIT" in env,
    }


def check_bands(bands):
    """'' when the bands are a valid schedule, else what is wrong with them (same rules as the stores' pricing.py)."""
    if not isinstance(bands, (list, tuple)) or not bands:
        return "The schedule needs at least one band."
    clean = []
    for item in bands:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            return "Each band is an upper bound and a profit %."
        bound, profit = item
        try:
            bound = None if bound in (None, "") else float(bound)
            profit = float(profit)
        except (TypeError, ValueError):
            return "Bounds and profits must be numbers."
        if bound is not None and bound <= 0:
            return "An upper bound must be above 0."
        if not 0 <= profit <= 1000:
            return "A profit % must be between 0 and 1000."
        clean.append([bound, profit])
    if clean[-1][0] is not None:
        return "The last band must have no upper bound (it covers everything above the previous one)."
    if any(b is None for b, _ in clean[:-1]):
        return "Only the last band may have no upper bound."
    for i in range(len(clean) - 2):
        if clean[i][0] >= clean[i + 1][0]:
            return "Upper bounds must rise from band to band."
    return ""


def clean_bands(bands):
    return [[None if b in (None, "") else float(b), float(p)] for b, p in bands]


def check_overrides(overrides):
    if overrides is None:
        return ""
    if not isinstance(overrides, (list, tuple)):
        return "The windows must be a list."
    for item in overrides:
        if not isinstance(item, (list, tuple)) or len(item) != 3:
            return "Each window is a low price, a high price and a profit %."
        try:
            lo, hi, pct = (float(x) for x in item)
        except (TypeError, ValueError):
            return "Window values must be numbers."
        if lo < 0 or hi < lo or not 0 <= pct <= 1000:
            return "A window needs 0 <= low <= high and a profit % between 0 and 1000."
    return ""


def clean_overrides(overrides):
    return None if overrides is None else [[float(a), float(b), float(c)] for a, b, c in overrides]


def validate_setting(raw):
    """The PROFIT_SCHEDULE text as the stores read it: {'bands', 'superseded', 'overrides'} or None when unset / malformed."""
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(data, dict) or check_bands(data.get("bands")):
        return None
    superseded = [clean_bands(old) for old in data.get("superseded") or [] if not check_bands(old)]
    overrides = None
    if "sell_price_overrides" in data:
        if check_overrides(data.get("sell_price_overrides") or []):
            return None
        overrides = clean_overrides(data.get("sell_price_overrides") or [])
    return {"bands": clean_bands(data["bands"]), "superseded": superseded, "overrides": overrides}


def effective_schedule(setting_raw, code):
    """What the store prices with right now: the setting when it parses, else the code's constants."""
    setting = validate_setting(setting_raw)
    if setting:
        overrides = setting["overrides"] if setting["overrides"] is not None else (code or {}).get("overrides")
        return {"source": "setting", "bands": setting["bands"], "overrides": overrides, "superseded": setting["superseded"]}
    if code:
        return {"source": "code", "bands": code["bands"], "overrides": code["overrides"], "superseded": code["superseded"]}
    return None


def build_setting(current, bands, overrides=None):
    """The PROFIT_SCHEDULE text for a new schedule: the schedule being replaced joins the superseded list."""
    superseded = [list(map(list, b)) for b in (current or {}).get("superseded") or []]
    old = (current or {}).get("bands")
    if old and old != bands and old not in superseded:
        superseded.append(old)
    data = {"bands": bands, "superseded": superseded}
    if overrides is not None:
        data["sell_price_overrides"] = overrides
    return json.dumps(data, separators=(",", ":"))


def describe_bands(bands):
    """[(range text, profit %), ...] for a table."""
    out, prev = [], None
    for i, (bound, profit) in enumerate(bands or []):
        if i == 0:
            text = f"under £{bound:g}" if bound is not None else "everything"
        elif bound is None:
            text = f"above £{prev:g}"
        else:
            text = f"£{prev:g} to £{bound:g}"
        out.append((text, profit))
        prev = bound if bound is not None else prev
    return out


def band_profit(bands, total_cost):
    """The band's profit for a cost + shipping (first band strict-below, the others inclusive, like the stores' _band_lookup)."""
    if not bands:
        return None
    if bands[0][0] is not None and total_cost < bands[0][0]:
        return bands[0][1]
    for bound, profit in bands[1:] if bands[0][0] is not None else bands:
        if bound is None or total_cost <= bound:
            return profit
    return bands[-1][1]


def price_for(total_cost, profit_pct, fee_effective_pct):
    """The schedule's selling price: cost + shipping, plus the profit, divided by what is left after OnBuy's deduction."""
    return round(total_cost * (1 + profit_pct / 100.0) / (1 - fee_effective_pct / 100.0), 2)


_TAB = re.compile(r"^=== (.+?) \((Amazon|eBay) pricing\): (\d+) rows with a SKU \| (.*)$")
_ACT = re.compile(r"^\s*(LOWER|RAISE): (\d+) rows \((\d+) in stock, (\d+) Buy Box-defended\) \| median (?:lower|raise) ([\d.]+)%")


def parse_even_margins(text):
    """The numbers of an even-margins run (dry run or apply)."""
    facts = {"tabs": []}
    current = None
    for raw in (text or "").splitlines():
        line = re.sub(r"\x1b\[[0-9;]*m", "", raw).rstrip()
        if line.startswith("DRY RUN |") or line.startswith("APPLY |"):
            facts["mode"] = "dry run" if line.startswith("DRY RUN") else "apply"
            continue
        m = _TAB.match(line)
        if m:
            current = {"tab": m.group(1), "kind": m.group(2), "rows": int(m.group(3))}
            for act, n in re.findall(r"(\w+) (\d+)", m.group(4)):
                current[act] = int(n)
            facts["tabs"].append(current)
            continue
        m = _ACT.match(line)
        if m and current is not None:
            act = m.group(1).lower()
            current[f"{act}_in_stock"] = int(m.group(3))
            current[f"{act}_defended"] = int(m.group(4))
            current[f"median_{act}_pct"] = float(m.group(5))
            continue
        m = re.match(r"^TOTAL: (\d+) price\(s\) to change, (\d+) held for review", line)
        if m:
            facts["to_change"], facts["held"] = int(m.group(1)), int(m.group(2))
            continue
        m = re.match(r"^STOP: (\d+) changes exceed the cap of (\d+)", line)
        if m:
            facts["cap_stop"] = f"{m.group(1)} changes exceed the cap of {m.group(2)}"
            continue
        m = re.match(r"^DONE: (\d+) row\(s\) put on the schedule, (\d+) skipped", line)
        if m:
            facts["written"], facts["skipped"] = int(m.group(1)), int(m.group(2))
            continue
        m = re.match(r"^backup tab '(.+?)': (\d+) row", line)
        if m:
            facts["backup_tab"], facts["backup_rows"] = m.group(1), int(m.group(2))
    lower = sum(t.get("lower", 0) for t in facts["tabs"])
    raise_ = sum(t.get("raise", 0) for t in facts["tabs"])
    if facts["tabs"]:
        facts["lower"], facts["raise"], facts["ok"] = lower, raise_, sum(t.get("ok", 0) for t in facts["tabs"])
    return facts
