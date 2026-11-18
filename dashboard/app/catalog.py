"""What each store workflow is for, where it belongs on the page and how careful a button it needs.

The repositories carry 113 workflow files between them; this map gives the ones a person runs a plain label, an area and a
risk level. Anything not listed is classified from its name (read-only probes, one-offs) and lands under Tools.

risk:  read  = reads only (sheet, OnBuy, GitHub) - runs on one press
       write = changes the sheet or OnBuy in a guarded way (dry run by default) - needs the apply switch
       danger = deletes, zeroes, prices or sale changes at scale - needs the apply switch AND the confirmation box
"""

AREAS = [
    ("sync", "Syncs and feeds"),
    ("pricing", "Pricing and fees"),
    ("catalogue", "Catalogue hygiene"),
    ("categories", "Categories"),
    ("sheet", "Sheet repairs"),
    ("sales", "Buy Box, sale, delivery"),
    ("orders", "Orders"),
    ("pictures", "Pictures"),
    ("monitoring", "Monitoring"),
    ("tools", "Tools and probes"),
]
AREA_NAMES = dict(AREAS)

# file -> (label, area, risk, apply input name or None, note)
CATALOG = {
    "run.yml": ("eBay sync (hourly)", "sync", "write", None, "Prices, stock, creations from the eBay rows; ends with the dead-row purge."),
    "run_amazon.yml": ("Amazon sync (Keepa)", "sync", "write", None, "Keepa prices with the usual-price rule, stock, OnBuy updates."),
    "amazon_seller_census.yml": ("Amazon seller census", "sync", "read", None, "Amazon rows by the seller Keepa last reported; how many the strict stock rule would zero."),
    "backfill_onbuy_status.yml": ("Backfill OnBuy status (hourly)", "sync", "write", None, "Creation-queue outcomes, OPC write-back, oversell guard."),
    "nightly_reconcile.yml": ("Nightly reconcile", "catalogue", "danger", None, "Content scan, zero/hold/delete wrong content, price fix, sale guard."),
    "semi_upload_watch.yml": ("Semi upload watch", "sync", "write", None, "Moves AliExpress CSV uploads onto their delivery template."),
    "purge_dead_rows.yml": ("Purge dead eBay rows", "catalogue", "danger", "dry_run", "Deletes out-of-stock and brand-blocked eBay rows on OnBuy and the sheet."),
    "stale_report.yml": ("Staleness report", "monitoring", "read", None, ""),
    "ebay_limit_probe.yml": ("eBay call budget", "monitoring", "read", None, ""),
    "new_sku_check.yml": ("New SKU check", "monitoring", "read", None, ""),
    "shipping_probe.yml": ("Shipping probe", "tools", "read", None, ""),
    "pricing_probe.yml": ("Pricing probe", "pricing", "read", None, "What the schedule gives a few rows."),
    "audit_price_drift.yml": ("Audit price drift", "pricing", "danger", "fix", "Report, or fix OnBuy prices that drifted from the sheet."),
    "even_margins.yml": ("Even margins", "pricing", "danger", "apply", "Puts every priced row on the profit schedule (backup tab first)."),
    "profit_band_impact.yml": ("Profit band impact", "pricing", "read", None, "Preview of a schedule change."),
    "price_impact_report.yml": ("Price impact of category fees", "pricing", "read", None, ""),
    "refresh_fees.yml": ("Refresh commission tables", "pricing", "danger", "commit", "Reads OnBuy's commission tables; commit=yes commits them (every sync prices from them)."),
    "observed_fee_feedback.yml": ("Observed fee feedback", "pricing", "danger", "apply", "Orders show the real commission; apply=yes writes Fee % overrides (prices follow)."),
    "order_fee_probe.yml": ("Order fee probe", "orders", "read", None, ""),
    "revert_fee_fallback.yml": ("Revert fee fallback prices", "pricing", "danger", "apply", ""),
    "ensure_fee_column.yml": ("Ensure Fee % column", "sheet", "write", "dry_run", ""),
    "probe_commission.yml": ("Probe commission", "tools", "read", None, ""),
    "scan_content_mismatch.yml": ("Content mismatch scan", "catalogue", "read", None, "Live names vs sheet titles."),
    "remove_wrong_content.yml": ("Remove wrong-content listings", "catalogue", "danger", "dry_run", "Deletes listings whose page shows another product (backup first)."),
    "zero_stock_mismatched.yml": ("Zero mismatched stock", "catalogue", "danger", "dry_run", ""),
    "zero_listings.yml": ("Zero named listings", "catalogue", "danger", "dry_run", "Takes the stock off the named SKUs on OnBuy, no sweep. The Catalogue page's Freeze drives it."),
    "frozen_report.yml": ("Frozen rows report", "catalogue", "read", None, ""),
    "oversell_guard.yml": ("Oversell guard", "catalogue", "write", "dry_run", "Re-zeroes listings the sheet says are out of stock."),
    "dup_removal.yml": ("Delete by list / duplicate removal", "catalogue", "danger", "dry_run", "Rows (backed up first) + OnBuy listings of an explicit SKU list, or live duplicates. The Delete page drives the list."),
    "remove_duplicate_sku_rows.yml": ("Remove duplicate SKU rows", "catalogue", "danger", "dry_run", ""),
    "analyze_upc_dups.yml": ("Analyze UPC duplicates", "catalogue", "read", None, ""),
    "ghost_listings.yml": ("Ghost listings", "catalogue", "read", None, "API creations that never went live."),
    "revive_suspended.yml": ("Revive suspended", "catalogue", "write", "dry_run", ""),
    "revive_zeroed_listings.yml": ("Revive zeroed listings", "catalogue", "danger", "dry_run", ""),
    "relink_listing.yml": ("Relink listings", "catalogue", "danger", "dry_run", ""),
    "repair_shifted_content.yml": ("Resubmit products (content + images)", "pictures", "write", "dry_run", "OnBuy's workaround for pictures that never processed. The Pictures page drives it, for the SKUs you name only."),
    "repair_descriptions.yml": ("Repair descriptions", "catalogue", "write", "dry_run", ""),
    "resanitize_sheet.yml": ("Resanitize descriptions", "sheet", "write", "dry_run", ""),
    "delete_listings.yml": ("Delete listings by SKU", "catalogue", "danger", "dry_run", ""),
    "delete_skus_batch.yml": ("Delete SKUs (list file)", "catalogue", "danger", "dry_run", ""),
    "bulk_delete_chain.yml": ("Bulk delete chain", "catalogue", "danger", None, ""),
    "bulk_delete_fast.yml": ("Bulk delete (fast)", "catalogue", "danger", "dry_run", ""),
    "bulk_remove_rows.yml": ("Bulk remove rows", "catalogue", "danger", "dry_run", ""),
    "yra_removal.yml": ("Removal (rows + listings)", "catalogue", "danger", "dry_run", ""),
    "unsuspend_and_delete.yml": ("Unsuspend and delete", "catalogue", "danger", "dry_run", ""),
    "reset_deleted_rows.yml": ("Reset deleted rows", "sheet", "write", "dry_run", ""),
    "refresh_categories.yml": ("Refresh OnBuy categories", "categories", "write", "dry_run", ""),
    "remap_denied_categories.yml": ("Remap denied categories", "categories", "write", "dry_run", ""),
    "remap_gone_categories.yml": ("Remap gone categories", "categories", "write", "dry_run", ""),
    "set_category_by_keyword.yml": ("Relabel categories by keyword", "categories", "danger", "apply", "Sheet only, backup tab first; the sync re-prices the rows from their new tier."),
    "category_keyword_census.yml": ("Category keyword census", "categories", "read", None, ""),
    "category_error_scan.yml": ("Category error scan", "categories", "read", None, ""),
    "fix_category_cell.yml": ("Fix one category cell", "categories", "write", None, ""),
    "set_product_category.yml": ("Set product category on OnBuy", "categories", "write", "dry_run", ""),
    "set_row_cell.yml": ("Set one cell", "sheet", "write", "dry_run", "One cell on one row, guarded by the SKU."),
    "set_row_sku.yml": ("Set row SKU", "sheet", "write", "dry_run", ""),
    "fix_header_cell.yml": ("Fix header cell", "sheet", "write", None, ""),
    "sheet_header_probe.yml": ("Sheet header probe", "sheet", "write", "fix", ""),
    "fix_tab_order.yml": ("Fix tab order", "sheet", "write", None, ""),
    "setup_amazon_tab.yml": ("Set up Amazon tab", "sheet", "write", None, ""),
    "clear_amazon_dup_skus.yml": ("Clear Amazon duplicate SKUs", "sheet", "write", "dry_run", ""),
    "row_cells.yml": ("Row cells", "tools", "read", None, "Every cell of the rows holding these SKUs."),
    "dump_rows.yml": ("Dump rows", "tools", "read", None, ""),
    "inspect_rows.yml": ("Inspect rows", "tools", "read", None, ""),
    "inspect_sku_rows.yml": ("Inspect SKU rows", "tools", "read", None, ""),
    "listing_lookup.yml": ("Listing lookup", "tools", "read", None, "The live OnBuy listing of these SKUs."),
    "sku_probe.yml": ("SKU probe", "tools", "read", None, ""),
    "buybox_defense.yml": ("Buy Box defense", "sales", "danger", "dry_run", "Undercuts rivals by the pence set; daily."),
    "store_sale.yml": ("Store sale (on / off)", "sales", "danger", "mode", "Price ranges with a sale % each, margin floor; plan / test / apply / cancel. The Sale page drives it."),
    "sale_guard.yml": ("Sale price guard", "sales", "write", "dry_run", ""),
    "sale_price_probe.yml": ("Sale price probe", "sales", "read", None, ""),
    "clear_sale_price.yml": ("Clear sale price", "sales", "write", "dry_run", ""),
    "sale_clear_experiment.yml": ("Sale clear experiment", "sales", "write", "dry_run", ""),
    "delivery_templates.yml": ("Delivery templates", "sales", "danger", "mode", "Plan counts, Test moves one listing, Apply moves every listing off its supplier's template. The Delivery page drives it."),
    "orders_lookup.yml": ("Orders lookup", "orders", "read", None, "Orders awaiting dispatch; never buyer details."),
    "orders_vs_list.yml": ("Orders vs list", "orders", "read", None, ""),
    "image_links_export.yml": ("Image links export", "pictures", "read", None, "OPC + image links for a SKU list (the picture ticket). The Pictures page runs it."),
    "image_scan_export.yml": ("Image scan export", "pictures", "read", None, ""),
    "image_probe.yml": ("Image probe", "pictures", "read", None, ""),
    "product_probe.yml": ("Product probe", "pictures", "read", None, ""),
    "probe_product_endpoints.yml": ("Probe product endpoints", "pictures", "read", None, ""),
    "product_category_probe.yml": ("Product category probe", "pictures", "read", None, ""),
    "watch_recovery.yml": ("Watch recovery", "monitoring", "read", None, ""),
    "daily_digest.yml": ("Weekly fleet digest", "monitoring", "read", None, ""),
    "snapshot_queue_history.yml": ("Snapshot queue history", "monitoring", "read", None, ""),
    "listings_snapshot.yml": ("Listings snapshot", "monitoring", "read", None, ""),
    "tests.yml": ("Tests", "monitoring", "read", None, ""),
    "sweep_impact.yml": ("Sweep impact", "monitoring", "read", None, ""),
}

# the status tiles on the home page and the Run now buttons on a store page, in order
STATUS_TILES = [
    ("run.yml", "eBay sync"),
    ("run_amazon.yml", "Amazon sync"),
    ("backfill_onbuy_status.yml", "Backfill"),
    ("nightly_reconcile.yml", "Nightly"),
    ("buybox_defense.yml", "Buy Box"),
    ("scan_content_mismatch.yml", "Content scan"),
    ("ebay_limit_probe.yml", "eBay budget"),
]
# what each status tile's job does: the hover text of the tile and the Home page's "What each job does"
TILE_NOTES = {
    "eBay sync": "Hourly (GitHub often runs it every 3-5 hours): reads the eBay rows of the sheet, prices them, updates stock and prices on OnBuy and creates new listings; it ends with the dead-row purge.",
    "Amazon sync": "The same for the Amazon rows, with prices and stock from Keepa.",
    "Backfill": "Hourly: follows up listings OnBuy has finished creating (writes their OnBuy product code into the sheet) and guards against overselling. On GTV it also carries the nightly work.",
    "Nightly": "Once a day: compares each live listing's name with its sheet row, freezes or deletes wrong ones, corrects listings priced below the sheet and runs the sale guard.",
    "Buy Box": "Once a day: lowers a price to win the Buy Box where it can stay above the price floor (see the Buy Box page).",
    "Content scan": "Once a day: reads the live listings' names and compares them with the sheet's titles (a report; it changes nothing).",
    "eBay budget": "Once a day: reports how many eBay calls are left for the day.",
}
RUN_NOW = ["run.yml", "run_amazon.yml", "backfill_onbuy_status.yml", "nightly_reconcile.yml", "scan_content_mismatch.yml",
           "audit_price_drift.yml", "purge_dead_rows.yml", "orders_lookup.yml"]

# GTV has no separate nightly workflow: its backfill embeds the nightly once a day, so its "Nightly" tile reads the backfill run
# that carried the content scan (the page recognises it by its log).
EMBEDDED_NIGHTLY = {"gtv": "backfill_onbuy_status.yml"}
NIGHTLY_MARKERS = ("UNDERPRICED on OnBuy", "MATCHED:")

# the modes (the store sale's, the delivery templates') that change listings on OnBuy (plan only reads)
ACTIVE_MODES = ("apply", "cancel", "test", "refresh")

# workflows that never hold the store's onbuy-api slot (no concurrency group): the CI tests every push to main starts. A CI run is "queued" for a few seconds while GitHub finds
# it a runner, which used to read as "a run is waiting for the store's slot" and refuse the next dispatch - right after every list file the dashboard commits (a picture
# ticket's, a delete plan's) the sheet read was refused (GTV, 2026-10-27). Such runs are left out of the queue the dashboard reasons about.
NOT_IN_SLOT = ("tests.yml",)

# how long a scheduled workflow may go without a run before the page calls it stale (hours)
# The Amazon lane of a store: the workflows that exist only to sync Amazon rows with Keepa. A store marked eBay-only (config/stores.json
# "amazon": false) parks them on purpose, so none of its pages may judge, list or plan them.
AMAZON_LANE_PREFIXES = ("run_amazon", "amazon_dispatch", "keepa", "probe_keepa")


def is_amazon_lane(path):
    """True for a workflow file of the Amazon lane (run_amazon.yml, amazon_dispatch.yml, keepa_status.yml, probe_keepa_*.yml ...)."""
    name = str(path or "").rsplit("/", 1)[-1]
    return name.startswith(AMAZON_LANE_PREFIXES)


def without_amazon(runs):
    """The run list of an eBay-only store: its Amazon-lane runs (old ones from before the lane was switched off) are not part of its story."""
    return [r for r in runs if not is_amazon_lane(r.get("path"))]


STALE_HOURS = {"daily_digest.yml": 8 * 24, "run_amazon.yml": 12, "run.yml": 8, "backfill_onbuy_status.yml": 8, "watch_recovery.yml": 14}
STALE_DEFAULT_HOURS = 30

_READ_WORDS = ("read-only", "probe", "report", "census", "lookup", "snapshot", "check", "scan", "export", "dump", "inspect")
_DANGER_WORDS = ("delete", "remove", "purge", "zero", "revive", "sale", "relink", "even", "bulk")


def classify(workflow_file, name="", inputs=None):
    """(label, area, risk, apply_input, note) for a workflow - from the catalog, else inferred from its name."""
    if workflow_file in CATALOG:
        return CATALOG[workflow_file]
    inputs = inputs or {}
    low = (name or workflow_file).lower()
    if any(w in low for w in _READ_WORDS):
        risk = "read"
    elif any(w in low for w in _DANGER_WORDS):
        risk = "danger"
    else:
        risk = "write"
    apply_input = next((k for k in ("dry_run", "apply", "fix") if k in inputs), None)
    return (name or workflow_file, "tools", risk, apply_input, "")


def is_live_request(apply_input, inputs):
    """True when the inputs ask for a real change (not a dry run)."""
    if not apply_input:
        return True
    value = str(inputs.get(apply_input, "")).strip().lower()
    if apply_input == "mode":                    # the store sale: plan only reads; test, apply, cancel and refresh change listings
        return value in ACTIVE_MODES
    if apply_input == "dry_run":
        return value in ("no", "0", "false", "off")
    return value in ("yes", "1", "true", "on")
