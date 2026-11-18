"""REAL log excerpts for the Amazon card's parser tests (cut from the runs' logs by a script, nothing typed in by hand):
MAKSTORE_LOG = the Amazon sync of Makstore 2026-10-27 09:21Z (run 40480177484, prefetch + sync jobs: Keepa waiting for its refill, the second looks, the guards' UNAVAILABLE lines, the
price sources, the OnBuy summary and a spread of re-derived prices with the run's biggest fall and rise), YRA_FAILED_LOG = YRA's run of 2026-10-26 20:59Z that ran out of Keepa tokens
(run 40400505100), OPENMAAL_LOG = OpenMaal's single-job run of 2026-10-27 09:17Z (run 40479631076), ONE_ROW_LOG = a manual run for ONE row (YRA 2026-10-27 11:38Z, run 40497632696: the dishwasher's activation), NEGATIVE_BALANCE_LOG = YRA's sync of 2026-10-27 20:39Z (run 40580046978) whose Keepa balance went NEGATIVE ("-108 left") and ended at -77, CENSUS_LOG = Makstore's seller census of 2026-10-27 07:05Z (run 40465041462)."""

MAKSTORE_LOG = '''2026-10-27 09:21:58,755 INFO TOTAL ROWS IN SHEET: 3205
2026-10-27 09:21:58,755 INFO Batch size: 1600 products/run (budget 4800 eBay calls/day over 12 runs/day) - a full refresh cycle over 3205 rows takes ~0.2 day(s)
2026-10-27 09:21:58,908 INFO Processing 1600 products
2026-10-27 09:22:21,686 INFO Keepa: 124 token(s) used, 1076 left, refill 20/min
2026-10-27 09:22:26,323 INFO Keepa: 122 token(s) used, 954 left, refill 20/min
2026-10-27 09:22:29,131 INFO Keepa: 120 token(s) used, 834 left, refill 20/min
2026-10-27 09:22:32,126 INFO Keepa: 121 token(s) used, 713 left, refill 20/min
2026-10-27 09:22:35,789 INFO Keepa: 122 token(s) used, 591 left, refill 20/min
2026-10-27 09:22:38,272 INFO Keepa: 124 token(s) used, 467 left, refill 20/min
2026-10-27 09:22:40,603 INFO Keepa: 115 token(s) used, 352 left, refill 20/min
2026-10-27 09:22:42,946 INFO Keepa: 116 token(s) used, 236 left, refill 20/min
2026-10-27 09:22:45,647 INFO Keepa: 119 token(s) used, 117 left, refill 20/min
2026-10-27 09:22:45,648 INFO Keepa: 117 token(s) left, 200 needed - waiting 302s for the refill (20/min)
2026-10-27 09:27:53,346 INFO Keepa: 115 token(s) used, 102 left, refill 20/min
2026-10-27 09:27:53,348 INFO Keepa: 102 token(s) left, 200 needed - waiting 302s for the refill (20/min)
2026-10-27 09:32:58,706 INFO Keepa: 112 token(s) used, 110 left, refill 20/min
2026-10-27 09:32:58,707 INFO Keepa: 110 token(s) left, 200 needed - waiting 302s for the refill (20/min)
2026-10-27 09:38:04,342 INFO Keepa: 113 token(s) used, 97 left, refill 20/min
2026-10-27 09:38:04,343 INFO Keepa: 97 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-27 09:44:08,827 INFO Keepa: 115 token(s) used, 102 left, refill 20/min
2026-10-27 09:44:08,829 INFO Keepa: 102 token(s) left, 200 needed - waiting 302s for the refill (20/min)
2026-10-27 09:49:14,105 INFO Keepa: 113 token(s) used, 89 left, refill 20/min
2026-10-27 09:49:14,107 INFO Keepa: 89 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-27 09:55:18,491 INFO Keepa: 112 token(s) used, 97 left, refill 20/min
2026-10-27 09:55:18,492 INFO Keepa: 97 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-27 10:01:24,113 INFO Keepa: 111 token(s) used, 106 left, refill 20/min
2026-10-27 10:01:24,136 INFO Keepa cache: 0 of 1600 ASIN(s) answered from the cache, 1600 fetched live
2026-10-27 10:01:24,136 INFO Keepa: 1600 of 1600 ASIN(s) answered, 1874 token(s) used, 106 left
2026-10-27 10:01:27,257 INFO Keepa: 67 token(s) used, 39 left, refill 20/min
2026-10-27 10:01:27,259 INFO Keepa real-price lookup: 17 product(s) flagged, 17 looked up with the Buy Box detail
2026-10-27 10:01:29,429 INFO Keepa cache: 1600 answer(s) for 1600 ASIN(s) stored (3035 KB)
2026-10-27 10:01:29,431 INFO Keepa prefetch done: 1600 ASIN(s) answered, 1941 token(s) used - no OnBuy contact, no sheet writes
2026-10-27 10:01:49,705 INFO TOTAL ROWS IN SHEET: 3205
2026-10-27 10:01:49,706 INFO Batch size: 1600 products/run (budget 4800 eBay calls/day over 12 runs/day) - a full refresh cycle over 3205 rows takes ~0.2 day(s)
2026-10-27 10:01:50,642 INFO OOS pass: 4 out-of-stock row(s) with a stale OnBuy push
2026-10-27 10:03:27,464 INFO OOS pass: 1 row(s) skipped - no usable price on row or listing
2026-10-27 10:03:29,797 INFO OOS pass: 3 zeroed on OnBuy, 0 bounced
2026-10-27 10:03:32,391 INFO Processing 1600 products
2026-10-27 10:03:48,158 INFO Keepa cache: 1600 of 1600 ASIN(s) answered from the cache, 0 fetched live
2026-10-27 10:03:48,158 INFO Keepa: 1600 of 1600 ASIN(s) answered, 0 token(s) used, None left
2026-10-27 10:05:01,010 INFO UNAVAILABLE: B0121HQQZM (Back-order (Amazon's own offer only))
2026-10-27 10:05:17,144 INFO UNAVAILABLE: B00EMX3CM4 (Back-order (Amazon's own offer only))
2026-10-27 10:05:18,606 INFO UNAVAILABLE: B07DC4G12S (Back-order (Amazon's own offer only))
2026-10-27 10:10:19,922 INFO UNAVAILABLE: B08PL4XKKR (Delayed (Amazon's own offer only))
2026-10-27 10:13:00,160 INFO UNAVAILABLE: B07N69DT9R (Delayed (Amazon's own offer only))
2026-10-27 10:14:39,309 INFO UNAVAILABLE: B08N4F8WX8 (Delayed (Amazon's own offer only))
2026-10-27 10:15:41,794 INFO UNAVAILABLE: B0DW8WW8VB (No Amazon offer)
2026-10-27 10:17:49,504 INFO UNAVAILABLE: B0GY5LWSR9 (Delayed (Amazon's own offer only))
2026-10-27 10:18:24,281 INFO UNAVAILABLE: B003H1CWPU (Delayed (Amazon's own offer only))
2026-10-27 10:20:05,690 INFO UNAVAILABLE: B0H1RT2T4S (Delayed (Amazon's own offer only))
2026-10-27 10:20:48,865 INFO Amazon prices kept above the formula (set by hand): 9
2026-10-27 10:20:48,865 INFO Amazon prices taken from the usual level instead of a deal / voucher / sale price: 467
2026-10-27 10:20:48,865 INFO Amazon prices taken from the Buy Box because the cheapest-offer price was refused (phantom Amazon offer / error price): 8
2026-10-27 10:20:48,865 INFO OnBuy: 0 created, 195 updated, 2 deferred (awaiting go-live), 0 postponed (transient), 0 failed, 0 removed (brand rejected), 43 brand-blocked (flagged), 0 skipped (dead eBay link), 0 awaiting category (worklist), 0 suspended-locked, 0 no-price skipped, 1 protected (repair pending), 0 creates paused
2026-10-27 10:17:42,378 INFO Row 89 (SKU 327210340093): Amazon price re-derived from current cost: 227.65 -> 117.22
2026-10-27 10:20:10,114 INFO Row 966 (SKU 107035632319): Amazon price re-derived from current cost: 265.55 -> 265.53
2026-10-27 10:03:52,179 INFO Row 2466 (SKU 493955514973): Amazon price re-derived from current cost: 408.29 -> 373.64
2026-10-27 10:08:54,410 INFO Row 2510 (SKU 494515135300): Amazon price re-derived from current cost: 46.81 -> 42.44
2026-10-27 10:10:58,360 INFO Row 2337 (SKU 491602840482): Amazon price re-derived from current cost: 121.19 -> 121.07
2026-10-27 10:12:08,269 INFO Row 885 (SKU 105203200858): Amazon price re-derived from current cost: 99.31 -> 99.24
2026-10-27 10:13:03,637 INFO Row 1297 (SKU 436371190222): Amazon price re-derived from current cost: 39.39 -> 39.37
2026-10-27 10:14:08,920 INFO Row 1278 (SKU 436033547845): Amazon price re-derived from current cost: 67.32 -> 67.26
2026-10-27 10:14:53,107 INFO Row 3024 (SKU 729913852666): Amazon price re-derived from current cost: 668.27 -> 667.27
2026-10-27 10:15:52,206 INFO Row 1241 (SKU 435434676345): Amazon price re-derived from current cost: 129.20 -> 129.16
2026-10-27 10:17:20,740 INFO Row 350 (SKU 0300000049116-zzz-19): Amazon price re-derived from current cost: 25.42 -> 25.40
2026-10-27 10:18:46,325 INFO Row 291 (SKU 9172662224696-zzz-40): Amazon price re-derived from current cost: 72.62 -> 70.03
'''

YRA_FAILED_LOG = '''2026-10-26 20:59:48,130 INFO TOTAL ROWS IN SHEET: 3125
2026-10-26 20:59:48,130 INFO Batch size: 2275 products/run (budget 4800 eBay calls/day over 12 runs/day) - a full refresh cycle over 3125 rows takes ~0.2 day(s)
2026-10-26 20:59:50,542 INFO Processing 2275 products
2026-10-26 21:00:07,240 INFO Keepa: 130 token(s) used, 1070 left, refill 20/min
2026-10-26 21:00:09,621 INFO Keepa: 119 token(s) used, 951 left, refill 20/min
2026-10-26 21:00:14,033 INFO Keepa: 123 token(s) used, 828 left, refill 20/min
2026-10-26 21:00:17,072 INFO Keepa: 121 token(s) used, 707 left, refill 20/min
2026-10-26 21:00:19,125 INFO Keepa: 120 token(s) used, 587 left, refill 20/min
2026-10-26 21:00:22,302 INFO Keepa: 126 token(s) used, 461 left, refill 20/min
2026-10-26 21:00:26,174 INFO Keepa: 120 token(s) used, 341 left, refill 20/min
2026-10-26 21:00:29,536 INFO Keepa: 123 token(s) used, 238 left, refill 20/min
2026-10-26 21:00:32,956 INFO Keepa: 117 token(s) used, 121 left, refill 20/min
2026-10-26 21:00:32,957 INFO Keepa: 121 token(s) left, 200 needed - waiting 242s for the refill (20/min)
2026-10-26 21:04:37,438 INFO Keepa: 119 token(s) used, 82 left, refill 20/min
2026-10-26 21:04:37,439 INFO Keepa: 82 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-26 21:10:41,726 INFO Keepa: 121 token(s) used, 81 left, refill 20/min
2026-10-26 21:10:41,727 INFO Keepa: 81 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-26 21:16:46,707 INFO Keepa: 118 token(s) used, 83 left, refill 20/min
2026-10-26 21:16:46,708 INFO Keepa: 83 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-26 21:22:51,610 INFO Keepa: 120 token(s) used, 83 left, refill 20/min
2026-10-26 21:22:51,611 INFO Keepa: 83 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-26 21:28:56,167 INFO Keepa: 120 token(s) used, 83 left, refill 20/min
2026-10-26 21:28:56,168 INFO Keepa: 83 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-26 21:35:01,495 INFO Keepa: 116 token(s) used, 87 left, refill 20/min
2026-10-26 21:35:01,496 INFO Keepa: 87 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-26 21:41:06,803 INFO Keepa: 113 token(s) used, 94 left, refill 20/min
2026-10-26 21:41:06,804 INFO Keepa: 94 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-26 21:47:12,075 INFO Keepa: 119 token(s) used, 95 left, refill 20/min
2026-10-26 21:47:12,076 INFO Keepa: 95 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-26 21:53:16,593 INFO Keepa: 123 token(s) used, -29 left, refill 20/min
2026-10-26 21:53:16,594 INFO Keepa: -29 token(s) left, 200 needed - waiting 600s for the refill (20/min)
2026-10-26 22:03:18,994 INFO Keepa: 113 token(s) used, -67 left, refill 20/min
2026-10-26 22:03:18,995 INFO Keepa: -67 token(s) left, 200 needed - waiting 600s for the refill (20/min)
2026-10-26 22:13:21,397 INFO Keepa: 110 token(s) used, -100 left, refill 20/min
2026-10-26 22:13:21,398 INFO Keepa: -100 token(s) left, 200 needed - waiting 600s for the refill (20/min)
2026-10-26 22:23:21,838 INFO Keepa: 0 token(s) used, -24 left, refill 20/min
2026-10-26 22:23:41,101 INFO Keepa: 0 token(s) used, -4 left, refill 20/min
2026-10-26 22:24:45,813 INFO Keepa: 112 token(s) used, -96 left, refill 20/min
2026-10-26 22:24:45,814 INFO Keepa: -96 token(s) left, 200 needed - waiting 600s for the refill (20/min)
2026-10-26 22:34:46,213 INFO Keepa: 0 token(s) used, -14 left, refill 20/min
2026-10-26 22:35:45,920 INFO Keepa: 114 token(s) used, -108 left, refill 20/min
2026-10-26 22:35:45,921 INFO Keepa: -108 token(s) left, 32 needed - waiting 422s for the refill (20/min)
2026-10-26 22:42:48,382 INFO Keepa: 0 token(s) used, -94 left, refill 20/min
2026-10-26 22:43:45,655 INFO Keepa: 0 token(s) used, -74 left, refill 20/min
2026-10-26 22:44:47,955 INFO Keepa: 0 token(s) used, -54 left, refill 20/min
2026-10-26 22:45:51,708 INFO Keepa: 0 token(s) used, -34 left, refill 20/min
2026-10-26 22:46:42,709 ERROR Keepa fetch failed for 2216 ASIN(s) - Amazon rows left untouched this run: keepa product: out of tokens
2026-10-26 22:46:47,149 INFO OnBuy: 0 created, 0 updated, 0 deferred (awaiting go-live), 0 postponed (transient), 0 failed, 0 removed (brand rejected), 0 brand-blocked (flagged), 0 skipped (dead eBay link), 0 awaiting category (worklist), 0 suspended-locked, 0 no-price skipped, 0 protected (repair pending), 0 creates paused
'''

OPENMAAL_LOG = '''2026-10-27 09:17:31,325 INFO TOTAL ROWS IN SHEET: 49
2026-10-27 09:17:31,325 INFO Batch size: 300 products/run (budget 4800 eBay calls/day over 12 runs/day) - a full refresh cycle over 49 rows takes ~0.1 day(s)
2026-10-27 09:17:33,758 INFO Processing 49 products
2026-10-27 09:17:40,593 INFO Keepa: 49 token(s) used, 1151 left, refill 20/min
2026-10-27 09:17:40,594 INFO Keepa: 44 of 44 ASIN(s) answered, 49 token(s) used, 1151 left
2026-10-27 09:17:43,823 INFO UNAVAILABLE: B0DYNS37SW (No Amazon offer)
2026-10-27 09:17:58,269 INFO UNAVAILABLE: B08LQNL42Z (No Amazon offer)
2026-10-27 09:18:31,004 INFO UNAVAILABLE: B079QX3MWM (No Amazon offer)
2026-10-27 09:19:07,063 INFO Amazon prices taken from the usual level instead of a deal / voucher / sale price: 15
2026-10-27 09:19:07,063 INFO OnBuy: 0 created, 43 updated, 1 deferred (awaiting go-live), 0 postponed (transient), 0 failed, 0 removed (brand rejected), 0 brand-blocked (flagged), 0 skipped (dead eBay link), 0 awaiting category (worklist), 0 suspended-locked, 0 no-price skipped, 0 protected (repair pending), 0 creates paused
2026-10-27 09:18:55,802 INFO Row 30 (SKU 5051216849902 -sun): Amazon price re-derived from current cost: 78.56 -> 76.06
2026-10-27 09:18:01,414 INFO Row 31 (SKU 0718037855363kk): Amazon price re-derived from current cost: 147.35 -> 147.33
2026-10-27 09:17:53,668 INFO Row 18 (SKU MXZ-28-5051219781643): Amazon price re-derived from current cost: 45.04 -> 44.99
2026-10-27 09:18:23,879 INFO Row 2 (SKU 001B0C3HCD34R-nad-50): Amazon price re-derived from current cost: 55.54 -> 55.51
2026-10-27 09:18:33,967 INFO Row 14 (SKU 0050036409841kk): Amazon price re-derived from current cost: 114.98 -> 114.96
2026-10-27 09:18:49,456 INFO Row 16 (SKU 5051216758266kk): Amazon price re-derived from current cost: 50.66 -> 49.15
2026-10-27 09:18:50,951 INFO Row 17 (SKU MXZ-32.99-5051218445416): Amazon price re-derived from current cost: 49.79 -> 49.75
'''

ONE_ROW_LOG = '''2026-10-27 11:38:31,847 INFO TOTAL ROWS IN SHEET: 3119
2026-10-27 11:38:31,847 INFO Batch size: 2275 products/run (budget 4800 eBay calls/day over 12 runs/day) - a full refresh cycle over 3119 rows takes ~0.2 day(s)
2026-10-27 11:38:32,679 INFO Activation pass: 1 created-but-inactive row(s) pending
2026-10-27 11:38:34,931 INFO Activation pass: 1 activated, 0 awaiting addressability, 0 bounced to rotation
2026-10-27 11:38:34,950 INFO Processing 1 products
2026-10-27 11:38:39,426 INFO Keepa: 1 token(s) used, 1199 left, refill 20/min
2026-10-27 11:38:39,427 INFO Keepa: 1 of 1 ASIN(s) answered, 1 token(s) used, 1199 left
2026-10-27 11:38:46,898 INFO OnBuy: 0 created, 1 updated, 0 deferred (awaiting go-live), 0 postponed (transient), 0 failed, 0 removed (brand rejected), 0 brand-blocked (flagged), 0 skipped (dead eBay link), 0 awaiting category (worklist), 0 suspended-locked, 0 no-price skipped, 0 protected (repair pending), 0 creates paused
'''

NEGATIVE_BALANCE_LOG = '''2026-10-27 20:40:15,575 INFO TOTAL ROWS IN SHEET: 3119
2026-10-27 20:40:15,575 INFO Batch size: 2275 products/run (budget 4800 eBay calls/day over 12 runs/day) - a full refresh cycle over 3119 rows takes ~0.2 day(s)
2026-10-27 20:40:16,361 INFO OOS pass: 89 out-of-stock row(s) with a stale OnBuy push
2026-10-27 20:40:18,480 INFO OOS pass: 88 zeroed on OnBuy, 1 bounced
2026-10-27 20:40:20,458 INFO Activation pass: 17 created-but-inactive row(s) pending
2026-10-27 20:40:22,379 INFO Activation pass: 17 activated, 0 awaiting addressability, 0 bounced to rotation
2026-10-27 20:40:22,410 INFO Processing 2275 products
2026-10-27 20:40:46,228 INFO Keepa: 134 token(s) used, 1066 left, refill 20/min
2026-10-27 20:40:49,489 INFO Keepa: 120 token(s) used, 946 left, refill 20/min
2026-10-27 20:40:52,443 INFO Keepa: 129 token(s) used, 817 left, refill 20/min
2026-10-27 20:40:54,862 INFO Keepa: 128 token(s) used, 689 left, refill 20/min
2026-10-27 20:40:57,004 INFO Keepa: 122 token(s) used, 567 left, refill 20/min
2026-10-27 20:40:59,758 INFO Keepa: 125 token(s) used, 442 left, refill 20/min
2026-10-27 20:41:02,333 INFO Keepa: 131 token(s) used, 311 left, refill 20/min
2026-10-27 20:41:05,314 INFO Keepa: 124 token(s) used, 187 left, refill 20/min
2026-10-27 20:41:05,315 INFO Keepa: 187 token(s) left, 200 needed - waiting 62s for the refill (20/min)
2026-10-27 20:42:10,200 INFO Keepa: 119 token(s) used, 88 left, refill 20/min
2026-10-27 20:42:10,201 INFO Keepa: 88 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-27 20:48:14,891 INFO Keepa: 123 token(s) used, 85 left, refill 20/min
2026-10-27 20:48:14,893 INFO Keepa: 85 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-27 20:54:19,182 INFO Keepa: 125 token(s) used, 100 left, refill 20/min
2026-10-27 20:54:19,183 INFO Keepa: 100 token(s) left, 200 needed - waiting 302s for the refill (20/min)
2026-10-27 20:59:23,792 INFO Keepa: 124 token(s) used, 76 left, refill 20/min
2026-10-27 20:59:23,794 INFO Keepa: 76 token(s) left, 200 needed - waiting 422s for the refill (20/min)
2026-10-27 21:06:28,100 INFO Keepa: 119 token(s) used, 97 left, refill 20/min
2026-10-27 21:06:28,101 INFO Keepa: 97 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-27 21:12:32,432 INFO Keepa: 127 token(s) used, 90 left, refill 20/min
2026-10-27 21:12:32,434 INFO Keepa: 90 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-27 21:18:37,321 INFO Keepa: 129 token(s) used, 81 left, refill 20/min
2026-10-27 21:18:37,323 INFO Keepa: 81 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-27 21:24:41,349 INFO Keepa: 113 token(s) used, 88 left, refill 20/min
2026-10-27 21:24:41,350 INFO Keepa: 88 token(s) left, 200 needed - waiting 362s for the refill (20/min)
2026-10-27 21:30:49,773 INFO Keepa: 121 token(s) used, -37 left, refill 20/min
2026-10-27 21:30:49,775 INFO Keepa: -37 token(s) left, 200 needed - waiting 600s for the refill (20/min)
2026-10-27 21:40:53,155 INFO Keepa: 114 token(s) used, -71 left, refill 20/min
2026-10-27 21:40:53,156 INFO Keepa: -71 token(s) left, 200 needed - waiting 600s for the refill (20/min)
2026-10-27 21:50:56,372 INFO Keepa: 114 token(s) used, -108 left, refill 20/min
2026-10-27 21:50:56,373 INFO Keepa: -108 token(s) left, 200 needed - waiting 600s for the refill (20/min)
2026-10-27 22:00:56,714 INFO Keepa: 0 token(s) used, -34 left, refill 20/min
2026-10-27 22:01:31,906 INFO Keepa: 0 token(s) used, -14 left, refill 20/min
2026-10-27 22:02:36,038 INFO Keepa: 114 token(s) used, -108 left, refill 20/min
2026-10-27 22:02:36,039 INFO Keepa: -108 token(s) left, 200 needed - waiting 600s for the refill (20/min)
2026-10-27 22:12:36,379 INFO Keepa: 0 token(s) used, -35 left, refill 20/min
2026-10-27 22:13:32,902 INFO Keepa: 0 token(s) used, -15 left, refill 20/min
2026-10-27 22:14:38,766 INFO Keepa: 115 token(s) used, -110 left, refill 20/min
2026-10-27 22:14:38,768 INFO Keepa: -110 token(s) left, 200 needed - waiting 600s for the refill (20/min)
2026-10-27 22:24:39,087 INFO Keepa: 0 token(s) used, -30 left, refill 20/min
2026-10-27 22:25:35,840 INFO Keepa: 0 token(s) used, -10 left, refill 20/min
2026-10-27 22:26:40,581 INFO Keepa: 127 token(s) used, -117 left, refill 20/min
2026-10-27 22:26:40,582 INFO Keepa: -117 token(s) left, 150 needed - waiting 600s for the refill (20/min)
2026-10-27 22:36:40,926 INFO Keepa: 0 token(s) used, -28 left, refill 20/min
2026-10-27 22:37:38,826 INFO Keepa: 0 token(s) used, -8 left, refill 20/min
2026-10-27 22:38:43,226 INFO Keepa: 89 token(s) used, -77 left, refill 20/min
2026-10-27 22:38:43,228 INFO Keepa: 2275 of 2275 ASIN(s) answered, 2786 token(s) used, -77 left
2026-10-27 22:38:43,236 INFO Keepa: -77 token(s) left, 32 needed - waiting 362s for the refill (20/min)
2026-10-27 22:44:45,585 INFO Keepa: 0 token(s) used, -72 left, refill 20/min
2026-10-27 22:45:40,650 INFO Keepa: 0 token(s) used, -52 left, refill 20/min
2026-10-27 22:46:42,833 INFO Keepa: 0 token(s) used, -32 left, refill 20/min
2026-10-27 22:47:46,989 INFO Keepa: 0 token(s) used, -12 left, refill 20/min
2026-10-27 22:48:37,991 WARNING Keepa real-price lookup stopped (keepa product: out of tokens) - the products not looked up stay held
2026-10-27 22:48:37,992 INFO Keepa real-price lookup: 8 product(s) flagged, 0 looked up with the Buy Box detail
2026-10-27 22:48:42,015 INFO UNAVAILABLE: B0CD1NJBN2 (No Amazon offer)
2026-10-27 22:51:45,069 INFO UNAVAILABLE: B08M3CQQ8V (No Amazon offer)
2026-10-27 22:56:44,649 INFO UNAVAILABLE: B08HM4133L (Delayed (Amazon's own offer only))
2026-10-27 23:00:01,879 INFO UNAVAILABLE: B0DMFCVMRW (Delayed (Amazon's own offer only))
2026-10-27 23:01:20,260 INFO UNAVAILABLE: B0DSKDRJLW (Delayed (Amazon's own offer only))
2026-10-27 23:01:35,337 INFO UNAVAILABLE: B0DMTFH97X (Delayed (Amazon's own offer only))
2026-10-27 23:02:42,369 INFO UNAVAILABLE: B0CG6TF2QD (Delayed (Amazon's own offer only))
2026-10-27 23:03:36,926 INFO UNAVAILABLE: B0FBWLPMP2 (No Amazon offer)
2026-10-27 23:06:14,978 INFO UNAVAILABLE: B0H54YP772 (No Amazon offer)
2026-10-27 23:06:31,816 INFO UNAVAILABLE: B000GXZ2GS (Invalid or removed ASIN)
2026-10-27 23:07:24,395 INFO UNAVAILABLE: B0DR8S2DQY (Delayed (Amazon's own offer only))
2026-10-27 23:07:57,880 INFO UNAVAILABLE: B0HGL41GDX (No Amazon offer)
2026-10-27 23:08:29,552 INFO UNAVAILABLE: B0F13KXRG8 (Delayed (Amazon's own offer only))
2026-10-27 23:09:49,979 INFO UNAVAILABLE: B09QXP3K47 (Delayed (Amazon's own offer only))
2026-10-27 23:11:11,312 INFO Amazon prices kept above the formula (set by hand): 10
2026-10-27 23:11:11,312 INFO Amazon prices taken from the usual level instead of a deal / voucher / sale price: 754
2026-10-27 23:11:11,312 INFO OnBuy: 67 created, 129 updated, 0 deferred (awaiting go-live), 0 postponed (transient), 0 failed, 0 removed (brand rejected), 73 brand-blocked (flagged), 1 skipped (dead eBay link), 0 awaiting category (worklist), 0 suspended-locked, 0 no-price skipped, 0 protected (repair pending), 0 creates paused
2026-10-27 23:10:00,728 INFO Row 2442 (SKU 723705176015): Amazon price re-derived from current cost: 83.40 -> 42.67
2026-10-27 22:56:36,546 INFO Row 1387 (SKU 669425970895): Amazon price re-derived from current cost: 266.49 -> 266.46
2026-10-27 22:48:50,743 INFO Row 2394 (SKU 722844979822): Amazon price re-derived from current cost: 30.29 -> 30.12
2026-10-27 22:56:05,014 INFO Row 1309 (SKU 668240430546): Amazon price re-derived from current cost: 95.36 -> 95.28
2026-10-27 22:59:23,953 INFO Row 1244 (SKU 632083529347): Amazon price re-derived from current cost: 28.66 -> 28.64
2026-10-27 23:03:00,013 INFO Row 1782 (SKU 713169360662): Amazon price re-derived from current cost: 63.72 -> 63.34
2026-10-27 23:05:46,404 INFO Row 238 (SKU 960797552376): Amazon price re-derived from current cost: 201.63 -> 200.95
2026-10-27 23:08:09,791 INFO Row 961 (SKU 334562544093): Amazon price re-derived from current cost: 22.81 -> 22.78
'''

CENSUS_LOG = '''tab 'Sheet1': no 'Amazon Seller' column - skipped
tab 'Amazon': 3028 Amazon-sourced rows

Amazon-sourced rows by the seller Keepa last reported (all / with stock above 0):
  3rd party (lowest New)         2236 /   2236
  Amazon                          557 /    557
  (none recorded)                 235 /      0

Would go to stock 0 under AMAZON_OWN_OFFER_ONLY=1 (live on a third-party offer only): 2236
  e.g. 3rd party (lowest New): 325746422429 (row 2, Synced); 325805249332 (row 3, Synced); 325808712307 (row 4, Synced); 325986042982 (row 5, Synced); 326012007067 (row 6, Synced); 326028393208 (row 7, Synced); 326205218331 (row 10, Synced); 692092290515 (row 11, Synced); 692322225812 (row 13, Synced); 692411803259 (row 14, Synced); 692496512336 (row 15, Synced); 692607518806 (row 16, Synced); 692612714729 (row 17, Synced); 693310750736 (row 19, Synced); 694049442701 (row 28, Synced); 694258970590 (row 29, Synced); 694326306054 (row 30, Synced); 695986647648 (row 37, Synced); 696417177628 (row 42, Synced); 696552659539 (row 43, Synced); 696580857600 (row 44, Synced); 696590964220 (row 45, Synced); 696754771466 (row 46, Synced); 697226897035 (row 47, Synced); 697535161469 (row 48, Synced)
'''
