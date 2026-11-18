"""An eBay-only store (config/stores.json "amazon": false, 2026-11-04, OpenMaal): its Amazon sync is parked ON PURPOSE, so no page may judge it
(stale 'has not run for 49 hours', 'prices fell in the last Amazon sync'), list it (home tile, Amazon schedule, Keepa plan) or count its
parked Keepa workflows as an activation gap. Stores that run Amazon behave exactly as before - every test has its control."""
import html
import re
from datetime import timedelta

import pytest

from app import catalog, config, digest, readiness
from app.config import Store
from conftest import NOW, make_run


@pytest.fixture
def stores():
    return [Store(id="gtv", name="GTV", repo="org/gtv", sheet="OnBuy_Feed_Master"),
            Store(id="yra", name="YRA", repo="org/yra", sheet="YRA_Full_Feed_Master", amazon=False)]


def add_old_amazon_run(fake):
    """YRA's last scheduled Amazon sync is 49 hours old - the sync was parked after it."""
    fake.runs["org/yra"].append(make_run(23, "run_amazon.yml", "Amazon Sync (Keepa)", NOW - timedelta(hours=49)))


# ---------------------------------------------------------------- the registry
def test_the_flag_is_written_only_when_switched_off_and_read_back(tmp_path):
    path = tmp_path / "stores.json"
    both = [Store(id="a", name="A", repo="o/a"), Store(id="b", name="B", repo="o/b", amazon=False)]
    config.save_stores(path, both)
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert '"amazon"' not in lines[1] and lines[2].rstrip(",").endswith('"amazon": false}') or '"amazon": false' in "".join(lines)
    assert sum('"amazon": false' in line for line in lines) == 1                          # only the switched-off store carries the key
    loaded = config.load_stores(path)
    assert [(s.id, s.amazon) for s in loaded] == [("a", True), ("b", False)]
    old = tmp_path / "old.json"
    old.write_text('[\n  {"id": "z", "name": "Z", "repo": "o/z"}\n]\n', encoding="utf-8")   # a registry from before the flag
    assert config.load_stores(old)[0].amazon is True


def test_the_real_registry_marks_openmaal_ebay_only_and_nobody_else():
    stores = config.load_stores(config.ROOT / "config" / "stores.json")
    assert {s.id: s.amazon for s in stores}["openmaal"] is False
    assert all(s.amazon for s in stores if s.id != "openmaal")


# ---------------------------------------------------------------- the pure helpers
@pytest.mark.parametrize("path,want", [("run_amazon.yml", True), ("amazon_dispatch.yml", True), ("keepa_status.yml", True), ("probe_keepa_deals.yml", True),
                                       (".github/workflows/run_amazon.yml", True), ("run.yml", False), ("amazon_seller_census.yml", False), ("", False), (None, False)])
def test_which_workflows_belong_to_the_amazon_lane(path, want):
    assert catalog.is_amazon_lane(path) is want


def test_an_old_amazon_run_is_not_stale_for_an_ebay_only_store():
    runs = [make_run(1, "run.yml", "Sync", NOW - timedelta(hours=1)), make_run(2, "run_amazon.yml", "Amazon Sync (Keepa)", NOW - timedelta(hours=49))]
    assert [s["path"] for s in digest.summarize_runs(runs, "2000-01-01T00:00:00Z", NOW)["stale"]] == ["run_amazon.yml"]            # control
    assert digest.summarize_runs(catalog.without_amazon(runs), "2000-01-01T00:00:00Z", NOW)["stale"] == []
    assert [r["path"] for r in catalog.without_amazon(runs)] == ["run.yml"]


def test_readiness_lists_the_parked_amazon_workflows_apart_and_does_not_ask_for_keepa():
    mine = {"secrets": {"GOOGLE_CREDENTIALS"}, "variables": {"FEE_MODE": "category"},
            "workflows": [{"path": "run.yml", "name": "Sync", "state": "active"},
                          {"path": "run_amazon.yml", "name": "Amazon", "state": "disabled_manually"},
                          {"path": "keepa_status.yml", "name": "Keepa", "state": "disabled_manually"},
                          {"path": "buybox_defense.yml", "name": "Buy Box", "state": "disabled_manually"}]}
    others = {"a": {"secrets": {"GOOGLE_CREDENTIALS", "KEEPA_API_KEY"}, "variables": {"FEE_MODE": "category", "KEEPA_DROP_HOLD_PERCENT": "40", "AMAZON_MAX_CYCLES_PER_DAY": "3", "EBAY_SHIPPING_COST": "1"}}}
    expected = ("GOOGLE_CREDENTIALS", "KEEPA_API_KEY")
    full = readiness.report(mine, others, expected)                                                                   # control: a store that runs Amazon
    assert full["secrets_missing"] == ["KEEPA_API_KEY"] and {g["name"] for g in full["variable_gaps"]} == {"KEEPA_DROP_HOLD_PERCENT", "AMAZON_MAX_CYCLES_PER_DAY", "EBAY_SHIPPING_COST"}
    assert [w["path"] for w in full["parked"]] == ["buybox_defense.yml", "keepa_status.yml", "run_amazon.yml"] and full["off_on_purpose"] == []
    only = readiness.report(mine, others, expected, amazon=False)
    assert only["secrets_missing"] == [] and [g["name"] for g in only["variable_gaps"]] == ["EBAY_SHIPPING_COST"]
    assert [w["path"] for w in only["off_on_purpose"]] == ["keepa_status.yml", "run_amazon.yml"]
    assert [w["path"] for w in only["parked"]] == ["buybox_defense.yml"] and not only["ready"]                          # a real parked job still counts
    mine["workflows"][3]["state"] = "active"
    assert readiness.report(mine, others, expected, amazon=False)["ready"] is True


# ---------------------------------------------------------------- the pages
def test_the_to_do_page_never_asks_an_ebay_only_store_for_an_amazon_sync(web, fake):
    add_old_amazon_run(fake)
    text = html.unescape(web.get("/todo?refresh=1").text)
    assert "YRA Amazon Sync (Keepa) has not run" not in text and "YRA" in text                                          # YRA is still on the page for its other findings
    assert "Amazon Sync (Keepa) has not run for 49 hours" not in text


def test_the_to_do_page_still_asks_a_store_that_runs_amazon(web, fake, settings):
    fake.runs["org/gtv"] = [r for r in fake.runs["org/gtv"] if r["path"] != "run_amazon.yml"]
    fake.runs["org/gtv"].append(make_run(24, "run_amazon.yml", "Amazon Sync (Keepa)", NOW - timedelta(hours=49)))
    text = html.unescape(web.get("/todo?refresh=1").text)
    assert "GTV" in text and "Amazon Sync (Keepa) has not run for 49 hours" in text                                    # control: the alarm is real for GTV


def test_the_home_page_has_no_amazon_tile_and_a_pill_for_an_ebay_only_store(web, fake):
    add_old_amazon_run(fake)
    text = web.get("/").text
    assert len(re.findall(r'<td title="[^"]*">Amazon sync</td>', text)) == 1                                           # GTV's tile only
    assert 'class="pill quiet" title="This store runs no Amazon lane' in text and text.count(">eBay only<") == 1


def test_the_amazon_page_says_so_for_an_ebay_only_store_and_works_for_the_others(web, fake):
    quiet = web.get("/amazon?store=yra")
    assert quiet.status_code == 200 and "YRA is an eBay-only store" in quiet.text and 'id="schedCard"' not in quiet.text
    normal = web.get("/amazon?store=gtv")
    assert normal.status_code == 200 and 'id="schedCard"' in normal.text and "eBay-only store" not in normal.text


def test_the_amazon_schedule_card_lists_only_the_stores_that_run_amazon(web, fake):
    rows = web.get("/api/amazon/schedule").json()["stores"]
    assert [r["store"]["id"] for r in rows] == ["gtv"]


def test_the_readiness_api_calls_the_parked_amazon_workflows_off_on_purpose(web, fake):
    fake.workflow_states[("org/yra", "run_amazon.yml")] = "disabled_manually"
    data = web.get("/api/stores/yra/readiness").json()
    assert data["amazon"] is False and [w["path"] for w in data["off_on_purpose"]] == ["run_amazon.yml"]
    assert "run_amazon.yml" not in [w["path"] for w in data["parked"]]
    assert "KEEPA_API_KEY" not in data["secrets_missing"]


def test_the_daily_check_shows_an_ebay_only_store_without_amazon_findings(web, fake):
    add_old_amazon_run(fake)
    page = web.get("/daily")
    assert page.status_code == 200
    stale = re.findall(r"Amazon Sync \(Keepa\)[^<]{0,80}stale|stale[^<]{0,80}Amazon Sync \(Keepa\)", page.text)
    assert stale == [] or all("YRA" not in s for s in stale)
