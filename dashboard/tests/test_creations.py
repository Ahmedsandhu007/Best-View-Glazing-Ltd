"""Creations in flight on the store page (2026-11-02): where the queued products stand. Kidoomi queued 225 products on
its first day and the only trace of the queue clearing - 196 OPCs assigned, 2 brand refusals, 1 OnBuy-side error - was
backfill log lines until this card."""
from datetime import timedelta

from conftest import NOW, make_run

from app import creations

# lines exactly as Kidoomi's 2026-11-02 11:18 backfill printed them
BACKFILL_LOG = """
[eBay] 3 pending SKU(s)
[Amazon] 196 pending SKU(s)
[opc-import] listings swept: 222 OPC->SKU pairs
[opc-fill] eBay: 26 blank OPC(s) filled from the listings, 0 row(s) OnBuy does not list
Checking 199 pending SKU(s) against OnBuy's queue history...
Found 199 of 199 pending SKU(s) in the queue history.
795067034579: status=success, opc=PYSC6CG
795035074040: status=success, opc=PYSC6CF
808457834472: status=failed, opc=None, reason=An error occurred: App\\Domains\\SaveProduct\\RulesEngine\\Match\\DataTransferObjects\\MatchedBrandData::__construct(): Argument #1 ($id) must be of type int, null given, called in /var/www/onbuy/releases/1163/app/Domains/SaveProduct/Persist/Pipes/CreateBrandPersistPipe.php on line 35
808397703623: status=failed, opc=None, reason=An error occurred: The supplied brand is owned by another seller.
808397703623: status=failed, opc=None, reason=An error occurred: The supplied brand is owned by another seller.
[eBay] Updated 6 sheet cell(s).
[Amazon] Updated 784 sheet cell(s).
"""


def test_parse_reads_the_queue_story_and_dedupes_repeated_status_lines():
    d = creations.parse_creations(BACKFILL_LOG)
    assert d["pending"] == {"ebay": 3, "amazon": 196}
    assert d["listings_live"] == 222 and d["queue_found"] == 199 and d["queue_checked"] == 199
    assert d["opc_fill"] == [{"tab": "ebay", "filled": 26, "unlisted": 0}]
    assert d["outcomes"] == {"success": 2, "failed": 2}                                   # the repeated SKU counts once
    assert d["failures"][1]["reason"] == "An error occurred: The supplied brand is owned by another seller."
    assert len(d["failures"][0]["reason"]) <= 160                                         # OnBuy's stack trace is cut
    assert d["sheet_cells_updated"] == {"ebay": 6, "amazon": 784}
    assert creations.parse_creations("") == {}


def test_the_api_reads_the_latest_backfill_and_the_card_is_on_the_store_page(web, fake):
    fake.runs["org/yra"].insert(0, make_run(801, "backfill_onbuy_status.yml", "YRA Full-Auto Backfill", NOW - timedelta(minutes=30)))
    fake.logs[801] = BACKFILL_LOG
    data = web.get("/api/store/yra/creations").json()
    assert data["pending"]["amazon"] == 196 and data["outcomes"]["success"] == 2 and data["run"]["url"]
    assert web.get("/api/store/nope/creations").status_code == 404

    text = web.get("/store/yra").text
    assert "Creations in flight" in text and 'id="creations"' in text
    assert "loadCreations" in web.get("/static/app.js?v=1").text
