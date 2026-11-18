"""The Delete card's brain: the list of SKUs a person gives, the file committed to the repository for the removal tool, the inputs it is started with and the numbers in its log.

One tool on every store: dup_removal.yml with an explicit list (oos_list_file). A SKU of the list that is on the sheet goes from the product tab - copied whole to a backup tab
first - and its OnBuy listing is deleted in batches; a SKU that is not on the sheet only has its listing deleted. The tool holds a row back when it shows stock (unless
allow_in_stock), when its SKU is on more than one row or on protected_skus.txt, and refuses a plan above max_remove. The dashboard also keeps the SKUs of open orders and of the
hold lists out of the list it commits, and only starts the real run for a list whose plan (a dry run of exactly that list) finished well.

Pure functions - the page reads what it needs from GitHub and hands the text in. The tests feed the parser the stores' real logs.
"""
import hashlib
import re
from datetime import datetime, timezone

from .catalogue import clean_lines, key, read_batch_line, split_skus
from .digest import age_hours

MAX_SKUS = 2000
LIST_DIR = "cleanup/dashboard"
WORKFLOW = "dup_removal.yml"
PLAN_VALID_HOURS = 24          # a plan older than this is no plan any more: the sheet and the orders move on
ORDERS_MAX_HOURS = 24          # a delete for real needs an orders lookup newer than this


def parse_pasted(text):
    """The SKUs of the pasted text -> (skus, pasted, error). `pasted` = how many were typed, so the page can say how many repeats it dropped."""
    skus, error = split_skus(text, limit=MAX_SKUS)
    if error:
        return None, 0, error
    parts = text if isinstance(text, (list, tuple)) else re.split(r"[,\s]+", str(text or ""))
    return skus, len([p for p in parts if str(p).strip()]), ""


def keep_out(skus, protected, order_skus):
    """Split the list -> (to delete, SKUs on the hold lists, SKUs on open orders). Leading zeros do not matter: the stores compare SKUs with and without them."""
    held_keys = {key(p) for p in protected}
    order_keys = {key(o) for o in order_skus}
    held = [s for s in skus if key(s) in held_keys]
    orders = [s for s in skus if key(s) in order_keys and key(s) not in held_keys]
    out = set(held) | set(orders)
    return [s for s in skus if s not in out], held, orders


def fingerprint(skus):
    """A short fingerprint of the list that is committed: the same SKUs always give the same one, whatever their order."""
    return hashlib.sha1("\n".join(sorted(skus)).encode("utf-8")).hexdigest()[:10]


def list_path(store_id, today, fp):
    return f"{LIST_DIR}/{store_id}_delete_{today}_{fp}.txt"


def path_fingerprint(path):
    m = re.search(r"_([0-9a-f]{10})\.txt$", path or "")
    return m.group(1) if m else ""


def list_text(store_name, skus, today):
    """The file the tool reads (one SKU per line; '#' lines are comments)."""
    head = f"# {store_name}: {len(skus)} SKU(s) to remove, one per line - written by the dashboard's Delete page on {today} for dup_removal.yml (oos_list_file)"
    return head + "\n" + "\n".join(sorted(skus)) + "\n"


def clean_backup_tab(text, today):
    """A tab name Google Sheets accepts (no [ ] * ? : / \\), at most 60 characters; empty = 'Removed <today>'."""
    name = re.sub(r"[\[\]*?:/\\]", "", str(text or "")).strip()[:60].strip()
    return name or f"Removed {today}"


def build_inputs(path, count, backup_tab, allow_in_stock, dry):
    """What dup_removal.yml is started with: only the list - live duplicates and dead copies off. max_remove = the list's size, so a plan that grew beyond it refuses."""
    return {"oos_list_file": path, "allow_in_stock": "yes" if allow_in_stock else "no", "remove_live_dups": "no", "remove_dead_copies": "no",
            "require_keeper_synced": "yes", "max_remove": str(max(int(count), 1)), "backup_tab": backup_tab, "dry_run": "yes" if dry else "no"}


def find_plan(dispatches, fp, backup_tab, allow_in_stock, now=None):
    """The newest dry run of exactly this list with these options that finished well and is not stale -> the dispatch row, or None. `dispatches` = newest first."""
    now = now or datetime.now(timezone.utc)
    for d in dispatches:
        i = d.get("inputs") or {}
        if d.get("workflow") != WORKFLOW or i.get("dry_run") != "yes" or d.get("status") != "success":
            continue
        if path_fingerprint(i.get("oos_list_file")) != fp or i.get("backup_tab") != backup_tab or (i.get("allow_in_stock") == "yes") != bool(allow_in_stock):
            continue
        age = age_hours(d.get("at"), now)
        if age is not None and age <= PLAN_VALID_HOURS:
            return d
    return None


# ---- the removal tool's log ---------------------------------------------------------------------------------------------------------
_REASON = re.compile(r"^\s+(\d+)\s+(\S+)\s+\| (.+)$")
_HELD = re.compile(r"^\s+held: (\S+) row (\d+) SKU (\S+) stock (\S+) created (\S+) - (.+)$")


def parse_guarded(text):
    """The numbers of a dup_removal run (guarded_remove_rows.py, then delete_listings_batch.py): the plan - rows that would go by reason, rows held back and why, SKUs that are
    not on the sheet - and, for a real run, what was deleted, the backup, the check afterwards and what OnBuy answered."""
    facts = {"will_remove": [], "held_reasons": [], "held_rows": [], "skipped": [], "suspended": [], "errors": []}
    section = ""
    for line in clean_lines(text):
        m = re.match(r"^listed SKUs: (\d+)(?: \| in-stock rows of the list: (REMOVED too|held))?.*\| (DRY RUN|LIVE RUN)$", line)
        if m:
            facts.update(listed=int(m.group(1)), mode="dry run" if m.group(3) == "DRY RUN" else "live")
            if m.group(2):
                facts["in_stock_ok"] = m.group(2) == "REMOVED too"
            continue
        m = re.match(r"^product rows: (.*)$", line)
        if m:
            facts["tabs"] = {tab: int(n) for tab, n in re.findall(r"'([^']+)': (\d+)", m.group(1))}
            continue
        m = re.match(r"^never removed \(open orders / protected\): (\d+) SKU", line)
        if m:
            facts["never"] = int(m.group(1))
            continue
        m = re.match(r"^WILL REMOVE (\d+) row\(s\):", line)
        if m:
            facts["planned"], section = int(m.group(1)), "will"
            continue
        m = re.match(r"^\s+of which live on OnBuy \(created=TRUE\): (\d+) \| in stock at this moment: (\d+)", line)
        if m:
            facts.update(live=int(m.group(1)), in_stock=int(m.group(2)))
            continue
        m = re.match(r"^HELD BACK (\d+) row\(s\):", line)
        if m:
            facts["held"], section = int(m.group(1)), "held"
            continue
        if section == "will":
            m = _REASON.match(line)
            if m:
                facts["will_remove"].append({"n": int(m.group(1)), "tab": m.group(2), "reason": m.group(3).strip()})
                continue
        if section == "held":
            m = _REASON.match(line)
            if m:
                facts["held_reasons"].append({"n": int(m.group(1)), "tab": m.group(2), "why": m.group(3).strip()})
                continue
            m = _HELD.match(line)
            if m:
                facts["held_rows"].append({"tab": m.group(1), "row": int(m.group(2)), "sku": m.group(3), "stock": m.group(4), "created": m.group(5) == "True", "why": m.group(6).strip()})
                continue
        m = re.match(r"^listed SKUs not on the sheet \(OnBuy may still hold them\): (\d+)", line)
        if m:
            facts["absent"], section = int(m.group(1)), ""
            continue
        m = re.match(r"^OnBuy delete list: (\d+) SKU\(s\)", line)
        if m:
            facts["onbuy_list"] = int(m.group(1))
            continue
        m = re.match(r"^backup verified: (\d+) row\(s\) written to '(.+)'", line)
        if m:
            facts["backup"] = {"rows": int(m.group(1)), "tab": m.group(2)}
            continue
        m = re.match(r"^DELETED (\d+) of (\d+) planned row\(s\) from the sheet", line)
        if m:
            facts["deleted"], facts["planned"] = int(m.group(1)), int(m.group(2))
            continue
        m = re.match(r"^\s+skipped (\S+) SKU (\S+): found on (\d+) row\(s\) at deletion time", line)
        if m:
            facts["skipped"].append({"tab": m.group(1), "sku": m.group(2), "rows": int(m.group(3))})
            continue
        m = re.match(r"^VERIFY: (\d+) removed SKU\(s\) still on the sheet", line)
        if m:
            facts["still_on_sheet"] = int(m.group(1))
            continue
        m = re.match(r"^(\d+) SKU\(s\) kept out of the OnBuy delete list because their row is still on the sheet", line)
        if m:
            facts["kept_out"] = int(m.group(1))
            continue
        m = re.match(r"^plan removes (\d+) rows, above MAX_REMOVE=(\d+) - refusing", line)
        if m:
            facts["refused"] = {"rows": int(m.group(1)), "max": int(m.group(2))}
            continue
        if read_batch_line(line, facts):
            continue
        if line.startswith("DRY RUN - nothing changed"):
            facts["nothing_changed"] = True
        elif line.startswith("nothing to remove"):
            facts["nothing"] = True
    gone = [e for e in facts["errors"] if "already removed" in e["why"].lower()]
    facts["errors"] = [e for e in facts["errors"] if e not in gone]
    if gone:
        facts["already_gone"] = [e["sku"] for e in gone]
    for k in ("will_remove", "held_reasons", "held_rows", "skipped", "suspended", "errors"):
        if not facts[k]:
            facts.pop(k)
    return facts
