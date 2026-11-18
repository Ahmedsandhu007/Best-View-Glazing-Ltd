"""The To do page on the fake GitHub: what it gathers from a store's runs, orders, logs, variables and files, how long it keeps its answer, and what a store that cannot be read does to it."""
import html
import json
import re
from datetime import timedelta

from amazon_data import MAKSTORE_LOG, YRA_FAILED_LOG
from conftest import NOW, make_run

OK = "ONBUY_API_PUSH_ENABLED"


def get(web, refresh=True):
    r = web.get("/todo?refresh=1" if refresh else "/todo")
    assert r.status_code == 200
    return html.unescape(r.text)                                                         # the page escapes every quote in a sentence: compare the sentences as written


def quiet_yra(fake):
    """YRA with an empty orders list and updates switched on: nothing to do there."""
    fake.runs["org/yra"].append(make_run(22, "orders_lookup.yml", "Orders Lookup (read-only)", NOW - timedelta(hours=1), event="workflow_dispatch"))
    fake.logs[22] = "DONE: scanned 0 order(s), 0 contained SKU NONE; oldest order seen -\n"
    fake.variables["org/yra"] = [{"name": OK, "value": "true", "updated_at": "2026-10-01T00:00:00Z"}]


def test_the_page_lists_what_needs_a_person_most_urgent_first(web, fake):
    text = get(web)
    assert text.index("<h2>Act now") < text.index("<h2>Look today")
    assert "1 order is past the dispatch date" in text and "T6N77VB" in text and "1 order must be dispatched today" in text and "T6QPP5J" in text      # GTV's orders list
    assert "The Amazon sync failed 3 h ago" in text                                                                                                   # GTV's run 9 failed
    assert "No orders list yet" in text                                                                                                              # YRA never ran an orders lookup
    assert "T6QR7NW" not in text                                                                                                                     # due in 3 days: not yet
    assert '<a href="/orders">Open the page</a>' in text and "https://github.com/x/y/actions/runs/9" in text


def test_the_counts_at_the_top_match_the_lists(web, fake):
    text = get(web)
    counts = [int(n) for n in re.findall(r"<div[^>]*><strong>(\d+)</strong><span>(?:act now|look today|for your information)</span></div>", text)]
    sections = {key: len(re.findall(r'<li class="todo-item">', block)) for key, block in re.findall(r'<section class="card todo-group todo-(\w+)">(.*?)</section>', text, re.S)}
    assert counts == [sections.get("act", 0), sections.get("look", 0), sections.get("fyi", 0)] and counts[0] >= 2


def test_a_store_with_nothing_to_do_is_named_at_the_bottom_not_listed(web, fake):
    quiet_yra(fake)
    text = get(web)
    assert "Nothing to do for: <a href=\"/store/yra\">YRA</a>" in text
    assert "YRA</span> <strong>" not in text


def test_an_amazon_sync_that_ran_out_of_keepa_tokens_is_named_for_what_it_is(web, fake):
    fake.logs[9] = YRA_FAILED_LOG                                                         # GTV's failed Amazon sync (run 9) is the real log of one that ran dry
    text = get(web)
    assert "The Amazon sync ran out of Keepa tokens" in text and "2,216 Amazon rows were left exactly as they were" in text and 'href="/amazon?store=gtv"' in text
    assert "The Amazon sync failed 3 h ago" not in text


def test_a_big_amazon_price_fall_in_the_last_good_sync_is_a_look_item(web, fake):
    fake.runs["org/gtv"].insert(0, make_run(90, "run_amazon.yml", "Amazon Sync (Keepa)", NOW - timedelta(minutes=30)))
    fake.logs[90] = MAKSTORE_LOG
    text = get(web)
    assert "1 price fell by 25% or more in the last Amazon sync" in text and "row 89 (SKU 327210340093) from £227.65 to £117.22 (-48.5%)" in text
    assert "The Amazon sync failed" not in text                                           # the newest Amazon sync is a good one: the older failure no longer counts


def test_a_sale_that_ends_tomorrow_and_updates_that_are_off_are_look_items(web, fake):
    fake.files[("org/gtv", "store_sale.json")] = json.dumps({"sale_end_date": (NOW.date() + timedelta(days=1)).isoformat(), "percent": 3})
    fake.variables["org/gtv"] = [{"name": OK, "value": "false", "updated_at": "2026-10-01T00:00:00Z"}]
    text = get(web)
    assert "The store sale ends tomorrow" in text and "OnBuy updates are switched off for this store" in text and 'ONBUY_API_PUSH_ENABLED is "false", not true' in text


def test_failing_tests_a_late_job_and_a_ghost_run_are_look_items(web, fake):
    fake.runs["org/gtv"].insert(0, make_run(91, "tests.yml", "Tests", NOW - timedelta(hours=5), event="push", conclusion="failure"))
    fake.pending["org/gtv"] = [{"name": "Makstore Full-Auto Sync", "path": "run.yml", "status": "queued", "created_at": (NOW - timedelta(days=66)).isoformat().replace("+00:00", "Z"),
                                "url": "https://github.com/x/y/actions/runs/32216976318"}]
    text = get(web)
    assert "The automated tests of this store's code are failing (5 h ago)" in text
    assert "A run of 'Makstore Full-Auto Sync' has been queued since" in text


def test_listings_the_nightly_froze_in_the_last_week_are_a_look_item_and_older_ones_are_not(web, fake):
    def hold(days_ago, sku):
        day = (NOW.date() - timedelta(days=days_ago)).isoformat()
        return f"# {day} the nightly found these listings showing ANOTHER product - zeroed and frozen automatically; release only after the page or the row is fixed\n{sku}  # Sheet1 row 5: row = a thing | page = another thing\n"
    fake.files[("org/gtv", "hold_at_zero_skus.txt")] = hold(2, "856689732127") + hold(12, "111111111111")
    fake.files[("org/gtv", "protected_skus.txt")] = ""
    fake.files[("org/gtv", "same_product_skus.txt")] = ""
    text = get(web)
    assert "1 listing frozen in the last 7 days because the OnBuy page shows another product" in text and "856689732127." in text and "111111111111" not in text
    fake.files[("org/gtv", "same_product_skus.txt")] = "856689732127  # checked by hand: the same product\n"          # judged the same product: nothing left to decide
    assert "frozen in the last 7 days" not in get(web)


def test_the_answer_is_kept_for_five_minutes_and_refresh_reads_again(web, fake):
    reads = []
    original = fake.list_runs
    fake.list_runs = lambda repo, **kw: reads.append(repo) or original(repo, **kw)
    get(web)
    first = len(reads)
    assert first >= 2                                                                       # both stores were read
    get(web, refresh=False)
    assert len(reads) == first                                                              # the second look came from the cache
    get(web)
    assert len(reads) == first * 2                                                          # ?refresh=1 read everything again


def test_a_store_that_cannot_be_read_is_named_and_the_others_still_show(web, fake):
    fake.fail_repo = "org/yra"
    text = get(web)
    assert "The dashboard could not read YRA" in text and "401" in text
    assert "1 order must be dispatched today" in text                                       # GTV is still there


def test_the_menu_has_the_page_and_it_only_reads(web):
    text = web.get("/todo").text
    assert 'href="/todo"' in text and 'class="on">To do</a>' in text
    assert web.post("/todo").status_code in (404, 405)


# ---- the home page's "Needs you today" band (2026-10-29) --------------------------------------------------------------------------------
def test_the_summary_endpoint_gives_each_stores_counts_and_top_titles(web, fake):
    quiet_yra(fake)
    data = web.get("/api/todo/summary").json()
    stores = {s["store"]: s for s in data["stores"]}
    assert set(stores) == {"gtv", "yra"} and data["at"]
    gtv = stores["gtv"]
    assert gtv["counts"]["act"] >= 1 and gtv["counts"]["total"] == len(gtv["top"]) or gtv["counts"]["total"] >= 2
    assert gtv["top"] and gtv["top"][0]["severity"] == "act" and len(gtv["top"]) <= 2
    assert stores["yra"]["counts"]["total"] == 0 and stores["yra"]["top"] == []            # nothing to do there -> the band says all clear


def test_the_home_page_carries_the_band_and_its_loader(web):
    text = web.get("/").text
    assert 'id="todoBand"' in text and "Needs you today" in text and 'id="todoBandBody"' in text


# ---- dead rows and suspended listings reach the To do flow (2026-10-29) -----------------------------------------------------------
def test_dead_rows_and_waiting_suspended_listings_reach_the_todo_flow(web, fake):
    fake.runs["org/yra"] += [make_run(240, "nightly_reconcile.yml", "Nightly Reconcile (content + price + orphans)", NOW - timedelta(hours=4)),
                             make_run(241, "nightly_reconcile.yml", "Nightly Reconcile (content + price + orphans)", NOW - timedelta(hours=28)),
                             make_run(242, "dup_removal.yml", "Duplicate Removal (sheet rows + OnBuy listings)", NOW - timedelta(hours=3), event="workflow_dispatch")]
    fake.logs[240] = "WARNING   FIX failed 607415117004: SKU does not exist\nINFO FIX done: 400 corrected, 1 failed\n"
    fake.logs[241] = "WARNING   FIX failed 607415117004: SKU does not exist\n"
    fake.logs[242] = "INFO DONE in 1 request(s): 1 suspended\nINFO SUSPENDED (needs OnBuy): 402986526152\n"
    text = get(web)
    assert "1 row failed the nightly's price fix again last night" in text and "2 nights running" in text
    assert "1 suspended listing waits for your hand-delete" in text and "1 was reported in the last two days." in text
