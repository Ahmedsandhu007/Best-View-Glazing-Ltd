"""REAL log excerpts of the stores' hourly eBay syncs (run.yml) of 2026-10-28, cut from the runs' logs by a script (nothing typed in by hand): GTV 40613453450 (01:10Z), YRA 40609999079 (00:38Z,
a batch of 1,499 rows, 672 rows with no supplier link, 16 dead rows purged), Arden 40613751879 (01:14Z), Makstore 40637692083 (05:23Z: the batch was CUT from 1,091 to 560 to stay inside eBay's
daily allowance, 9 purged listings suspended on OnBuy) and OpenMaal 40643333169 (06:21Z: 1,075 of 1,230 rows in one run)."""

GTV_LOG = '''2026-10-28 01:11:12,239 INFO TOTAL ROWS IN SHEET: 4440
2026-10-28 01:11:12,295 INFO Batch size: 740 products/run (budget 4800 eBay calls/day over 24 runs/day) - a full refresh cycle over 4440 rows takes ~0.2 day(s)
2026-10-28 01:11:15,433 INFO Skipping 475 row(s) with no eBay/Amazon Supplier URL yet (not counted against this run's batch)
2026-10-28 01:11:15,477 INFO Rotation: scored by age x risk - 3798 live in-stock row(s), 2 out of stock, 2 flagged and not live (low weight)
2026-10-28 01:11:15,477 INFO Processing 740 products
2026-10-28 01:11:16,211 INFO eBay allowance: 1780 call(s) left in today's window (reserve 150)
2026-10-28 01:26:00,379 INFO Updated rows: 740
2026-10-28 01:26:00,379 INFO Pricing: 733 row(s) priced with their category's commission, 5 formula price(s) followed it down
2026-10-28 01:26:00,379 INFO eBay delivery cost: 714 free, 26 paid (fee GBP mean 4.65, median 3.99, p90 7.50, max 19.99), 0 not stated by eBay (cell left as it was); 1 Shipping Cost cell(s) written
2026-10-28 01:26:00,379 INFO OnBuy: 0 created, 179 updated, 19 deferred (awaiting go-live), 0 postponed (transient), 0 failed, 0 removed (brand rejected), 0 brand-blocked (flagged), 0 skipped (dead eBay link), 0 awaiting category (worklist), 0 suspended-locked, 0 no-price skipped, 1 protected (repair pending), 0 creates paused
LIVE RUN | tab 'Sheet1' | kinds brand,oos | max 200 rows, 150 eBay checks
eBay tab: 4440 rows | looking dead: brand-blocked 0, out of stock 0 | held back 2
  held     1  oos: protected listing (protected_skus.txt)
  held     1  oos: open order (awaiting dispatch)
TO DELETE THIS RUN: 0 row(s) (brand 0, out of stock 0; 0 marked live on OnBuy)
'''

YRA_LOG = '''2026-10-28 00:38:31,265 INFO TOTAL ROWS IN SHEET: 7001
2026-10-28 00:38:31,318 INFO Batch size: 1499 products/run (budget 4800 eBay calls/day over 24 runs/day) - a full refresh cycle over 7001 rows takes ~0.2 day(s)
2026-10-28 00:38:40,332 INFO Skipping 672 row(s) with no eBay/Amazon Supplier URL yet (not counted against this run's batch)
2026-10-28 00:38:40,409 INFO Rotation: scored by age x risk - 6069 live in-stock row(s), 2 out of stock, 229 flagged and not live (low weight)
2026-10-28 00:38:40,409 INFO Processing 1499 products
2026-10-28 00:38:41,168 INFO eBay allowance: 1690 call(s) left in today's window (reserve 150)
2026-10-28 01:17:02,560 INFO Updated rows: 1499
2026-10-28 01:17:02,560 INFO Pricing: 1496 row(s) priced with their category's commission, 7 formula price(s) followed it down
2026-10-28 01:17:02,560 INFO eBay delivery cost: 1471 free, 9 paid (fee GBP mean 1.77, median 0.99, p90 3.99, max 3.99), 3 not stated by eBay (cell left as it was); 0 Shipping Cost cell(s) written
2026-10-28 01:17:02,560 INFO OnBuy: 13 created, 182 updated, 2 deferred (awaiting go-live), 0 postponed (transient), 0 failed, 0 removed (brand rejected), 0 brand-blocked (flagged), 0 skipped (dead eBay link), 0 awaiting category (worklist), 0 suspended-locked, 0 no-price skipped, 0 protected (repair pending), 0 creates paused
LIVE RUN | tab 'Sheet1' | kinds brand,oos | max 200 rows, 150 eBay checks
eBay tab: 7000 rows | looking dead: brand-blocked 0, out of stock 17 | held back 1
  held     1  oos: open order (awaiting dispatch)
eBay confirmation of the out-of-stock rows: gone 16, alive again 1, unknown 0 (17 call(s)), not looked at this run 0
TO DELETE THIS RUN: 16 row(s) (brand 0, out of stock 16; 16 marked live on OnBuy)
DELETED 16 row(s) from the sheet (0 kept for the next run, 0 skipped at deletion time: [])
PURGE DONE: 16 row(s) removed (brand 0, out of stock 16); suspended on OnBuy 0; OnBuy errors 0
'''

ARDEN_LOG = '''2026-10-28 01:14:07,662 INFO TOTAL ROWS IN SHEET: 7143
2026-10-28 01:14:07,732 INFO Batch size: 738 products/run (budget 4800 eBay calls/day over 24 runs/day) - a full refresh cycle over 7143 rows takes ~0.4 day(s)
2026-10-28 01:14:11,332 INFO Skipping 161 row(s) with no eBay/Amazon Supplier URL yet (not counted against this run's batch)
2026-10-28 01:14:11,387 INFO Rotation: scored by age x risk - 6879 live in-stock row(s), 4 out of stock, 97 flagged and not live (low weight)
2026-10-28 01:14:11,387 INFO Processing 738 products
2026-10-28 01:14:12,075 INFO eBay allowance: 1790 call(s) left in today's window (reserve 150)
2026-10-28 01:30:38,371 INFO Updated rows: 738
2026-10-28 01:30:38,371 INFO Pricing: 733 row(s) priced with their category's commission, 5 formula price(s) followed it down
2026-10-28 01:30:38,371 INFO eBay delivery cost: 723 free, 4 paid (fee GBP mean 24.23, median 44.95, p90 50.00, max 50.00), 0 not stated by eBay (cell left as it was); 2 Shipping Cost cell(s) written
2026-10-28 01:30:38,371 INFO OnBuy: 0 created, 196 updated, 3 deferred (awaiting go-live), 0 postponed (transient), 0 failed, 0 removed (brand rejected), 0 brand-blocked (flagged), 0 skipped (dead eBay link), 0 awaiting category (worklist), 0 suspended-locked, 0 no-price skipped, 0 protected (repair pending), 0 creates paused
LIVE RUN | tab 'Sheet1' | kinds brand,oos | max 200 rows, 150 eBay checks
eBay tab: 7139 rows | looking dead: brand-blocked 0, out of stock 15 | held back 0
eBay confirmation of the out-of-stock rows: gone 11, alive again 4, unknown 0 (15 call(s)), not looked at this run 0
TO DELETE THIS RUN: 11 row(s) (brand 0, out of stock 11; 11 marked live on OnBuy)
DELETED 11 row(s) from the sheet (0 kept for the next run, 0 skipped at deletion time: [])
PURGE DONE: 11 row(s) removed (brand 0, out of stock 11); suspended on OnBuy 0; OnBuy errors 0
'''

MAKSTORE_LOG = '''2026-10-28 05:23:37,099 INFO TOTAL ROWS IN SHEET: 6682
2026-10-28 05:23:37,156 INFO Batch size: 1091 products/run (budget 4800 eBay calls/day over 24 runs/day) - a full refresh cycle over 6682 rows takes ~0.3 day(s)
2026-10-28 05:23:39,931 INFO Skipping 76 row(s) with no eBay/Amazon Supplier URL yet (not counted against this run's batch)
2026-10-28 05:23:40,009 INFO Rotation: scored by age x risk - 6554 live in-stock row(s), 2 out of stock, 50 flagged and not live (low weight)
2026-10-28 05:23:40,009 INFO Processing 1091 products
2026-10-28 05:23:41,353 INFO eBay allowance: 710 call(s) left in today's window (reserve 150)
2026-10-28 05:23:41,354 WARNING Batch cut from 1091 to 560 row(s) to stay inside eBay's daily allowance
2026-10-28 05:39:14,110 INFO Updated rows: 560
2026-10-28 05:39:14,110 INFO Pricing: 550 row(s) priced with their category's commission, 1 formula price(s) followed it down
2026-10-28 05:39:14,110 INFO eBay delivery cost: 545 free, 3 paid (fee GBP mean 23.22, median 20.99, p90 44.95, max 44.95), 0 not stated by eBay (cell left as it was); 0 Shipping Cost cell(s) written
2026-10-28 05:39:14,110 INFO OnBuy: 3 created, 183 updated, 13 deferred (awaiting go-live), 0 postponed (transient), 0 failed, 0 removed (brand rejected), 0 brand-blocked (flagged), 0 skipped (dead eBay link), 0 awaiting category (worklist), 0 suspended-locked, 0 no-price skipped, 0 protected (repair pending), 0 creates paused
LIVE RUN | tab 'Sheet1' | kinds brand,oos | max 200 rows, 150 eBay checks
eBay tab: 6672 rows | looking dead: brand-blocked 0, out of stock 14 | held back 0
eBay confirmation of the out-of-stock rows: gone 9, alive again 5, unknown 0 (14 call(s)), not looked at this run 0
TO DELETE THIS RUN: 9 row(s) (brand 0, out of stock 9; 9 marked live on OnBuy)
DELETED 9 row(s) from the sheet (0 kept for the next run, 0 skipped at deletion time: [])
SUSPENDED 385476307274  Bluetooth Ceiling Speaker Set - A100B with 4x FCS5 with Fire
SUSPENDED 401168481814  4-Zone Multi Room Ceiling Speaker System PV240BT Bluetooth A
SUSPENDED 403420955811  3 Tier End Table Narrow Side Table with Uk-Plug Charging Sta
SUSPENDED 415709850991  Opticron 8 x 42 Oregon 4 PC Oasis Waterproof Monocular # 307
SUSPENDED 419004782247  ZIMX HB1 Plus - Black Hoverboard with LED Wheels UL2272 + HK
SUSPENDED 419015802736  ZIMX HB1 Plus - Blue Hoverboard with LED Wheels UL2272 + HK5
SUSPENDED 419301689003  ZIMX HB1 Plus - Pink Hoverboard with LED Wheels UL2272 + HK5
SUSPENDED 419400576051  ZIMX HB1 Plus - Purple Hoverboard with LED Wheels UL2272 + H
SUSPENDED 428305113773  2x D3S LED Xenon Headlight Bulbs Hi Low Beam Replacement 200
PURGE DONE: 9 row(s) removed (brand 0, out of stock 9); suspended on OnBuy 9; OnBuy errors 0
'''

OPENMAAL_LOG = '''2026-10-28 06:21:41,520 INFO TOTAL ROWS IN SHEET: 1232
2026-10-28 06:21:41,578 INFO Batch size: 1075 products/run (budget 4800 eBay calls/day over 24 runs/day) - a full refresh cycle over 1232 rows takes ~0.1 day(s)
2026-10-28 06:21:44,412 INFO Skipping 2 row(s) with no eBay/Amazon Supplier URL yet (not counted against this run's batch)
2026-10-28 06:21:44,427 INFO Rotation: scored by age x risk - 1230 live in-stock row(s), 0 out of stock, 0 flagged and not live (low weight)
2026-10-28 06:21:44,427 INFO Processing 1075 products
2026-10-28 06:21:45,054 INFO eBay allowance: 1390 call(s) left in today's window (reserve 150)
2026-10-28 06:45:16,734 INFO Updated rows: 1075
2026-10-28 06:45:16,734 INFO Pricing: 1075 row(s) priced with their category's commission, 0 formula price(s) followed it down
2026-10-28 06:45:16,734 INFO eBay delivery cost: 1040 free, 23 paid (fee GBP mean 2.99, median 2.99, p90 2.99, max 2.99), 12 not stated by eBay (cell left as it was); 0 Shipping Cost cell(s) written
2026-10-28 06:45:16,734 INFO OnBuy: 0 created, 196 updated, 0 deferred (awaiting go-live), 0 postponed (transient), 0 failed, 0 removed (brand rejected), 0 brand-blocked (flagged), 0 skipped (dead eBay link), 0 awaiting category (worklist), 0 suspended-locked, 0 no-price skipped, 3 protected (repair pending), 0 creates paused
LIVE RUN | tab 'Sheet1' | kinds brand,oos | max 200 rows, 150 eBay checks
eBay tab: 1231 rows | looking dead: brand-blocked 0, out of stock 0 | held back 0
TO DELETE THIS RUN: 0 row(s) (brand 0, out of stock 0; 0 marked live on OnBuy)
nothing to purge
'''
