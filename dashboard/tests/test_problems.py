"""Rows that keep failing: the per-SKU refusals of the nightly logs, one bad night told apart from a dead row (2026-10-29).

The real case: Arden's nightly reported "FIX done: 417 corrected, 75 failed" with 75 'SKU does not exist' warnings - were they the same
75 rows every night (dead rows to delete) or a bad night (nothing to do)? The card answers that from the logs the disk store already holds.
"""
from datetime import timedelta

from conftest import NOW, make_run

from app import problems

# lines exactly as Arden's and Makstore's nightly logs print them (2026-10-28), and GTV's backfill oversell guard
ARDEN_NIGHT = """
INFO UNDERPRICED on OnBuy (listing below sheet): 133
WARNING   FIX failed 607415117004: SKU does not exist
WARNING   FIX failed 606872125683: SKU does not exist
WARNING   FIX failed 650818399539: SKU does not exist
INFO FIX done: 417 corrected, 3 failed
"""
SUSPENDED_NIGHT = """
INFO batch 1 (1 SKUs) -> HTTP 400: {"error":{"message":"No listings were deleted."}}
INFO DONE in 1 request(s): 1 suspended
INFO SUSPENDED (needs OnBuy): 402986526152
"""
BOUNCE_NIGHT = """
oversell guard: re-zeroed 283 listing(s) in 1 PUT request(s) (0 GET, 0 auth); 8 bounced
oversell guard:   bounced 'SKU does not exist': 8 e.g. 653709952448, 346410324498, 451714795278
"""


def night(day, text, url="https://github.com/x/y/actions/runs/1"):
    return {"day": day, "url": url, "problems": problems.parse_problems(text)}


def test_the_fix_failed_lines_are_read_with_their_reason_and_a_sku_counts_once_per_night():
    parsed = problems.parse_problems(ARDEN_NIGHT + "WARNING   FIX failed 607415117004: SKU does not exist\n")
    assert [f["sku"] for f in parsed["fix"]] == ["607415117004", "606872125683", "650818399539"]
    assert parsed["fix"][0]["reason"] == "SKU does not exist"


def test_the_suspended_and_bounced_lines_are_read_and_the_bounce_count_is_the_guards_not_the_examples():
    parsed = problems.parse_problems(SUSPENDED_NIGHT + BOUNCE_NIGHT)
    assert parsed["suspended"] == ["402986526152"]
    assert parsed["bounce_total"] == 8 and parsed["bounce"] == ["653709952448", "346410324498", "451714795278"]
    several = problems.parse_problems("INFO SUSPENDED (needs OnBuy): 111, 222 333\n")
    assert several["suspended"] == ["111", "222", "333"]


def test_a_quiet_log_parses_to_nothing():
    parsed = problems.parse_problems("INFO FIX done: 1234 corrected, 0 failed\nINFO DONE: 1 zeroed, 0 failed, 0 untouched\n")
    assert parsed == {"fix": [], "bounce_total": 0, "bounce": [], "suspended": []}


def test_gather_tells_the_dead_rows_from_one_bad_night_and_from_a_repeat_that_healed():
    """607415117004 fails all three nights (a dead row - the act list); 650818399539 failed the two OLD nights but not last night
    (healed - GTV's case after the sale rollback: counted as a repeat, kept out of the act list); 606872125683 one night only."""
    nights = [
        night("2026-10-28", "WARNING   FIX failed 607415117004: SKU does not exist\nWARNING   FIX failed 606872125683: SKU does not exist\n"),
        night("2026-10-27", "WARNING   FIX failed 607415117004: SKU does not exist\nWARNING   FIX failed 650818399539: SKU does not exist\n"),
        night("2026-10-26", "WARNING   FIX failed 607415117004: SKU does not exist\nWARNING   FIX failed 650818399539: SKU does not exist\n"),
    ]
    answer = problems.gather(nights)
    assert [n["fix"] for n in answer["nights"]] == [2, 2, 2]
    fix = answer["kinds"][0]
    assert fix["kind"] == "fix" and fix["latest"] == 2 and fix["reason"] == "SKU does not exist"
    assert fix["skus"] == ["607415117004"] and fix["repeat_count"] == 2 and fix["most_nights"] == 3 and fix["once_count"] == 1


def test_gather_lists_every_suspended_sku_but_only_the_repeated_fix_skus():
    nights = [night("2026-10-28", SUSPENDED_NIGHT + ARDEN_NIGHT), night("2026-10-27", "INFO SUSPENDED (needs OnBuy): 999\n")]
    kinds = {k["kind"]: k for k in problems.gather(nights)["kinds"]}
    assert kinds["suspended"]["skus"] == ["402986526152", "999"]              # even one night: only a person can delete them
    assert kinds["fix"]["skus"] == [] and kinds["fix"]["latest"] == 3         # no fix SKU repeated, so the act list is empty
    assert "by hand" in kinds["suspended"]["note"]


def test_gather_with_no_nights_answers_empty():
    assert problems.gather([]) == {"nights": [], "kinds": []}


def test_the_api_reads_a_week_of_nightlies_and_groups_the_refusals(web, fake):
    """YRA gets three canned nightlies; GTV's only embedded nightly (run 7) refuses nothing, so GTV reads as clear."""
    for rid, hours, text in ((201, 26, ARDEN_NIGHT + SUSPENDED_NIGHT), (202, 50, "WARNING   FIX failed 607415117004: SKU does not exist\n"),
                             (203, 74, "WARNING   FIX failed 607415117004: SKU does not exist\n")):
        fake.runs["org/yra"].append(make_run(rid, "nightly_reconcile.yml", "Nightly Reconcile (content + price + orphans)", NOW - timedelta(hours=hours)))
        fake.logs[rid] = text
    data = web.get("/api/problems").json()
    assert data["window"] == problems.NIGHTS
    by_store = {s["store"]: s for s in data["stores"]}
    assert by_store["gtv"]["kinds"] == [] and len(by_store["gtv"]["nights"]) == 1
    yra = by_store["yra"]
    assert [n["fix"] for n in yra["nights"]] == [3, 1, 1]
    kinds = {k["kind"]: k for k in yra["kinds"]}
    assert kinds["fix"]["skus"] == ["607415117004"] and kinds["fix"]["most_nights"] == 3 and kinds["fix"]["once_count"] == 2
    assert kinds["suspended"]["skus"] == ["402986526152"]


def test_the_daily_page_carries_the_card_and_the_script_fills_it(web):
    text = web.get("/daily").text
    assert 'id="problemsCard"' in text and 'id="problemsBody"' in text
    assert "loadProblems" in web.get("/static/app.js?v=1").text
