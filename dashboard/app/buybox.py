"""The Buy Box card: the settings of the daily Buy Box defense (three repository variables), the numbers in the engine's log, and the plain words for what it does.

The engine (buybox_defense.py, one live run a day on every store) asks OnBuy which in-stock listings do not hold the Buy Box and at what price the winner sits. Where the winner's price
minus the undercut is still at or above the FLOOR - the price that leaves the profit % of the SELLING price after OnBuy's commission - it lowers our price to win the box; where it is not, it
holds (never chases a loss) and a price already under the floor goes back up; where a contest has ended the price goes back to the sheet's price.

Pure functions - the page reads the variables and the logs and hands them in. The tests feed the parser the stores' real logs.
"""
import re

from .catalogue import clean_lines

ENABLED_VARIABLE = "BUYBOX_DEFENSE_ENABLED"
UNDERCUT_VARIABLE = "BUYBOX_DEFENSE_UNDERCUT_PENCE"
PROFIT_VARIABLE = "BUYBOX_DEFENSE_PROFIT_PERCENT"
PUSH_VARIABLE = "ONBUY_API_PUSH_ENABLED"
DEFAULT_UNDERCUT = 1
DEFAULT_PROFIT = 15.0
MAX_UNDERCUT = 20
PROFIT_RANGE = (1.0, 50.0)
OFF_WORDS = ("no", "0", "false", "off")


def clean_undercut(value):
    """Pence under the Buy Box price -> (int, "") or (None, why). 0 means level with the winner."""
    text = str(value if value is not None else "").strip()
    if not re.fullmatch(r"\d{1,2}", text) or int(text) > MAX_UNDERCUT:
        return None, f"The undercut is a whole number of pence from 0 to {MAX_UNDERCUT}."
    return int(text), ""


def clean_profit(value):
    """The profit % of the selling price the floor keeps -> (float, "") or (None, why)."""
    text = str(value if value is not None else "").strip().replace("%", "").replace(",", ".")
    try:
        number = float(text)
    except ValueError:
        return None, f"The profit is a number between {PROFIT_RANGE[0]:g} and {PROFIT_RANGE[1]:g} (percent of the selling price)."
    if not PROFIT_RANGE[0] <= number <= PROFIT_RANGE[1]:
        return None, f"The profit must be between {PROFIT_RANGE[0]:g} and {PROFIT_RANGE[1]:g} percent of the selling price."
    return round(number, 2), ""


def settings_view(variables):
    """The settings in force from the store's repository variables (a list of {name, value}): what the daily run will use, which of them are set explicitly, and whether prices are pushed."""
    values = {v["name"]: str(v.get("value") or "").strip() for v in variables}
    enabled = values.get(ENABLED_VARIABLE, "").lower() not in OFF_WORDS
    undercut, _ = clean_undercut(values.get(UNDERCUT_VARIABLE, ""))
    profit, _ = clean_profit(values.get(PROFIT_VARIABLE, ""))
    return {"enabled": enabled, "undercut": DEFAULT_UNDERCUT if undercut is None else undercut, "profit": DEFAULT_PROFIT if profit is None else profit,
            "set": {"enabled": ENABLED_VARIABLE in values, "undercut": undercut is not None, "profit": profit is not None},
            "push": values.get(PUSH_VARIABLE, "").lower() == "true", "push_value": values.get(PUSH_VARIABLE, "")}


def winning_share(facts):
    """The share of the checked listings that hold the Buy Box, in percent (one decimal), or None."""
    candidates, winning = facts.get("candidates"), (facts.get("counts") or {}).get("winning")
    if not candidates or winning is None:
        return None
    return round(100.0 * winning / candidates, 1)


def parse_defense(text):
    """The numbers of a Buy Box defense run: what it looked at, how the listings sort (winning / cheaper-not-winning / no cost / no data / reprice / held / restored), the prices it
    pushed and the ones it put back, and whether the run was live. A run that was switched off says so."""
    facts = {"pushes": [], "restores": [], "waits": 0}
    for line in clean_lines(text):
        m = re.match(r"^sheet rows with cost: (\d+) \| protected: (\d+) \| push enabled: (True|False) \| dry run: (True|False)", line)
        if m:
            facts.update(with_cost=int(m.group(1)), protected=int(m.group(2)), push_enabled=m.group(3) == "True", dry_run=m.group(4) == "True")
            continue
        m = re.match(r"^live listings: (\d+) \| in-stock unprotected candidates: (\d+)", line)
        if m:
            facts.update(live=int(m.group(1)), candidates=int(m.group(2)))
            continue
        m = re.match(r"^check-winning calls: (\d+) \| answers: (\d+)", line)
        if m:
            facts.update(calls=int(m.group(1)), answers=int(m.group(2)))
            continue
        m = re.match(r"^summary: (.+)$", line)
        if m:
            facts["counts"] = {name.strip(): int(n) for name, n in re.findall(r"([a-z][a-z -]*): (\d+)", m.group(1))}
            continue
        m = re.match(r"^\s+push (\S+) -> ([\d.]+)\s*$", line)
        if m:
            facts["pushes"].append({"sku": m.group(1), "price": float(m.group(2))})
            continue
        m = re.match(r"^\s+restore (\S+) -> ([\d.]+) \(contest ended\)", line)
        if m:
            facts["restores"].append({"sku": m.group(1), "price": float(m.group(2))})
            continue
        m = re.match(r"^pushed: (\d+) \| failed: (\d+)", line)
        if m:
            facts.update(pushed=int(m.group(1)), failed=int(m.group(2)))
            continue
        m = re.match(r"^BuyBox tab written: (\d+) contested row", line)
        if m:
            facts["contested"] = int(m.group(1))
            continue
        if line.startswith("DRY RUN - no prices pushed"):
            facts["nothing_pushed"] = True
        elif "waiting" in line and ("burst limit" in line or "HTTP 429" in line or "HTTP 5" in line):
            facts["waits"] += 1
        elif line.startswith("Buy Box defense is switched off"):
            facts["off"] = True
    for key in ("pushes", "restores"):
        if not facts[key]:
            facts.pop(key)
    if not facts["waits"]:
        facts.pop("waits")
    share = winning_share(facts)
    if share is not None:
        facts["share"] = share
    return facts


def trigger_label(run):
    """How a run started: 'daily' (the schedule) or 'manual'."""
    return "daily" if run.get("event") == "schedule" else "manual"


def describe_cron(expr):
    """'17 4 * * *' -> 'daily at 04:17 UTC' (GitHub usually starts a scheduled run a few hours late); any other schedule is shown as it is."""
    m = re.fullmatch(r"(\d{1,2}) (\d{1,2}) \* \* \*", str(expr).strip())
    return f"daily at {int(m.group(2)):02d}:{int(m.group(1)):02d} UTC" if m else str(expr)
