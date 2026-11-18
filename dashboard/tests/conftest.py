"""Fixtures: two pretend stores, a fake GitHub client with canned runs, an in-memory database, the app and its test client."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings, Store  # noqa: E402
from app.db import Database  # noqa: E402
from app.github_client import GitHubError  # noqa: E402
from app.jobs import Jobs  # noqa: E402
from app.main import create_app  # noqa: E402
from pictures_data import Links  # noqa: E402


def iso(dt):
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


NOW = datetime.now(timezone.utc).replace(microsecond=0)          # the app reads the real clock, so the canned runs and orders hang off it
TODAY = NOW.date().isoformat()
IN_3_DAYS = (NOW + timedelta(days=3)).date().isoformat()
MONTH_AGO = (NOW - timedelta(days=30)).date().isoformat()

NIGHTLY_LOG = """
MATCHED: 5911 | MISMATCHED: 3 | kinds: {'shift+2': 1, 'shift+1': 1, 'collision': 1}
INFO TARGET|1149|203648462166|shift+1|33.59|5|Smart WiFi Video Doorbell Camera|Video Doorbell Wireless WiFi
INFO ZEROED 203648462166 (shift+1, row 1149)
INFO mismatched listings to zero: 1 (3 held in all, stock or not)
INFO held at zero for the audit: 3
INFO DONE: 1 zeroed, 0 failed, 0 untouched
DELETED 1 of 1 planned row(s) from the sheet
Ama-B0BRHJTQZ6-5 - borderline (word overlap 0.44: below the match line, not clearly another product) - left frozen for review
INFO UNDERPRICED on OnBuy (listing below sheet): 589
INFO FIX done: 1234 corrected, 6 failed
sale guard: 0 of 7938 listings carry a sale price
Requirement already satisfied: pip in /opt/hostedtoolcache (26.2.2)
"""

ORDERS_LOG = f"""
ORDER-LINE T6QPP5J | Awaiting Dispatch | 2026-10-20 13:18:57 | SKUs ['0145936976019'] | dispatch by ['{TODAY} 22:59:59']
ORDER-LINE T6QR7NW | Awaiting Dispatch | 2026-10-21 22:48:35 | SKUs ['303553980790'] | dispatch by ['{IN_3_DAYS} 23:59:59']
ORDER-LINE T6N77VB | Awaiting Dispatch | 2026-08-14 19:44:11 | SKUs ['304285306230'] | dispatch by ['{MONTH_AGO} 23:59:59']
DONE: scanned 3 order(s), 0 contained SKU NONE; oldest order seen 2026-08-14 19:44:11
"""


GTV_PRICING_SOURCE = """
PLATFORM_FEE_PERCENT = 20
PROFIT_BANDS = (
    (5.0, 100),
    (10.0, 80),
    (50.0, 40),
    (None, 20),
)
SELL_PRICE_OVERRIDES = (
    (10.0, 20.0, 15),
)
_SUPERSEDED_PROFIT_BANDS = (
    ((5.0, 80), (10.0, 80), (30.0, 40), (100.0, 40), (None, 30)),
)
"""

FLAT_PRICING_SOURCE = """
PLATFORM_FEE_PERCENT = 20
STANDARD_TOP_BAND_PROFIT = 20.0
FLAT_PROFIT = 20.0
TOP_BAND_FROM = 30.0


def _top_band_profit():
    return STANDARD_TOP_BAND_PROFIT


TOP_BAND_PROFIT = _top_band_profit()
SELL_PRICE_OVERRIDES = ()
PROFIT_BANDS = (
    (5.0, FLAT_PROFIT),
    (10.0, FLAT_PROFIT),
    (TOP_BAND_FROM, FLAT_PROFIT),
    (None, TOP_BAND_PROFIT),
)
_SUPERSEDED_PROFIT_BANDS = (
    ((5.0, 100), (10.0, 80), (50.0, 40), (None, 25)),
)
"""


TIERS_CSV = """Tier ID,Name,Lower %,Upper %,Threshold (£),Min Fee (£)
9ccfe96a-5232-4864-b848-51c93b23881a,Baby & Toddler,8.00,15.00,10.00,0.25
9ccfe96a-6a76-4522-8337-bea4f660a8ce,Consumer Electronics,7.00,,,0.25
9ccfe96a-dba1-4b3d-9b4e-dc78a0836077,Jewellery,20.00,5.00,,0.25
d2722109-c832-45ba-a1cd-28523c319250,Standard Selling Fee,15.00,,,0.25
"""

CATEGORY_TIERS_CSV = """Category ID,Commission Tier ID,Tier Name
2144,9ccfe96a-5232-4864-b848-51c93b23881a,Baby & Toddler
11656,9ccfe96a-6a76-4522-8337-bea4f660a8ce,Consumer Electronics
10483,d2722109-c832-45ba-a1cd-28523c319250,Standard Selling Fee
28683,d2722109-c832-45ba-a1cd-28523c319250,Standard Selling Fee
38245,,
"""

RELABEL_SOURCE = '''
DEFAULT_RULES = r"""
(3d[ -]?print(er|ing)s?|resin printers?)(?!\\s*filament) => Arts, Crafts & Sewing > Other Crafts > 3D Printing > 3D Printers
filament => Arts, Crafts & Sewing > Other Crafts > 3D Printing > 3D Printer Filament
"""
'''

FEEDBACK_DRY_LOG = """
orders page 1: 100 order(s) read, oldest 2026-09-10 16:57:46
DRY RUN | 90 days | SKUs with usable orders: 171 | sheet rows: 9463
UNDER-CHARGED - OnBuy takes more than the sheet's tier: 2 row(s) to override
   612227390835 | Sheet1 row 1568 | Business, Office & Industrial Supplies > Hospitality Supplie | sheet tier Large Appliances 7% | OnBuy charged 15% ex VAT (2 order(s), 2 kept; e.g. T6PJPTD, T6PZHY5) | Fee % 8.40 -> 18.00 | price 55.67 | stock 5
   Ama-B0BCK4K9ZC-6 | Amazon row 965 | Electronics & Technology > Computing & Gaming > iPads, Table | sheet tier Consumer Electronics 7% | OnBuy charged 15% ex VAT (2 order(s), 2 kept; e.g. T6PVN7H, T6Q7SRR) | Fee % 9.99 -> 18.00 | price 8.48 | stock 5
   extra commission already paid on the kept orders of these SKUs: GBP 8.83 ex VAT (GBP 10.60 inc VAT)
OVER-CHARGED by the sheet - OnBuy takes less than the tier (prices could be lower; nothing written): 7 row(s)
   282005682294 | Sheet1 row 3370 | Home & Garden > Celebrations, Occasions and Gifting > Gift S | sheet tier Standard Selling Fee 15% | OnBuy charged 7% ex VAT (1 order(s), 0 kept; e.g. T6PHJN2) | Fee % 18.00 | price 23.89 | stock 5
TIERED categories (two rates; not compared): 1
   555 | Amazon row 12 | Baby & Toddler > Feeding | sheet tier Baby & Toddler 8%/15% above 10 | OnBuy charged 15% ex VAT (1 order(s), 1 kept; e.g. T6PZZZZ) | Fee % 9.60 | price 12.5 | stock 5
rows matching their tier: 67 | ordered SKUs not in the sheet (team / legacy listings): 95
DRY RUN - nothing written. Re-run with apply=yes to write the Fee % overrides.
"""

FEEDBACK_APPLY_LOG = """
APPLY | 90 days | SKUs with usable orders: 171 | sheet rows: 9657
UNDER-CHARGED - OnBuy takes more than the sheet's tier: 2 row(s) to override
   612227390835 | Sheet1 row 1568 | Business, Office & Industrial Supplies > Hospitality Supplie | sheet tier Large Appliances 7% | OnBuy charged 15% ex VAT (2 order(s), 2 kept; e.g. T6PJPTD, T6PZHY5) | Fee % 8.40 -> 18.00 | price 55.67 | stock 5
   extra commission already paid on the kept orders of these SKUs: GBP 8.83 ex VAT (GBP 10.60 inc VAT)
rows matching their tier: 67 | ordered SKUs not in the sheet (team / legacy listings): 95
backup tab 'Fee overrides 2026-10-22': 2 row(s)
WRITTEN: 2 Fee % override(s), 0 skipped. The sync re-prices these rows from the new fee at its next visit (or run the audit to push them now).
"""

PROBE_LOG = """
ORDER T6QQY7Q | Awaiting Dispatch | 2026-10-21 | sku 896104760397 | lines 1 | subtotal 6.84 delivery 0.0 discount 0.0 total 6.84 | sales_fee_ex_VAT 1.03 (15.06% of subtotal+delivery) sales_fee_inc_VAT 1.24 (18.13%) | line {} | tier Standard Selling Fee 15.0 [Sheet1] | cat Tools & DIY > Workwear
page 1: scanned 100 order(s), oldest 2026-09-10 16:57:46
SUMMARY - OnBuy's own sales fee as a share of subtotal+delivery, per FLAT tier (nominal -> observed):
  nominal 7%: 19 order(s) | ex-VAT median 7.00% (min 6.98, max 15.00) ratio to nominal 1.000 | inc-VAT median 8.41% ratio 1.201
      charged: 7% x15, 15% x4
  nominal 13%: 6 order(s) | ex-VAT median 13.00% (min 13.00, max 13.01) ratio to nominal 1.000 | inc-VAT median 15.59% ratio 1.200
      charged: 13% x6
  nominal 15%: 63 order(s) | ex-VAT median 15.00% (min 6.99, max 15.10) ratio to nominal 1.000 | inc-VAT median 18.00% ratio 1.200
      charged: 7% x5, 13% x2, 15% x56
MISMATCHES: 11 single-line order(s) where OnBuy charged a different flat rate than the sheet's category tier | extra commission paid on the kept orders: GBP 8.83 ex VAT (x1.2 inc VAT = GBP 10.60)
     2 order(s) | sheet tier 15% | charged [7] | Health & Beauty > Medication & Remedies > Medication > Stress & Anxiety Relief Medication | e.g. 782012511117
     2 order(s) | sheet tier 7% | charged [15] | Electronics & Technology > Computing & Gaming > iPads, Tablets & eBook Readers > Tablets | e.g. Ama-B0BCK4K9ZC-6
DONE: scanned 200 order(s), 200 line(s) listed, oldest 2026-06-13 21:59:11
"""

CENSUS_LOG = """
KEYWORD ROWS ('3d[ -]?print|filament|3d pen|resin printer'): 2
   4020740160723-zzz | Amazon row 800 | cat Electronics & Technology > Computing & Gaming > Printers & Accessories [-] | Fee % 8.40 | price 342.69 | stock 5.0 | Synced | X-Maker Joy AI Kids 3D Printer for Beginners, Fully Enclosed, Ready to
   262415797696 | Amazon row 2033 | cat Arts, Crafts & Sewing > Other Crafts > 3D Printing > 3D Printer Filame [-] | Fee % 18.00 | price 25.59 | stock None | Synced | GIANTARM Filament PLA 1.75mm Silk Silver,3D Printer PLA Filament 1kg S
   per category: Electronics & Technology > Computing & Gaming > Printers & Accessories: 1; Arts, Crafts & Sewing > Other Crafts > 3D Printing > 3D Printer Filame: 1

EXPOSURE CENSUS (priced rows by tab / tier / nominal % / Fee % cell): rows | in stock | sum of selling prices
   Amazon     | Standard Selling Fee                     | nominal 15               | Fee % cell 18.00  |   2144 rows |   2009 in stock | GBP 219,356
   Amazon     | Consumer Electronics                     | nominal 7                | Fee % cell 8.40   |    656 rows |    602 in stock | GBP 131,591
   Amazon     | Baby & Toddler                           | nominal 8/15 above 10    | Fee % cell 9.60   |     18 rows |     18 in stock | GBP 2,390
   Amazon     | (no tier)                                | nominal -                | Fee % cell 24.00  |     28 rows |     27 in stock | GBP 2,248
   Sheet1     | Standard Selling Fee                     | nominal 15               | Fee % cell 18.00  |   4556 rows |   4554 in stock | GBP 625,792

CATEGORIES WITH NO TIER (rows): Home & Garden > Kitchen & Home Appliances > Appliance Parts & Accessor: 387; Cars & Automotive > In-Car Entertainment & Electronics > Car Audio & V: 346
"""

STALE_CENSUS_LOG = """
KEYWORD ROWS ('3d[ -]?print|filament|3d pen|resin printer'): 61
   per category: Electronics & Technology > Computing & Gaming > Printers & Accessories: 42

EXPOSURE CENSUS (priced rows by tab / tier / nominal % / Fee % cell): rows | in stock | sum of selling prices
   Amazon     | (no tier)                                | nominal -                | Fee % cell 18.00  |   2144 rows |   2009 in stock | GBP 219,356
   Sheet1     | (no tier)                                | nominal -                | Fee % cell 8.40   |   1560 rows |   1560 in stock | GBP 360,559
"""

RELABEL_LOG = """
DRY RUN | 3 rule(s): /(3d[ -]?print(er|ing)s?|resin printers?)(?!\\s*filament)/ -> 3D Printers [10483]; /3d[ -]?(printing[ -]?)?pens?/ -> 3D Printing Pens [18215]; /filament/ -> 3D Printer Filament [8723]

ROWS TO RELABEL: 2 (already on the target path: 17)
   4020740160723-zzz | Amazon row 800 | Electronics & Technology > Computing & Gaming > Printers & A [-] (Consumer Electronics 7%) -> 3D Printers [10483] (Standard Selling Fee 15%) | Fee % 8.40 | price 342.69 | stock 5.0 | X-Maker Joy AI Kids 3D Printer for Beginners, Fully Enclosed
   646768201893 | Amazon row 2794 | Cars & Automotive > Car Parts > Motorhome Parts & Accessorie [-] (Standard Selling Fee 15%) -> 3D Printers [10483] (Standard Selling Fee 15%) | Fee % 18.00 | price 124.01 | stock 5.0 | Large Resin 3D Enclosure with Ventilation Kit LED Light, 3D
DRY RUN - nothing written. Re-run with apply=yes to relabel.
"""

RELABEL_APPLY_LOG = """
APPLY | 3 rule(s): /filament/ -> 3D Printer Filament [8723]

ROWS TO RELABEL: 43 (already on the target path: 17)
   4020740160723-zzz | Amazon row 800 | Electronics & Technology > Computing & Gaming > Printers & A [-] (Consumer Electronics 7%) -> 3D Printers [10483] (Standard Selling Fee 15%) | Fee % 8.40 | price 342.69 | stock 5.0 | X-Maker Joy AI Kids 3D Printer
backup tab 'Categories relabelled 2026-10-22': 43 row(s)
WRITTEN: 43 row(s) relabelled, 0 skipped. The sync re-prices them from the new tier at its next visit.
"""

REFRESH_LOG = """
commission tiers: 29
   Arts, Crafts & Sewing                       15.00%  min £0.25
   Baby & Toddler                               8.00%, 15.00% above £10.00  min £0.25
   Jewellery                                   20.00%, 5.00% upper (no threshold given)  min £0.25
categories fetched: 7549 | with a tier: 7536
written: onbuy_commission_tiers.csv (29 rows), onbuy_category_tiers.csv (7549 rows)

listable categories by tier:
    5719  Standard Selling Fee
     548  DIY & Tools
listable categories with NO tier: 11
    38245 Appliances > Furniture, Furnishings & Decor > Lighting > Ceiling Lights
    38247 Appliances > Furniture, Furnishings & Decor > Lighting > Lamps

sample category record: {"category_id": 2144, "name": "Baby & Toddler"}
TABLES DIFFER: tiers unchanged; categories 462 gone, 11 new, 0 changed tier (commit=yes writes them)
   gone: 38245 Appliances > Furniture, Furnishings & Decor > Lighting > Ceiling Lights (Standard Selling Fee)
"""

IMPACT_LOG = """
rows priced: 6652 | would LOWER: 1 | would RAISE: 3217 | KEEP: 3434
skipped: no cost 184 | no category 5 | category without a tier 97
tier mode: marginal (upper rate on the part above the threshold)

tier                                      rows lower raise  keep  avg flat20  avg tier  avg cell
Standard Selling Fee                      4944     1  2562  2381       63.02     59.25     60.87
Consumer Electronics                      1054     0   299   755      164.41    141.05    144.58

examples (LOWER):
   Sheet1 row 2475 797250095190 [Standard Selling Fee 16.50%] cost 11.29 -> flat20 20.14, tier 18.93, cell 20.14
wrote price_impact.csv (6652 rows)
"""


SALE_PLAN_LOG = """
MODE plan | sale 5% off GBP 0 to GBP 9.99; no sale on GBP 10 to GBP 20; 3% off GBP 20.01 and above | window 2026-10-25 00:00:00 .. 2026-10-28 23:59:59 | scope all | margin floor 10.0% profit on cost + shipping after the fee, skip | state: none
costs: 8985 SKUs from 'OnBuy_Feed_Master'
sweep: 8936 listings in 95 page(s), short pages 1, metadata ***'limit': 100, 'offset': 0, 'total_rows': 8936***
sales on the account now: 0 of 8936 listings | end dates -
PLAN 5% off GBP 0 to GBP 9.99; no sale on GBP 10 to GBP 20; 3% off GBP 20.01 and above | 7500 update(s) in 15 request(s)
ACTIONS sale on=7500; skip: price in the excluded range=656; skip: no cost on the sheet=304; skip: below the margin floor=38; skip: too cheap for a sale=2
RANGE 1 | GBP 0 to GBP 9.99 | 5% | 900 listings | 800 on sale | 60 no cost | 30 below the floor | 10 other | GBP 112.50 off | 0 sale(s) ended
RANGE 2 | GBP 10 to GBP 20 | kept out | 656 listings | 0 on sale | 0 no cost | 0 below the floor | 656 other | GBP 0.00 off | 0 sale(s) ended
RANGE 3 | GBP 20.01 and above | 3% | 7380 listings | 6700 on sale | 244 no cost | 8 below the floor | 428 other | GBP 26,000.00 off | 3 sale(s) ended
RANGE other | outside every selected range | 0 listings
after this run 7500 of 8936 listings carry the sale, GBP 26,112.50 off in total (one unit of each)
PLAN ONLY - nothing changed.
"""

# the first runs of 2026-10-26 (GTV, run 40306712708 and 40306403184): the v2 format, counts inside braces the runners mask as ***
SALE_V2_APPLY_LOG = """
MODE apply | percent 3.0 | window 2026-10-25 00:00:00 .. 2026-11-25 23:59:59 | scope all | excluded prices GBP 10 to GBP 20 (both included) | margin floor 10.0% profit on cost + shipping after the fee, skip | state: none
costs: 8985 SKUs from 'OnBuy_Feed_Master'
sweep: 8936 listings in 95 page(s), short pages 1, metadata ***'limit': 100, 'offset': 0, 'total_rows': 8936***
sales on the account now: 0 of 8936 listings | end dates ***
PLAN 3.0% off: ***'sale on': 7938, 'skip: price in the excluded range': 656, 'skip: no cost on the sheet': 304, 'skip: below the margin floor': 38*** -> 7938 update(s) in 16 request(s)
after this run 7938 of 8936 listings carry the sale, GBP 26,593.01 off in total (one unit of each)
store_sale.json written (3.0% until 2026-11-25, floor 10.0% skip, excluded prices GBP 10 to GBP 20 (both included))
chunk 16: 438 ok of 438
APPLIED: 7938 ok, 0 failed ***
read-back after 60s: 8 of 8 already show the sale (OnBuy applies updates within about a minute)
"""

SALE_V2_TEST_LOG = """
MODE test | percent 3.0 | window 2026-10-25 00:00:00 .. 2026-11-25 23:59:59 | scope all | excluded prices GBP 10 to GBP 20 (both included) | margin floor 10.0% profit on cost + shipping after the fee, skip | state: none
738516204215: before ***"price": "27.13", "stock": 5, "sale_price": null*** | cost base 15.89 fee 18.0% floor 21.32 -> sale on at 26.32
SALE ON sent: 1 ok, 0 failed *** (3s)
RESULT sale on: visible after 15s
SALE OFF sent: 1 ok, 0 failed *** (3s)
RESULT sale off: gone after 60s
"""

SALE_CANCEL_LOG = """
MODE cancel | sale - | window 2026-10-25 00:00:00 .. 2026-11-25 23:59:59 | scope all | margin floor 10.0% profit on cost + shipping after the fee, skip | state: ACTIVE 3% off every listing except GBP 10 to GBP 20 until 2026-10-28
sweep: 8936 listings in 95 page(s), short pages 1, metadata ***'limit': 100***
sales on the account now: 7938 of 8936 listings | end dates 2026-10-28=7938
TO END: 7938 sale(s)
CANCELLED: 7938 ok, 0 failed | errors none | store_sale.json removed
read-back after 90s: 8 of 8 already show no sale (OnBuy drops an ended sale within a minute or two)
"""

SALE_STATE_LEGACY = {"percent": 3.0, "scope": "all", "sale_start_date": "2026-10-25 00:00:00", "sale_end_date": f"{IN_3_DAYS} 23:59:59", "exclude_price_from": 10.0,
                     "exclude_price_to": 20.0, "min_profit_percent": 10.0, "floor_mode": "skip", "applied_at": "2026-10-26 10:30:54Z", "listings": 7938}

# GTV's three hold lists as the nightly writes them (cut down from the repository's files of 2026-10-26)
HOLD_TEXT = """# SKUs whose OnBuy listing shows ANOTHER product (title, description, images) or another model/spec than the sheet row. The nightly price/stock audit holds them at stock 0
# instead of pushing the sheet's stock, and protected_skus.txt stops the hourly sync from restocking them.
# Remove a line only after the listing's content has been repaired (and then from protected_skus.txt too).
# 2026-10-16 the nightly found these listings showing ANOTHER product - zeroed and frozen automatically; release only after the page or the row is fixed
856689732127  # Sheet1 row 1004: row = 9000000mAh Power Bank Magnetic Battery Pack W | page = POWER BANK FOR ELECTRIC HEATED VEST JACKET BO
# 2026-10-20 the nightly found these listings showing ANOTHER product - zeroed and frozen automatically; release only after the page or the row is fixed
# 2026-10-22 the nightly found these listings showing ANOTHER product - zeroed and frozen automatically; release only after the page or the row is fixed
Ama-B0BRHJTQZ6-5  # Amazon row 772: row = zoerbufan Toe Separators, 3 Pairs, Soft Silic | page = Toe Separators [3 Pair], Toe Stretcher for Ov
"""
PROTECTED_TEXT = """# OnBuy content-shift incident 2026-08-21: listings whose OnBuy page shows another product.
# No price/stock pushes (main loop + activation pass) until the content repair is verified.
773086105845
Ebay-125275026740-13
# 2026-09-04: 757763636464 released - OnBuy's API logs showed our own
# submission carried the wrong content (not a platform fault).
653709952448  # 2026-09-22 source OOS on page, listing stayed in stock - held at 0 pending diagnosis
# 2026-10-16 the nightly found these listings showing ANOTHER product - zeroed and frozen automatically; release only after the page or the row is fixed
856689732127  # Sheet1 row 1004: row = 9000000mAh Power Bank Magnetic Battery Pack W | page = POWER BANK FOR ELECTRIC HEATED VEST JACKET BO
# 2026-10-22 the nightly found these listings showing ANOTHER product - zeroed and frozen automatically; release only after the page or the row is fixed
Ama-B0BRHJTQZ6-5  # Amazon row 772: row = zoerbufan Toe Separators, 3 Pairs, Soft Silic | page = Toe Separators [3 Pair], Toe Stretcher for Ov
"""
SAME_TEXT = """# SKUs checked BY HAND on 2026-10-10 (full row title next to the full live page name): the OnBuy page IS this row's product, only worded
# differently (shared catalogue titles), so the nightly content check must not count them as 'shows another product' and must not zero them.

781908348462  # Premium Quartz Clock Insert with Roman Numerals 65
Ama-B0FKH8WM2B-29  # Remington Almond Allure Hair Straightener, 31 cm,
"""

# the last steps of an eBay sync (run.yml), the format of purge_dead_rows.py
PURGE_LOG = """
LIVE RUN | tab 'eBay' | kinds brand,oos | max 200 rows, 40 eBay checks
eBay tab: 4210 rows | looking dead: brand-blocked 3, out of stock 17 | held back 4
  held     3  protected listing (protected_skus.txt)
  held     1  open order (awaiting dispatch)
eBay confirmation of the out-of-stock rows: gone 12, alive again 2, unknown 3 (40 checks)
TO DELETE THIS RUN: 15 row(s) (brand 3, out of stock 12; 2 of 3 suspended listings need deleting by hand)
SUSPENDED 305812347721  Women Waterproof Walking Shoes Lightweight Sneakers
DELETED 15 row(s) from the sheet (0 kept for the next run, 0 skipped at deletion time: [])
SUSPENDED 305812347721  Women Waterproof Walking Shoes Lightweight Sneakers
PURGE DONE: 15 row(s) removed (brand 3, out of stock 12); suspended on OnBuy 1; OnBuy errors 0
"""

# purge_dead_rows.yml as a dry run (the form on the Catalogue page)
PURGE_DRY_LOG = """
DRY RUN | tab 'eBay' | kinds brand,oos | max 200 rows, 250 eBay checks
eBay tab: 4210 rows | looking dead: brand-blocked 3, out of stock 17 | held back 4
  held     3  protected listing (protected_skus.txt)
  held     1  open order (awaiting dispatch)
eBay confirmation of the out-of-stock rows: gone 12, alive again 2, unknown 3 (17 checks)
TO DELETE THIS RUN: 15 row(s) (brand 3, out of stock 12; 0 already deleted)

DRY RUN - nothing deleted.
"""

# purge_dead_rows.yml with list_suspended=yes: the purged rows OnBuy would not delete, read back from the 'Purged ...' tabs
PURGE_SUSPENDED_LOG = """
2 purged SKU(s) whose OnBuy listing is suspended - OnBuy refuses to delete them, delete them by hand on OnBuy:
SUSPENDED 305812347721  Women Waterproof Walking Shoes Lightweight Sneakers
SUSPENDED Ebay-174409866283-2  Portable Mini Fan Handheld USB Rechargeable
"""

# a remove_wrong_content.yml run that went all the way: one row deleted, the listing suspended on OnBuy (the batch script logs with a level prefix)
REMOVAL_LIVE_LOG = """
sheet rows read: ***'Sheet1': 6012, 'Amazon': 2930*** | 1 SKU(s) asked for | LIVE RUN

WILL REMOVE 1 row(s) and their OnBuy listings:
  Sheet1  row  1004 | 856689732127 | sheet stock 3 | OnBuy stock 0 OPC 99 | overlap 0.12
           row  : 9000000mAh Power Bank Magnetic Battery Pack W
           page : POWER BANK FOR ELECTRIC HEATED VEST JACKET BO

HELD BACK 0:

DELETED 1 of 1 planned row(s) from the sheet
VERIFY: 0 removed SKU(s) still on the sheet
hold lists (protected_skus.txt + hold_at_zero_skus.txt): 2 line(s) dropped for the removed SKUs
INFO DONE in 1 request(s): 1 suspended
INFO SUSPENDED (needs OnBuy): 856689732127
"""

# dup_removal.yml (guarded_remove_rows.py) as the Delete page runs it: a dry run on a list of 8 SKUs, live duplicates off - one row is back in stock, one is on the protected list
GUARDED_PLAN_LOG = """
listed SKUs: 8 | in-stock rows of the list: held | live duplicates: off | dead copies: off | DRY RUN
product rows: ***'Sheet1': 5153, 'Amazon': 3629***
never removed (open orders / protected): 26 SKU(s) | keeper must be Synced: yes

WILL REMOVE 5 row(s):
      1  Amazon  | listed (out of stock)
      4  Sheet1  | listed (out of stock)
  of which live on OnBuy (created=TRUE): 4 | in stock at this moment: 0

HELD BACK 2 row(s):
      1  Sheet1  | back in stock  since the list was made
      1  Amazon  | excluded (open order / protected SKU) - not touched
     held: Sheet1 row 262 SKU 634439213559 stock 52 created True - back in stock (stock 52) since the list was made
     held: Amazon row 126 SKU 351178147104 stock 5 created True - excluded (open order / protected SKU) - not touched

listed SKUs not on the sheet (OnBuy may still hold them): 1

keepers of the duplicates being removed: ***

FLAGGED as duplicate by the sync, live, but NOT removed: 33 (of 36 flagged live)
      2  it is now the FIRST row of its supplier product (the original is gone)
     21  alone on its supplier link
     kept: Sheet1 row 262 SKU 634439213559 stock 52 | group of 2: Sheet1 257, Sheet1 262*
OnBuy delete list: 6 SKU(s) -> onbuy_delete_list.txt

DRY RUN - nothing changed.
"""

# the same tool for real (the format of the 2026-10-08 run that removed 742 rows), with what OnBuy answered
GUARDED_LIVE_LOG = """
listed SKUs: 3 | live duplicates: off | dead copies: off | LIVE RUN
product rows: ***'Sheet1': 5153, 'Amazon': 3629***
never removed (open orders / protected): 26 SKU(s) | keeper must be Synced: yes

WILL REMOVE 3 row(s):
      1  Amazon  | listed (out of stock)
      2  Sheet1  | listed (out of stock)
  of which live on OnBuy (created=TRUE): 2 | in stock at this moment: 0

HELD BACK 0 row(s):

listed SKUs not on the sheet (OnBuy may still hold them): 0
OnBuy delete list: 3 SKU(s) -> onbuy_delete_list.txt
backup tab 'Removed 2026-10-26' created
backup verified: 3 row(s) written to 'Removed 2026-10-26'
  Sheet1: deleted 2 row(s) so far
  Amazon: deleted 1 row(s) so far

DELETED 3 of 3 planned row(s) from the sheet
VERIFY: 0 removed SKU(s) still on the sheet
INFO SKUs to delete: 3 (0 sent under their platform spelling)
INFO DONE in 1 request(s): 1 gone, 1 ok, 1 suspended, 2 other error
INFO SUSPENDED (needs OnBuy): 305812347721
WARNING ERROR 772793799866: Listing is already removed
WARNING ERROR 859123422103: HTTP 500 the platform went away
"""

# buybox_defense.py: GTV's daily live run of 2026-10-26 (cut down: the counts are the real ones, only a few of the 52 price lines are kept)
BUYBOX_LIVE_LOG = """
sheet rows with cost: 4035 | protected: 13 | push enabled: True | dry run: False
live listings: 8936 | in-stock unprotected candidates: 8695
check-winning calls: 87 | answers: 8695
summary: winning: 7465 | no data: 525 | cheaper-not-winning: 107 | no cost: 419 | reprice: 48 | held: 131 | restored: 3
  push 473302857618 -> 30.97
  push 473176853495 -> 25.99
  push Ebay-126172742134-11 -> 18.18
  restore 733653967719 -> 24.44 (contest ended)
  restore 797581478891 -> 79.45 (contest ended)
pushed: 52 | failed: 0
BuyBox tab written: 705 contested row(s)
Post job cleanup.
"""

# the day before: a rate limit on the way, a failed push
BUYBOX_LIVE_LOG_2 = """
sheet rows with cost: 4057 | protected: 13 | push enabled: True | dry run: False
live listings: 8961 | in-stock unprotected candidates: 8697
listings page: HTTP 429 - waiting 120s before retrying
burst limit - waiting 90s
check-winning calls: 87 | answers: 8697
summary: winning: 7506 | no data: 490 | cheaper-not-winning: 79 | no cost: 429 | reprice: 65 | held: 128 | restored: 7
  push 473302857618 -> 31.50
pushed: 70 | failed: 2
BuyBox tab written: 701 contested row(s)
"""

# a manual dry run: classifies, writes the tab, pushes nothing
BUYBOX_DRY_LOG = """
sheet rows with cost: 4035 | protected: 13 | push enabled: True | dry run: True
live listings: 8936 | in-stock unprotected candidates: 8695
check-winning calls: 87 | answers: 8695
summary: winning: 7465 | no data: 525 | cheaper-not-winning: 107 | no cost: 419 | reprice: 70 | held: 109 | restored: 3
  push 473302857618 -> 30.97
DRY RUN - no prices pushed
BuyBox tab written: 705 contested row(s)
"""

BUYBOX_OFF_LOG = """
Buy Box defense is switched off - the repository variable BUYBOX_DEFENSE_ENABLED is no - so the daily run does nothing
"""

# delivery_templates.py: Arden's plan of 2026-10-13 07:42Z (the braces of the dict prints are masked as *** on the runners)
DELIVERY_PLAN_LOG = """
MODE plan | templates: eBay 54810, Amazon 54809 | sheet SKUs by supplier: ***'ebay': 7508, 'amazon': 2159, 'none': 148***
sweep: 12130 listings in 127 page(s), short pages 1, metadata ***'limit': 100, 'offset': 0, 'total_rows': 12130***
listings: 12130 | delivery_template_id: ***'54810': 7342, '52506': 2682, '54809': 2106*** | handling_time: ***'0': 12129, '5': 1***
  ebay      7410 listings | templates ***'54810': 7340, '52506': 70*** | handling ***'0': 7410***
  amazon    2102 listings | templates ***'54809': 2097, '52506': 5*** | handling ***'0': 2102***
  legacy    2618 listings | templates ***'52506': 2607, '54809': 9, '54810': 2*** | handling ***'0': 2617, '5': 1***
TO MOVE: 75 listing(s): ebay 52506->54810: 70, amazon 52506->54809: 5
PLAN ONLY - nothing changed.
"""

# the same tool as an apply on 2026-10-13 07:24Z: eleven batches, one answered HTTP 500
DELIVERY_APPLY_LOG = """
MODE apply | templates: eBay 54810, Amazon 54809 | sheet SKUs by supplier: ***'ebay': 7508, 'amazon': 2159, 'none': 148***
sweep: 12130 listings in 127 page(s), short pages 1, metadata ***'limit': 100, 'offset': 0, 'total_rows': 12130***
listings: 12130 | delivery_template_id: ***'52506': 11352, '54809': 659, '54810': 119*** | handling_time: ***'0': 12129, '5': 1***
TO MOVE: 8750 listing(s): ebay 52506->54810: 7290, amazon 52506->54809: 1455, ebay 54809->54810: 4, amazon 54810->54809: 1
batch 1: HTTP 200, 499 ok of 499
batch 2: HTTP 500, 0 ok of 500
batch 3: HTTP 200, 498 ok of 498
APPLIED: 7675 ok, 1000 failed ***'error: HTTP 500': 1000***
read-back sample: 11 of 12 already show the new template (OnBuy applies updates with a delay - re-run MODE=plan later for the full count)
"""

# the one-listing test of 2026-10-13 07:20Z
DELIVERY_TEST_LOG = """
MODE test | templates: eBay 54810, Amazon 54809 | sheet SKUs by supplier: ***'ebay': 7508, 'amazon': 2160, 'none': 148***
283826373354: class ebay | before: template 52506 handling 0 price 243.83 stock 6 | want 54810
PUT -> HTTP 200 | per-SKU answer ***'283826373354': ''*** | ***"success":true***
read-back after 10s: template 52506 handling 0 price 243.83 stock 6 updated_at 2026-10-12 11:20:42
read-back after 30s: template 54810 handling 0 price 243.83 stock 6 updated_at 2026-10-13 07:20:23
RESULT: the API accepts delivery_template_id - the template moved
"""

# the step inside Makstore's nightly of 2026-10-26: shared sweep, the semi sheet, 158 listings OnBuy never put live
DELIVERY_NIGHTLY_LOG = """
INFO DONE: 1 zeroed, 0 failed, 0 untouched
semi sheet 'Makstore_Feed_Master': 2374 SKUs by supplier ***'ali': 2374***, 2374 added (not in the full sheet)
MODE apply | templates: eBay 35109, Amazon 22069, AliExpress 43190 | clear own handling time: yes | sheet SKUs by supplier: ***'ebay': 6680, 'amazon': 3198, 'ali': 2374, 'none': 65, 'other': 1***
shared sweep: 12405 listings
listings: 12405 | delivery_template_id: ***'35109': 6543, '22069': 3866, '43190': 1996*** | handling_time: ***'0': 12193, '2': 161, '3': 25***
  ebay      6624 listings | templates ***'35109': 6467, '22069': 157*** | handling ***'0': 6624***
  amazon    2806 listings | templates ***'22069': 2806*** | handling ***'0': 2806***
  ali       1976 listings | templates ***'43190': 1975, '22069': 1*** | handling ***'0': 1975, '5': 1***
  legacy     999 listings | templates ***'22069': 902, '35109': 76, '43190': 21*** | handling ***'0': 788, '2': 161***
listings with their own handling time: 212 -> handling_times.csv
TO MOVE: 158 listing(s): ebay 22069->35109: 157, ali 22069->43190: 1 | handling time cleared on 1
skipped 158 listing(s) with no price above zero on OnBuy (never-live listings; a PUT needs a price) - they stay where they are
nothing to send
"""

# the workflow files as the dashboard reads them: GTV's with built-in fallbacks (like Makstore's), YRA's without (like the stores that never had a template)
DELIVERY_WORKFLOW_FALLBACKS = """
          TEMPLATE_EBAY: ${{ inputs.template_ebay || vars.DELIVERY_TEMPLATE_EBAY || '54810' }}
          TEMPLATE_AMAZON: ${{ inputs.template_amazon || vars.DELIVERY_TEMPLATE_AMAZON || '54809' }}
          TEMPLATE_ALI: ${{ inputs.template_ali || vars.DELIVERY_TEMPLATE_ALI || '43190' }}
"""
DELIVERY_WORKFLOW_BARE = """
          TEMPLATE_EBAY: ${{ inputs.template_ebay || vars.DELIVERY_TEMPLATE_EBAY }}
          TEMPLATE_AMAZON: ${{ inputs.template_amazon || vars.DELIVERY_TEMPLATE_AMAZON }}
          TEMPLATE_ALI: ${{ inputs.template_ali || vars.DELIVERY_TEMPLATE_ALI }}
"""

# a remove_wrong_content.yml dry run on the borderline above (GitHub masks the braces of the first line as ***)
REMOVAL_LOG = """
sheet rows read: ***'Sheet1': 6012, 'Amazon': 2930*** | 2 SKU(s) asked for | DRY RUN

WILL REMOVE 1 row(s) and their OnBuy listings:
  Amazon  row   772 | Ama-B0BRHJTQZ6-5 | sheet stock 5 | OnBuy stock 0 OPC 1234567890 | overlap 0.44
           row  : zoerbufan Toe Separators, 3 Pairs, Soft Silic
           page : Toe Separators [3 Pair], Toe Stretcher for Ov

HELD BACK 1:
  856689732127 - the OnBuy page now matches the row (word overlap 0.80) - not wrong content

DRY RUN - nothing changed.
"""


# the env block of GTV's run_amazon.yml (cut down): the variables the Amazon sync really passes on
AMAZON_WORKFLOW_TEXT = """
      - name: Run script
        env:
          SHEET_TAB: Amazon
          KEEPA_BUYBOX: ${{ vars.KEEPA_BUYBOX }}
          AMAZON_OWN_OFFER_ONLY: ${{ vars.AMAZON_OWN_OFFER_ONLY }}
          KEEPA_REGULAR_PRICE: ${{ vars.KEEPA_REGULAR_PRICE }}
          KEEPA_DROP_HOLD_PERCENT: ${{ vars.KEEPA_DROP_HOLD_PERCENT }}
          KEEPA_REAL_PRICE_LOOKUP: ${{ vars.KEEPA_REAL_PRICE_LOOKUP }}
          KEEPA_REAL_PRICE_MAX: ${{ vars.KEEPA_REAL_PRICE_MAX }}
          MAX_PRODUCTS_PER_RUN: ${{ vars.AMAZON_MAX_PRODUCTS_PER_RUN || '300' }}
"""


def make_run(rid, path, name, created, status="completed", conclusion="success", event="schedule"):
    return {"id": rid, "name": name, "path": path, "status": status, "conclusion": conclusion, "event": event,
            "created_at": iso(created), "updated_at": iso(created), "url": f"https://github.com/x/y/actions/runs/{rid}",
            "run_number": rid, "title": name}


class FakeGitHub:
    """Answers like the real client, from canned data; records dispatches."""

    def __init__(self):
        self.runs = {
            "org/gtv": [
                make_run(11, "run.yml", "Generate OnBuy Feed", NOW - timedelta(hours=1)),
                make_run(10, "nightly_reconcile.yml", "Nightly Reconcile (content + price + orphans)", NOW - timedelta(hours=5)),
                make_run(9, "run_amazon.yml", "Amazon Sync (Keepa)", NOW - timedelta(hours=3), conclusion="failure"),
                make_run(8, "orders_lookup.yml", "Orders Lookup (read-only)", NOW - timedelta(hours=2), event="workflow_dispatch"),
                make_run(7, "backfill_onbuy_status.yml", "Backfill OnBuy Status", NOW - timedelta(hours=40)),
                make_run(31, "observed_fee_feedback.yml", "Observed Fee Feedback (orders -> Fee % overrides)", NOW - timedelta(days=2), event="workflow_dispatch"),
                make_run(32, "order_fee_probe.yml", "Order Fee Probe (read-only)", NOW - timedelta(days=2), event="workflow_dispatch"),
                make_run(33, "category_keyword_census.yml", "Category Keyword Census (read-only)", NOW - timedelta(days=2), event="workflow_dispatch"),
                make_run(34, "refresh_fees.yml", "Refresh OnBuy Commission Tables (read-only API)", NOW - timedelta(days=3), event="workflow_dispatch"),
                make_run(35, "store_sale.yml", "Store Sale (one click on / off)", NOW - timedelta(hours=2), event="workflow_dispatch"),
                make_run(36, "remove_wrong_content.yml", "Remove Wrong-Content Listings", NOW - timedelta(hours=3), event="workflow_dispatch"),
                make_run(37, "purge_dead_rows.yml", "Purge Dead eBay Rows (dry run / live)", NOW - timedelta(hours=4), event="workflow_dispatch"),
                make_run(40, "dup_removal.yml", "Duplicate Removal (sheet rows + OnBuy listings)", NOW - timedelta(hours=5), event="workflow_dispatch"),
                make_run(41, "dup_removal.yml", "Duplicate Removal (sheet rows + OnBuy listings)", NOW - timedelta(hours=6), event="workflow_dispatch"),
                make_run(50, "buybox_defense.yml", "Buy Box Defense", NOW - timedelta(hours=3), event="schedule"),
                make_run(51, "buybox_defense.yml", "Buy Box Defense", NOW - timedelta(hours=27), event="schedule"),
                make_run(52, "buybox_defense.yml", "Buy Box Defense", NOW - timedelta(hours=30), event="workflow_dispatch"),
                make_run(53, "buybox_defense.yml", "Buy Box Defense", NOW - timedelta(hours=51), event="schedule"),
                make_run(54, "buybox_defense.yml", "Buy Box Defense", NOW - timedelta(hours=75), event="schedule", conclusion="failure"),
                make_run(60, "delivery_templates.yml", "Delivery Templates (plan / test / apply)", NOW - timedelta(hours=2), event="workflow_dispatch"),
                make_run(61, "delivery_templates.yml", "Delivery Templates (plan / test / apply)", NOW - timedelta(hours=30), event="workflow_dispatch"),
                make_run(62, "delivery_templates.yml", "Delivery Templates (plan / test / apply)", NOW - timedelta(hours=50), event="workflow_dispatch"),
                make_run(63, "nightly_reconcile.yml", "Nightly Reconcile (content + price + orphans)", NOW - timedelta(hours=26)),
            ],
            "org/yra": [make_run(21, "run.yml", "YRA Full-Auto Sync", NOW - timedelta(hours=2))],
        }
        self.pending = {"org/gtv": [], "org/yra": []}
        self.in_progress = {"org/gtv": [], "org/yra": []}
        # run 7 is GTV's backfill: on GTV the nightly runs inside it, so its log carries the content scan
        self.logs = {7: NIGHTLY_LOG, 8: ORDERS_LOG, 10: NIGHTLY_LOG, 11: PURGE_LOG, 31: FEEDBACK_DRY_LOG, 32: PROBE_LOG, 33: CENSUS_LOG, 34: REFRESH_LOG, 35: SALE_PLAN_LOG,
                     36: REMOVAL_LOG, 37: PURGE_DRY_LOG, 38: REMOVAL_LIVE_LOG, 39: PURGE_SUSPENDED_LOG, 40: GUARDED_PLAN_LOG, 41: GUARDED_LIVE_LOG, 50: BUYBOX_LIVE_LOG, 51: BUYBOX_LIVE_LOG_2, 52: BUYBOX_DRY_LOG, 53: BUYBOX_OFF_LOG, 60: DELIVERY_PLAN_LOG, 61: DELIVERY_APPLY_LOG, 62: DELIVERY_TEST_LOG, 63: DELIVERY_NIGHTLY_LOG}
        self.commits = {("org/gtv", "onbuy_commission_tiers.csv"): {"sha": "60ef441", "date": "2026-09-09T11:40:00Z",
                                                                     "message": "OnBuy commission tables from the API (refresh_fees run 34346220435)",
                                                                     "url": "https://github.com/x/y/commit/60ef441"}}
        self.dispatched = []
        self.secrets = {"org/gtv": {"ONBUY_CONSUMER_KEY": "x", "ONBUY_SECRET_KEY": "x", "ONBUY_SELLER_ID": "x", "ONBUY_SITE_ID": "x", "GOOGLE_CREDENTIALS": "x", "KEEPA_API_KEY": "x"}}
        self.variables = {"org/gtv": [{"name": "FEE_MODE", "value": "category", "updated_at": "2026-10-01T00:00:00Z"},
                                      {"name": "ONBUY_API_PUSH_ENABLED", "value": "true", "updated_at": "2026-10-01T00:00:00Z"}], "org/yra": []}
        self.definitions = {
            "run.yml": {"file": "run.yml", "name": "Generate OnBuy Feed", "manual": True, "group": "onbuy-api", "schedule": ["7 * * * *"],
                        "scripts": ["generate_xml.py"], "inputs": {"rows": {"description": "rows", "default": "", "required": False, "type": "string", "options": []}}},
            "purge_dead_rows.yml": {"file": "purge_dead_rows.yml", "name": "Purge Dead eBay Rows (dry run / live)", "manual": True, "group": "onbuy-api",
                                    "schedule": [], "scripts": ["purge_dead_rows.py"],
                                    "inputs": {"dry_run": {"description": "yes/no", "default": "yes", "required": False, "type": "string", "options": []},
                                               "list_suspended": {"description": "yes = only list", "default": "no", "required": False, "type": "string", "options": []}}},
            "orders_lookup.yml": {"file": "orders_lookup.yml", "name": "Orders Lookup (read-only)", "manual": True, "group": "onbuy-api", "schedule": [],
                                  "scripts": ["orders_lookup.py"],
                                  "inputs": {"sku": {"description": "SKU", "default": "", "required": True, "type": "string", "options": []},
                                             "list_all": {"description": "yes", "default": "", "required": False, "type": "string", "options": []}}},
            "row_cells.yml": {"file": "row_cells.yml", "name": "Row Cells (read-only)", "manual": True, "group": "onbuy-api", "schedule": [], "scripts": [],
                              "inputs": {"skus": {"description": "SKUs", "default": "", "required": True, "type": "string", "options": []}}},
            "even_margins.yml": {"file": "even_margins.yml", "name": "Even Margins (dry run / apply)", "manual": True, "group": "", "schedule": [],
                                 "scripts": ["even_margins.py"],
                                 "inputs": {k: {"description": k, "default": d, "required": False, "type": "string", "options": []}
                                            for k, d in (("apply", "no"), ("tabs", ""), ("outlier_ratio", "2.0"), ("max_changes", "800"), ("schedule_json", ""))}},
            "audit_price_drift.yml": {"file": "audit_price_drift.yml", "name": "Audit Price Drift (report / fix)", "manual": True, "group": "onbuy-api",
                                      "schedule": [], "scripts": ["audit_price_drift.py"],
                                      "inputs": {"fix": {"description": "yes = fix", "default": "no", "required": False, "type": "string", "options": []}}},
            "remove_wrong_content.yml": {"file": "remove_wrong_content.yml", "name": "Remove Wrong-Content Listings (dry run / live)", "manual": True, "group": "onbuy-api",
                                         "schedule": [], "scripts": ["remove_wrong_content.py"],
                                         "inputs": {"skus": {"description": "SKUs", "default": "", "required": True, "type": "string", "options": []},
                                                    **{k: {"description": k, "default": d, "required": False, "type": "string", "options": []}
                                                       for k, d in (("backup_tab", "Removed"), ("max_remove", "40"), ("keep_at", "0.5"), ("dry_run", "yes"))}}},
            "dup_removal.yml": {"file": "dup_removal.yml", "name": "Duplicate Removal (sheet rows + OnBuy listings)", "manual": True, "group": "onbuy-api", "schedule": [],
                                "scripts": ["guarded_remove_rows.py", "delete_listings_batch.py"],
                                "inputs": {k: {"description": k, "default": d, "required": False, "type": "string", "options": []}
                                           for k, d in (("oos_list_file", ""), ("allow_in_stock", "no"), ("remove_live_dups", "yes"), ("remove_dead_copies", "no"), ("require_keeper_synced", "yes"),
                                                        ("dup_list_file", ""), ("exclude_file", ""), ("max_remove", "200"), ("backup_tab", "Removed 2026-10-05"), ("dry_run", "yes"))}},
            "buybox_defense.yml": {"file": "buybox_defense.yml", "name": "Buy Box Defense", "manual": True, "group": "onbuy-api", "schedule": ["17 4 * * *"],
                                   "scripts": ["buybox_defense.py"],
                                   "inputs": {k: {"description": k, "default": d, "required": False, "type": "string", "options": []}
                                              for k, d in (("dry_run", "yes"), ("undercut_pence", ""), ("profit_percent", ""), ("check_batch", "100"))}},
            "delivery_templates.yml": {"file": "delivery_templates.yml", "name": "Delivery Templates (plan / test / apply)", "manual": True, "group": "onbuy-api", "schedule": [],
                                       "scripts": ["delivery_templates.py"],
                                       "inputs": {k: {"description": k, "default": d, "required": False, "type": "string", "options": []}
                                                  for k, d in (("mode", "plan"), ("template_ebay", ""), ("template_amazon", ""), ("template_ali", ""), ("test_sku", ""), ("max_changes", "3000"), ("clear_handling", "no"))}},
            "zero_listings.yml": {"file": "zero_listings.yml", "name": "Zero Named Listings (cheap)", "manual": True, "group": "onbuy-api", "schedule": [],
                                  "scripts": ["zero_listings.py"],
                                  "inputs": {"skus": {"description": "SKUs", "default": "", "required": True, "type": "string", "options": []},
                                             "dry_run": {"description": "yes = report only", "default": "yes", "required": False, "type": "string", "options": []}}},
        }
        for file, name, group, inputs in (
                ("observed_fee_feedback.yml", "Observed Fee Feedback (orders -> Fee % overrides)", "onbuy-api", (("apply", ""), ("days", "90"), ("max_pages", "30"), ("only_skus", ""))),
                ("order_fee_probe.yml", "Order Fee Probe (read-only)", "onbuy-api", (("skus", ""), ("days", "30"), ("status", "all"), ("keys", ""), ("max_pages", "30"))),
                ("category_keyword_census.yml", "Category Keyword Census (read-only)", "", (("keywords", ""), ("show", "400"))),
                ("set_category_by_keyword.yml", "Set Category By Keyword (sheet only)", "", (("apply", ""), ("rules", ""), ("only_from", ""))),
                ("refresh_fees.yml", "Refresh OnBuy Commission Tables (read-only API)", "onbuy-api", (("commit", "no"),)),
                ("price_impact_report.yml", "Price Impact of Category Fees (read-only)", "", (("tier_mode", "marginal"),)),
                ("store_sale.yml", "Store Sale (one click on / off)", "onbuy-api",
                 (("mode", "plan"), ("percent", ""), ("sale_end", ""), ("min_profit", "10"), ("floor_mode", "skip"), ("scope", "all"), ("price_ranges", ""),
                  ("exclude_price_from", ""), ("exclude_price_to", ""), ("test_sku", ""), ("max_changes", "0")))):
            self.definitions[file] = {"file": file, "name": name, "manual": True, "group": group, "schedule": [], "scripts": [file.replace(".yml", ".py")],
                                      "inputs": {k: {"description": k, "default": d, "required": False, "type": "string", "options": []} for k, d in inputs}}
        self.files = {("org/gtv", "pricing.py"): GTV_PRICING_SOURCE, ("org/yra", "pricing.py"): FLAT_PRICING_SOURCE,
                      ("org/gtv", "onbuy_commission_tiers.csv"): TIERS_CSV, ("org/gtv", "onbuy_category_tiers.csv"): CATEGORY_TIERS_CSV,
                      ("org/gtv", "set_category_by_keyword.py"): RELABEL_SOURCE,
                      ("org/gtv", "store_sale.json"): json.dumps(SALE_STATE_LEGACY),
                      ("org/gtv", ".github/workflows/delivery_templates.yml"): DELIVERY_WORKFLOW_FALLBACKS, ("org/yra", ".github/workflows/delivery_templates.yml"): DELIVERY_WORKFLOW_BARE,
                      ("org/gtv", "hold_at_zero_skus.txt"): HOLD_TEXT, ("org/gtv", "protected_skus.txt"): PROTECTED_TEXT, ("org/gtv", "same_product_skus.txt"): SAME_TEXT}
        for file, name, group, inputs in (
                ("image_links_export.yml", "Image Links Export (read-only)", "", (("sku_file", "cleanup/image_ticket_skus_2026-10-03.txt"),)),
                ("repair_shifted_content.yml", "Repair Shifted Content (one-off)", "onbuy-api", (("dry_run", "yes"), ("repair_limit", "0"), ("repair_skus", ""), ("only_listed", "no"), ("tab", "")))):
            self.definitions[file] = {"file": file, "name": name, "manual": True, "group": group, "schedule": [], "scripts": [file.replace(".yml", ".py")],
                                      "inputs": {k: {"description": k, "default": d, "required": False, "type": "string", "options": []} for k, d in inputs}}
        self.definitions["listing_lookup.yml"] = {"file": "listing_lookup.yml", "name": "Listing Lookup (read-only)", "manual": True, "group": "onbuy-api", "schedule": [], "scripts": ["listing_lookup.py"],
                                                  "inputs": {"skus": {"description": "Comma-separated SKUs to look up", "default": "", "required": True, "type": "string", "options": []}}}
        self.definitions["run_amazon.yml"] = {"file": "run_amazon.yml", "name": "Amazon Sync (Keepa)", "manual": True, "group": "onbuy-api", "schedule": ["13 0-20/4 * * *"], "scripts": ["generate_xml.py"],
                                              "inputs": {k: {"description": k, "default": "no" if k == "recategorize" else "", "required": False, "type": "string", "options": []}
                                                         for k in ("recategorize", "refresh_all", "rows")}}
        self.definitions["amazon_seller_census.yml"] = {"file": "amazon_seller_census.yml", "name": "Amazon Seller Census (read-only)", "manual": True, "group": "", "schedule": [],
                                                        "scripts": ["amazon_seller_census.py"], "inputs": {"sample": {"description": "examples per seller", "default": "15", "required": False, "type": "string", "options": []}}}
        self.files[("org/gtv", ".github/workflows/run_amazon.yml")] = AMAZON_WORKFLOW_TEXT
        self.edits = []          # (repo, path, commit message) of every update_file that changed something
        self.artifacts = {}      # run id -> [{id, name, size, expired}]
        self.artifact_zips = {}  # artifact id -> the zip's bytes
        self.script = {}         # run id -> states the run goes through, one per look at it: [{"status": "in_progress"}, {"status": "completed", "conclusion": "success"}]
        self.on_dispatch = None  # called as on_dispatch(fake, repo, workflow_file, inputs, run) right after a dispatch: a test makes the run do what it should
        self.workflow_states = {}  # (repo, path) -> state; anything absent lists as "active"
        self.fail_repo = None

    def last_commit(self, repo, path, ref="main"):
        self._check(repo)
        return self.commits.get((repo, path))

    def get_file(self, repo, path, ref="main", fresh=False):
        self._check(repo)
        try:
            return self.files[(repo, path)]
        except KeyError:
            raise GitHubError("GitHub answered 404: Not Found", 404)

    def update_file(self, repo, path, transform, message, ref="main", attempts=3):
        self._check(repo)
        text = self.files.get((repo, path), "")
        new = transform(text)
        if new == text:
            return {"changed": False, "commit": "", "url": ""}
        self.files[(repo, path)] = new
        self.edits.append((repo, path, message))
        sha = f"c{len(self.edits):06d}"
        return {"changed": True, "commit": sha, "url": f"https://github.com/x/y/commit/{sha}"}

    def _check(self, repo):
        if repo == self.fail_repo:
            raise GitHubError("GitHub answered 401: Bad credentials", 401)

    def whoami(self):
        return {"login": "tester", "name": ""}

    def repo_ok(self, repo):
        return (True, "ok") if repo != self.fail_repo else (False, "no access")

    def list_runs(self, repo, limit=100, since=None, workflow=None):
        self._check(repo)
        runs = [r for r in self.runs.get(repo, []) if not workflow or r["path"] == workflow]
        if since:
            since_iso = since if isinstance(since, str) else iso(since)
            runs = [r for r in runs if r["created_at"] >= since_iso]
        return runs[:limit]

    def queue(self, repo):
        self._check(repo)
        return {"in_progress": list(self.in_progress.get(repo, [])), "pending": list(self.pending.get(repo, []))}

    def run(self, repo, run_id):
        for r in self.runs.get(repo, []):
            if r["id"] == run_id:
                if self.script.get(run_id):
                    r.update(self.script[run_id].pop(0))                  # a scripted run changes state each time somebody looks at it
                return r
        raise GitHubError("GitHub answered 404: Not Found", 404)

    def list_dir(self, repo, path, ref="main"):
        self._check(repo)
        prefix = path.strip("/") + "/"
        return [{"name": p[len(prefix):], "path": p, "type": "file"} for (r, p) in sorted(self.files) if r == repo and p.startswith(prefix) and "/" not in p[len(prefix):]]

    def run_artifacts(self, repo, run_id):
        self._check(repo)
        return list(self.artifacts.get(run_id, []))

    def download_artifact(self, repo, artifact_id, max_bytes=30_000_000):
        self._check(repo)
        if artifact_id not in self.artifact_zips:
            raise GitHubError("GitHub answered 404: Not Found", 404)
        return self.artifact_zips[artifact_id]

    def run_log(self, repo, run_id):
        return self.logs.get(run_id, "")

    def list_secrets(self, repo):
        self._check(repo)
        return sorted(({"name": n, "updated_at": "2026-10-31T00:00:00Z"} for n in self.secrets.get(repo, ())), key=lambda s: s["name"])

    def set_secret(self, repo, name, value):
        self._check(repo)
        self.secrets.setdefault(repo, {})[name] = value          # kept so a test can prove the CLIENT saw the value while nothing else did
        return True

    def dispatch(self, repo, workflow_file, inputs=None, ref="main"):
        self._check(repo)
        self.dispatched.append((repo, workflow_file, dict(inputs or {}), ref))
        new = make_run(100 + len(self.dispatched), workflow_file, self.definitions.get(workflow_file, {}).get("name", workflow_file),
                       NOW, status="queued", conclusion="", event="workflow_dispatch")
        self.runs.setdefault(repo, []).insert(0, new)
        if self.on_dispatch:
            self.on_dispatch(self, repo, workflow_file, dict(inputs or {}), new)
        return NOW

    def find_dispatched_run(self, repo, workflow_file, started, attempts=8, wait=5):
        for r in self.runs.get(repo, []):
            if r["path"] == workflow_file and r["event"] == "workflow_dispatch" and r["status"] == "queued":
                return r
        return None

    def list_workflows(self, repo):
        self._check(repo)
        return [{"id": i, "name": d["name"], "path": f, "state": self.workflow_states.get((repo, f), "active")}
                for i, (f, d) in enumerate(self.definitions.items(), 1)]

    def set_workflow_state(self, repo, workflow_file, enabled):
        self._check(repo)
        self.workflow_states[(repo, workflow_file)] = "active" if enabled else "disabled_manually"
        return True

    def workflow_definition(self, repo, workflow_file, ref="main"):
        self._check(repo)
        if workflow_file not in self.definitions:
            raise GitHubError("GitHub answered 404: Not Found", 404)
        return self.definitions[workflow_file]

    def list_variables(self, repo):
        self._check(repo)
        return list(self.variables.get(repo, []))

    def set_variable(self, repo, name, value):
        self._check(repo)
        vals = self.variables.setdefault(repo, [])
        for v in vals:
            if v["name"] == name:
                v["value"] = value
                return True
        vals.append({"name": name, "value": value, "updated_at": iso(NOW)})
        return True


@pytest.fixture
def stores():
    return [Store(id="gtv", name="GTV", repo="org/gtv", sheet="OnBuy_Feed_Master"),
            Store(id="yra", name="YRA", repo="org/yra", sheet="YRA_Full_Feed_Master")]


@pytest.fixture
def settings(stores, tmp_path):
    return Settings(github_token="t", stores=stores, data_dir=tmp_path, stores_file=tmp_path / "stores.json")


@pytest.fixture
def fake():
    return FakeGitHub()


@pytest.fixture
def db():
    return Database(":memory:")


@pytest.fixture
def jobs():
    return Jobs(inline=True)                  # a background job runs to its end inside the request that starts it


@pytest.fixture
def links():
    return Links()


@pytest.fixture
def app(settings, fake, db, jobs, links):
    return create_app(settings=settings, client=fake, database=db, jobs=jobs, link_fetch=links, sleep=lambda seconds: None)


@pytest.fixture
def web(app):
    from fastapi.testclient import TestClient
    return TestClient(app)
