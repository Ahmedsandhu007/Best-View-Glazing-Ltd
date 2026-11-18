"""The Delivery card: which OnBuy delivery template each supplier's listings should sit on, where they sit now, and the numbers in the delivery tool's log.

On OnBuy every listing sits on a delivery template (handling time, delivery time and cost). eBay- and Amazon-sourced products dispatch fast, AliExpress ones take longer, so each
supplier has its own template. The tool (delivery_templates.py, on every store) works out a listing's supplier from the sheet - the first product tab by its link, the Amazon tab
as Amazon, on Makstore the semi sheet as AliExpress - and moves a listing that sits off its supplier's template; a listing with no sheet row is never moved. The template ids are per
OnBuy account and live in three repository variables the dashboard sets. Arden and Makstore also run the tool every night on what was created during the day.

Pure functions - the page reads the variables, the workflow file and the logs and hands them in. The tests feed the parser the stores' real logs.
"""
import re

from .catalogue import clean_lines

SUPPLIERS = (
    {"key": "ebay", "label": "eBay", "variable": "DELIVERY_TEMPLATE_EBAY", "input": "template_ebay", "env": "TEMPLATE_EBAY"},
    {"key": "amazon", "label": "Amazon", "variable": "DELIVERY_TEMPLATE_AMAZON", "input": "template_amazon", "env": "TEMPLATE_AMAZON"},
    {"key": "ali", "label": "AliExpress", "variable": "DELIVERY_TEMPLATE_ALI", "input": "template_ali", "env": "TEMPLATE_ALI"},
)
OTHER_CLASSES = (("legacy", "No sheet row (legacy)"), ("other", "A link of another supplier"), ("none", "A sheet row without a link"))
IN_NIGHTLY = ("arden", "makstore")           # the stores whose nightly run also puts what was created during the day onto its supplier's template
MAX_CHANGES = (1, 20000)


def clean_id(value):
    """A delivery template id: a whole number of up to 9 digits -> (id as text, "") or (None, why)."""
    text = str(value if value is not None else "").strip()
    if not re.fullmatch(r"[1-9]\d{0,8}", text):
        return None, "A template id is the template's number (digits only, e.g. 54810)."
    return text, ""


def clean_max_changes(value, default=3000):
    """Most listings an apply may move -> (int, "") or (None, why)."""
    text = str(value if value is not None else "").strip()
    if text == "":
        return default, ""
    if not text.isdigit() or not MAX_CHANGES[0] <= int(text) <= MAX_CHANGES[1]:
        return None, f"The limit is a whole number from {MAX_CHANGES[0]} to {MAX_CHANGES[1]:,}."
    return int(text), ""


def read_wiring(text):
    """From the store's delivery_templates.yml: which suppliers it takes an id for, whether a manual run reads the repository variable, and the built-in fallback id."""
    out = {}
    for s in SUPPLIERS:
        m = re.search(r"%s: \$\{\{ inputs\.%s(?: \|\| vars\.%s)?(?: \|\| '(\d+)')? \}\}" % (s["env"], s["input"], s["variable"]), text or "")
        if m:
            out[s["key"]] = {"variable_read": f"vars.{s['variable']}" in m.group(0), "fallback": m.group(1) or ""}
    return out


def effective_ids(variables, wiring):
    """The template id each supplier's listings are moved to: the repository variable, else the workflow's built-in fallback, else none -> [{key, label, id, source, wired, ...}]."""
    values = {v["name"]: str(v.get("value") or "").strip() for v in variables}
    out = []
    for s in SUPPLIERS:
        w = wiring.get(s["key"])
        if not w:
            continue
        var, _ = clean_id(values.get(s["variable"], ""))
        if var:
            source, tid = "variable", var
        elif w["fallback"]:
            source, tid = "built in", w["fallback"]
        else:
            source, tid = "none", ""
        out.append({**s, "id": tid, "source": source, "wired": w["variable_read"]})
    return out


def _counts(text):
    """{'52506': 7291, '54810': 115} as the log prints it (GitHub masks the braces as ***) -> {'52506': 7291, ...}."""
    return {k: int(v) for k, v in re.findall(r"'([^']+)': (\d+)", text or "")}


def parse_templates(text):
    """The numbers of a delivery-template run (a manual plan / test / apply, or the nightly's step): the template ids it used, the census (listings per supplier and the templates
    they sit on), how many would move and what was moved, or the one-listing test and its read-back."""
    facts = {"classes": {}, "moves": [], "batches": []}
    for line in clean_lines(text):
        m = re.match(r"^MODE (\w+) \| templates: eBay ([^\s,|]+), Amazon ([^\s,|]+)(?:, AliExpress ([^\s,|]+))? \|(.*)$", line)
        if m:
            tail = m.group(5)
            facts.update(mode=m.group(1), ids={"ebay": "" if m.group(2) == "-" else m.group(2), "amazon": "" if m.group(3) == "-" else m.group(3),
                                               "ali": "" if (m.group(4) or "-") == "-" else m.group(4)})
            c = re.search(r"clear own handling time: (yes|no)", tail)
            if c:
                facts["clear_handling"] = c.group(1) == "yes"
            b = re.search(r"sheet SKUs by supplier: (.*)$", tail)
            if b:
                facts["sheet_skus"] = _counts(b.group(1))
            continue
        m = re.match(r"^semi sheet '(.+)': (\d+) SKUs by supplier (.*), (\d+) added", line)
        if m:
            facts["semi"] = {"sheet": m.group(1), "skus": int(m.group(2)), "added": int(m.group(4))}
            continue
        if line.startswith("WARNING: semi sheet"):
            facts["semi_warning"] = line[len("WARNING: "):][:200]
            continue
        m = re.match(r"^(?:shared sweep|sweep): (\d+) listings", line)
        if m:
            facts["swept"] = int(m.group(1))
            continue
        m = re.match(r"^listings: (\d+) \| delivery_template_id: (.+?) \| handling_time: (.+)$", line)
        if m:
            facts.update(listings=int(m.group(1)), templates=_counts(m.group(2)), handling=_counts(m.group(3)))
            continue
        m = re.match(r"^\s+(ebay|amazon|ali|other|none|legacy)\s+(\d+) listings \| templates (.+?) \| handling (.+)$", line)
        if m:
            facts["classes"][m.group(1)] = {"listings": int(m.group(2)), "templates": _counts(m.group(3)), "handling": _counts(m.group(4))}
            continue
        m = re.match(r"^listings with their own handling time: (\d+)", line)
        if m:
            facts["own_handling"] = int(m.group(1))
            continue
        m = re.match(r"^TO MOVE: (\d+) listing\(s\):(.*?)(?: \| handling time cleared on (\d+))?$", line)
        if m:
            facts["to_move"] = int(m.group(1))
            facts["moves"] = [{"supplier": c, "from": f, "to": t, "n": int(n)} for c, f, t, n in re.findall(r"(\w+) (\S+?)->(\S+?): (\d+)", m.group(2))]
            if m.group(3) is not None:
                facts["handling_cleared"] = int(m.group(3))
            continue
        if line.startswith("PLAN ONLY - nothing changed"):
            facts["plan_only"] = True
            continue
        m = re.match(r"^skipped (\d+) listing\(s\) with no price above zero", line)
        if m:
            facts["priceless"] = int(m.group(1))
            continue
        if line.startswith("nothing to move") or line.startswith("nothing to send"):
            facts["nothing_to_send"] = True
            continue
        m = re.match(r"^batch (\d+): HTTP (\d+), (\d+) ok of (\d+)", line)
        if m:
            facts["batches"].append({"n": int(m.group(1)), "http": int(m.group(2)), "ok": int(m.group(3)), "of": int(m.group(4))})
            continue
        m = re.match(r"^APPLIED: (\d+) ok, (\d+) failed(.*)$", line)
        if m:
            facts.update(applied_ok=int(m.group(1)), applied_failed=int(m.group(2)))
            errors = m.group(3).replace("***", "").strip()          # the runner masks the error dict's braces
            if errors:
                facts["applied_errors"] = errors[:160]
            continue
        m = re.match(r"^read-back sample: (\d+) of (\d+) already show", line)
        if m:
            facts["readback"] = {"ok": int(m.group(1)), "of": int(m.group(2))}
            continue
        m = re.match(r"^(\S+): class (\w+) \| before: template (\S+) handling (\S+) price (\S+) stock (\S+) \| want (?:template )?([^\s,]+)", line)
        if m:
            facts["test"] = {"sku": m.group(1), "supplier": m.group(2), "before": m.group(3), "want": m.group(7)}
            continue
        m = re.match(r"^read-back after (\d+)s: template (\S+)", line)
        if m:
            facts.setdefault("test", {})["after"] = m.group(2)
            continue
        m = re.match(r"^RESULT: (.+)$", line)
        if m:
            facts["result"] = m.group(1)[:200]
            continue
        m = re.match(r"^(\d+) moves exceed MAX_CHANGES=(\d+) - refusing", line)
        if m:
            facts["refused"] = {"moves": int(m.group(1)), "max": int(m.group(2))}
    for key in ("classes", "moves", "batches"):
        if not facts[key]:
            facts.pop(key)
    return facts


def census_rows(facts, current_ids=None):
    """The census as table rows: for each supplier its listings, how many sit on the template that run used for it, how many are off it, and where those sit. The ids are the run's own
    (what it moved by), else the settings in force."""
    ids = dict((facts.get("ids") or {}))
    for item in current_ids or []:
        ids.setdefault(item["key"], item["id"])
    rows = []
    for s in SUPPLIERS:
        c = (facts.get("classes") or {}).get(s["key"])
        if not c:
            continue
        wanted = ids.get(s["key"]) or ""
        right = c["templates"].get(wanted, 0) if wanted else None
        rows.append({"label": s["label"], "id": wanted, "listings": c["listings"], "right": right, "off": None if right is None else c["listings"] - right,
                     "sits": sorted(c["templates"].items(), key=lambda kv: -kv[1])})
    for key, label in OTHER_CLASSES:
        c = (facts.get("classes") or {}).get(key)
        if c:
            rows.append({"label": label, "id": "", "listings": c["listings"], "right": None, "off": None, "sits": sorted(c["templates"].items(), key=lambda kv: -kv[1])})
    return rows


def headline(facts):
    """One line of state for a run with a census: 'ok' (nothing that can be moved is off its template), 'moves' (some listings are off), 'noids' (the run had no template id, so it
    checked nothing) or 'unknown' (no census in the run). A run that
    skipped listings for having no price tells how many of the moves were never-live listings, which no PUT can carry."""
    if "to_move" not in facts:
        return {"state": "unknown"}
    ids = facts.get("ids")
    if ids is not None and not any(ids.values()):
        return {"state": "noids"}                         # a run with no template id checks nothing: "nothing to move" would be a false all-clear
    priceless = facts.get("priceless")
    movable = max(facts["to_move"] - (priceless or 0), 0)
    return {"state": "ok" if movable == 0 else "moves", "to_move": facts["to_move"], "movable": movable, "priceless": priceless or 0, "exact": priceless is not None or facts["to_move"] == 0}


def kind_label(run, facts):
    """How a run in the history started: the nightly's step, or a manual plan / test / apply."""
    if run.get("path") == "nightly_reconcile.yml":
        return "nightly"
    return facts.get("mode") or "manual"
