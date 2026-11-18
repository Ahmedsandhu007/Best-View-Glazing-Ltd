"""The catalogue card's brain: the lists of listings a store holds at zero, the edits a person makes to them (freeze, release, "same product"), and the numbers in the
dead-row purge's log.

The stores keep these decisions in three plain text files at the repository root (one SKU per line, '#' starts a note):
  hold_at_zero_skus.txt   the nightly audit takes any stock off these listings and never pushes the sheet's stock onto them
  protected_skus.txt      the hourly syncs push no price and no stock to these listings
  same_product_skus.txt   checked by hand: the live page IS the row's product, only worded differently - the content check never flags or removes them
A dated comment line ("# 2026-10-18 the nightly found these listings showing ANOTHER product ...") heads each block the nightly or a person appended.

Pure functions - the page reads the files and hands the text in; the edits return the new text. The tests feed them the stores' real files.
"""
import re

HOLD_FILE = "hold_at_zero_skus.txt"
PROTECTED_FILE = "protected_skus.txt"
SAME_FILE = "same_product_skus.txt"
MAX_SKUS = 100

_DATED = re.compile(r"^#\s*(\d{4}-\d{2}-\d{2})\b[:,]?\s*(.*)$")
_NOTE = re.compile(r"^(?P<where>.*?):\s*row = (?P<row>.*?)\s*\|\s*page = (?P<page>.*)$")


def forms(sku):
    """A SKU as the stores compare it: with and without leading zeros."""
    s = str(sku or "").strip()
    return {s, s.lstrip("0")} - {""}


def same_sku(a, b):
    return bool(forms(a) & forms(b))


def key(sku):
    s = str(sku or "").strip()
    return s.lstrip("0") or s


def split_skus(text, limit=MAX_SKUS):
    """SKUs typed or ticked on the page: separated by commas, spaces or lines; no '#', no duplicates -> (list, error)."""
    if isinstance(text, (list, tuple)):
        raw = [str(t) for t in text]
    else:
        raw = re.split(r"[,\s]+", str(text or ""))
    out = []
    for token in raw:
        token = token.strip()
        if not token:
            continue
        if "#" in token or len(token) > 80:
            return None, f"'{token[:30]}' is not a SKU."
        if token not in out:
            out.append(token)
    if not out:
        return None, "Give at least one SKU."
    if len(out) > limit:
        return None, f"At most {limit:,} SKUs at a time."
    return out, ""


def parse_list(text):
    """The SKU lines of one of the files -> [{sku, note, since, reason}]: `note` = the text after '#' on the SKU's own line, `since` / `reason` = the nearest dated
    comment above it (empty for a line under the file's opening comments); a note that starts with a date dates its own line ('653709952448  # 2026-09-22 source OOS ...')."""
    out, since, reason = [], "", ""
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            m = _DATED.match(line)
            if m:
                since, reason = m.group(1), m.group(2).strip()
            continue
        sku, _, note = line.partition("#")
        sku, note = sku.strip(), note.strip()
        if sku:
            own = _DATED.match("# " + note) if note else None
            out.append({"sku": sku, "note": note, "since": own.group(1) if own else since, "reason": own.group(2).strip() if own else reason})
    return out


def split_note(note):
    """'Sheet1 row 1004: row = <sheet title> | page = <live page name>' -> where / row / page (the nightly writes both names, cut at 50 characters)."""
    m = _NOTE.match(note or "")
    if m:
        return {"where": m.group("where").strip(), "row": m.group("row").strip(), "page": m.group("page").strip()}
    return {"where": "", "row": "", "page": ""}


def merge_holds(hold_text, protected_text, same_text="", overlaps=None):
    """Every listing a store keeps frozen, once each: {sku, since, reason, note, where, row, page, in_hold, in_protected, same_listed, overlap}. Newest first.
    `overlaps` = {sku: word overlap} of the nightly's borderlines."""
    overlaps = overlaps or {}
    same = {key(e["sku"]) for e in parse_list(same_text)}
    merged = {}
    for source, text in (("in_hold", hold_text), ("in_protected", protected_text)):
        for e in parse_list(text):
            k = key(e["sku"])
            row = merged.setdefault(k, {"sku": e["sku"], "since": "", "reason": "", "note": "", "in_hold": False, "in_protected": False})
            row[source] = True
            if e["note"] and not row["note"]:
                row["note"] = e["note"]
            if e["since"] and (not row["since"] or (source == "in_hold" and e["since"] < row["since"])):
                row["since"], row["reason"] = e["since"], e["reason"]
            elif e["reason"] and not row["reason"]:
                row["reason"] = e["reason"]
    for k, row in merged.items():
        row.update(split_note(row["note"]))
        row["same_listed"] = k in same
        row["overlap"] = next((v for s, v in overlaps.items() if key(s) == k), None)
    return sorted(merged.values(), key=lambda r: (r["since"] or "0000", r["sku"]), reverse=True)


def remove_skus(text, skus):
    """The text without the SKU lines of `skus` (comments and every other line untouched) -> (new text, SKUs removed)."""
    want = list(skus)
    keep, removed = [], []
    for raw in (text or "").splitlines():
        sku = raw.partition("#")[0].strip()
        if sku and not raw.lstrip().startswith("#") and any(same_sku(sku, w) for w in want):
            removed.append(sku)
            continue
        keep.append(raw)
    out = "\n".join(keep)
    if (text or "").endswith("\n") and not out.endswith("\n"):
        out += "\n"
    return out, removed


def add_skus(text, skus, header, notes=None):
    """The text with a dated header and one line per SKU appended (a SKU already on the list is skipped) -> (new text, SKUs added)."""
    notes = notes or {}
    present = [e["sku"] for e in parse_list(text)]
    fresh = [s for s in skus if not any(same_sku(s, p) for p in present)]
    if not fresh:
        return text or "", []
    body = (text or "")
    if body and not body.endswith("\n"):
        body += "\n"
    lines = [f"# {header}"] + [f"{s}  # {notes[s]}" if notes.get(s) else s for s in fresh]
    return body + "\n".join(lines) + "\n", fresh


def freeze_header(today, reason):
    return f"{today} frozen from the dashboard: {reason.strip()[:160]} - release only after the page or the row is fixed"


def same_header(today):
    return f"{today} checked by hand in the dashboard (the row's title next to the live page name): the OnBuy page IS this row's product, only worded differently"


def same_note(entry):
    """The note a same-product line carries: the row's title (the way the file's other lines do), else what the hold said."""
    return (entry.get("row") or entry.get("note") or "")[:50]


# ---- the dead-row purge's log -------------------------------------------------------------------------------------------------------
def clean_lines(text):
    for raw in (text or "").splitlines():
        yield re.sub(r"\x1b\[[0-9;]*m", "", raw).rstrip()


def parse_purge(text):
    """The numbers of a dead-row purge (the last step of every eBay sync, or purge_dead_rows.yml): mode, rows that look dead, rows held back, what was deleted, and
    the purged SKUs whose OnBuy listing is suspended - OnBuy refuses to delete those, the user deletes them by hand."""
    facts = {"suspended": [], "held": []}
    for line in clean_lines(text):
        m = re.match(r"^(DRY RUN|LIVE RUN) \| tab '(.*?)' \| kinds (\S+) \| max (\d+) rows, (\d+) eBay checks", line)
        if m:
            facts.update(mode="dry run" if m.group(1) == "DRY RUN" else "live", tab=m.group(2), max_rows=int(m.group(4)), max_checks=int(m.group(5)))
            continue
        m = re.match(r"^eBay tab: (\d+) rows \| looking dead: brand-blocked (\d+), out of stock (\d+) \| held back (\d+)", line)
        if m:
            facts.update(rows=int(m.group(1)), brand=int(m.group(2)), oos=int(m.group(3)), held_back=int(m.group(4)))
            continue
        m = re.match(r"^\s+held\s+(\d+)\s+(.+)$", line)
        if m:
            facts["held"].append({"rows": int(m.group(1)), "why": m.group(2).strip()})
            continue
        m = re.match(r"^eBay confirmation of the out-of-stock rows: gone (\d+), alive again (\d+), unknown (\d+)", line)
        if m:
            facts.update(ebay_gone=int(m.group(1)), ebay_alive=int(m.group(2)), ebay_unknown=int(m.group(3)))
            continue
        m = re.match(r"^TO DELETE THIS RUN: (\d+) row\(s\)", line)
        if m:
            facts["to_delete"] = int(m.group(1))
            continue
        m = re.match(r"^DELETED (\d+) row\(s\) from the sheet", line)
        if m:
            facts["deleted"] = int(m.group(1))
            continue
        m = re.match(r"^SUSPENDED (\S+)\s*(.*)$", line)
        if m:
            if not any(s["sku"] == m.group(1) for s in facts["suspended"]):
                facts["suspended"].append({"sku": m.group(1), "title": m.group(2).strip()})
            continue
        m = re.match(r"^(\d+) purged SKU\(s\) whose OnBuy listing is suspended", line)
        if m:
            facts["suspended_total"] = int(m.group(1))
            continue
        m = re.match(r"^PURGE DONE: (\d+) row\(s\) removed \(brand (\d+), out of stock (\d+)\)(?:; suspended on OnBuy (\d+); OnBuy errors (\d+))?", line)
        if m:
            facts.update(done=int(m.group(1)), done_brand=int(m.group(2)), done_oos=int(m.group(3)))
            if m.group(4) is not None:
                facts.update(suspended_count=int(m.group(4)), onbuy_errors=int(m.group(5)))
            continue
        if line.startswith("nothing to purge") or line.startswith("nothing to delete this run"):
            facts["nothing"] = True
        if line.startswith("DRY RUN - nothing deleted"):
            facts["nothing_changed"] = True
    if not facts["suspended"]:
        facts.pop("suspended")
    if not facts["held"]:
        facts.pop("held")
    return facts


# ---- remove_wrong_content.yml ---------------------------------------------------------------------------------------------------------
_PLAN = re.compile(r"^\s+(\S+)\s+row\s+(\d+) \| (.+?) \| sheet stock (\S+) \| OnBuy stock (\S+) OPC (\S+) \| overlap ([\d.]+)$")


def read_batch_line(line, facts):
    """The lines delete_listings_batch.py logs - the OnBuy half of every removal -> True when `line` was one of them: facts["onbuy"] = {ok, gone, suspended, other error},
    facts["suspended"] = [sku] (OnBuy refuses to delete these, the user does it by hand), facts["errors"] = [{sku, why}]."""
    m = re.match(r"^(?:INFO )?DONE in (\d+) request\(s\): (.+)$", line)
    if m:
        facts["onbuy"] = {word: int(n) for n, word in re.findall(r"(\d+) (ok|gone|suspended|other error)", m.group(2))}
        return True
    m = re.match(r"^(?:INFO )?SUSPENDED \(needs OnBuy\): (\S+)", line)
    if m:
        facts["suspended"].append(m.group(1))
        return True
    m = re.match(r"^(?:WARNING )?ERROR (\S+): (.+)$", line)
    if m:
        facts["errors"].append({"sku": m.group(1), "why": m.group(2).strip()[:120]})
        return True
    return False


def parse_removal(text):
    """The numbers of a remove_wrong_content run: the plan (each row with the sheet's title next to the live page name), what was held back and why, what was deleted."""
    facts = {"will_remove": [], "held_back": [], "suspended": [], "errors": []}
    current, section = None, ""
    for line in clean_lines(text):
        m = re.match(r"^sheet rows read: .* \| (\d+) SKU\(s\) asked for \| (DRY RUN|LIVE RUN)", line)
        if m:
            facts.update(asked=int(m.group(1)), mode="dry run" if m.group(2) == "DRY RUN" else "live")
            continue
        m = re.match(r"^WILL REMOVE (\d+) row\(s\)", line)
        if m:
            facts["planned"], section = int(m.group(1)), "plan"
            continue
        m = re.match(r"^HELD BACK (\d+):", line)
        if m:
            facts["held"], section, current = int(m.group(1)), "held", None
            continue
        if section == "plan":
            m = _PLAN.match(line)
            if m:
                current = {"tab": m.group(1), "row": int(m.group(2)), "sku": m.group(3), "sheet_stock": m.group(4), "onbuy_stock": m.group(5), "opc": m.group(6),
                           "overlap": float(m.group(7)), "row_title": "", "page_name": ""}
                facts["will_remove"].append(current)
                continue
            m = re.match(r"^\s+row\s*: (.*)$", line)
            if m and current:
                current["row_title"] = m.group(1)
                continue
            m = re.match(r"^\s+page\s*: (.*)$", line)
            if m and current:
                current["page_name"] = m.group(1)
                continue
        if section == "held":
            m = re.match(r"^\s+(\S+) - (.+)$", line)
            if m:
                facts["held_back"].append({"sku": m.group(1), "why": m.group(2).strip()})
                continue
        m = re.match(r"^DELETED (\d+) of (\d+) planned row\(s\) from the sheet", line)
        if m:
            facts["deleted"], facts["planned"] = int(m.group(1)), int(m.group(2))
            continue
        m = re.match(r"^VERIFY: (\d+) removed SKU\(s\) still on the sheet", line)
        if m:
            facts["still_on_sheet"] = int(m.group(1))
            continue
        m = re.match(r"^hold lists .*: (\d+) line\(s\) dropped", line)
        if m:
            facts["hold_lines_dropped"] = int(m.group(1))
            continue
        if read_batch_line(line, facts):
            continue
        if line.startswith("DRY RUN - nothing changed"):
            facts["nothing_changed"] = True
        elif line.startswith("nothing to remove"):
            facts["nothing"] = True
    for k in ("will_remove", "held_back", "suspended", "errors"):
        if not facts[k]:
            facts.pop(k)
    return facts


def deleted_skus(facts):
    """The SKUs a finished live remove_wrong_content run took off the sheet: only when it deleted every planned row and none is left (a partial run proves nothing)."""
    if facts.get("mode") != "live" or not facts.get("planned") or facts.get("deleted") != facts.get("planned") or facts.get("still_on_sheet"):
        return []
    return [w["sku"] for w in facts.get("will_remove", [])]


def mark_deleted(holds, removals):
    """Flag the held listings that a later live removal deleted: holds = merge_holds rows, removals = [{sku, day, run}] (day = the run's date). A hold dated after the run's
    day is a new listing under a reused SKU, not the deleted one. Each row gets `deleted_by` (the run, or None)."""
    for row in holds:
        row["deleted_by"] = next((r["run"] for r in removals if same_sku(r["sku"], row["sku"]) and (row["since"] or "0000-00-00") <= r["day"]), None)
    return holds
