"""The Best View Glazing dashboard: one FastAPI app, server-rendered pages, a few JSON endpoints for the buttons.

Start it with `python run.py` (reads .env). Pages never touch OnBuy directly: everything goes through the store repositories'
GitHub Actions, exactly as it does when a person presses "Run workflow" on GitHub - with two house rules enforced here:
a workflow is never started while another run is waiting for the store's slot (it would be cancelled), and anything that
deletes, zeroes or re-prices at scale needs the apply switch AND the confirmation box.
"""
import csv
import io
import json
import math
import os
import re
import secrets
import sqlite3
import shutil
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import amazon, amazon_schedule, buybox, catalog, catalogue, creations, deletion, delivery, digest, ebay, fees, orphans, pictures, pricing, problems, readiness, sale, sheethealth, suspended, todo
from . import auth as auth_module
from . import config as config_module
from .auth import COOKIE, AuthMiddleware, SessionAuth
from .config import Store, load_settings
from .db import Database
from .github_client import GitHubClient, GitHubError
from .jobs import JobFailed, Jobs
from .logstore import LogStore

HERE = Path(__file__).resolve().parent
ORDERS_FRESH_HOURS = 36
STUCK_PENDING_HOURS = 48          # a run "queued" for days is a GitHub ghost (Makstore carried one from 19 August), not a wait for the slot


def utcnow():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def create_app(settings=None, client=None, database=None, jobs=None, link_fetch=None, sleep=time.sleep):
    """jobs, link_fetch and sleep are for the tests: the background job registry, the function that opens an image link, and the pause between two looks at a running workflow."""
    settings = settings or load_settings()
    jobs = jobs or Jobs()
    client = client or GitHubClient(settings.github_token, settings.github_api)
    database = database or Database(Path(settings.data_dir) / "dashboard.db")
    secret = settings.dashboard_secret or database.get("session_secret")          # DASHBOARD_SECRET keeps sign-ins valid across restarts on a host that forgets files
    if not secret:
        secret = secrets.token_hex(32)
        database.set("session_secret", secret)
    auth = SessionAuth(settings.dashboard_password, secret=secret)
    throttle = auth_module.Throttle()

    app = FastAPI(title="Best View Glazing dashboard", docs_url=None, redoc_url=None)
    app.state.settings, app.state.client, app.state.db, app.state.auth = settings, client, database, auth
    app.state.throttle = throttle
    app.add_middleware(AuthMiddleware, auth=auth)
    app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")
    templates = Jinja2Templates(directory=str(HERE / "templates"))
    templates.env.filters["age"] = fmt_age
    templates.env.globals["tile_notes"] = catalog.TILE_NOTES
    templates.env.filters["when"] = fmt_when
    templates.env.filters["tojson_pretty"] = lambda v: json.dumps(v, indent=1, ensure_ascii=False)
    templates.env.filters["num"] = lambda v: "" if v is None else f"{float(v):g}"
    # the script and the stylesheet carry the time they were last changed: a browser that cached the old app.js kept the new card's buttons dead until a hard refresh (found on the Amazon card, 2026-10-27)
    templates.env.globals["asset_v"] = str(int(max((HERE / "static" / name).stat().st_mtime for name in ("app.js", "style.css"))))
    pool = ThreadPoolExecutor(max_workers=6)

    def page(request, name, **ctx):
        base = {"request": request, "stores": settings.stores, "login_required": auth.enabled, "store": None, "active": "",
                "now": utcnow(), "user": auth.session(request)}
        base.update(ctx)
        return templates.TemplateResponse(request, name, base)

    def store_or_404(store_id):
        try:
            return settings.store(store_id)
        except KeyError:
            return None

    # ---- data helpers -------------------------------------------------------------------------------------------------------
    def split_queue(queue):
        """The store's queue with ghosts set apart: a run pending for more than STUCK_PENDING_HOURS is 'stuck', not waiting. CI runs (catalog.NOT_IN_SLOT) are not part of it."""
        pending, stuck = [], []
        for r in queue.get("pending") or []:
            if r.get("path") in catalog.NOT_IN_SLOT:
                continue
            hours = digest.age_hours(r.get("created_at"))
            (stuck if hours is not None and hours > STUCK_PENDING_HOURS else pending).append(r)
        return {"in_progress": [r for r in queue.get("in_progress") or [] if r.get("path") not in catalog.NOT_IN_SLOT], "pending": pending, "stuck": stuck}

    def store_status(store, runs_limit=100):
        """Queue + the latest run of each status tile, for one store."""
        out = {"store": store, "queue": {"in_progress": [], "pending": [], "stuck": []}, "tiles": [], "runs": [], "error": "", "sale": None}
        try:
            runs = client.list_runs(store.repo, limit=runs_limit)
            if not store.amazon:                     # an eBay-only store: its Amazon-lane runs (from before it was switched off) are not part of its story
                runs = catalog.without_amazon(runs)
            out["runs"] = runs
            out["queue"] = split_queue(client.queue(store.repo))
        except GitHubError as exc:
            out["error"] = str(exc)
            return out
        try:
            out["sale"] = sale_state(store)
        except GitHubError:
            out["sale"] = None                       # the sale pill is a courtesy: a failed read shows nothing, never an error
        now = utcnow()
        for path, label in catalog.STATUS_TILES:
            if path == "run_amazon.yml" and not store.amazon:
                continue                             # no Amazon tile for an eBay-only store
            if path == "nightly_reconcile.yml" and store.id in catalog.EMBEDDED_NIGHTLY:
                run, label = find_nightly(store, runs), "Nightly (in backfill)"
            else:
                run = next((r for r in runs if r["path"] == path), None)
            hours = digest.age_hours(run["created_at"], now) if run else None
            limit = catalog.STALE_HOURS.get(path, catalog.STALE_DEFAULT_HOURS)
            state = "none"
            if run:
                if run["status"] != "completed":
                    state = "running"
                elif run["conclusion"] == "success":
                    state = "ok"
                elif run["conclusion"] == "cancelled":
                    state = "cancelled"
                else:
                    state = "failed"
            out["tiles"].append({"path": path, "label": label, "run": run, "hours": hours, "state": state,
                                 "stale": bool(run) and hours is not None and hours > limit})
        return out

    def all_status(runs_limit=60):
        return list(pool.map(lambda s: store_status(s, runs_limit), settings.stores))

    log_cache = {}
    log_store = LogStore(Path(settings.data_dir) / "logs")

    def run_text(store, run):
        """A finished run's log: memory first, then the disk store, then GitHub - so a run's log is downloaded once EVER, not once per restart
        (the user restarts the dashboard for every update, and the cold To do page used to download tens of megabytes again). A running run is never kept."""
        key = (store.repo, run["id"])
        if key in log_cache:
            return log_cache[key]
        finished = run["status"] == "completed"
        stored = log_store.get(store.repo, run["id"]) if finished else None
        text = stored if stored is not None else client.run_log(store.repo, run["id"])
        if finished:
            if len(log_cache) > 400:
                log_cache.clear()
            log_cache[key] = text
            if stored is None:
                log_store.put(store.repo, run["id"], text)
        return text

    def find_nightly(store, runs):
        """The latest run that did the nightly work: nightly_reconcile.yml, or for a store whose backfill embeds it, the newest
        completed backfill whose log carries the content scan."""
        host = catalog.EMBEDDED_NIGHTLY.get(store.id)
        if host:
            candidates = [r for r in runs if r["path"] == host and r["status"] == "completed"][:8]
            for r in candidates:
                try:
                    if any(m in run_text(store, r) for m in catalog.NIGHTLY_MARKERS):
                        return r
                except GitHubError:
                    continue
            return None
        return next((r for r in runs if r["path"] == "nightly_reconcile.yml" and r["status"] == "completed"), None)

    def run_facts(store, run):
        """Key log lines + headline numbers of a finished run."""
        text = run_text(store, run)
        facts = {}
        if run["path"] in ("nightly_reconcile.yml", "backfill_onbuy_status.yml"):
            facts = digest.parse_nightly(text)
        elif run["path"] == "orders_lookup.yml":
            facts = digest.parse_orders(text)
        elif run["path"] == "ebay_limit_probe.yml":
            facts = digest.parse_ebay_budget(text)
        elif run["path"] in ("run.yml", "run_amazon.yml"):
            facts = digest.parse_sync_summary(text)
            facts.update(digest.parse_keepa(text))
        elif run["path"] == "even_margins.yml":
            facts = pricing.parse_even_margins(text)
        elif run["path"] in fees.PARSERS:
            facts = fees.PARSERS[run["path"]](text)
        elif run["path"] == "store_sale.yml":
            facts = sale.parse_store_sale(text)
        elif run["path"] == "purge_dead_rows.yml":
            facts = catalogue.parse_purge(text)
        elif run["path"] == "remove_wrong_content.yml":
            facts = catalogue.parse_removal(text)
        elif run["path"] in ("dup_removal.yml", "yra_removal.yml"):
            facts = deletion.parse_guarded(text)
        elif run["path"] == "buybox_defense.yml":
            facts = buybox.parse_defense(text)
        elif run["path"] == amazon.CENSUS_WORKFLOW:
            facts = amazon.parse_census(text)
        elif run["path"] == "delivery_templates.yml":
            facts = delivery.parse_templates(text)
        elif run["path"] == pictures.REPAIR_WORKFLOW:
            facts = pictures.parse_repair(text)
        return {"lines": digest.key_lines(text), "facts": facts}

    def load_schedule(store):
        """The store's schedule as it prices right now, plus where it comes from and what else the page needs."""
        variables = {v["name"]: v["value"] for v in client.list_variables(store.repo)}
        setting_raw = variables.get("PROFIT_SCHEDULE", "")
        knob = variables.get("PROFIT_TOP_BAND_PERCENT") or variables.get("PROFIT_ABOVE_50_PERCENT") or None
        source = client.get_file(store.repo, "pricing.py", ref=settings.github_ref)
        code = pricing.code_schedule(source, knob=knob)
        paths = {w["path"] for w in client.list_workflows(store.repo) if w["state"] == "active"}
        return {"setting_raw": setting_raw, "knob": knob, "code": code, "schedule": pricing.effective_schedule(setting_raw, code),
                "has_even_margins": "even_margins.yml" in paths, "has_audit": "audit_price_drift.yml" in paths}

    def proposed_schedule(body, current):
        """Validate a proposed schedule from the page -> (bands, overrides, error)."""
        bands = body.get("bands")
        error = pricing.check_bands(bands)
        if error:
            return None, None, error
        overrides = None
        if current and current.get("overrides") is not None:
            overrides = body.get("overrides") if body.get("overrides") is not None else current["overrides"]
            error = pricing.check_overrides(overrides)
            if error:
                return None, None, error
            overrides = pricing.clean_overrides(overrides)
        return pricing.clean_bands(bands), overrides, ""

    def latest_run_facts(store, workflow, parser, limit=5, successful=False):
        """The newest finished run of a workflow with the numbers in its log (None when the store never ran it). successful=True skips runs that did not
        succeed and reports the newest one that failed after it under "newer"."""
        try:
            runs = client.list_runs(store.repo, limit=limit, workflow=workflow)
        except GitHubError:
            return None
        done = [r for r in runs if r["status"] == "completed"]
        if not done:
            return None
        run = next((r for r in done if r["conclusion"] == "success"), done[0]) if successful else done[0]
        newer = done[0] if (successful and done[0] is not run and done[0]["conclusion"] != "success") else None
        try:
            text = run_text(store, run)
        except GitHubError:
            return {"run": run, "facts": {}, "lines": [], "newer": newer}
        return {"run": run, "facts": parser(text) if run["conclusion"] == "success" else {}, "lines": digest.key_lines(text, limit=20), "newer": newer}

    def load_fees(store):
        """The fee model a store prices with, its committed commission tables, and the latest run of each fee tool."""
        variables = client.list_variables(store.repo)
        code = pricing.code_schedule(client.get_file(store.repo, "pricing.py", ref=settings.github_ref))
        model = fees.fee_model(variables, code)
        tiers, categories, tables_error = [], {"categories": 0, "by_tier": {}, "without_tier": 0}, ""
        try:
            tiers = fees.parse_tiers_csv(client.get_file(store.repo, "onbuy_commission_tiers.csv", ref=settings.github_ref), vat=model["vat"])
            categories = fees.summarize_category_tiers(client.get_file(store.repo, "onbuy_category_tiers.csv", ref=settings.github_ref))
        except GitHubError as exc:
            tables_error = f"The commission tables could not be read from the repository: {exc}"
        try:
            committed = client.last_commit(store.repo, "onbuy_commission_tiers.csv", ref=settings.github_ref)
        except GitHubError:
            committed = None
        try:
            rules = fees.default_rules(client.get_file(store.repo, "set_category_by_keyword.py", ref=settings.github_ref))
        except GitHubError:
            rules = ""
        paths = {w["path"] for w in client.list_workflows(store.repo) if w["state"] == "active"}

        def one(item):
            key, workflow = item
            return key, (latest_run_facts(store, workflow, fees.PARSERS[workflow]) if workflow in paths else None)

        latest = dict(pool.map(one, fees.LATEST.items()))
        return {"model": model, "tiers": tiers, "categories": categories, "tables_error": tables_error, "committed": committed,
                "rules": rules, "available": {key: wf in paths for key, wf in fees.LATEST.items()}, "latest": latest}

    def read_text(store, path, fresh=True):
        """A text file of the store's repository, read fresh; a file that is not there is empty."""
        try:
            return client.get_file(store.repo, path, ref=settings.github_ref, fresh=fresh)
        except GitHubError as exc:
            if exc.status == 404:
                return ""
            raise

    def load_catalogue(store):
        """The catalogue card's data: the frozen listings (three text files of the repository), the latest nightly's wrong-content numbers, the dead-row purge."""
        hold, protected = read_text(store, catalogue.HOLD_FILE), read_text(store, catalogue.PROTECTED_FILE)
        same = read_text(store, catalogue.SAME_FILE)
        all_runs = client.list_runs(store.repo, limit=250)
        nightly = None
        found = find_nightly(store, all_runs)
        if found:
            try:
                nightly = {"run": found, "facts": digest.parse_nightly(run_text(store, found))}
            except GitHubError:
                nightly = {"run": found, "facts": {}}
        overlaps = {b["sku"]: b["overlap"] for b in ((nightly or {}).get("facts") or {}).get("borderlines", [])}
        paths = {w["path"] for w in client.list_workflows(store.repo) if w["state"] == "active"}
        purge = None
        sync = next((r for r in all_runs if r["path"] == "run.yml" and r["status"] == "completed" and r["conclusion"] == "success"), None)
        if sync:
            try:
                purge = {"run": sync, "facts": catalogue.parse_purge(run_text(store, sync))}
            except GitHubError:
                purge = {"run": sync, "facts": {}}
        variables = [v for v in client.list_variables(store.repo) if v["name"].startswith("PURGE_")]
        holds = catalogue.mark_deleted(catalogue.merge_holds(hold, protected, same, overlaps), deleted_by_runs(store, all_runs))
        return {"holds": holds, "gone": [h for h in holds if h["deleted_by"]], "nightly": nightly, "purge": purge, "purge_vars": variables,
                "available": {"remove": "remove_wrong_content.yml" in paths, "zero": "zero_listings.yml" in paths, "purge": "purge_dead_rows.yml" in paths}}

    def deleted_by_runs(store, runs):
        """[{sku, day, run}] of the listings the finished live remove_wrong_content runs deleted. The manual form commits no change to the hold lists (the nightly's own
        removal does), so the lines of a deleted listing stay on them until somebody drops them."""
        out = []
        for run in [r for r in runs if r["path"] == "remove_wrong_content.yml" and r["status"] == "completed" and r["conclusion"] == "success"][:10]:
            try:
                skus = catalogue.deleted_skus(catalogue.parse_removal(run_text(store, run)))
            except GitHubError:
                continue
            out.extend({"sku": sku, "day": run["created_at"][:10], "run": {"id": run["id"], "number": run.get("run_number") or run["id"], "url": run["url"]}} for sku in skus)
        return out

    OPEN_STATES = ("dispatched", "queued", "waiting", "pending", "requested", "in_progress")

    def settled(store, rows):
        """The dispatches of a store with their runs' latest status: a run that was still open when the page that started it was left (or the browser closed) is looked up
        again, so "Started from here" never keeps saying queued for a run that finished."""
        for d in rows:
            if d.get("run_id") and d.get("status") in OPEN_STATES:
                try:
                    run = client.run(store.repo, d["run_id"])
                except GitHubError:
                    continue
                now = run["conclusion"] if run["status"] == "completed" else run["status"]
                if now and now != d["status"]:
                    database.update_dispatch(d["id"], status=now)
                    d["status"] = now
        return rows

    def sale_state(store, fresh=False):
        """The running store sale (store_sale.json) as the pages show it, or None when the repository has none. Any other GitHub error propagates."""
        try:
            text = client.get_file(store.repo, "store_sale.json", ref=settings.github_ref, fresh=fresh)
        except GitHubError as exc:
            if exc.status == 404:
                return None
            raise
        return sale.state_view(text, today=utcnow().date())

    def load_sale(store):
        """The sale card's data: the running sale (read fresh), whether the repository has the tool, its latest finished run and what was started from here."""
        state = sale_state(store, fresh=True)
        paths = {w["path"] for w in client.list_workflows(store.repo) if w["state"] == "active"}
        available = "store_sale.yml" in paths
        latest = latest_run_facts(store, "store_sale.yml", sale.parse_store_sale, limit=15, successful=True) if available else None
        started = settled(store, [d for d in database.recent_dispatches(store.id, limit=40) if d["workflow"] == "store_sale.yml"][:8])
        return {"state": state, "available": available, "latest": latest, "dispatches": started}

    def load_buybox(store):
        """The Buy Box card's data: the three settings in force and the push gate, the workflow's schedule, the last runs with their numbers, a running sale, and what was started from here."""
        paths = {w["path"] for w in client.list_workflows(store.repo) if w["state"] == "active"}
        if "buybox_defense.yml" not in paths:
            return {"available": False}
        definition = client.workflow_definition(store.repo, "buybox_defense.yml", ref=settings.github_ref)
        variables = client.list_variables(store.repo)
        runs = [r for r in client.list_runs(store.repo, limit=25, workflow="buybox_defense.yml") if r["status"] == "completed"][:7]

        def one(run):
            if run["conclusion"] != "success":
                return {"run": run, "facts": {}}
            try:
                return {"run": run, "facts": buybox.parse_defense(run_text(store, run))}
            except GitHubError:
                return {"run": run, "facts": {}}

        history = list(pool.map(one, runs))
        started = settled(store, [d for d in database.recent_dispatches(store.id, limit=60) if d["workflow"] == "buybox_defense.yml"][:6])
        return {"available": True, "settings": buybox.settings_view(variables), "schedule": [buybox.describe_cron(c) for c in definition.get("schedule") or []],
                "wired": "profit_percent" in definition["inputs"], "history": history, "latest": next((h for h in history if (h["facts"] or {}).get("counts")), None),
                "dispatches": started, "sale": sale_state(store)}

    def amazon_wiring(store):
        """The settings in force for the store's Amazon sync -> (the settings as the page shows them, the set of repository variables its workflow passes on)."""
        wired = amazon.read_wiring(client.get_file(store.repo, f".github/workflows/{amazon.WORKFLOW}", ref=settings.github_ref))
        return amazon.settings_view(client.list_variables(store.repo), wired), wired

    def load_amazon(store):
        """The Amazon card's data: the settings in force, the last syncs with their numbers, the biggest price falls of the last real sync, the latest seller count and what was started from here."""
        paths = {w["path"] for w in client.list_workflows(store.repo) if w["state"] == "active"}
        if amazon.WORKFLOW not in paths:
            return {"available": False}
        view, _ = amazon_wiring(store)
        definition = client.workflow_definition(store.repo, amazon.WORKFLOW, ref=settings.github_ref)
        runs = [r for r in client.list_runs(store.repo, limit=40, workflow=amazon.WORKFLOW) if r["status"] == "completed"][:8]

        def one(run):
            if run["conclusion"] not in ("success", "failure"):
                return {"run": run, "facts": {}}
            try:
                return {"run": run, "facts": amazon.parse_sync(run_text(store, run))}
            except GitHubError:
                return {"run": run, "facts": {}}

        history = list(pool.map(one, runs))
        answered = [h for h in history if h["run"]["conclusion"] == "success" and h["facts"].get("answered")]
        # "the last good sync" is a real one (scheduled, or a manual one of many rows) - not a manual run for a single row, which refreshed one product and says nothing about the store
        latest = next((h for h in answered if h["run"]["event"] == "schedule" or h["facts"].get("processing", 0) >= 30), answered[0] if answered else None)
        failed = next((h for h in history if (h["facts"] or {}).get("keepa_failed")), None)
        # a failure only matters as a banner while no good run has come after it
        if failed and latest and latest["run"]["created_at"] > failed["run"]["created_at"]:
            failed = None
        moves_from = next((h for h in history if h["run"]["conclusion"] == "success" and h["facts"].get("moves") and h["facts"].get("processing", 0) >= 30), None)
        census = latest_run_facts(store, amazon.CENSUS_WORKFLOW, amazon.parse_census, limit=8, successful=True) if amazon.CENSUS_WORKFLOW in paths else None
        started = settled(store, [d for d in database.recent_dispatches(store.id, limit=60) if d["workflow"] in (amazon.CENSUS_WORKFLOW, amazon.WORKFLOW)][:8])
        plan = keepa_plan()
        return {"available": True, "settings": view, "schedule": [buybox.describe_cron(c) for c in definition.get("schedule") or []], "history": history, "latest": latest,
                "keepa_failed": failed, "token_note": amazon.token_note(latest["facts"]) if latest else "", "waited": {h["run"]["id"]: amazon.waited_minutes(h["facts"]) for h in history},
                "moves": amazon.price_moves(moves_from["facts"]["moves"]) if moves_from else None, "moves_run": moves_from["run"] if moves_from else None,
                "census": census if census and (census["facts"] or {}).get("sellers") else None, "dispatches": started, "strict": next((s["value"] for s in view if s["key"] == "own_only"), False),
            "plan": plan, "plan_totals": amazon.plan_totals(plan)}

    def load_ebay(store):
        """The eBay card's data: the last eBay syncs with their numbers, the estimate of how long the whole sheet takes to come round, the budget and the variables behind it."""
        paths = {w["path"] for w in client.list_workflows(store.repo) if w["state"] == "active"}
        if ebay.WORKFLOW not in paths:
            return {"available": False}
        definition = client.workflow_definition(store.repo, ebay.WORKFLOW, ref=settings.github_ref)
        variables = {v["name"]: str(v.get("value") or "").strip() for v in client.list_variables(store.repo)}
        runs = [r for r in client.list_runs(store.repo, limit=60, workflow=ebay.WORKFLOW) if r["status"] == "completed"][:12]

        def one(run):
            if run["conclusion"] not in ("success", "failure"):
                return {"run": run, "facts": {}}
            try:
                return {"run": run, "facts": ebay.parse_sync(run_text(store, run))}
            except GitHubError:
                return {"run": run, "facts": {}}

        history = list(pool.map(one, runs))
        good = [{"created_at": h["run"]["created_at"], "facts": h["facts"], "run": h["run"]} for h in history if h["run"]["conclusion"] == "success" and h["facts"].get("rows")]
        return {"available": True, "history": history, "latest": good[0] if good else None, "cycle": ebay.cycle_estimate(good),
                "schedule": [buybox.describe_cron(c) for c in definition.get("schedule") or []],
                "variables": {name: variables.get(name, "") for name in ("EBAY_DAILY_CALL_BUDGET", "EBAY_SHIPPING_COST", "RUNS_PER_DAY")}}

    TODO_FRESH_SECONDS = 300
    todo_cache = {}                       # store id -> (monotonic time, answer): the page keeps an answer for 5 minutes, ?refresh=1 asks again

    def gather_todo(store, refresh=False):
        """What the To do card needs from one store: the run list (one read), the queue, and the few logs behind the facts (orders, the last Amazon syncs, the nightly, the last fee refresh) -> the store's items.
        A source that cannot be read is left out (the others still count); a store that cannot be read at all says so. `refresh` reaches the dead-rows and suspended caches too."""
        now = utcnow()
        facts = {}
        runs = client.list_runs(store.repo, limit=250)
        if not store.amazon:
            runs = catalog.without_amazon(runs)      # an eBay-only store is never asked for an Amazon sync (no 'has not run', no 'prices fell')
        summary = digest.summarize_runs(runs, iso(now - timedelta(hours=24)), now)
        facts["stale"] = [{"name": s["name"], "hours": s["hours"], "limit": s["limit"]} for s in summary["stale"]]

        def newest_finished(path):
            return next((r for r in runs if r["path"] == path and r["status"] == "completed" and r["conclusion"] in ("success", "failure")), None)

        newest = {}
        for path in todo.WATCHED:
            run = newest_finished(path)
            if run:
                run_facts = {}
                if path == amazon.WORKFLOW and run["conclusion"] == "failure":
                    try:
                        run_facts = amazon.parse_sync(run_text(store, run))
                    except GitHubError:
                        run_facts = {}
                newest[path] = {"run": run, "facts": run_facts}
        facts["newest"] = newest
        facts["ci"] = newest_finished("tests.yml")
        facts["stuck"] = [{"name": r["name"], "created_at": r["created_at"], "url": r["url"]} for r in split_queue(client.queue(store.repo))["stuck"]]
        orders_run = next((r for r in runs if r["path"] == "orders_lookup.yml" and r["conclusion"] == "success"), None)
        facts["orders"] = None
        if orders_run:
            try:
                facts["orders"] = {**digest.parse_orders(run_text(store, orders_run)), "age_hours": digest.age_hours(orders_run["created_at"], now)}
            except GitHubError:
                facts.pop("orders")
        try:
            for r in [r for r in runs if r["path"] == amazon.WORKFLOW and r["conclusion"] == "success"][:3]:
                parsed = amazon.parse_sync(run_text(store, r))
                if parsed.get("moves") and parsed.get("processing", 0) >= 30:
                    moves = amazon.price_moves(parsed["moves"])
                    facts["falls"] = {"alerts": moves["alerts"], "alert_percent": moves["alert_percent"], "worst": moves["falls"][0] if moves["falls"] else None}
                    break
            nightly_run = find_nightly(store, runs)
            if nightly_run:
                facts["nightly"] = {"run": nightly_run, "facts": digest.parse_nightly(run_text(store, nightly_run)), "age_hours": digest.age_hours(nightly_run["created_at"], now)}
            fee_run = next((r for r in runs if r["path"] == "refresh_fees.yml" and r["conclusion"] == "success"), None)
            if fee_run:
                parsed = fees.parse_refresh_fees(run_text(store, fee_run))
                if parsed.get("tables"):
                    facts["fees"] = {"tables": parsed["tables"], "note": parsed.get("tables_note", ""), "run": fee_run, "age_days": (digest.age_hours(fee_run["created_at"], now) or 0) / 24}
        except GitHubError:
            pass
        try:
            fix = next((k for k in problems_for(store, refresh)["kinds"] if k["kind"] == "fix"), None)
            if fix and fix["skus"]:
                facts["dead_rows"] = {"count": len(fix["skus"]), "most_nights": fix["most_nights"], "reason": fix.get("reason", "")}
        except GitHubError:
            pass
        try:
            answer = load_suspended(store, refresh)
            if answer["counts"]["waiting"]:
                fresh_cut = (now - timedelta(days=2)).date().isoformat()
                facts["suspended"] = {"waiting": answer["counts"]["waiting"],
                                      "new": sum(1 for r in answer["rows"] if not r["done"] and r["last"] >= fresh_cut)}
        except GitHubError:
            pass
        try:
            holds = catalogue.merge_holds(read_text(store, catalogue.HOLD_FILE, fresh=False), read_text(store, catalogue.PROTECTED_FILE, fresh=False), read_text(store, catalogue.SAME_FILE, fresh=False))
            cutoff = (now - timedelta(days=todo.FROZEN_DAYS)).date().isoformat()
            facts["frozen"] = [{"sku": h["sku"], "since": h["since"]} for h in holds if h["since"] and h["since"] >= cutoff and h["row"] and not h["same_listed"]]
        except GitHubError:
            pass
        try:
            current = sale_state(store)
            if current:
                facts["sale"] = {"active": current["active"], "ends": current["ends"]}
            value = next((str(v.get("value") or "").strip() for v in client.list_variables(store.repo) if v["name"] == "ONBUY_API_PUSH_ENABLED"), "")
            facts["push"], facts["push_value"] = value.lower() == "true", value
        except GitHubError:
            pass
        return todo.items_for(store.id, store.name, facts, now)

    def todo_for(store, refresh=False):
        """One store's To do answer {store, items, error, at}, from the cache while it is younger than TODO_FRESH_SECONDS."""
        cached = todo_cache.get(store.id)
        if cached and not refresh and time.monotonic() - cached[0] < TODO_FRESH_SECONDS:
            return cached[1]
        try:
            answer = {"store": store, "items": gather_todo(store, refresh), "error": "", "at": utcnow()}
        except GitHubError as exc:
            answer = {"store": store, "items": [], "error": str(exc), "at": utcnow()}
        todo_cache[store.id] = (time.monotonic(), answer)
        return answer

    def delivery_wiring(store):
        """What the store's delivery_templates.yml takes (an id per supplier), whether a manual run reads the repository variables, and its built-in fallbacks -> (workflow text, wiring)."""
        text = client.get_file(store.repo, ".github/workflows/delivery_templates.yml", ref=settings.github_ref)
        return text, delivery.read_wiring(text)

    def load_delivery(store):
        """The Delivery card's data: the template ids in force and where each comes from, the census of the latest runs (manual ones and the nightly's step), what was started from here."""
        paths = {w["path"] for w in client.list_workflows(store.repo) if w["state"] == "active"}
        if "delivery_templates.yml" not in paths:
            return {"available": False}
        _, wiring = delivery_wiring(store)
        ids = delivery.effective_ids(client.list_variables(store.repo), wiring)
        done = lambda r: r["status"] == "completed" and r["conclusion"] != "cancelled"
        runs = [r for r in client.list_runs(store.repo, limit=20, workflow="delivery_templates.yml") if done(r)][:4]
        if store.id in delivery.IN_NIGHTLY:
            runs += [r for r in client.list_runs(store.repo, limit=10, workflow="nightly_reconcile.yml") if done(r)][:3]

        def one(run):
            try:
                facts = delivery.parse_templates(run_text(store, run))
            except GitHubError:
                facts = {}
            return {"run": run, "facts": facts, "kind": delivery.kind_label(run, facts)}

        history = sorted((h for h in pool.map(one, runs) if h["facts"].get("mode")), key=lambda h: h["run"]["created_at"], reverse=True)
        latest = next((h for h in history if h["facts"].get("classes") or "to_move" in h["facts"]), None)
        started = settled(store, [d for d in database.recent_dispatches(store.id, limit=60) if d["workflow"] == "delivery_templates.yml"][:6])
        return {"available": True, "ids": ids, "wired": bool(ids) and all(i["wired"] for i in ids), "history": history, "latest": latest,
                "rows": delivery.census_rows(latest["facts"], ids) if latest else [], "headline": delivery.headline(latest["facts"]) if latest else None,
                "nightly": store.id in delivery.IN_NIGHTLY, "dispatches": started}

    # ---- pictures ---------------------------------------------------------------------------------------------------------------
    def pictures_dir(store):
        return Path(settings.data_dir) / "pictures" / store.id

    def load_latest(store):
        """The result of the store's last finished ticket build (kept on disk, so a restart does not lose it), or None."""
        try:
            job_id = (pictures_dir(store) / "latest.txt").read_text(encoding="utf-8").strip()
            return json.loads((pictures_dir(store) / job_id / "result.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def resubmitted_map(store):
        """Which SKUs were resubmitted from the dashboard (the live runs of repair_shifted_content.yml that ended) and how it went -> {norm sku: {at, run_url, ok}}."""
        rows = [d for d in database.recent_dispatches(store.id, limit=200)
                if d["workflow"] == pictures.REPAIR_WORKFLOW and d["inputs"].get("dry_run") == "no" and d.get("run_id")][:30]
        runs = []
        for d in settled(store, rows):
            if d["status"] not in ("success", "failure"):
                continue
            try:
                facts = pictures.parse_repair(run_text(store, {"id": d["run_id"], "status": "completed"}))
            except GitHubError:
                continue
            runs.append({"at": d["at"], "run_url": d.get("run_url") or "", "ok": facts.get("ok", []), "failed": [f["sku"] for f in facts.get("failed", [])]})
        return pictures.resubmission_history(runs)

    def sweep_pause(store):
        """Minutes the store has to wait before another full read of its OnBuy listings (0 = go ahead): see pictures.sweep_wait."""
        runs = []
        for workflow in pictures.SWEEPERS:
            runs += client.list_runs(store.repo, limit=6, workflow=workflow)
        return pictures.sweep_wait(runs)

    def dispatch_and_wait(job, store, workflow, inputs, label, actor, timeout=2400):
        """Start a read-only workflow of the store and wait for it to end well -> the finished run. A refusal, a run that fails or one that never ends is a JobFailed with the reason."""
        began = iso(utcnow() - timedelta(seconds=10))
        try:
            result = start_workflow(store, workflow, inputs, False, actor, note=f"pictures: {label.lower()}")
        except GitHubError as exc:
            raise JobFailed(f"{label}: {exc}") from exc
        if "error" in result:
            raise JobFailed(f"{label}: {result['error']}")
        run = result.get("run")
        for _ in range(12):
            if run:
                break
            sleep(5)
            run = next((r for r in client.list_runs(store.repo, limit=10, workflow=workflow) if r["event"] == "workflow_dispatch" and r["created_at"] >= began), None)
        if not run:
            raise JobFailed(f"{label}: GitHub has not listed the run yet - look at the store's Actions page.")
        waited, glitches = time.time(), 0
        while True:
            try:
                current = client.run(store.repo, run["id"])
                glitches = 0
            except GitHubError as exc:
                glitches += 1
                if glitches > 3:
                    raise JobFailed(f"{label}: GitHub does not answer ({exc}). The run keeps going: {run['url']}") from exc
                sleep(6)
                continue
            if current["status"] == "completed":
                database.update_dispatch(result["dispatch_id"], run=current, status=current["conclusion"] or "completed")
                if current["conclusion"] != "success":
                    raise JobFailed(f"{label} ended with '{current['conclusion']}'. Open the run on GitHub: {current['url']}")
                return current
            job.set_detail(f"{label}: {current['status'].replace('_', ' ')} for {int(time.time() - waited)} s (run {current['run_number']})")
            if time.time() - waited > timeout:
                raise JobFailed(f"{label} did not end within {timeout // 60} minutes; it keeps running on GitHub: {current['url']}")
            sleep(6)

    def build_ticket(job, store, skus, opts, actor):
        """The ticket: save the list, read the sheet, ask OnBuy for the OPCs the sheet lacks, open every image link, write the files and the reply draft."""
        today = utcnow().date().isoformat()
        path = pictures.list_path(today, pictures.fingerprint(skus))
        job.set_step("Saving the list in the repository")
        client.update_file(store.repo, path, lambda old: pictures.list_text(store.name, skus, today),
                           f"dashboard: picture ticket list of {store.name} ({len(skus)} SKUs)", ref=settings.github_ref)
        job.set_step("Reading the earlier ticket lists")
        earlier_entries = pictures.earlier_lists(client.list_dir(store.repo, pictures.LIST_DIR, ref=settings.github_ref), exclude=path, before=today)
        earlier = set()
        for entry in earlier_entries:
            earlier |= {pictures.norm(s) for s in pictures.read_list(read_text(store, entry["path"], fresh=False))}
        job.set_step("Reading the sheet (the pictures and OPCs of these SKUs)")
        run = dispatch_and_wait(job, store, "image_links_export.yml", {"sku_file": path}, "The sheet read", actor)
        artifact = next((a for a in client.run_artifacts(store.repo, run["id"]) if a["name"] == "image-links" and not a["expired"]), None)
        if not artifact:
            raise JobFailed(f"The sheet read finished but its files (the artifact image-links) are not there. Open the run: {run['url']}")
        export = pictures.read_export(pictures.read_zip(client.download_artifact(store.repo, artifact["id"])))
        lookup, need = {}, pictures.missing_opc(export)
        if need:
            wait = sweep_pause(store)
            if wait:
                raise JobFailed(f"{len(need)} SKU(s) have no OPC on the sheet, so OnBuy has to be asked - but OnBuy refuses reads that come too fast and {pictures.SWEEPS_PER_HOUR} full reads "
                                f"of this store's listings (lookups and resubmissions) started in the last hour. Build the ticket again in {wait} minute(s). Nothing was changed.")
            job.set_step(f"Asking OnBuy for the OPC of {len(need)} SKU(s) the sheet has none for")
            lookup_run = dispatch_and_wait(job, store, "listing_lookup.yml", {"skus": ",".join(need)}, "The OnBuy lookup", actor)
            lookup, _ = pictures.read_lookup(run_text(store, lookup_run))
        rows = pictures.build_rows(export, lookup, earlier, resubmitted_map(store))
        links = pictures.links_of(rows)
        job.set_step(f"Opening {len(links)} image links")
        results = pictures.check_links(links, link_fetch or pictures.make_fetch(), progress=job.progress)
        pictures.mark_links(rows, results)
        job.set_step("Writing the files")
        summary = pictures.summarize(rows, len(skus), export, results)
        names = pictures.file_names(store.name, today)
        reply = pictures.reply_text(store.name, summary, names, earlier_entries, len(earlier | {pictures.norm(s) for s in skus}), opts["agent"], opts["signed_by"])
        folder = pictures_dir(store) / job.id
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "attachment.csv").write_text(pictures.attachment_csv(rows), encoding="utf-8", newline="")
        (folder / "reference.csv").write_text(pictures.reference_csv(rows), encoding="utf-8", newline="")
        (folder / "reply.txt").write_text(reply, encoding="utf-8", newline="")
        keep = ("sku", "opc", "source", "tab", "row", "status", "created", "repeat", "resubmitted", "title", "url")
        result = {"job_id": job.id, "built_at": iso(utcnow()), "store": store.id, "day": today, "asked": len(skus), "list_path": path, "summary": summary, "files": names, "opts": opts,
                  "earlier": [e["date"] for e in earlier_entries], "reply": reply, "groups": pictures.resubmit_groups(rows),
                  "rows": [{**{k: r[k] for k in keep}, "dead": len(r["dead"])} for r in rows]}
        (folder / "result.json").write_text(json.dumps(result), encoding="utf-8")
        (pictures_dir(store) / "latest.txt").write_text(job.id, encoding="utf-8")
        for old in sorted((p for p in pictures_dir(store).iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime)[:-10]:
            shutil.rmtree(old, ignore_errors=True)                                     # the last ten builds are kept
        database.audit(actor, store.id, "pictures_ticket_built", {"skus": len(skus), "ticket": summary["ticket"], "job": job.id})
        return {"job_id": job.id, "ticket": summary["ticket"], "asked": len(skus)}

    def ticket_job(job, store, skus, opts, actor):
        try:
            return build_ticket(job, store, skus, opts, actor)
        except GitHubError as exc:
            raise JobFailed(f"GitHub: {exc}") from exc

    def pictures_builds(store):
        """The ticket builds still on disk (the last ten are kept), newest first: day, counts and whether the three files are there - so an older ticket's files stay reachable."""
        out = []
        try:
            folders = [p for p in pictures_dir(store).iterdir() if p.is_dir()]
        except OSError:
            return out
        for folder in sorted(folders, key=lambda p: p.stat().st_mtime, reverse=True)[:10]:
            try:
                r = json.loads((folder / "result.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            out.append({"job_id": r.get("job_id") or folder.name, "day": r.get("day", ""), "built_at": r.get("built_at", ""),
                        "asked": r.get("asked", 0), "ticket": (r.get("summary") or {}).get("ticket", 0), "files": r.get("files") or {}})
        return out

    def load_pictures(store):
        """The Pictures card's data: which tools the store has, the earlier ticket lists, the last ticket build, the resubmission state per tab, what was started from here."""
        paths = {w["path"] for w in client.list_workflows(store.repo) if w["state"] == "active"}
        tools = {"export": "image_links_export.yml" in paths, "lookup": "listing_lookup.yml" in paths, "repair": pictures.REPAIR_WORKFLOW in paths}
        earlier = pictures.earlier_lists(client.list_dir(store.repo, pictures.LIST_DIR, ref=settings.github_ref)) if tools["export"] else []
        latest = load_latest(store)
        history = resubmitted_map(store) if tools["repair"] and latest else {}
        groups = [{**{k: v for k, v in state.items() if k != "todo"}, "left": len(state["todo"])} for state in (pictures.group_state(g, history) for g in (latest or {}).get("groups", []))]
        if latest:
            latest = {**latest, "rows_total": len(latest["rows"]), "rows": latest["rows"][:150]}
        watched = (pictures.REPAIR_WORKFLOW, "image_links_export.yml", "listing_lookup.yml")
        started = settled(store, [d for d in database.recent_dispatches(store.id, limit=80) if d["workflow"] in watched][:10])
        running = jobs.running("pictures", store.id)
        return {"tools": tools, "earlier": earlier, "latest": latest, "groups": groups, "started": started, "running": running.view() if running else None, "builds": pictures_builds(store),
                "canary": pictures.CANARY, "max_skus": pictures.MAX_SKUS, "sweeps": pictures.SWEEPS_PER_HOUR}

    def open_orders(store):
        """The SKUs on orders awaiting dispatch, from the store's latest successful orders lookup -> {run, hours, skus, count}; run is None when there is no such lookup."""
        runs = client.list_runs(store.repo, limit=10, workflow="orders_lookup.yml")
        run = next((r for r in runs if r["status"] == "completed" and r["conclusion"] == "success"), None)
        if not run:
            return {"run": None, "hours": None, "skus": [], "count": 0}
        facts = digest.parse_orders(run_text(store, run))
        return {"run": run, "hours": digest.age_hours(run["created_at"]), "skus": sorted({sku for o in facts["orders"] for sku in o["skus"]}), "count": facts["count"]}

    def delete_tool(store):
        """Whether the store's dup_removal.yml takes an explicit SKU list -> (True, "") or (False, why)."""
        try:
            definition = client.workflow_definition(store.repo, deletion.WORKFLOW, ref=settings.github_ref)
        except GitHubError as exc:
            return False, f"{deletion.WORKFLOW} is not in this repository ({exc})."
        if definition.get("error") or not definition.get("manual"):
            return False, f"{deletion.WORKFLOW} cannot be started from here: {definition.get('error') or 'no manual trigger'}."
        missing = [k for k in ("oos_list_file", "allow_in_stock") if k not in definition["inputs"]]
        if missing:
            return False, f"{deletion.WORKFLOW} of this repository has no {' / '.join(missing)} input yet: it removes duplicates only."
        return True, ""

    def hold_skus(store):
        """Every SKU on the store's hold lists (hold at zero + protected), the way the removal tool protects them."""
        return [e["sku"] for e in catalogue.parse_list(read_text(store, catalogue.HOLD_FILE)) + catalogue.parse_list(read_text(store, catalogue.PROTECTED_FILE))]

    def load_delete(store):
        """The Delete card's data: whether the store's tool takes a list, how fresh the open-order data is, the hold lists' size and what was started from here."""
        available, why = delete_tool(store)
        orders = open_orders(store) if available else {"run": None, "hours": None, "skus": [], "count": 0}
        started = settled(store, [d for d in database.recent_dispatches(store.id, limit=60) if d["workflow"] == deletion.WORKFLOW][:10])
        return {"available": available, "why": why, "orders": orders, "protected": len({catalogue.key(sku) for sku in hold_skus(store)}) if available else 0, "dispatches": started,
                "max_skus": deletion.MAX_SKUS, "orders_max_hours": deletion.ORDERS_MAX_HOURS}

    def delete_prepare(store, body):
        """The list of a request, checked -> (info, error): the SKUs that may go (the pasted list minus the hold lists' and the open orders'), what was kept out and why, the
        fingerprint the plan is matched by, the backup tab and the in-stock switch."""
        today = utcnow().date().isoformat()
        skus, pasted, error = deletion.parse_pasted(body.get("skus"))
        if error:
            return None, error
        orders = open_orders(store)
        to_delete, held, on_orders = deletion.keep_out(skus, hold_skus(store), orders["skus"])
        if not to_delete:
            return None, "Nothing is left to delete: every SKU of the list is on the hold lists or on an open order."
        return {"skus": to_delete, "pasted": pasted, "unique": len(skus), "held": held, "on_orders": on_orders, "fingerprint": deletion.fingerprint(to_delete),
                "backup_tab": deletion.clean_backup_tab(body.get("backup_tab"), today), "allow_in_stock": bool(body.get("allow_in_stock")), "today": today,
                "orders": {"hours": orders["hours"], "count": orders["count"], "run": orders["run"]}}, ""

    def start_workflow(store, workflow_file, inputs, confirm, actor, note=""):
        """The house rules, then the dispatch. Returns a dict for the JSON answer."""
        definition = client.workflow_definition(store.repo, workflow_file, ref=settings.github_ref)
        if definition.get("error"):
            return {"error": f"{workflow_file}: {definition['error']}"}
        if not definition.get("manual"):
            return {"error": f"{definition['name']} has no manual trigger."}
        label, area, risk, apply_input, _ = catalog.classify(workflow_file, definition["name"], definition["inputs"])
        clean = {}
        for key, spec in definition["inputs"].items():
            value = inputs.get(key)
            if value is None or str(value) == "":
                if spec["required"] and not spec["default"]:
                    return {"error": f"The input '{key}' is required."}
                continue
            clean[key] = str(value)
        live = catalog.is_live_request(apply_input, clean) if apply_input else (risk != "read")
        if risk == "danger" and live and not confirm:
            return {"error": f"'{label}' changes the store for real with these inputs. Tick the confirmation box to go ahead."}
        queue = split_queue(client.queue(store.repo))
        if queue["pending"]:
            waiting = ", ".join(r["name"] for r in queue["pending"][:3])
            return {"error": f"A run is already waiting for the store's slot ({waiting}). Starting another now would cancel it - "
                             f"try again once it is running."}
        warn = ""
        if queue["in_progress"] and definition.get("group") == "onbuy-api":
            warn = "It will wait behind " + ", ".join(r["name"] for r in queue["in_progress"][:3]) + "."
        started = client.dispatch(store.repo, workflow_file, clean, ref=settings.github_ref)
        dispatch_id = database.record_dispatch(actor, store.id, workflow_file, clean, status="dispatched", note=note)
        database.audit(actor, store.id, "run", {"workflow": workflow_file, "inputs": clean, "live": live})
        run = client.find_dispatched_run(store.repo, workflow_file, started, attempts=6, wait=5)
        if run:
            database.update_dispatch(dispatch_id, run=run, status=run["status"])
        return {"ok": True, "run": run, "dispatch_id": dispatch_id, "label": label, "live": live, "warning": warn}

    # ---- pages ----------------------------------------------------------------------------------------------------------------
    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        return page(request, "home.html", active="home", statuses=all_status())

    @app.get("/store/{store_id}", response_class=HTMLResponse)
    def store_page(request: Request, store_id: str):
        store = store_or_404(store_id)
        if not store:
            return RedirectResponse("/", status_code=303)
        status = store_status(store, runs_limit=60)
        try:
            available = {w["path"] for w in client.list_workflows(store.repo) if w["state"] == "active"}
        except GitHubError:
            available = set(catalog.RUN_NOW)
        run_now = []
        for path in catalog.RUN_NOW:
            if path in catalog.CATALOG and path in available:
                label, area, risk, apply_input, note = catalog.CATALOG[path]
                run_now.append({"path": path, "label": label, "risk": risk, "apply_input": apply_input, "note": note})
        return page(request, "store.html", active="store", store=store, status=status, run_now=run_now,
                    dispatches=settled(store, database.recent_dispatches(store.id, limit=15)))

    @app.get("/daily", response_class=HTMLResponse)
    def daily(request: Request, hours: int = 24):
        hours = max(1, min(hours, 24 * 14))
        since = iso(utcnow() - timedelta(hours=hours))

        def one(store):
            item = {"store": store, "summary": None, "nightly": None, "budget": {}, "keepa": {}, "orders": None, "error": ""}
            try:
                all_runs = client.list_runs(store.repo, limit=250)        # the window is applied by the digest; the nightly may be older
                if not store.amazon:
                    all_runs = catalog.without_amazon(all_runs)           # eBay-only store: no Amazon sync, no Keepa tokens, no stale Amazon cron
                item["summary"] = digest.summarize_runs(all_runs, since)
                nightly = find_nightly(store, all_runs)
                if nightly:
                    text = run_text(store, nightly)
                    item["nightly"] = {"run": nightly, "facts": digest.parse_nightly(text), "lines": digest.key_lines(text, limit=25)}
                probe = next((r for r in all_runs if r["path"] == "ebay_limit_probe.yml" and r["conclusion"] == "success"), None)
                if probe:
                    item["budget"] = digest.parse_ebay_budget(run_text(store, probe))
                    item["budget"]["run"] = probe
                amazon = next((r for r in all_runs if r["path"] == "run_amazon.yml" and r["conclusion"] == "success"), None)
                if amazon:
                    item["keepa"] = digest.parse_keepa(run_text(store, amazon))
                    item["keepa"]["run"] = amazon
                orders_run = next((r for r in all_runs if r["path"] == "orders_lookup.yml" and r["conclusion"] == "success"), None)
                if orders_run and (digest.age_hours(orders_run["created_at"]) or 0) <= ORDERS_FRESH_HOURS:
                    item["orders"] = digest.parse_orders(run_text(store, orders_run))
                    item["orders"]["run"] = orders_run
            except GitHubError as exc:
                item["error"] = str(exc)
            return item

        items = list(pool.map(one, settings.stores))
        totals = {"runs": sum(i["summary"]["count"] for i in items if i["summary"]),
                  "failures": sum(i["summary"]["failures"] for i in items if i["summary"]),
                  "cancels": sum(i["summary"]["cancels"] for i in items if i["summary"]),
                  "stale": sum(len(i["summary"]["stale"]) for i in items if i["summary"]),
                  "orders": sum(i["orders"]["count"] for i in items if i["orders"]),
                  "due_today": sum(i["orders"]["due_today"] for i in items if i["orders"]),
                  "overdue": sum(i["orders"]["overdue"] for i in items if i["orders"])}
        database.set("last_daily_check", iso(utcnow()))
        return page(request, "daily.html", active="daily", items=items, totals=totals, hours=hours, since=since, problem_nights=problems.NIGHTS)

    # ---- rows that keep failing ---------------------------------------------------------------------------------------------------
    PROBLEMS_FRESH_SECONDS = 900
    problems_cache = {}

    def nightly_history(store, nights=problems.NIGHTS):
        """The store's last `nights` finished nightly runs, newest first. On a store whose backfill embeds the nightly, each day's
        earliest backfill runs are checked for the nightly's markers (the embed runs with the day's first ones); the disk store keeps
        every log looked at, so the week costs one download ever, and a budget caps the first look."""
        host = catalog.EMBEDDED_NIGHTLY.get(store.id)
        if not host:
            runs = client.list_runs(store.repo, limit=100, workflow="nightly_reconcile.yml")
            return [r for r in runs if r["status"] == "completed"][:nights]
        by_day = {}
        for r in client.list_runs(store.repo, limit=250, workflow=host):
            if r["status"] == "completed":
                by_day.setdefault(str(r["created_at"])[:10], []).append(r)
        out, budget = [], 30
        for day in sorted(by_day, reverse=True):
            for r in sorted(by_day[day], key=lambda run: run["created_at"])[:4]:
                if budget <= 0:
                    break
                budget -= 1
                try:
                    if any(m in run_text(store, r) for m in catalog.NIGHTLY_MARKERS):
                        out.append(r)
                        break
                except GitHubError:
                    continue
            if len(out) >= nights or budget <= 0:
                break
        return out

    def problems_for(store, refresh=False):
        """One store's "rows that keep failing" answer, kept for 15 minutes per store (the logs behind it are on disk, but a week of
        runs is still dozens of parses). Per store, so the To do gather can ask inline without recomputing the fleet."""
        hit = problems_cache.get(store.id)
        if hit and not refresh and time.monotonic() - hit[0] < PROBLEMS_FRESH_SECONDS:
            return hit[1]
        nights = []
        for r in nightly_history(store):
            try:
                text = run_text(store, r)
            except GitHubError:
                continue
            nights.append({"day": str(r["created_at"])[:10], "url": r.get("url", ""), "problems": problems.parse_problems(text)})
        answer = problems.gather(nights)
        problems_cache[store.id] = (time.monotonic(), answer)
        return answer

    def problems_fleet(refresh=False):
        def one(store):
            try:
                return {"store": store.id, "name": store.name, "error": "", **problems_for(store, refresh)}
            except GitHubError as exc:
                return {"store": store.id, "name": store.name, "error": str(exc), "nights": [], "kinds": []}

        return {"stores": list(pool.map(one, settings.stores)), "at": iso(utcnow()), "window": problems.NIGHTS}

    @app.get("/api/problems")
    def api_problems(refresh: int = 0):
        """The Daily check page's "Rows that keep failing" card: per store, the per-SKU refusals of the last week's nightlies, grouped
        across nights so the dead rows (refused night after night) stand apart from one bad night."""
        return problems_fleet(bool(refresh))

    orphans_cache = {}

    def orphans_for(store, refresh=False):
        """(the card's answer, every parsed row) from the latest finished content scan - or the latest nightly, which runs
        the same scan - cached like the problems card so repeats are free."""
        hit = orphans_cache.get(store.id)
        if hit and not refresh and time.monotonic() - hit[0] < 600:
            return hit[1], hit[2]
        runs = [r for r in client.list_runs(store.repo, limit=30, workflow="scan_content_mismatch.yml")
                if r["status"] == "completed" and r["conclusion"] == "success"]
        if not runs:
            runs = [r for r in client.list_runs(store.repo, limit=30, workflow="nightly_reconcile.yml")
                    if r["status"] == "completed" and r["conclusion"] in ("success", "failure")]
        if not runs:
            return {"error": "no finished content scan or nightly yet - the card fills after the store's first one"}, []
        run = runs[0]
        parsed = orphans.parse_orphans(run_text(store, run))
        rows = orphans.display_rows(parsed["rows"])
        answer = {"run": {"url": run.get("url", ""), "when": str(run["created_at"])[:16].replace("T", " ")},
                  "count": parsed["count"] if parsed["count"] is not None else len(rows),
                  "in_stock": sum(1 for r in rows if r["stock"] > 0),
                  "rows": rows[:500], "truncated": len(rows) > 500}
        orphans_cache[store.id] = (time.monotonic(), answer, rows)
        return answer, rows

    schedule_cache = {}

    def schedule_for(store, refresh=False):
        """One account's line for the Amazon schedule card: the newest finished dispatcher tick (its AMAZON_PLAN line), and how many syncs
        really started in the last 24 hours. A store whose repository has no dispatcher yet answers on_plan False - never an error."""
        hit = schedule_cache.get(store.id)
        if hit and not refresh and time.monotonic() - hit[0] < 300:
            return hit[1]
        entry = {"id": store.id, "name": store.name}
        try:
            ticks = [r for r in client.list_runs(store.repo, limit=30, workflow="amazon_dispatch.yml")
                     if r["status"] == "completed" and r["conclusion"] == "success"]
        except GitHubError:
            ticks = []                                                  # no such workflow (yet): the store is still on its own cron
        plan = amazon_schedule.parse_plan(run_text(store, ticks[0])) if ticks else None
        tick = {"when": str(ticks[0]["created_at"])[:16].replace("T", " "), "url": ticks[0].get("url", "")} if ticks else None
        syncs_24h, last_sync = 0, None
        try:
            runs = [r for r in client.list_runs(store.repo, limit=40, workflow=amazon.WORKFLOW) if r["event"] == "schedule"]
            floor = utcnow() - timedelta(hours=24)
            started = [r for r in runs if r["conclusion"] != "cancelled" and digest.parse_iso(r["created_at"]) >= floor]
            syncs_24h = len(started)
            if runs:
                last_sync = {"when": str(runs[0]["created_at"])[:16].replace("T", " "), "url": runs[0].get("url", ""),
                             "state": runs[0]["conclusion"] or runs[0]["status"], "planned": runs[0].get("planned", False)}
        except GitHubError:
            pass
        row = amazon_schedule.card_row(entry, plan, syncs_24h, last_sync, tick)
        schedule_cache[store.id] = (time.monotonic(), row)
        return row

    @app.get("/api/amazon/schedule")
    def api_amazon_schedule(refresh: int = 0):
        """The Amazon page's schedule card: per account the plan its dispatcher made (products, runs a day, products per run, how often a
        product is refreshed, the Keepa tokens that spends) and what really ran in the last 24 hours."""
        rows = list(pool.map(lambda s: schedule_for(s, bool(refresh)), [s for s in settings.stores if s.amazon]))
        return {"stores": rows}

    creations_cache = {}

    @app.get("/api/store/{store_id}/creations")
    def api_creations(store_id: str, refresh: int = 0):
        """The store page's Creations card: where the queued products stand, from the latest backfill - how many wait per
        tab, how many the queue has answered with an OPC, and the refusals with OnBuy's own reason."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        hit = creations_cache.get(store.id)
        if hit and not refresh and time.monotonic() - hit[0] < 600:
            return hit[1]
        try:
            runs = [r for r in client.list_runs(store.repo, limit=20, workflow="backfill_onbuy_status.yml")
                    if r["status"] == "completed" and r["conclusion"] in ("success", "failure")]
            if not runs:
                return {"missing": "no finished backfill yet"}
            run = runs[0]
            answer = {**creations.parse_creations(run_text(store, run)),
                      "run": {"url": run.get("url", ""), "when": str(run["created_at"])[:16].replace("T", " ")}}
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        creations_cache[store.id] = (time.monotonic(), answer)
        return answer

    sheet_cache = {}

    @app.get("/api/store/{store_id}/sheet")
    def api_sheet_health(store_id: str, refresh: int = 0):
        """The store page's Sheet health card: the sheet-side facts of the latest eBay and Amazon sync logs - rows missing
        a SKU or a supplier URL, rows fighting over one supplier link, and what the last push created or refused. Fix the
        sheet and the next scheduled run picks the rows up by itself."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        hit = sheet_cache.get(store.id)
        if hit and not refresh and time.monotonic() - hit[0] < 600:
            return hit[1]
        answer = {}
        try:
            for tab, workflow in (("ebay", "run.yml"), ("amazon", "run_amazon.yml")):
                runs = [r for r in client.list_runs(store.repo, limit=20, workflow=workflow)
                        if r["status"] == "completed" and r["conclusion"] in ("success", "failure")]
                if not runs:
                    answer[tab] = {"missing": "no finished sync yet"}
                    continue
                run = runs[0]
                parsed = sheethealth.parse_sheet(run_text(store, run))
                answer[tab] = {**parsed, "issues": sheethealth.issues(parsed),
                               "run": {"url": run.get("url", ""), "when": str(run["created_at"])[:16].replace("T", " "),
                                       "conclusion": run["conclusion"]}}
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        sheet_cache[store.id] = (time.monotonic(), answer)
        return answer

    @app.get("/api/store/{store_id}/orphans")
    def api_orphans(store_id: str, refresh: int = 0):
        """The Catalogue page's Orphans card: every live listing the latest content scan found on NO product tab - the
        manual/import-era population that gets no price fix, no stock sync and no purge. In-stock ones first."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        try:
            answer, _rows = orphans_for(store, bool(refresh))
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        return answer

    @app.get("/api/store/{store_id}/orphans.csv")
    def api_orphans_csv(store_id: str):
        """The full orphan list as a CSV download (sku, price, stock, created, title) - the card caps its table, this holds
        every row, for a ticket, a sheet import or the day a batch is retired."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        try:
            answer, rows = orphans_for(store)
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        if answer.get("error"):
            return JSONResponse({"error": answer["error"]}, status_code=404)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["sku", "price", "stock", "created", "title"])
        for r in rows:
            w.writerow([r["sku"], r["price"], r["stock"], r["created"], r["title"]])
        return Response(buf.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": f'attachment; filename="{store.id}_orphans_{utcnow().date().isoformat()}.csv"'})

    @app.get("/todo", response_class=HTMLResponse)
    def todo_page(request: Request, refresh: int = 0):
        answers = list(pool.map(lambda s: todo_for(s, bool(refresh)), settings.stores))
        items = [i for a in answers for i in a["items"]]
        items.sort(key=lambda i: todo.SEVERITY_ORDER[i["severity"]])
        counts = todo.summarize(items)
        clear = [a["store"] for a in answers if not a["items"] and not a["error"]]
        at = min(a["at"] for a in answers)
        return page(request, "todo.html", active="todo", groups=todo.grouped(items), counts=counts, clear=clear, errors=[a for a in answers if a["error"]], at=at, fresh_seconds=TODO_FRESH_SECONDS)

    @app.get("/api/todo/summary")
    def api_todo_summary():
        """The home page's "Needs you today" band: per store the To do counts and the most urgent item titles, from the same cache as the To do page (the first ask after a restart fills it)."""
        answers = list(pool.map(lambda s: todo_for(s), settings.stores))
        out = []
        for a in answers:
            ordered = sorted(a["items"], key=lambda i: todo.SEVERITY_ORDER[i["severity"]])
            out.append({"store": a["store"].id, "name": a["store"].name, "error": a["error"], "counts": todo.summarize(a["items"]),
                        "top": [{"severity": i["severity"], "title": i["title"]} for i in ordered[:2]]})
        return {"stores": out, "at": iso(min(a["at"] for a in answers))}

    @app.get("/orders", response_class=HTMLResponse)
    def orders(request: Request):
        def one(store):
            item = {"store": store, "run": None, "orders": None, "hours": None, "error": ""}
            try:
                runs = client.list_runs(store.repo, limit=10, workflow="orders_lookup.yml")
                run = next((r for r in runs if r["conclusion"] == "success"), None)
                if run:
                    item["run"] = run
                    item["hours"] = digest.age_hours(run["created_at"])
                    item["orders"] = digest.parse_orders(run_text(store, run))
            except GitHubError as exc:
                item["error"] = str(exc)
            return item

        items = list(pool.map(one, settings.stores))
        totals = {"orders": sum(i["orders"]["count"] for i in items if i["orders"]),
                  "due_today": sum(i["orders"]["due_today"] for i in items if i["orders"]),
                  "overdue": sum(i["orders"]["overdue"] for i in items if i["orders"])}
        return page(request, "orders.html", active="orders", items=items, totals=totals)

    @app.get("/tools", response_class=HTMLResponse)
    def tools(request: Request, store: str = ""):
        current = store_or_404(store) or settings.stores[0]
        areas, error = [], ""
        try:
            workflows = client.list_workflows(current.repo)
            grouped = {key: [] for key, _ in catalog.AREAS}
            for w in workflows:
                if w["state"] != "active" or w["path"] in ("tests.yml",):
                    continue
                label, area, risk, apply_input, note = catalog.classify(w["path"], w["name"])
                grouped[area].append({"path": w["path"], "name": w["name"], "label": label, "risk": risk, "note": note,
                                      "apply_input": apply_input})
            areas = [(key, name, sorted(grouped[key], key=lambda x: x["label"].lower())) for key, name in catalog.AREAS if grouped[key]]
        except GitHubError as exc:
            error = str(exc)
        return page(request, "tools.html", active="tools", store=current, areas=areas, error=error)

    def connection_info():
        """What the Settings and Help pages show about the dashboard's links: who the token is, whether each store's repository answers, the optional Google key."""
        whoami, who_error = {}, ""
        try:
            whoami = client.whoami()
        except GitHubError as exc:
            who_error = str(exc)
        checks = list(pool.map(lambda s: (s, client.repo_ok(s.repo)), settings.stores))
        google_file = settings.google_credentials_file
        return {"whoami": whoami, "who_error": who_error, "checks": checks, "token_set": bool(settings.github_token),
                "google_ok": bool(google_file) and os.path.exists(google_file), "google_file": google_file}

    def pretty_detail(detail):
        """The audit's detail column as words, not JSON: {"name": "X", "value": "Y"} -> name: X, value: Y (long values cut)."""
        try:
            d = json.loads(detail) if isinstance(detail, str) else detail
            if isinstance(d, dict):
                return ", ".join(f"{k}: {str(v)[:90]}" for k, v in d.items())
        except (ValueError, TypeError):
            pass
        return str(detail or "")

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page(request: Request):
        audit_rows = [{**dict(a), "detail": pretty_detail(dict(a).get("detail"))} for a in database.recent_audit(limit=40)]
        return page(request, "settings.html", active="settings", **connection_info(), audit=audit_rows, stores_file=str(settings.stores_file),
                    last_daily=database.get("last_daily_check"), employees=database.employees(), roles=auth_module.ROLES, logstats=log_store.stats(),
                    ghstats={"reused": getattr(client, "answers_reused", 0), "fetched": getattr(client, "answers_fetched", 0)})

    @app.get("/help", response_class=HTMLResponse)
    def help_page(request: Request):
        return page(request, "help.html", active="help", **connection_info())

    # ---- the store registry (Settings; admin once the login is on) ---------------------------------------------------------------
    @app.post("/api/stores")
    async def api_store_add(request: Request):
        """Onboard a store to this dashboard: validate, prove the token can reach its repository, write config/stores.json and add it
        live - every page grows the store's chip at once. Nothing on GitHub or OnBuy changes; the store's own secrets and workflows
        live in its repository as always. Other running copies of the dashboard see it at their next start."""
        body = await request.json()
        store_id, why = config_module.clean_store_id(body.get("id"))
        if why:
            return JSONResponse({"error": why}, status_code=400)
        repo, why = config_module.clean_repo(body.get("repo"))
        if why:
            return JSONResponse({"error": why}, status_code=400)
        name = re.sub(r"\s+", " ", str(body.get("name") or "")).strip()[:40]
        if not name:
            return JSONResponse({"error": "Give the store a name."}, status_code=400)
        if any(s.id == store_id for s in settings.stores):
            return JSONResponse({"error": f"'{store_id}' is already a store on this dashboard."}, status_code=400)
        if any(s.repo.lower() == repo.lower() for s in settings.stores):
            return JSONResponse({"error": f"{repo} already belongs to the store '{next(s.id for s in settings.stores if s.repo.lower() == repo.lower())}'."}, status_code=400)
        ok, why = client.repo_ok(repo)
        if not ok:
            return JSONResponse({"error": f"The GitHub token cannot use {repo}: {why}. Give the token access to the repository first - every card reads and starts that repository's jobs."}, status_code=400)
        store = Store(id=store_id, name=name, repo=repo, sheet=str(body.get("sheet") or "").strip(),
                      product_tab=str(body.get("product_tab") or "").strip() or "Sheet1",
                      amazon_tab=str(body.get("amazon_tab") or "").strip() or "Amazon",
                      sheet_url=str(body.get("sheet_url") or "").strip())
        settings.stores.append(store)
        try:
            config_module.save_stores(settings.stores_file, settings.stores)
        except OSError as exc:
            settings.stores.remove(store)
            return JSONResponse({"error": f"Could not write the stores file: {exc}"}, status_code=500)
        database.audit(auth.actor(request), store_id, "store_added", {"repo": repo, "name": name})
        return {"ok": True, "store": {"id": store.id, "name": store.name, "repo": store.repo}}

    @app.post("/api/stores/{store_id}/remove")
    async def api_store_remove(request: Request, store_id: str):
        """Take a store off this dashboard (the registry file + the live list). Nothing on GitHub, OnBuy or its sheet changes - the
        store's jobs keep running without the dashboard watching them."""
        body = await request.json()
        store = next((s for s in settings.stores if s.id == store_id), None)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        if len(settings.stores) == 1:
            return JSONResponse({"error": "The last store stays: a dashboard with no stores cannot show anything."}, status_code=400)
        if not body.get("confirm"):
            return JSONResponse({"error": "Tick the confirmation box: every page loses this store's chip (the store itself keeps running untouched)."}, status_code=400)
        settings.stores.remove(store)
        try:
            config_module.save_stores(settings.stores_file, settings.stores)
        except OSError as exc:
            settings.stores.append(store)
            return JSONResponse({"error": f"Could not write the stores file: {exc}"}, status_code=500)
        database.audit(auth.actor(request), store_id, "store_removed", {"repo": store.repo})
        return {"ok": True}

    EXPECTED_SECRETS = ("ONBUY_CONSUMER_KEY", "ONBUY_SECRET_KEY", "ONBUY_SELLER_ID", "ONBUY_SITE_ID", "GOOGLE_CREDENTIALS", "KEEPA_API_KEY")

    @app.get("/api/stores/{store_id}/secrets")
    def api_store_secrets(store_id: str):
        """The store repository's Actions secrets - NAMES and update times only (GitHub never returns a value to anyone), plus which
        of the usual names are still missing. For onboarding a new store without ever opening GitHub's settings."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        try:
            secrets_list = client.list_secrets(store.repo)
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        have = {s["name"] for s in secrets_list}
        return {"repo": store.repo, "secrets": secrets_list, "missing": [n for n in EXPECTED_SECRETS if n not in have]}

    @app.post("/api/stores/{store_id}/secrets")
    async def api_store_secret_set(request: Request, store_id: str):
        """Set one Actions secret on the store's repository. The value is sealed with the repository's public key on this machine and
        only the ciphertext goes to GitHub; it is never stored, logged, audited or echoed - the audit row carries the NAME only."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        name = str(body.get("name") or "").strip().upper()
        value = str(body.get("value") or "")
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,99}", name):
            return JSONResponse({"error": "A secret's name is capital letters, digits and underscores (e.g. ONBUY_CONSUMER_KEY)."}, status_code=400)
        if not value.strip():
            return JSONResponse({"error": "The value is empty - nothing was sent."}, status_code=400)
        if len(value) > 60_000:
            return JSONResponse({"error": "GitHub takes secrets up to 48 KB - this value is bigger."}, status_code=400)
        try:
            client.set_secret(store.repo, name, value)
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        database.audit(auth.actor(request), store_id, "secret_set", {"name": name})
        return {"ok": True, "name": name}

    @app.get("/api/stores/{store_id}/readiness")
    def api_store_readiness(store_id: str):
        """What the store still needs before it runs like its siblings: the usual secrets that are missing, the secret and
        variable names at least half the OTHER stores carry (a variable's value is offered only when the siblings agree on
        one), and the store's workflows with their state - parked ones first. Built for the moment after 'Add a store'."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        try:
            mine = {"secrets": {s["name"] for s in client.list_secrets(store.repo)},
                    "variables": {v["name"]: str(v.get("value") or "") for v in client.list_variables(store.repo)},
                    "workflows": client.list_workflows(store.repo)}
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        others = {}
        for s in settings.stores:
            if s.id == store.id:
                continue
            try:
                others[s.id] = {"secrets": {x["name"] for x in client.list_secrets(s.repo)},
                                "variables": {v["name"]: str(v.get("value") or "") for v in client.list_variables(s.repo)}}
            except GitHubError:
                continue                                        # a sibling the token cannot read just stays out of the comparison
        out = readiness.report(mine, others, EXPECTED_SECRETS, amazon=store.amazon)
        out["repo"] = store.repo
        return out

    @app.post("/api/stores/{store_id}/workflows")
    async def api_store_workflow_state(request: Request, store_id: str):
        """Enable or disable one workflow file on the store's repository (the activation sweep as single clicks). Enabling
        starts its schedule from the next tick; disabling parks it - the file itself is untouched either way."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        path = str(body.get("path") or "").strip()
        action = str(body.get("action") or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]+\.ya?ml", path):
            return JSONResponse({"error": "bad workflow file name"}, status_code=400)
        if action not in ("enable", "disable"):
            return JSONResponse({"error": "action is enable or disable"}, status_code=400)
        if not body.get("confirm"):
            return JSONResponse({"error": "Tick the confirmation box: enabling starts the workflow's schedule from its next tick."}, status_code=400)
        try:
            if path not in {w["path"] for w in client.list_workflows(store.repo)}:
                return JSONResponse({"error": f"{path} is not a workflow of {store.repo}"}, status_code=400)
            client.set_workflow_state(store.repo, path, action == "enable")
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        database.audit(auth.actor(request), store.id, "workflow_" + action, {"path": path})
        return {"ok": True, "path": path, "state": "active" if action == "enable" else "disabled_manually"}

    @app.get("/api/backup")
    def api_backup(request: Request):
        """One zip of everything the dashboard itself remembers - the database (employees, audit, tick-marks, started runs) and the
        data folder's small files (ticket builds, the stores file). The run-log store stays out: GitHub still has every log. Restore =
        unzip into DATA_DIR before the first start. Admin only once the login is on: the zip holds the accounts and the audit."""
        if auth.enabled and auth.role(request) != "admin":
            return JSONResponse({"error": "Only an admin code downloads the backup: it holds the accounts and the audit."}, status_code=403)
        day = utcnow().date().isoformat()
        root = Path(settings.data_dir)
        snapshot = root / f".backup-{secrets.token_hex(4)}.db"
        buf = io.BytesIO()
        try:
            database.backup_to(snapshot)
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                z.write(snapshot, "data/dashboard.db")
                skipped = []
                for p in sorted(root.rglob("*")):
                    rel = p.relative_to(root)
                    if p.is_dir() or rel.parts[0] == "logs" or p.name == "dashboard.db" or p.name == snapshot.name or p.suffix in (".db-journal", ".tmp"):
                        continue
                    if p.stat().st_size > 20_000_000:
                        skipped.append(rel.as_posix())
                        continue
                    z.write(p, f"data/{rel.as_posix()}")
                stores_file = Path(settings.stores_file)
                if stores_file.is_file():
                    z.write(stores_file, "stores.json")
                z.writestr("README.txt", f"Best View Glazing dashboard backup, {day}.\n\n"
                           "Restore: put the data folder into the new dashboard's DATA_DIR (next to run.py by default) BEFORE the first start,\n"
                           "and stores.json where the old one was. The run-log store is not in here: logs come back from GitHub as they are needed.\n"
                           + (("\nLeft out (bigger than 20 MB): " + ", ".join(skipped) + "\n") if skipped else ""))
        finally:
            snapshot.unlink(missing_ok=True)
        database.audit(auth.actor(request), "-", "backup", "")
        return Response(buf.getvalue(), media_type="application/zip",
                        headers={"Content-Disposition": f'attachment; filename="best-view-glazing-dashboard-backup-{day}.zip"'})

    # ---- login -----------------------------------------------------------------------------------------------------------------
    @app.get("/login", response_class=HTMLResponse)
    def login_form(request: Request, next: str = "/"):
        if not auth.enabled:
            return RedirectResponse("/", status_code=303)
        return page(request, "login.html", active="", next=next, error="")

    def employee_for(code):
        """The active employee a typed code belongs to, or None. Every active hash is tried: there is no name field on the sign-in form, exactly like the stores' other dashboard."""
        for e in database.employee_secrets():
            if auth_module.verify_code(code, e["salt"], e["code_hash"]):
                return e
        return None

    @app.post("/login")
    def login(request: Request, password: str = Form(""), next: str = Form("/")):
        wait = throttle.wait_seconds()
        if wait:
            return page(request, "login.html", active="", next=next,
                        error=f"Too many wrong tries in a row: sign-in is paused for another {max(1, math.ceil(wait / 60))} minute(s). It unlocks by itself.")
        if auth.check_password(password):
            name, role = "owner", "admin"
        else:
            emp = employee_for(password)
            if not emp:
                throttle.record_failure()
                database.audit("anonymous", "-", "login_failed", "")
                return page(request, "login.html", active="", next=next, error="That is not the password or an employee code.")
            name, role = emp["name"], emp["role"]
        resp = RedirectResponse(next if next.startswith("/") else "/", status_code=303)
        resp.set_cookie(COOKIE, auth.cookie_value(name, role), httponly=True, samesite="lax", max_age=12 * 3600)
        database.audit(name, "-", "login", {"role": role} if name != "owner" else "")
        return resp

    @app.get("/logout")
    def logout():
        resp = RedirectResponse("/login", status_code=303)
        resp.delete_cookie(COOKIE)
        return resp

    # ---- employees (admin only - the middleware refuses every other role) --------------------------------------------------------
    @app.post("/api/employees")
    async def api_employee_add(request: Request):
        """A new employee: the admin types the name and picks the role; the code is made here and shown exactly once - only its salted hash is kept."""
        body = await request.json()
        name = re.sub(r"\s+", " ", str(body.get("name") or "")).strip()[:40]
        role = str(body.get("role") or "")
        if not name:
            return JSONResponse({"error": "Give the employee a name."}, status_code=400)
        if role not in auth_module.ROLES:
            return JSONResponse({"error": "The role is view, operate or admin."}, status_code=400)
        code, salt = auth_module.new_code(), auth_module.new_salt()
        try:
            emp_id = database.add_employee(name, role, salt, auth_module.hash_code(code, salt))
        except sqlite3.IntegrityError:
            return JSONResponse({"error": f"There already is an employee called {name}."}, status_code=400)
        database.audit(auth.actor(request), "-", "employee_added", {"name": name, "role": role})
        return {"ok": True, "employee": database.employee(emp_id), "code": code}

    @app.post("/api/employees/{emp_id}")
    async def api_employee_change(request: Request, emp_id: int):
        """Change the role, or switch the sign-in off and on. A new role counts from the employee's NEXT sign-in (the cookie carries the old one for up to 12 hours)."""
        body = await request.json()
        changes = {}
        if "role" in body:
            if body["role"] not in auth_module.ROLES:
                return JSONResponse({"error": "The role is view, operate or admin."}, status_code=400)
            changes["role"] = body["role"]
        if "active" in body:
            changes["active"] = bool(body["active"])
        if not changes:
            return JSONResponse({"error": "Nothing to change."}, status_code=400)
        emp = database.set_employee(emp_id, **changes)
        if not emp:
            return JSONResponse({"error": "unknown employee"}, status_code=404)
        database.audit(auth.actor(request), "-", "employee_changed", {"name": emp["name"], **changes})
        return {"ok": True, "employee": emp}

    @app.post("/api/employees/{emp_id}/code")
    async def api_employee_code(request: Request, emp_id: int):
        """A fresh code (the old one stops working at once - a signed-in session lasts until its cookie runs out). Shown exactly once."""
        code, salt = auth_module.new_code(), auth_module.new_salt()
        emp = database.set_employee(emp_id, salt=salt, code_hash=auth_module.hash_code(code, salt))
        if not emp:
            return JSONResponse({"error": "unknown employee"}, status_code=404)
        database.audit(auth.actor(request), "-", "employee_new_code", {"name": emp["name"]})
        return {"ok": True, "employee": emp, "code": code}

    @app.post("/api/employees/{emp_id}/delete")
    async def api_employee_delete(request: Request, emp_id: int):
        emp = database.employee(emp_id)
        if not emp:
            return JSONResponse({"error": "unknown employee"}, status_code=404)
        database.delete_employee(emp_id)
        database.audit(auth.actor(request), "-", "employee_removed", {"name": emp["name"]})
        return {"ok": True}

    # ---- JSON for the buttons --------------------------------------------------------------------------------------------------
    @app.post("/api/store/{store_id}/run")
    async def api_run(request: Request, store_id: str):
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        workflow = str(body.get("workflow") or "").strip()
        if not workflow.endswith(".yml") or "/" in workflow:
            return JSONResponse({"error": "bad workflow name"}, status_code=400)
        try:
            result = start_workflow(store, workflow, body.get("inputs") or {}, bool(body.get("confirm")), auth.actor(request),
                                    note=str(body.get("note") or "")[:200])
        except GitHubError as exc:
            result = {"error": str(exc)}
        return JSONResponse(result, status_code=400 if "error" in result else 200)

    @app.get("/api/store/{store_id}/run/{run_id}")
    def api_run_status(store_id: str, run_id: int, facts: int = 1):
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        try:
            run = client.run(store.repo, run_id)
            out = {"run": run}
            if run["status"] == "completed" and facts:
                out.update(run_facts(store, run))
                for d in database.recent_dispatches(store.id, limit=30):
                    if d["run_id"] == run_id and d["status"] != run["conclusion"]:
                        database.update_dispatch(d["id"], status=run["conclusion"] or "completed")
            return out
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)

    @app.get("/api/store/{store_id}/queue")
    def api_queue(store_id: str):
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        try:
            return client.queue(store.repo)
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)

    @app.get("/api/store/{store_id}/workflow/{workflow}")
    def api_workflow(store_id: str, workflow: str):
        store = store_or_404(store_id)
        if not store or not workflow.endswith(".yml") or "/" in workflow:
            return JSONResponse({"error": "unknown store or workflow"}, status_code=404)
        try:
            definition = client.workflow_definition(store.repo, workflow, ref=settings.github_ref)
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        label, area, risk, apply_input, note = catalog.classify(workflow, definition["name"], definition["inputs"])
        definition.update({"label": label, "area": area, "risk": risk, "apply_input": apply_input, "note": note})
        return definition

    @app.get("/api/store/{store_id}/variables")
    def api_variables(store_id: str):
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        try:
            return {"variables": client.list_variables(store.repo)}
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)

    @app.post("/api/store/{store_id}/variables")
    async def api_set_variable(request: Request, store_id: str):
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        name = str(body.get("name") or "").strip().upper()
        value = str(body.get("value") if body.get("value") is not None else "")
        if not name.replace("_", "").isalnum():
            return JSONResponse({"error": "bad variable name"}, status_code=400)
        if not body.get("confirm"):
            return JSONResponse({"error": "Tick the confirmation box: the next runs of the store will use the new value."}, status_code=400)
        try:
            client.set_variable(store.repo, name, value)
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        database.audit(auth.actor(request), store.id, "set_variable", {"name": name, "value": value})
        return {"ok": True, "name": name, "value": value}

    @app.get("/api/store/{store_id}/dispatches")
    def api_dispatches(store_id: str):
        return {"dispatches": database.recent_dispatches(store_id, limit=20)}

    # ---- pricing ----------------------------------------------------------------------------------------------------------------
    @app.get("/pricing", response_class=HTMLResponse)
    def pricing_page(request: Request, store: str = ""):
        current = store_or_404(store) or settings.stores[0]
        data = {"setting_raw": "", "knob": None, "code": None, "schedule": None, "has_even_margins": False, "has_audit": False}
        error = ""
        try:
            data = load_schedule(current)
        except GitHubError as exc:
            error = str(exc)
        described = pricing.describe_bands(data["schedule"]["bands"]) if data["schedule"] else []
        return page(request, "pricing.html", active="pricing", store=current, error=error, described=described,
                    schedule_json=json.dumps(data["schedule"]) if data["schedule"] else "null", **data)

    @app.post("/api/store/{store_id}/pricing/preview")
    async def api_pricing_preview(request: Request, store_id: str):
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        try:
            current = load_schedule(store)
            bands, overrides, error = proposed_schedule(body, current["schedule"])
            if error:
                return JSONResponse({"error": error}, status_code=400)
            if not current["has_even_margins"]:
                return JSONResponse({"error": "This store has no even-margins workflow yet."}, status_code=400)
            setting = pricing.build_setting(current["schedule"], bands, overrides)
            result = start_workflow(store, "even_margins.yml", {"apply": "no", "max_changes": "20000", "schedule_json": setting},
                                    False, auth.actor(request), note="pricing preview")
        except GitHubError as exc:
            result = {"error": str(exc)}
        if "error" not in result:
            result["setting"] = setting
        return JSONResponse(result, status_code=400 if "error" in result else 200)

    @app.post("/api/store/{store_id}/pricing/apply")
    async def api_pricing_apply(request: Request, store_id: str):
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        if not body.get("confirm"):
            return JSONResponse({"error": "Tick the confirmation box: this re-prices the store's rows on the sheet."}, status_code=400)
        try:
            current = load_schedule(store)
            bands, overrides, error = proposed_schedule(body, current["schedule"])
            if error:
                return JSONResponse({"error": error}, status_code=400)
            if not current["has_even_margins"]:
                return JSONResponse({"error": "This store has no even-margins workflow yet."}, status_code=400)
            queue = split_queue(client.queue(store.repo))
            if queue["pending"]:
                return JSONResponse({"error": "A run is waiting for the store's slot - apply once it is running."}, status_code=400)
            setting = pricing.build_setting(current["schedule"], bands, overrides)
            client.set_variable(store.repo, "PROFIT_SCHEDULE", setting)
            database.audit(auth.actor(request), store.id, "set_variable", {"name": "PROFIT_SCHEDULE", "value": setting})
            result = start_workflow(store, "even_margins.yml", {"apply": "yes", "max_changes": "20000", "schedule_json": setting},
                                    True, auth.actor(request), note="pricing apply")
        except GitHubError as exc:
            result = {"error": str(exc)}
        if "error" not in result:
            result["setting"] = setting
        return JSONResponse(result, status_code=400 if "error" in result else 200)

    # ---- catalogue --------------------------------------------------------------------------------------------------------------
    @app.get("/catalogue", response_class=HTMLResponse)
    def catalogue_page(request: Request, store: str = ""):
        current = store_or_404(store) or settings.stores[0]
        data, error = None, ""
        try:
            data = load_catalogue(current)
        except GitHubError as exc:
            error = str(exc)
        return page(request, "catalogue.html", active="catalogue", store=current, error=error, data=data)

    def edit_lists(store, edits):
        """Commit the edits [(path, transform, message)] one file at a time -> [{file, changed, commit, url}]. The caller orders them so a failure half-way leaves
        the safe state."""
        done = []
        for path, transform, message in edits:
            done.append({"file": path, **client.update_file(store.repo, path, transform, message, ref=settings.github_ref)})
        return done

    def short_names(skus):
        return ", ".join(skus[:3]) + (f" and {len(skus) - 3} more" if len(skus) > 3 else "")

    @app.post("/api/store/{store_id}/catalogue/release")
    async def api_catalogue_release(request: Request, store_id: str):
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        skus, error = catalogue.split_skus(body.get("skus"))
        if error:
            return JSONResponse({"error": error}, status_code=400)
        if not body.get("confirm"):
            return JSONResponse({"error": "Tick the confirmation box: a released listing gets its stock back at the next sync."}, status_code=400)
        same_product = bool(body.get("same_product"))
        try:
            hold, protected = read_text(store, catalogue.HOLD_FILE), read_text(store, catalogue.PROTECTED_FILE)
            entries = {catalogue.key(e["sku"]): e for e in catalogue.merge_holds(hold, protected, read_text(store, catalogue.SAME_FILE))}
            unknown = [s for s in skus if catalogue.key(s) not in entries]
            if unknown:
                return JSONResponse({"error": f"Not on any hold list: {', '.join(unknown)}."}, status_code=400)
            today = utcnow().date().isoformat()
            names = short_names(skus)
            edits = []
            if same_product:      # the same-product list first: if a later edit fails the listing simply stays frozen, the safe side
                notes = {s: catalogue.same_note(entries[catalogue.key(s)]) for s in skus}
                edits.append((catalogue.SAME_FILE, lambda t: catalogue.add_skus(t, skus, catalogue.same_header(today), notes)[0],
                              f"dashboard: {names} checked by hand - the same product"))
            for path in (catalogue.PROTECTED_FILE, catalogue.HOLD_FILE):
                edits.append((path, lambda t: catalogue.remove_skus(t, skus)[0], f"dashboard: release {names} from {path}"))
            done = edit_lists(store, edits)
        except GitHubError as exc:
            return JSONResponse({"error": f"{exc} - reload to see which lists were already edited."}, status_code=502)
        database.audit(auth.actor(request), store.id, "release", {"skus": skus, "same_product": same_product, "files": [d["file"] for d in done if d["changed"]]})
        return {"ok": True, "released": skus, "same_product": same_product, "files": done}

    @app.post("/api/store/{store_id}/catalogue/freeze")
    async def api_catalogue_freeze(request: Request, store_id: str):
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        skus, error = catalogue.split_skus(body.get("skus"))
        reason = str(body.get("reason") or "").strip()
        if error:
            return JSONResponse({"error": error}, status_code=400)
        if len(reason) < 3:
            return JSONResponse({"error": "Say why, in a few words: the reason stays in the list for whoever reads it next."}, status_code=400)
        if not body.get("confirm"):
            return JSONResponse({"error": "Tick the confirmation box: these listings stop selling."}, status_code=400)
        today = utcnow().date().isoformat()
        names = short_names(skus)
        notes = {s: reason[:60] for s in skus}
        try:
            done = edit_lists(store, [(path, lambda t: catalogue.add_skus(t, skus, catalogue.freeze_header(today, reason), notes)[0], f"dashboard: freeze {names} ({reason[:60]})")
                                      for path in (catalogue.HOLD_FILE, catalogue.PROTECTED_FILE)])
            zero, zero_error = None, ""
            if body.get("zero_now"):
                result = start_workflow(store, "zero_listings.yml", {"skus": ",".join(skus), "dry_run": "no"}, True, auth.actor(request), note="freeze")
                zero, zero_error = (result, "") if "error" not in result else (None, result["error"])
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        database.audit(auth.actor(request), store.id, "freeze", {"skus": skus, "reason": reason, "zero_now": bool(zero)})
        return {"ok": True, "frozen": skus, "files": done, "zero": zero, "zero_error": zero_error}

    @app.post("/api/store/{store_id}/catalogue/delete")
    async def api_catalogue_delete(request: Request, store_id: str):
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        skus, error = catalogue.split_skus(body.get("skus"))
        if error:
            return JSONResponse({"error": error}, status_code=400)
        dry = str(body.get("dry_run") or "yes").strip().lower() != "no"
        if not dry and not body.get("confirm"):
            return JSONResponse({"error": "Tick the confirmation box: this deletes the sheet rows (backed up first) and the OnBuy listings."}, status_code=400)
        inputs = {"skus": ",".join(skus), "backup_tab": f"Removed {utcnow().date().isoformat()}", "max_remove": "40", "keep_at": "0.5", "dry_run": "yes" if dry else "no"}
        try:
            result = start_workflow(store, "remove_wrong_content.yml", inputs, bool(body.get("confirm")), auth.actor(request), note="catalogue delete" + (" check" if dry else ""))
        except GitHubError as exc:
            result = {"error": str(exc)}
        return JSONResponse(result, status_code=400 if "error" in result else 200)

    @app.post("/api/store/{store_id}/catalogue/forget")
    async def api_catalogue_forget(request: Request, store_id: str):
        """Drop the hold-list lines of listings a finished live removal deleted. The server works out which those are, so a SKU that was not deleted cannot be dropped here."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        try:
            hold, protected = read_text(store, catalogue.HOLD_FILE), read_text(store, catalogue.PROTECTED_FILE)
            gone = [h["sku"] for h in catalogue.mark_deleted(catalogue.merge_holds(hold, protected), deleted_by_runs(store, client.list_runs(store.repo, limit=20, workflow="remove_wrong_content.yml"))) if h["deleted_by"]]
            if not gone:
                return {"ok": True, "forgotten": [], "files": []}
            names = short_names(gone)
            done = edit_lists(store, [(path, lambda t: catalogue.remove_skus(t, gone)[0], f"dashboard: {names} deleted by a removal run - dropped from {path}")
                                      for path in (catalogue.PROTECTED_FILE, catalogue.HOLD_FILE)])
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        database.audit(auth.actor(request), store.id, "forget", {"skus": gone, "files": [d["file"] for d in done if d["changed"]]})
        return {"ok": True, "forgotten": gone, "files": done}

    @app.post("/api/store/{store_id}/catalogue/purge")
    async def api_catalogue_purge(request: Request, store_id: str):
        """Read-only: a dry run of the purge, or (suspended=true) the list of purged listings OnBuy would not delete."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        inputs = {"dry_run": "yes", "list_suspended": "yes"} if body.get("suspended") else {"dry_run": "yes"}
        try:
            result = start_workflow(store, "purge_dead_rows.yml", inputs, False, auth.actor(request), note="purge " + ("suspended list" if body.get("suspended") else "dry run"))
        except GitHubError as exc:
            result = {"error": str(exc)}
        return JSONResponse(result, status_code=400 if "error" in result else 200)

    # ---- delete by list ---------------------------------------------------------------------------------------------------------
    @app.get("/delete", response_class=HTMLResponse)
    def delete_page(request: Request, store: str = ""):
        current = store_or_404(store) or settings.stores[0]
        data, error = None, ""
        try:
            data = load_delete(current)
        except GitHubError as exc:
            error = str(exc)
        return page(request, "delete.html", active="delete", store=current, error=error, data=data, today=utcnow().date().isoformat())

    def delete_summary(info):
        """The part of a prepared list the page shows (the SKU lists cut to what fits)."""
        return {"count": len(info["skus"]), "pasted": info["pasted"], "unique": info["unique"], "fingerprint": info["fingerprint"], "backup_tab": info["backup_tab"],
                "allow_in_stock": info["allow_in_stock"], "held": info["held"][:100], "held_count": len(info["held"]), "on_orders": info["on_orders"][:100],
                "on_orders_count": len(info["on_orders"]), "orders_hours": info["orders"]["hours"], "orders_count": info["orders"]["count"]}

    async def delete_request(request, store_id):
        """The checks every request of the Delete card starts with -> (store, body, info, error response)."""
        store = store_or_404(store_id)
        if not store:
            return None, None, None, JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        try:
            ok, why = delete_tool(store)
            if not ok:
                return store, body, None, JSONResponse({"error": why}, status_code=400)
            info, error = delete_prepare(store, body)
        except GitHubError as exc:
            return store, body, None, JSONResponse({"error": str(exc)}, status_code=502)
        if error:
            return store, body, None, JSONResponse({"error": error}, status_code=400)
        return store, body, info, None

    @app.post("/api/store/{store_id}/delete/check")
    async def api_delete_check(request: Request, store_id: str):
        store, body, info, refused = await delete_request(request, store_id)
        return refused or {"ok": True, **delete_summary(info)}

    @app.post("/api/store/{store_id}/delete/plan")
    async def api_delete_plan(request: Request, store_id: str):
        """Commit the list, then run the removal tool as a dry run on it."""
        store, body, info, refused = await delete_request(request, store_id)
        if refused:
            return refused
        path = deletion.list_path(store.id, info["today"], info["fingerprint"])
        try:
            written = client.update_file(store.repo, path, lambda old: deletion.list_text(store.name, info["skus"], info["today"]),
                                         f"dashboard: delete list of {store.name} ({len(info['skus'])} SKUs, for the plan)", ref=settings.github_ref)
            inputs = deletion.build_inputs(path, len(info["skus"]), info["backup_tab"], info["allow_in_stock"], dry=True)
            result = start_workflow(store, deletion.WORKFLOW, inputs, False, auth.actor(request), note=f"delete plan, {len(info['skus'])} SKU(s)")
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        if "error" in result:
            return JSONResponse(result, status_code=400)
        database.audit(auth.actor(request), store.id, "delete_plan", {"list": path, "skus": len(info["skus"]), "kept_out": len(info["held"]) + len(info["on_orders"])})
        return {**result, **delete_summary(info), "list": {"path": path, "changed": written["changed"], "commit": written["commit"],
                                                            "url": f"https://github.com/{store.repo}/blob/{settings.github_ref}/{path}"}}

    @app.post("/api/store/{store_id}/delete/apply")
    async def api_delete_apply(request: Request, store_id: str):
        """The real run: only for a list whose plan (a dry run of exactly this list, same options) finished well in the last day, with open-order data from the last day."""
        store, body, info, refused = await delete_request(request, store_id)
        if refused:
            return refused
        if not body.get("confirm"):
            return JSONResponse({"error": "Tick the confirmation box: this deletes the sheet rows (copied to the backup tab first) and the OnBuy listings."}, status_code=400)
        hours = info["orders"]["hours"]
        if info["orders"]["run"] is None or hours is None or hours > deletion.ORDERS_MAX_HOURS:
            return JSONResponse({"error": "The open-orders data is more than a day old (or missing): refresh it on the Orders page, then plan again. A listing on an open order must stay."}, status_code=400)
        try:
            plan = deletion.find_plan(settled(store, database.recent_dispatches(store.id, limit=60)), info["fingerprint"], info["backup_tab"], info["allow_in_stock"])
            if not plan:
                return JSONResponse({"error": "There is no finished plan for exactly this list and these options (or it is more than a day old). Press Plan first and wait for it to finish."}, status_code=400)
            path = plan["inputs"]["oos_list_file"]
            inputs = deletion.build_inputs(path, len(info["skus"]), info["backup_tab"], info["allow_in_stock"], dry=False)
            result = start_workflow(store, deletion.WORKFLOW, inputs, True, auth.actor(request), note=f"delete for real, {len(info['skus'])} SKU(s), plan run {plan.get('run_id')}")
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        if "error" in result:
            return JSONResponse(result, status_code=400)
        database.audit(auth.actor(request), store.id, "delete_apply", {"list": path, "skus": len(info["skus"]), "plan_run": plan.get("run_id"), "allow_in_stock": info["allow_in_stock"]})
        return {**result, **delete_summary(info), "list": {"path": path, "url": f"https://github.com/{store.repo}/blob/{settings.github_ref}/{path}"}}

    # ---- suspended listings (only a person can delete them) ---------------------------------------------------------------------
    SUSPENDED_FRESH_SECONDS = 600
    suspended_cache = {}

    def suspended_reports(store):
        """Every tool's SUSPENDED reports for one store, read from the recent runs' logs (the disk store keeps them, so repeats are free)."""
        reports = []

        def scan(workflow, parser, source, keep):
            try:
                runs = [r for r in client.list_runs(store.repo, limit=30, workflow=workflow)
                        if r["status"] == "completed" and r["conclusion"] in ("success", "failure")][:keep]
            except GitHubError:
                return
            for run in runs:
                try:
                    facts = parser(run_text(store, run))
                except GitHubError:
                    continue
                for item in facts.get("suspended") or []:
                    sku, title = (item["sku"], item.get("title", "")) if isinstance(item, dict) else (item, "")
                    reports.append(suspended.report(sku, run["created_at"], suspended.SOURCES[source], run.get("url", ""), title))

        scan(deletion.WORKFLOW, deletion.parse_guarded, "delete", 12)
        scan("yra_removal.yml", deletion.parse_guarded, "delete", 6)        # YRA's delete-by-list workflow prints the same SUSPENDED lines
        scan("purge_dead_rows.yml", catalogue.parse_purge, "purge", 6)
        scan("remove_wrong_content.yml", catalogue.parse_removal, "removal", 6)
        for r in nightly_history(store):
            try:
                parsed = problems.parse_problems(run_text(store, r))
            except GitHubError:
                continue
            for sku in parsed.get("suspended") or []:
                reports.append(suspended.report(sku, r["created_at"], suspended.SOURCES["nightly"], r.get("url", "")))
        return reports

    def load_suspended(store, refresh=False):
        """The card's answer: the merged to-do with the person's done-marks laid over it. The GitHub side is cached; the marks are read fresh,
        so a tick shows at once on every open page."""
        hit = suspended_cache.get(store.id)
        if hit and not refresh and time.monotonic() - hit[0] < SUSPENDED_FRESH_SECONDS:
            reports = hit[1]
        else:
            reports = suspended_reports(store)
            suspended_cache[store.id] = (time.monotonic(), reports)
        rows = suspended.merge(reports, database.suspended_marks(store.id))
        return {"rows": rows, "counts": suspended.counts(rows), "waiting_skus": suspended.waiting_skus(rows)}

    @app.get("/api/store/{store_id}/suspended")
    def api_suspended(store_id: str, refresh: int = 0):
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        try:
            return load_suspended(store, bool(refresh))
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)

    @app.post("/api/store/{store_id}/suspended/mark")
    async def api_suspended_mark(request: Request, store_id: str):
        """Remember that a suspended listing was deleted by hand on OnBuy (done=false unticks). Bookkeeping only: nothing is sent to OnBuy."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        sku = str(body.get("sku") or "").strip()
        if not sku or len(sku) > 80:
            return JSONResponse({"error": "No SKU came with the tick."}, status_code=400)
        done = bool(body.get("done"))
        if done:
            database.mark_suspended(store.id, catalogue.key(sku), auth.actor(request))
        else:
            database.unmark_suspended(store.id, catalogue.key(sku))
        database.audit(auth.actor(request), store.id, "suspended_done" if done else "suspended_undone", {"sku": sku})
        return {"ok": True, "sku": sku, "done": done}

    # ---- delivery templates -----------------------------------------------------------------------------------------------------
    @app.get("/delivery", response_class=HTMLResponse)
    def delivery_page(request: Request, store: str = ""):
        current = store_or_404(store) or settings.stores[0]
        data, error = None, ""
        try:
            data = load_delivery(current)
        except GitHubError as exc:
            error = str(exc)
        return page(request, "delivery.html", active="delivery", store=current, error=error, data=data)

    @app.post("/api/store/{store_id}/delivery/settings")
    async def api_delivery_settings(request: Request, store_id: str):
        """Save the template ids (repository variables). The nightly step of Arden and Makstore and every run from the dashboard move listings onto these ids, so the box is required."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        try:
            _, wiring = delivery_wiring(store)
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        values = {}
        for s in delivery.SUPPLIERS:
            if s["key"] not in wiring or str(body.get(s["key"]) or "").strip() == "":
                continue
            tid, error = delivery.clean_id(body.get(s["key"]))
            if error:
                return JSONResponse({"error": f"{s['label']}: {error}"}, status_code=400)
            values[s["variable"]] = tid
        if not values:
            return JSONResponse({"error": "Type at least one template id (a blank field keeps what it has)."}, status_code=400)
        if not body.get("confirm"):
            return JSONResponse({"error": "Tick the confirmation box: listings are moved onto these templates by the next run" + (" and by tonight's nightly" if store.id in delivery.IN_NIGHTLY else "") + "."}, status_code=400)
        try:
            for name, value in values.items():
                client.set_variable(store.repo, name, value)
            ids = delivery.effective_ids(client.list_variables(store.repo), wiring)
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        database.audit(auth.actor(request), store.id, "delivery_settings", values)
        return {"ok": True, "ids": [{"label": i["label"], "id": i["id"], "source": i["source"]} for i in ids]}

    @app.post("/api/store/{store_id}/delivery/run")
    async def api_delivery_run(request: Request, store_id: str):
        """plan = counts only; test = ONE listing moved and read back; apply = every listing off its supplier's template. Always started with the ids in force, so it agrees with the nightly."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        mode = body.get("mode")
        if mode not in ("plan", "test", "apply"):
            return JSONResponse({"error": "mode is plan, test or apply"}, status_code=400)
        try:
            _, wiring = delivery_wiring(store)
            ids = delivery.effective_ids(client.list_variables(store.repo), wiring)
            inputs = {"mode": mode, **{i["input"]: i["id"] for i in ids if i["id"]}}
            if mode != "plan":
                if not any(i["id"] for i in ids):
                    return JSONResponse({"error": "No template id is set for this store yet: save at least one id (Template ids on this page) before a test or an apply."}, status_code=400)
                if not body.get("confirm"):
                    return JSONResponse({"error": "Tick the confirmation box: this moves " + ("one listing" if mode == "test" else "every listing that is off its supplier's template") + " to another delivery template."}, status_code=400)
                inputs["clear_handling"] = "yes" if body.get("clear_handling") else "no"
            if mode == "test":
                skus, error = catalogue.split_skus(body.get("test_sku"), limit=1)
                if error:
                    return JSONResponse({"error": "Give the one SKU to test with. " + error}, status_code=400)
                inputs["test_sku"] = skus[0]
            if mode == "apply":
                limit, error = delivery.clean_max_changes(body.get("max_changes"))
                if error:
                    return JSONResponse({"error": error}, status_code=400)
                inputs["max_changes"] = str(limit)
            result = start_workflow(store, "delivery_templates.yml", inputs, bool(body.get("confirm")), auth.actor(request), note=f"delivery {mode}")
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        return JSONResponse(result, status_code=400 if "error" in result else 200)

    # ---- pictures routes --------------------------------------------------------------------------------------------------------
    @app.get("/pictures", response_class=HTMLResponse)
    def pictures_page(request: Request, store: str = ""):
        current = store_or_404(store) or settings.stores[0]
        data, error = None, ""
        try:
            data = load_pictures(current)
        except GitHubError as exc:
            error = str(exc)
        return page(request, "pictures.html", active="pictures", store=current, error=error, data=data)

    def short_name(text, default):
        return re.sub(r"[^A-Za-z .'-]", "", str(text or "")).strip()[:30].strip() or default

    @app.post("/api/store/{store_id}/pictures/ticket")
    async def api_pictures_ticket(request: Request, store_id: str):
        """Start the ticket build for a pasted list of SKUs: a background job that starts two read-only workflows and opens every image link."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        skus, _, error = deletion.parse_pasted(body.get("skus"))
        if not error and len(skus) > pictures.MAX_SKUS:
            error = f"At most {pictures.MAX_SKUS:,} SKUs at a time."
        if error:
            return JSONResponse({"error": error}, status_code=400)
        try:
            paths = {w["path"] for w in client.list_workflows(store.repo) if w["state"] == "active"}
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        missing = [w for w in ("image_links_export.yml", "listing_lookup.yml") if w not in paths]
        if missing:
            return JSONResponse({"error": f"This store's repository has no {' / '.join(missing)}, so the ticket cannot be built here."}, status_code=400)
        if jobs.running("pictures", store.id):
            return JSONResponse({"error": "A ticket build is already running for this store - wait for it to finish."}, status_code=400)
        opts = {"agent": short_name(body.get("agent"), "Ash"), "signed_by": short_name(body.get("signed_by"), "Sadia")}
        job = jobs.start("pictures", store.id, ticket_job, store, skus, opts, auth.actor(request))
        return {"ok": True, "job": job.view()}

    @app.post("/api/store/{store_id}/pictures/scan")
    async def api_pictures_scan(request: Request, store_id: str):
        """Read an uploaded file for the ticket box. The browser scan's own CSV (onbuy_image_scan_<Store>.csv) is understood: only the stuck products go in the box, the fine ones are
        left out and the rows the scan could not see are listed. Any other file keeps the old reading: the first column of every line. Nothing is stored and nothing goes anywhere."""
        if not store_or_404(store_id):
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        text = str(body.get("text") or "")
        if len(text) > 30_000_000:
            return JSONResponse({"error": "That file is over 30 MB - it is not a scan file or a SKU list."}, status_code=400)
        scan = pictures.read_scan(text)
        if scan is not None:
            report = pictures.scan_report(scan)
            return {"scan": True, "total": report["total"], "fine": report["fine"], "why": report["why"],
                    "stuck": [r["sku"] for r in report["stuck"]], "stuck_why": report["stuck"][:40],
                    "unclear": len(report["unclear"]), "unclear_rows": report["unclear"][:40],
                    "over": len(report["stuck"]) > pictures.MAX_SKUS}
        skus, _, error = deletion.parse_pasted("\n".join(pictures.read_sku_file(text)))
        if error:
            return JSONResponse({"error": error}, status_code=400)
        return {"scan": False, "skus": skus, "count": len(skus)}

    @app.get("/api/store/{store_id}/pictures/last_skus")
    def api_pictures_last_skus(store_id: str):
        """The last ticket build's full SKU list, for the 'Start from the last ticket's list' button: pastes arrive in dribs, and the next ticket usually means
        'everything from last time plus these' - this fills the box so nothing is merged by hand (the page shows at most 150 rows, so the box cannot be filled from there)."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        latest = load_latest(store)
        if not latest:
            return JSONResponse({"error": "No ticket build yet: nothing to start from."}, status_code=404)
        return {"skus": [r["sku"] for r in latest.get("rows", [])], "day": latest.get("day", ""), "asked": latest.get("asked", 0)}

    @app.get("/api/store/{store_id}/pictures/job/{job_id}")
    def api_pictures_job(store_id: str, job_id: str):
        job = jobs.get(job_id)
        if not job or job.store_id != store_id:
            return JSONResponse({"error": "unknown job (the dashboard was restarted?) - reload the page"}, status_code=404)
        return job.view()

    @app.get("/api/store/{store_id}/pictures/file/{job_id}/{kind}")
    def api_pictures_file(store_id: str, job_id: str, kind: str):
        store = store_or_404(store_id)
        if not store or kind not in pictures.FILES or not re.fullmatch(r"[0-9a-f]{12}", job_id):
            return JSONResponse({"error": "no such file"}, status_code=404)
        folder = pictures_dir(store) / job_id
        try:
            names = json.loads((folder / "result.json").read_text(encoding="utf-8"))["files"]
        except (OSError, ValueError, KeyError):
            return JSONResponse({"error": "no such file"}, status_code=404)
        stored = {"attachment": "attachment.csv", "reference": "reference.csv", "reply": "reply.txt"}[kind]
        if not (folder / stored).exists():
            return JSONResponse({"error": "no such file"}, status_code=404)
        return FileResponse(folder / stored, media_type=pictures.FILES[kind][0], filename=names[kind])

    @app.post("/api/store/{store_id}/pictures/resubmit")
    async def api_pictures_resubmit(request: Request, store_id: str):
        """Resubmit the products of one sheet tab of the last ticket build: preview = a dry run, canary = the first few for real, rest = all that are not yet resubmitted OK."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        mode = body.get("mode")
        if mode not in ("preview", "canary", "rest"):
            return JSONResponse({"error": "mode is preview, canary or rest"}, status_code=400)
        latest = load_latest(store)
        group = next((g for g in (latest or {}).get("groups", []) if g["tab"] == body.get("tab")), None)
        if not group:
            return JSONResponse({"error": "That tab is not in the last ticket build: build the ticket first."}, status_code=400)
        if mode != "preview" and not body.get("confirm"):
            return JSONResponse({"error": "Tick the confirmation box: this sends these products to OnBuy again (their content and pictures; the price and stock stay as they are)."}, status_code=400)
        try:
            try:
                definition = client.workflow_definition(store.repo, pictures.REPAIR_WORKFLOW, ref=settings.github_ref)
            except GitHubError as exc:
                if exc.status == 404:
                    return JSONResponse({"error": f"This store's repository has no {pictures.REPAIR_WORKFLOW}, so nothing can be resubmitted from here."}, status_code=400)
                raise
            lacking = [k for k in pictures.REPAIR_INPUTS if k not in (definition.get("inputs") or {})]
            if lacking:
                return JSONResponse({"error": f"This store's {pictures.REPAIR_WORKFLOW} has no {' / '.join(lacking)} input yet. Without it the run could resubmit listings you did not name, so it is not started."}, status_code=400)
            todo = pictures.group_state(group, resubmitted_map(store))["todo"]
            if not todo:
                return JSONResponse({"error": "Every product of this tab was resubmitted already."}, status_code=400)
            inputs = pictures.repair_inputs(mode, group["tab"], todo)
            if len(inputs["repair_skus"]) > 60000:
                return JSONResponse({"error": "Too many SKUs for one run: build the ticket for a shorter list."}, status_code=400)
            wait = sweep_pause(store)
            if wait:
                return JSONResponse({"error": f"OnBuy refuses reads that come too fast: {pictures.SWEEPS_PER_HOUR} full reads of this store's listings (lookups and resubmissions) started in the last hour. "
                                              f"Try again in {wait} minute(s)."}, status_code=400)
            result = start_workflow(store, pictures.REPAIR_WORKFLOW, inputs, mode != "preview", auth.actor(request), note=f"pictures {mode}: {group['tab']}, {len(todo)} SKU(s)")
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        if "error" in result:
            return JSONResponse(result, status_code=400)
        database.audit(auth.actor(request), store.id, f"pictures_{mode}", {"tab": group["tab"], "skus": len(todo)})
        return {**result, "count": len(todo), "tab": group["tab"], "mode": mode}

    # ---- buy box ----------------------------------------------------------------------------------------------------------------
    @app.get("/buybox", response_class=HTMLResponse)
    def buybox_page(request: Request, store: str = ""):
        current = store_or_404(store) or settings.stores[0]
        data, error = None, ""
        try:
            data = load_buybox(current)
        except GitHubError as exc:
            error = str(exc)
        return page(request, "buybox.html", active="buybox", store=current, error=error, data=data, defaults={"undercut": buybox.DEFAULT_UNDERCUT, "profit": buybox.DEFAULT_PROFIT})

    @app.post("/api/store/{store_id}/buybox/settings")
    async def api_buybox_settings(request: Request, store_id: str):
        """Save the three settings the daily run reads (repository variables). They change real prices on OnBuy from the next daily run, so the box is required."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        undercut, e1 = buybox.clean_undercut(body.get("undercut_pence"))
        profit, e2 = buybox.clean_profit(body.get("profit_percent"))
        if e1 or e2:
            return JSONResponse({"error": e1 or e2}, status_code=400)
        if not body.get("confirm"):
            return JSONResponse({"error": "Tick the confirmation box: the daily run uses these settings to change real prices on OnBuy."}, status_code=400)
        values = {buybox.ENABLED_VARIABLE: "yes" if body.get("enabled") else "no", buybox.UNDERCUT_VARIABLE: str(undercut), buybox.PROFIT_VARIABLE: f"{profit:g}"}
        try:
            for name, value in values.items():
                client.set_variable(store.repo, name, value)
            current = buybox.settings_view(client.list_variables(store.repo))
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        database.audit(auth.actor(request), store.id, "buybox_settings", values)
        return {"ok": True, "settings": current}

    @app.post("/api/store/{store_id}/buybox/run")
    async def api_buybox_run(request: Request, store_id: str):
        """A manual run: mode 'preview' = a dry run (classifies and writes the BuyBox tab, pushes nothing; may try other values), 'live' = pushes prices with the SAVED settings."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        live = body.get("mode") == "live"
        inputs = {"dry_run": "no" if live else "yes"}
        try:
            if live:
                if not body.get("confirm"):
                    return JSONResponse({"error": "Tick the confirmation box: a live run lowers prices on OnBuy now."}, status_code=400)
                if not buybox.settings_view(client.list_variables(store.repo))["push"]:
                    return JSONResponse({"error": f"{buybox.PUSH_VARIABLE} is not true on this store, so a live run would only be a dry run: nothing is pushed to OnBuy while it is off."}, status_code=400)
            else:
                for key, text, clean in (("undercut_pence", body.get("undercut_pence"), buybox.clean_undercut), ("profit_percent", body.get("profit_percent"), buybox.clean_profit)):
                    if str(text or "").strip() == "":
                        continue
                    value, error = clean(text)
                    if error:
                        return JSONResponse({"error": error}, status_code=400)
                    if key not in client.workflow_definition(store.repo, "buybox_defense.yml", ref=settings.github_ref)["inputs"]:
                        return JSONResponse({"error": f"This store's Buy Box workflow does not take a trial {key.replace('_', ' ')} yet."}, status_code=400)
                    inputs[key] = f"{value:g}"
            result = start_workflow(store, "buybox_defense.yml", inputs, live, auth.actor(request), note="buybox " + ("live" if live else "preview"))
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        return JSONResponse(result, status_code=400 if "error" in result else 200)

    # ---- amazon -----------------------------------------------------------------------------------------------------------------
    plan_cache = {}

    def keepa_plan():
        """The Keepa-plan numbers of all five stores (the decision "keep five 20/min keys, raise some, or share one bigger key" needs the fleet, not one store).
        Each store's last real syncs are parsed from the disk-cached logs; the answer is kept for 15 minutes so hopping between stores does not recompute it."""
        hit = plan_cache.get("plan")
        if hit and time.monotonic() - hit[0] < 900:
            return hit[1]

        def one(store):
            try:
                runs = [r for r in client.list_runs(store.repo, limit=30, workflow=amazon.WORKFLOW)
                        if r["status"] == "completed" and r["conclusion"] in ("success", "failure")][:8]
                rows = [{"run": r, "facts": amazon.parse_sync(run_text(store, r))} for r in runs]
                return {"store": {"id": store.id, "name": store.name}, "eco": amazon.economics(rows)}
            except GitHubError as exc:
                return {"store": {"id": store.id, "name": store.name}, "eco": None, "error": str(exc)}

        out = list(pool.map(one, [s for s in settings.stores if s.amazon]))      # an eBay-only store spends no Keepa tokens: it is not in the plan
        plan_cache["plan"] = (time.monotonic(), out)
        return out

    @app.get("/amazon", response_class=HTMLResponse)
    def amazon_page(request: Request, store: str = ""):
        current = store_or_404(store) or settings.stores[0]
        data, error = None, ""
        if current.amazon:
            try:
                data = load_amazon(current)
            except GitHubError as exc:
                error = str(exc)
        return page(request, "amazon.html", active="amazon", store=current, error=error, data=data)

    @app.post("/api/store/{store_id}/amazon/settings")
    async def api_amazon_settings(request: Request, store_id: str):
        """Save the Amazon sync's settings (repository variables) - only the ones that changed. They decide which price the next sync believes and what counts as in stock, so the box is required;
        switching the strict stock rule ON (every row live on a third-party offer alone goes to stock 0) needs a second box."""
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        try:
            view, wired = amazon_wiring(store)
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        writes, error = amazon.changes_from(view, body.get("values") or {})
        if error:
            return JSONResponse({"error": error}, status_code=400)
        if not body.get("confirm"):
            return JSONResponse({"error": "Tick the confirmation box: the next Amazon sync uses these settings to price and stock real listings."}, status_code=400)
        if writes.get(amazon.BY_KEY["own_only"]["variable"]) == "yes" and not body.get("confirm_strict"):
            return JSONResponse({"error": "Switching the strict stock rule on takes every row that is live on a third-party offer alone to stock 0 at the next sync (the seller count below shows how many). "
                                          "Tick the second box to go ahead."}, status_code=400)
        if not writes:
            return {"ok": True, "written": {}, "settings": view, "note": "Nothing changed: every value is already what the sync uses."}
        try:
            for name, value in writes.items():
                client.set_variable(store.repo, name, value)
            current = amazon.settings_view(client.list_variables(store.repo), wired)
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        database.audit(auth.actor(request), store.id, "amazon_settings", writes)
        return {"ok": True, "written": writes, "settings": current}

    # ---- ebay -------------------------------------------------------------------------------------------------------------------
    @app.get("/ebay", response_class=HTMLResponse)
    def ebay_page(request: Request, store: str = ""):
        current = store_or_404(store) or settings.stores[0]
        data, error = None, ""
        try:
            data = load_ebay(current)
        except GitHubError as exc:
            error = str(exc)
        return page(request, "ebay.html", active="ebay", store=current, error=error, data=data, slow_hours=ebay.SLOW_HOURS)

    # ---- sale -------------------------------------------------------------------------------------------------------------------
    @app.get("/sale", response_class=HTMLResponse)
    def sale_page(request: Request, store: str = ""):
        current = store_or_404(store) or settings.stores[0]
        data, error = None, ""
        try:
            data = load_sale(current)
        except GitHubError as exc:
            error = str(exc)
        today = utcnow().date()
        return page(request, "sale.html", active="sale", store=current, error=error, data=data, brackets=sale.BRACKETS, today=today.isoformat(),
                    max_end=(today + timedelta(days=sale.MAX_DAYS)).isoformat())

    async def sale_dispatch(request, store_id, mode):
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        inputs, error = sale.build_inputs(body, mode, today=utcnow().date())
        if error:
            return JSONResponse({"error": error}, status_code=400)
        confirm = bool(body.get("confirm"))
        if mode in sale.ACTIVE_MODES and not confirm:
            what = {"apply": "puts the sale live on OnBuy for customers", "cancel": "ends the sale on every listing of the store",
                    "test": "puts a sale on that one listing for a few minutes and then takes it off"}[mode]
            return JSONResponse({"error": f"Tick the confirmation box: this {what}."}, status_code=400)
        try:
            result = start_workflow(store, "store_sale.yml", inputs, confirm, auth.actor(request), note=f"sale {mode}")
        except GitHubError as exc:
            result = {"error": str(exc)}
        if "error" not in result:
            result["inputs"] = inputs
        return JSONResponse(result, status_code=400 if "error" in result else 200)

    def make_sale_endpoint(mode):
        async def endpoint(request: Request, store_id: str):
            return await sale_dispatch(request, store_id, mode)
        return endpoint

    for _mode in ("plan", "apply", "test", "cancel"):
        app.post(f"/api/store/{{store_id}}/sale/{_mode}")(make_sale_endpoint(_mode))

    # ---- fees -------------------------------------------------------------------------------------------------------------------
    @app.get("/fees", response_class=HTMLResponse)
    def fees_page(request: Request, store: str = ""):
        current = store_or_404(store) or settings.stores[0]
        data, error = None, ""
        try:
            data = load_fees(current)
        except GitHubError as exc:
            error = str(exc)
        return page(request, "fees.html", active="fees", store=current, error=error, data=data)

    @app.post("/api/store/{store_id}/fees/mode")
    async def api_fee_mode(request: Request, store_id: str):
        store = store_or_404(store_id)
        if not store:
            return JSONResponse({"error": "unknown store"}, status_code=404)
        body = await request.json()
        mode = str(body.get("mode") or "").strip().lower()
        tier_mode = str(body.get("tier_mode") or "").strip().lower()
        if mode not in ("category", "flat") or tier_mode not in ("marginal", "step"):
            return JSONResponse({"error": "The fee mode is 'category' or 'flat'; the tier mode 'marginal' or 'step'."}, status_code=400)
        if not body.get("confirm"):
            return JSONResponse({"error": "Tick the confirmation box: the store's next syncs price every row with the new fee model."},
                                status_code=400)
        try:
            client.set_variable(store.repo, "FEE_MODE", mode)
            client.set_variable(store.repo, "FEE_TIER_MODE", tier_mode)
        except GitHubError as exc:
            return JSONResponse({"error": str(exc)}, status_code=502)
        database.audit(auth.actor(request), store.id, "set_variable", {"name": "FEE_MODE", "value": mode, "FEE_TIER_MODE": tier_mode})
        return {"ok": True, "mode": mode, "tier_mode": tier_mode}

    return app


# ---- template filters -----------------------------------------------------------------------------------------------------------
def fmt_age(iso_text):
    hours = digest.age_hours(iso_text)
    if hours is None:
        return "-"
    if hours < 1:
        return f"{int(hours * 60)} min ago"
    if hours < 48:
        return f"{hours:.1f} h ago"
    return f"{hours / 24:.1f} days ago"


def fmt_when(iso_text):
    try:
        return digest.parse_iso(iso_text).strftime("%d %b %H:%M") + "Z"
    except (ValueError, TypeError):
        return str(iso_text or "-")


app = None


def get_app():
    global app
    if app is None:
        app = create_app()
    return app
