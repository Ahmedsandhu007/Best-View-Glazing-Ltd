"""The suspended listings only a person can delete: every tool's "SUSPENDED" reports merged into one list to work through.

OnBuy's API refuses to delete a suspended listing, so four tools end up naming them: the delete-by-list runs, the dead-row purge
(which also knows their titles), the wrong-content removals and the nightly. Until 2026-10-29 those reports lived in run logs and
hand-written files; the same day proved the scale (243 in one afternoon - a suspended listing answers "SKU does not exist" to price
updates, so they also sat behind every "price fix refused" repeat). This merges the reports, remembers which ones a person has
already deleted by hand (the marks live in the dashboard's database), and keeps the rest as the to-do.

Pure functions: the page reads the runs and logs (the disk store keeps them) and hands the reports in.
"""
from .catalogue import key

# the source labels, in the order reports usually arrive
SOURCES = {"delete": "delete by list", "purge": "dead-row purge", "removal": "wrong-content removal", "nightly": "nightly"}


def report(sku, day, source, url="", title=""):
    return {"sku": str(sku).strip(), "day": str(day or "")[:10], "source": source, "url": url, "title": title.strip()}


def merge(reports, marks=None):
    """reports (any order, repeats fine) + marks {normalized sku: {"actor", "at"}} -> the rows of the card.

    One row per SKU (normalized, so leading zeros do not split one listing into two): the first and last day it was reported,
    by which tool (the latest report wins; a title is kept from any report that has one), and whether a person marked it done.
    Waiting rows first, the freshest report at the top; done rows after, so the list reads as a to-do.
    """
    rows = {}
    for r in sorted((r for r in reports if str(r.get("sku", "")).strip()), key=lambda r: r["day"]):
        k = key(r["sku"])
        row = rows.setdefault(k, {"sku": r["sku"], "title": "", "first": r["day"], "last": r["day"], "source": r["source"], "url": r.get("url", "")})
        row.update(last=r["day"], source=r["source"])
        if r.get("url"):
            row["url"] = r["url"]
        if r.get("title"):
            row["title"] = r["title"]
    for k, row in rows.items():
        mark = (marks or {}).get(k)
        row.update(done=bool(mark), by=(mark or {}).get("actor", ""), at=(mark or {}).get("at", ""))
    # two stable sorts: newest report first, then the waiting ones before the done ones
    out = sorted(rows.values(), key=lambda r: r["last"], reverse=True)
    out.sort(key=lambda r: r["done"])
    return out


def counts(rows):
    done = sum(1 for r in rows if r["done"])
    return {"waiting": len(rows) - done, "done": done, "total": len(rows)}


def waiting_skus(rows):
    """The SKUs still to delete by hand, ready for the copy box."""
    return [r["sku"] for r in rows if not r["done"]]
