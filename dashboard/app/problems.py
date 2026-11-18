"""Rows that keep failing: the per-SKU refusals in the last week's nightly logs, grouped so a dead row is told apart from a bad night.

The nightly corrects underpriced listings and re-zeroes oversold ones row by row, and the purge deletes dead rows; OnBuy refuses a few
each night ("SKU does not exist", suspended). One refusal means little - OnBuy wobbles - but the same SKU refused night after night is a
row that will not heal on its own. Pure functions: the page downloads the logs (the disk store keeps old ones, so a week costs one
download ever) and hands their text in here.
"""
import re

NIGHTS = 7                                           # how many nightly logs back the card reads

FIX_FAILED = re.compile(r"FIX failed (\S+): (.+)")
BOUNCED = re.compile(r"bounced 'SKU does not exist': (\d[\d,]*)(?: e\.g\.\s*(\S[^\n]*))?")
SUSPENDED = re.compile(r"SUSPENDED \(needs OnBuy\): (\S[^\n]*)")

# kind -> (label on the card, what it means and what to do, what the SKU box holds)
KINDS = {
    "fix": ("Price fix refused", 'The listing is priced below the sheet but OnBuy would not take the update - usually a suspended or half-deleted '
            'listing the sweep still sees. A row refused night after night will not heal: check one or two on OnBuy, then delete the dead ones '
            'from the Delete page (the row is backed up first).', "The SKUs refused last night and on earlier nights too"),
    "suspended": ("Suspended - only you can delete these", "OnBuy refuses to delete a suspended listing over the API, so the purge leaves them "
                  "to you: remove them by hand on OnBuy.", "Every suspended SKU the nights named"),
    "bounce": ("Oversell re-zero bounced", 'The sheet says these are out of stock, but the re-zero bounced with "SKU does not exist". The guard '
               "logs a few examples only, so the box holds the examples it named, not every one.", "The example SKUs named last night and before"),
}


def _split_skus(text):
    return [s for s in re.split(r"[,\s]+", (text or "").strip()) if s]


def parse_problems(text):
    """One night's refusals: {"fix": [{"sku", "reason"}], "bounce_total": n, "bounce": [skus], "suspended": [skus]} (each SKU once)."""
    fix, seen = [], set()
    for m in FIX_FAILED.finditer(text or ""):
        sku, reason = m.group(1), m.group(2).strip().rstrip(".")
        if sku not in seen:
            seen.add(sku)
            fix.append({"sku": sku, "reason": reason})
    bounce_total, bounce, suspended = 0, [], []
    for m in BOUNCED.finditer(text or ""):
        bounce_total += int(m.group(1).replace(",", ""))
        bounce += [s for s in _split_skus(m.group(2)) if s not in bounce]
    for m in SUSPENDED.finditer(text or ""):
        suspended += [s for s in _split_skus(m.group(1)) if s not in suspended]
    return {"fix": fix, "bounce_total": bounce_total, "bounce": bounce, "suspended": suspended}


def _night_skus(kind, problems):
    if kind == "fix":
        return [(f["sku"], f["reason"]) for f in problems.get("fix") or []]
    return [(sku, "") for sku in problems.get(kind) or []]


def gather(nights):
    """The card's answer for one store, from its parsed nights (newest first, each {"day", "url", "problems"}).

    nights -> the per-night refusal counts (the trend line); kinds -> only the kinds that happened, each with the newest night's count,
    how many SKUs were refused on 2+ nights (the dead rows) and the SKU list a person acts on.
    """
    trend = [{"day": n["day"], "url": n.get("url", ""), "fix": len(n["problems"].get("fix") or []),
              "bounce": n["problems"].get("bounce_total") or 0, "suspended": len(n["problems"].get("suspended") or [])} for n in nights]
    kinds = []
    for kind, (label, note, skus_label) in KINDS.items():
        seen = {}
        for night in reversed(nights):                                      # oldest first, so "last" ends on the newest night
            for sku, reason in _night_skus(kind, night["problems"]):
                entry = seen.setdefault(sku, {"sku": sku, "nights": 0, "reason": reason, "first": night["day"], "last": night["day"]})
                entry["nights"] += 1
                entry["last"] = night["day"]
                if reason:
                    entry["reason"] = reason
        latest = _night_skus(kind, nights[0]["problems"]) if nights else []
        latest_count = (nights[0]["problems"].get("bounce_total") or 0) if (kind == "bounce" and nights) else len(latest)
        if not seen and not latest_count:
            continue
        repeat = sorted((e for e in seen.values() if e["nights"] >= 2), key=lambda e: (-e["nights"], e["sku"]))
        latest_set = {sku for sku, _ in latest}
        # the act list: every suspended SKU (one night is enough - only a person can delete them), else the repeats STILL failing
        # on the newest night (a repeat that stopped - GTV after the sale rollback - needs nothing)
        skus = sorted(e["sku"] for e in seen.values()) if kind == "suspended" else [e["sku"] for e in repeat if e["sku"] in latest_set]
        reasons = [e["reason"] for e in seen.values() if e["reason"]]
        kinds.append({"kind": kind, "label": label, "note": note, "skus_label": skus_label, "latest": latest_count,
                      "repeat_count": len(repeat), "once_count": sum(1 for e in seen.values() if e["nights"] == 1),
                      "most_nights": repeat[0]["nights"] if repeat else 0, "skus": skus,
                      "reason": max(set(reasons), key=reasons.count) if reasons else ""})
    return {"nights": trend, "kinds": kinds}
