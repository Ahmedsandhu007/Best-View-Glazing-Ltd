"""The Pictures card: products whose pictures never load on OnBuy ("stuck loading"), the ticket files OnBuy support works from, and the resubmission that fixes them.

OnBuy's own answer (2026-10-22): its image workers time out now and then, the images are never applied and the product page stays "loading" / 404 - not a problem of our links.
The workaround is to resubmit the affected products with their OPC and image links, or to send support a CSV of OPCs + image links. This module is the pure part of both:
  * the ticket: from the sheet's export of a SKU list (image_links_export.yml's artifact) and OnBuy's own record for the SKUs the sheet has no OPC for (listing_lookup.yml's log) it
    builds the rows, opens every image link, and writes the attachment CSV (OPC, SKU, main image link, additional image links), the internal reference CSV and a reply draft;
  * the resubmission: the SKUs per sheet tab and the numbers in repair_shifted_content.yml's log, and which SKUs were resubmitted before.
Pure functions - the page and the job hand in the artifact, the log and the link fetcher. The tests feed it real files and logs.
"""
import csv
import hashlib
import io
import json
import math
import re
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import httpx

from .catalogue import clean_lines

LIST_DIR = "cleanup"
LIST_NAME = re.compile(r"^image_ticket_skus_(\d{4}-\d{2}-\d{2})(?:_([0-9a-f]{10}))?\.txt$")
MAX_SKUS = 1500
CANARY = 3
LINK_WORKERS = 12
SWEEPERS = ("listing_lookup.yml", "repair_shifted_content.yml")      # the workflows of this page that read every live listing of the store from OnBuy
SWEEPS_PER_HOUR = 3                                                  # OnBuy refused a 5th full read within 35 minutes (HTTP 429)
REPAIR_WORKFLOW = "repair_shifted_content.yml"
REPAIR_INPUTS = ("dry_run", "repair_limit", "repair_skus", "only_listed", "tab")      # all of them must exist, or the run would repair listings that were not named
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
FILES = {"attachment": ("text/csv", "{store}_stuck_loading_image_links_{day}.csv"), "reference": ("text/csv", "{store}_image_ticket_reference_{day}.csv"),
         "reply": ("text/plain", "{store}_ticket_additional_images_reply_{day}.txt")}


def norm(sku):
    """A SKU the way the stores compare it: commas and leading zeros do not count (spreadsheet pastes drop the zeros)."""
    s = str(sku or "").replace(",", "").strip()
    return s.lstrip("0") or s


# ---- the list ---------------------------------------------------------------------------------------------------------------------
def fingerprint(skus):
    return hashlib.sha1("\n".join(sorted(norm(s) for s in skus)).encode("utf-8")).hexdigest()[:10]


def list_path(today, fp):
    return f"{LIST_DIR}/image_ticket_skus_{today}_{fp}.txt"


def list_text(store_name, skus, today):
    """The list file the export reads: ONE SKU PER LINE and nothing else. The stores' image_links_export.py takes every non-empty line for a SKU (it does not skip '#' lines), so a comment
    header became a fourth "SKU not on the sheet" and made the build sweep all of OnBuy's listings for it (the first live build, GTV 2026-10-27); who wrote the list is in the commit message."""
    return "\n".join(skus) + "\n"


def read_list(text):
    return [line.strip() for line in (text or "").splitlines() if line.strip() and not line.lstrip().startswith("#")]


def earlier_lists(entries, exclude="", before=""):
    """The ticket lists already in the repository's cleanup folder -> [{name, path, date}] oldest first (the list being built is not an earlier one; `before` = an ISO day:
    only lists of earlier days count, so building the same ticket twice in a day does not report its own products as "reported before")."""
    out = []
    for e in entries or []:
        m = LIST_NAME.match(e.get("name") or "")
        if e.get("type") == "file" and m and e.get("path") != exclude and (not before or m.group(1) < before):
            out.append({"name": e["name"], "path": e["path"], "date": m.group(1)})
    return sorted(out, key=lambda x: (x["date"], x["name"]))


# ---- the scan file ----------------------------------------------------------------------------------------------------------------
SCAN_MARKERS = {"sku", "page_status"}        # the columns that mark the browser scan's own CSV

def read_scan(text):
    """The browser scan's CSV (onbuy_image_scan_<Store>.csv, one row per scanned listing: sku, product_url, page_status, images_found, images_failed, first_image, first_status,
    all_statuses, note) -> its rows with lowercase keys, the first row per SKU - or None when the text is not that file. The scan runs in the person's own signed-in browser
    (OnBuy's product pages sit behind a bot check, so no server can look); this reads what it downloaded."""
    rows = read_csv(str(text or "").lstrip("﻿"))
    if not rows or not SCAN_MARKERS <= {str(k or "").strip().lower() for k in rows[0]}:
        return None
    out, seen = [], set()
    for r in rows:
        row = {str(k or "").strip().lower(): str(v or "").strip() for k, v in r.items()}
        key = norm(row.get("sku"))
        if key and key not in seen:
            seen.add(key)
            out.append(row)
    return out


def _count(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def scan_verdict(row):
    """One scanned listing -> ('stuck' | 'fine' | 'unclear', why). Stuck = what the scan proves broken: the product page answers 404, a picture fails to load, or the page shows
    no picture at all ('placeholder only' / 'no image on page'). Unclear = the scan could not see the page (a bot check, repeated 429s, a fetch error): scan those again."""
    status, note = row.get("page_status", ""), row.get("note", "")
    if status == "404":
        return "stuck", "page 404"
    if status != "200":
        return "unclear", note or f"page answered {status or 'nothing'}"
    failed, found = _count(row.get("images_failed")), _count(row.get("images_found"))
    if failed:
        return "stuck", f"{failed} of {found} picture(s) do not load"
    if note:
        return "stuck", note                                         # 'placeholder only' / 'no image on page'
    return "fine", ""


def scan_report(rows):
    """What the uploaded scan file says: the stuck products (they go in the box), how many are fine (left out) and the rows the scan could not see."""
    stuck, unclear, fine, why = [], [], 0, Counter()
    for row in rows:
        verdict, reason = scan_verdict(row)
        if verdict == "stuck":
            stuck.append({"sku": row["sku"], "why": reason})
            why["pictures fail to load" if "do not load" in reason else reason] += 1
        elif verdict == "unclear":
            unclear.append({"sku": row["sku"], "why": reason})
        else:
            fine += 1
    return {"total": len(rows), "stuck": stuck, "fine": fine, "unclear": unclear, "why": dict(why.most_common())}


def read_sku_file(text):
    """Any other uploaded file, as the page always read one: the first column of every line is a SKU (quotes dropped, a 'SKU' header line too)."""
    lines = [line.split(",")[0].strip().strip('"').strip() for line in str(text or "").splitlines()]
    lines = [l for l in lines if l]
    if lines and lines[0].lower() == "sku":
        lines = lines[1:]
    return lines


# ---- what the two read-only runs hand over ----------------------------------------------------------------------------------------
def read_zip(data):
    """{file name: text} of an artifact's zip (UTF-8, the byte-order mark dropped)."""
    out = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if not info.is_dir():
                out[info.filename.rsplit("/", 1)[-1]] = z.read(info).decode("utf-8-sig", errors="replace")
    return out


def read_csv(text):
    return list(csv.DictReader(io.StringIO(text or "")))


def read_export(files):
    """image_links_export's artifact -> {found: [row dicts of all_found_images.csv], reference: {norm sku: row}, not_on_sheet: [sku], duplicates: [[sku, where...]]}."""
    reference = {}
    for r in read_csv(files.get("reference.csv")):
        reference.setdefault(norm(r.get("SKU")), r)
    dups = [row for row in csv.reader(io.StringIO(files.get("duplicates.csv") or ""))][1:]
    return {"found": read_csv(files.get("all_found_images.csv")), "reference": reference,
            "not_on_sheet": [line.strip() for line in (files.get("not_on_sheet.txt") or "").splitlines() if line.strip() and not line.lstrip().startswith("#")],
            "duplicates": [d for d in dups if d]}


def read_lookup(log_text):
    """OnBuy's own record per SKU out of a listing_lookup run -> ({norm sku: record}, [SKUs the sweep did not find])."""
    found, missing = {}, []
    for line in clean_lines(log_text):
        if line.startswith("LISTING|"):
            raw = line[len("LISTING|"):]
            try:
                rec = json.loads(raw)
            except ValueError:
                rec = _loose_record(raw)
            if isinstance(rec, dict) and rec.get("sku") is not None:
                found[norm(rec["sku"])] = rec
        elif line.startswith("NOT IN SWEEP:"):
            missing.append(line.split(":", 1)[1].strip())
    return found, missing


def _loose_record(raw):
    """A listing line whose braces the runner masked as ***: the quoted fields are still readable."""
    rec = {}
    for key in ("sku", "opc", "created_at", "product_url", "name"):
        m = re.search(r'"%s":\s*"([^"]*)"' % key, raw)
        if m:
            rec[key] = m.group(1)
    return rec or None


# ---- the rows -----------------------------------------------------------------------------------------------------------------------
def split_links(extra):
    return [u.strip() for u in str(extra or "").split(",") if u.strip()]


def _date(text):
    m = re.match(r"\d{4}-\d{2}-\d{2}", str(text or ""))
    return m.group(0) if m else ""


def build_rows(export, lookup, earlier, resubmitted=None):
    """One row per SKU asked for: the OPC (the sheet's, else OnBuy's own record), the image links, the sheet's own facts, whether an earlier ticket already named it and
    whether it was resubmitted. Sheet rows first (sheet order), then the SKUs that are not on the sheet."""
    resubmitted = resubmitted or {}
    rows = []
    for r in export["found"]:
        sku = str(r.get("SKU") or "").strip()
        ref = export["reference"].get(norm(sku), {})
        rec = lookup.get(norm(sku)) or {}
        opc, source = str(r.get("OPC") or "").strip(), "sheet"
        if opc.upper() in ("", "PENDING"):
            opc = str(rec.get("opc") or "").strip()
            source = "OnBuy" if opc else "none"
        rows.append({"sku": sku, "opc": opc, "source": source, "main": str(r.get("Main image link") or "").strip(), "extra": str(r.get("Additional image links") or "").strip(),
                     "tab": str(r.get("Tab") or ""), "row": str(r.get("Row") or ""), "status": str(r.get("Sync Status") or ""),
                     "created": _date(rec.get("created_at")) or _date(ref.get("OnBuy Product Created")), "url": str(rec.get("product_url") or ref.get("Product URL") or ""),
                     "title": str(ref.get("Title") or rec.get("name") or "")[:100], "repeat": norm(sku) in earlier, "resubmitted": resubmitted.get(norm(sku)), "dead": []})
    for sku in export["not_on_sheet"]:
        rec = lookup.get(norm(sku)) or {}
        opc = str(rec.get("opc") or "").strip()
        rows.append({"sku": sku, "opc": opc, "source": "OnBuy (no sheet row)" if opc else "none", "main": "", "extra": "", "tab": "", "row": "", "status": "not on the sheet",
                     "created": _date(rec.get("created_at")), "url": str(rec.get("product_url") or ""), "title": str(rec.get("name") or "")[:100], "repeat": norm(sku) in earlier,
                     "resubmitted": resubmitted.get(norm(sku)), "dead": []})
    return rows


def missing_opc(export):
    """The SKUs the sheet gives no usable OPC for (and the ones it does not hold at all): the ones OnBuy's own record has to be asked about."""
    out = [str(r.get("SKU") or "").strip() for r in export["found"] if str(r.get("OPC") or "").strip().upper() in ("", "PENDING")]
    return out + list(export["not_on_sheet"])


# ---- the links ----------------------------------------------------------------------------------------------------------------------
def links_of(rows):
    """Every image link of the rows that could go in the attachment (an OPC and a main image) -> [(sku, 'main' | 'extra', url)]."""
    out = []
    for r in rows:
        if r["opc"] and r["main"]:
            out.append((r["sku"], "main", r["main"]))
            out.extend((r["sku"], "extra", u) for u in split_links(r["extra"]))
    return out


def link_ok(result):
    return result[3] == 200 and str(result[4]).startswith("image/")


def make_fetch(http=None):
    """The real link opener: GET (the body is not read) -> (HTTP status or 0, content type or the error). One shared client; the threads may use it together."""
    http = http or httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=20, follow_redirects=True)

    def fetch(url):
        err = ""
        for _ in range(2):
            try:
                with http.stream("GET", url) as resp:
                    return resp.status_code, (resp.headers.get("content-type") or "").split(";")[0]
            except Exception as exc:  # noqa: BLE001 - a dead host is a result, not a crash
                err = str(exc)[:60]
        return 0, err
    return fetch


def check_links(links, fetch, workers=LINK_WORKERS, progress=None):
    """Open every link -> [(sku, kind, url, status, content type or error)] in the order given."""
    results = []

    def one(item):
        sku, kind, url = item
        status, info = fetch(url)
        return (sku, kind, url, status, info)

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for n, res in enumerate(pool.map(one, links), 1):
            results.append(res)
            if progress and (n % 25 == 0 or n == len(links)):
                progress(n, len(links))
    return results


def mark_links(rows, results):
    """Put each row's dead links on the row: [{kind, url, status, info}]."""
    bad = defaultdict(list)
    for sku, kind, url, status, info in results:
        if not link_ok((sku, kind, url, status, info)):
            bad[norm(sku)].append({"kind": kind, "url": url, "status": status, "info": str(info)})
    for r in rows:
        r["dead"] = bad.get(norm(r["sku"]), [])
    return rows


def ticket_rows(rows):
    """The products that go in the attachment: an OPC, a main image and every link open. New ones first, then the ones reported before."""
    return sorted([r for r in rows if r["opc"] and r["main"] and not r["dead"]], key=lambda r: (r["repeat"], r["sku"]))


def summarize(rows, asked, export, results):
    """The numbers of a ticket build and the lists the person has to look at."""
    ticket = ticket_rows(rows)
    on_sheet = [r for r in rows if r["tab"]]
    hosts = Counter()
    for r in ticket:
        for u in [r["main"]] + split_links(r["extra"]):
            hosts[u.split("/")[2] if "//" in u else "?"] += 1
    created = sorted(r["created"] for r in ticket if r["created"])
    extras = [len(split_links(r["extra"])) for r in ticket]
    bad = [r for r in results if not link_ok(r)]
    return {"asked": asked, "on_sheet": len({norm(r["sku"]) for r in on_sheet}), "rows_on_sheet": len(on_sheet), "not_on_sheet": list(export["not_on_sheet"]),
            "duplicates": [d[0] for d in export["duplicates"]], "ticket": len(ticket), "new": sum(1 for r in ticket if not r["repeat"]), "repeat": sum(1 for r in ticket if r["repeat"]),
            "opc_from_onbuy": sum(1 for r in ticket if r["source"] != "sheet"), "no_opc": [r["sku"] for r in rows if not r["opc"]],
            "no_links": [r["sku"] for r in rows if r["opc"] and not r["main"]], "dead": [{"sku": r["sku"], "links": r["dead"]} for r in rows if r["dead"]],
            "links": {"checked": len(results), "ok": len(results) - len(bad), "bad": len(bad)}, "hosts": dict(hosts.most_common(5)),
            "created": {"first": created[0], "last": created[-1]} if created else None, "extra_per_product": round(sum(extras) / len(extras), 1) if extras else 0,
            "tabs": dict(Counter(r["tab"] for r in on_sheet)), "resubmitted": sum(1 for r in ticket if r["resubmitted"])}


# ---- the files ----------------------------------------------------------------------------------------------------------------------
def _csv_text(header, body, bom=False):
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    w.writerows(body)
    return ("﻿" if bom else "") + buf.getvalue()


def attachment_csv(rows):
    """What OnBuy support is sent: OPC, SKU, main image link, the additional image links - the layout of every earlier file."""
    return _csv_text(["OPC", "SKU", "Main image link", "Additional image links"], [[r["opc"], r["sku"], r["main"], ",".join(split_links(r["extra"]))] for r in ticket_rows(rows)])


def reference_csv(rows):
    """For us only: every SKU asked for with where it sits on the sheet, where its OPC came from, whether it was reported or resubmitted before, and what is wrong with it."""
    body = []
    for r in sorted(rows, key=lambda r: (r["repeat"], r["sku"])):
        problem = "no OPC" if not r["opc"] else ("not on the sheet" if not r["tab"] else ("no main image link" if not r["main"] else ("dead link: " + r["dead"][0]["url"] if r["dead"] else "")))
        body.append([r["sku"], r["tab"], r["row"], r["opc"], r["source"], r["status"], r["created"], "yes" if r["repeat"] else "",
                     (r["resubmitted"] or {}).get("at", "")[:10] if r["resubmitted"] else "", problem, r["url"], r["title"]])
    return _csv_text(["SKU", "Tab", "Row", "OPC", "OPC source", "Sync Status", "Created on OnBuy", "Reported before", "Resubmitted", "Problem", "Product URL", "Title"], body, bom=True)


def _dates_text(dates):
    """['2026-10-03', '2026-10-08', '2026-10-15'] -> '3, 8 and 15 October 2026' (one month; otherwise each with its month)."""
    from datetime import date
    days = [date.fromisoformat(d) for d in dates]
    if not days:
        return ""
    names = [f"{d.day} {d.strftime('%B')}" for d in days]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def reply_text(store_name, summary, files, earlier, cumulative, agent="Ash", signed_by="Sadia"):
    """A draft of the reply to add to the open image-processing ticket, in the voice of the earlier ones: counts, the layout, the link check, the creation dates, the resubmission."""
    n, new, repeat = summary["ticket"], summary["new"], summary["repeat"]
    dates = [e["date"] for e in earlier]
    layout = f"same layout as the files of {_dates_text(dates)}" if dates else "the layout OnBuy asked for"
    head = f"{n} products; {layout}; {new} new" + (f", {repeat} reported before" if repeat else "")
    lines = [f"Reply to add to the ongoing {store_name} ticket (image processing) - a draft in {signed_by}'s voice for {store_name} only",
             f"Attach: {files['attachment']}   ({head})", f"Internal only (do not send): {files['reference']}", "", "-" * 102, "", f"Hi {agent},", "",
             "Thank you again for your help with the product pages that are not loading on our account.", ""]
    since = f" since our file of {_dates_text(dates[-1:])}" if dates else ""
    first = f"We have found another {n} products with the same problem{since}: the dashboard shows the picture still loading and the product page does not open. "
    first += ("None of them was in any of our earlier files. " if not repeat else (f"{repeat} of them were in our earlier files and are still not loading. " if repeat > 1 else "One of them was in an earlier file and is still not loading. "))
    first += "The attached CSV lists them in the same layout as before: the OPC, our SKU, the main image link and the additional image links, exactly as sent when each product was created, "
    links = summary["links"]
    first += ("and we have re-checked every link today - all of them open." if not links["bad"] else f"and we have re-checked every link today - {links['ok']} of {links['checked']} open (the products with a link that does not open are left out).")
    if summary["created"]:
        a, b = summary["created"]["first"], summary["created"]["last"]
        first += f" The products were created between {_dates_text([a])} and {_dates_text([b])} {b[:4]}." if a != b else f" The products were created on {_dates_text([a])} {a[:4]}."
    lines += [first, ""]
    if summary["resubmitted"]:
        lines += [f"{summary['resubmitted']} of these were also resubmitted through the products endpoint with their OPC and image links, as you suggested, and the pages still do not load.", ""]
    lines += [f"With this file we have now reported at least {cumulative} different products on this ticket. New products are still affected every week, so could you please process "
              "the images for these OPCs so that the pages load, and let us know whether your team has found what is stopping new products' images from being picked up? If it would help, "
              "we can also resubmit the affected products through the API with their image links - please say if that is what you would prefer.", "", "Many thanks,", signed_by, ""]
    return "\n".join(lines)


def file_names(store_name, day):
    return {kind: pattern.format(store=store_name, day=day) for kind, (_, pattern) in FILES.items()}


# ---- the resubmission -----------------------------------------------------------------------------------------------------------------
def resubmit_groups(rows):
    """The SKUs that can be resubmitted, per sheet tab, in sheet order (the tool takes one tab per run) -> [{tab, skus}]."""
    by_tab = defaultdict(list)
    for r in rows:
        if r["tab"]:
            try:
                n = int(r["row"])
            except ValueError:
                n = 0
            by_tab[r["tab"]].append((n, r["sku"]))
    return [{"tab": tab, "skus": [sku for _, sku in sorted(items)]} for tab, items in by_tab.items()]


def parse_repair(text):
    """The numbers of a repair_shifted_content run (a resubmission): how many listings it looked at, the products it would resubmit or did, the ones that failed, and rate limits."""
    facts = {"targets": [], "ok": [], "failed": [], "collisions": []}
    for line in clean_lines(text):
        m = re.match(r"^(?:INFO )?live listings: (\d+)", line)
        if m:
            facts["live"] = int(m.group(1))
            continue
        m = re.match(r"^worksheet: (.+)$", line)
        if m:
            facts["worksheet"] = m.group(1).strip()
            continue
        m = re.match(r"^(?:INFO )?shift-repairable: (\d+) \(skipped incomplete: (\d+)\) \| barcode-collision \(report-only\): (\d+)", line)
        if m:
            facts.update(repairable=int(m.group(1)), skipped_incomplete=int(m.group(2)), collision_count=int(m.group(3)))
            continue
        m = re.match(r"^(?:INFO )?  COLLISION row (\d+) SKU (\S+) \|", line)
        if m:
            facts["collisions"].append({"row": int(m.group(1)), "sku": m.group(2)})
            continue
        m = re.match(r"^(?:INFO )?REPAIR_LIMIT: repairing first (\d+)", line)
        if m:
            facts["limit"] = int(m.group(1))
            continue
        m = re.match(r"^(?:INFO )?  target (\S+) \(onbuy shows: (.*)\)$", line)
        if m:
            facts["targets"].append({"sku": m.group(1), "shows": m.group(2)})
            continue
        if re.match(r"^(?:INFO )?DRY RUN - nothing submitted", line):
            facts["dry_run"] = True
            continue
        m = re.match(r"^(?:INFO )?REPAIR (\S+): submitted OK", line)
        if m:
            facts["ok"].append(m.group(1))
            continue
        m = re.match(r"^(?:WARNING )?REPAIR (\S+): failed - (.*)$", line)
        if m:
            facts["failed"].append({"sku": m.group(1), "why": m.group(2)[:160]})
            continue
        m = re.match(r"^(?:INFO )?DONE: (\d+) submitted, (\d+) failed", line)
        if m:
            facts.update(submitted=int(m.group(1)), failed_count=int(m.group(2)))
            continue
        if "rate limited" in line and "stopping this run" in line:
            facts["rate_limited"] = True
    for key in ("targets", "ok", "failed", "collisions"):
        if not facts[key]:
            facts.pop(key)
    return facts


def resubmission_history(runs):
    """Which SKUs were resubmitted, when and with what outcome -> {norm sku: {at, run_url, ok}}. `runs` = [{at, run_url, ok: [skus], failed: [skus]}] NEWEST FIRST; the newest word on a SKU stays."""
    out = {}
    for run in runs:
        for sku in run.get("ok", []):
            out.setdefault(norm(sku), {"at": run["at"], "run_url": run.get("run_url", ""), "ok": True})
        for sku in run.get("failed", []):
            out.setdefault(norm(sku), {"at": run["at"], "run_url": run.get("run_url", ""), "ok": False})
    return out


def repair_inputs(mode, tab, skus):
    """What repair_shifted_content.yml is started with for one sheet tab: ONLY the named SKUs (only_listed), as a dry run (preview), the first few for real (canary) or all of them (rest)."""
    return {"dry_run": "yes" if mode == "preview" else "no", "repair_skus": ",".join(skus), "only_listed": "yes", "tab": tab, "repair_limit": str(CANARY) if mode == "canary" else "0"}


def _when(text):
    try:
        return datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None


def sweep_wait(runs, now=None):
    """Minutes to wait before another full read of the store's OnBuy listings -> 0 when it may go now. OnBuy refuses reads that come too fast (the 5th full read within 35 minutes got
    HTTP 429), so at most SWEEPS_PER_HOUR runs of the SWEEPERS workflows (cancelled ones do not count) may have started in the last hour. `runs` = the store's recent runs of them."""
    now = now or datetime.now(timezone.utc)
    starts = sorted((t for t in (_when(r.get("created_at")) for r in runs if r.get("path") in SWEEPERS and r.get("conclusion") != "cancelled") if t and now - t < timedelta(hours=1)), reverse=True)
    if len(starts) < SWEEPS_PER_HOUR:
        return 0
    return max(1, math.ceil((starts[SWEEPS_PER_HOUR - 1] + timedelta(hours=1) - now).total_seconds() / 60))


def group_state(group, history):
    """For one tab's SKUs: how many were resubmitted OK, how many failed last time, and the ones still to do (in sheet order)."""
    done = [s for s in group["skus"] if history.get(norm(s), {}).get("ok")]
    failed = [s for s in group["skus"] if norm(s) in history and not history[norm(s)]["ok"]]
    todo = [s for s in group["skus"] if not history.get(norm(s), {}).get("ok")]
    return {"tab": group["tab"], "total": len(group["skus"]), "done": len(done), "failed": len(failed), "todo": todo}
