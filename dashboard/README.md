# Best View Glazing dashboard

Best View Glazing Ltd has its own copy of the OnBuy dashboard: the same pages and tools, in the company branding
(logo, charcoal header, petrol teal accents, Manrope and Inter type). One page for the OnBuy store automations (GTV, YRA, Arden, Makstore, OpenMaal). It shows what the store repositories'
GitHub Actions have done, starts the workflows a person would otherwise start on GitHub, follows the run and reads its
result out of the log, and edits the repositories' variables. It never talks to OnBuy itself and holds no OnBuy key.

Built for one person first (this PC; the login stays off while `DASHBOARD_PASSWORD` is empty). Employees are on Settings: each gets their
own code (shown once, stored as a salted hash) and a role - **view** sees every page and presses nothing, **operate** presses the run and
apply buttons, **admin** also changes settings (repository variables, fee mode, the per-card settings) and the accounts. The owner password
signs in as admin. The VPS deployment comes once the
features and tests have settled; the app is a plain Python web service so that move is a configuration change, not a rewrite.

## Run it on your PC (Windows, step by step)

The same steps, with a live checklist, are on the dashboard's **Help** page.

1. **Python.** Install Python 3.11 or newer from python.org; on the first installer screen tick *Add python.exe to PATH*. Check in PowerShell: `python --version`.
2. **GitHub CLI.** Install it from cli.github.com, then sign in once with `gh auth login` (GitHub.com, HTTPS, "Login with a web browser", the account that owns the store
   repositories). Check: `gh auth status` says "Logged in". The dashboard uses this login, so there is no password to type in. (Or put a token in `.env`, step 7.)
3. **The folder.** On this PC it is `E:\Academics\Dev-Projects\best-view-glazing-dashboard`. On another PC: `git clone https://github.com/bestviewglazing/BVG-Site` (the dashboard is its `dashboard` folder)``.
4. **Start it.** Double-click **`start-dashboard.bat`** in the folder: the first time it installs what it needs (about a minute), starts the dashboard and opens your browser.
   By hand, in PowerShell:

       cd E:\Academics\Dev-Projects\best-view-glazing-dashboard
       pip install -r requirements.txt        (first time only)
       python run.py

5. **Open** http://127.0.0.1:8787. The Help page's first table must show the GitHub token and all five stores green.
6. **Leave the black window open** while you use it - it is the dashboard. Close it (or Ctrl+C) to stop. Red text in it is where to look first when a page shows an error.
7. **Settings file (only if needed).** Copy `.env.example` to `.env` and fill in what you need: `GITHUB_TOKEN`, `DASHBOARD_PASSWORD`, `DASHBOARD_PORT` (another port if 8787 is taken).

## Put it online

On your PC it works only while the PC is on, and only for you. To open it from anywhere, run it on an always-on computer: a small rented server (the plan) or Google Cloud Run -
step by step in **[HOSTING.md](HOSTING.md)** (the folder has a `Dockerfile` for Cloud Run). **Google Apps Script cannot run it** (it is Python; Apps Script runs only JavaScript): HOSTING.md
says why and what an Apps Script rewrite would take. Whatever the host: set `DASHBOARD_PASSWORD` first and use HTTPS.

## Check it

1. **Is it up?** http://127.0.0.1:8787/healthz answers `{"ok":true}`.
2. **Does it reach GitHub?** The **Help** page's first table (and *Settings*) show the token and `ok` for each of the five stores. Anything else means the token is missing or has no access to that repository.
3. **Look around** - these pages only read: *Home*, *To do*, *Daily check*, *Orders*, *Pricing*, *Fees*, *Sale*, *Buy Box*, *Delivery*, *eBay*, *Amazon*, *Pictures*, *Catalogue*, *Delete* (the list form), *Tools*. Every page opens with a short brief of what it does and
   every button has a hint.
4. **Press something that cannot hurt.** Each of these starts a workflow that only reads or does a dry run, and shows its result under the button when the run finishes (a few minutes: it is a real GitHub run):
   *Orders* -> Refresh, *Pricing* -> Preview, *Sale* -> Preview, *Buy Box* -> Preview now, *Delivery* -> Plan now, *Amazon* -> Count the sellers now, *Pictures* -> Build the ticket and Preview (dry run), *Catalogue* -> "Check the delete (dry run)", *Delete* -> Check the list / Plan (dry run), *Fees* -> the census and the probes.
5. **Know what changes real things.** Only these do, and every one of them needs the confirmation box ticked first (the page refuses without it): *Pricing* Apply / Push, *Fees* mode and "commit", *Sale* Apply / Cancel /
   Try on one listing, *Buy Box* Save the settings and Run live now, *Delivery* Save the ids / Test / Apply, *Amazon* Save the settings, *Pictures* Canary / Resubmit the rest, *Catalogue* Release / Same product / Freeze / Delete for real, *Delete* "Delete for real" (only after a plan of that exact list finished well),
   *Settings* variable edits, and the dangerous workflows on *Tools*. The *Settings* page keeps a log of everything pressed.
6. **Run the tests:** `python -m pytest -q` in this folder - about 240 tests, half a minute, no network (they use a fake GitHub).

## Pages

- **To do** - what needs you today, store by store, most urgent first (act now / look today / for your information): orders past their date or due today, syncs that failed or ran out of Keepa tokens, late
  schedules, price falls of a quarter or more, listings frozen for your call, a sale that ends, commission tables that changed - each with the page that deals with it. It only reads; it keeps its answer for 5 minutes.

- **Home** - the five stores: queue (running / waiting), and the latest eBay sync, Amazon sync, backfill, nightly, Buy Box,
  content scan and eBay budget run with result and age; a run older than its usual cadence is marked stale; a "sale until" pill.
- **Store** - the same status, **Run now** for the everyday workflows, the runs started from here with their outcome, and the
  recent runs. A result box follows the run and shows the headline numbers and key log lines when it finishes.
- **Daily check** - the "check the logs and give todos" in one page: runs per workflow and the ones that were not green, stale
  schedules, the nightly's numbers (mismatched, zeroed, deleted rows, underpriced, corrected, sale guard) with the SKUs it
  zeroed and the borderlines it left for a decision, the eBay call budget, Keepa tokens, and the orders awaiting dispatch with
  due-today and overdue counts.
- **Orders** - orders awaiting dispatch per store from the latest orders lookup, with a Refresh button (a new lookup run).
- **Pricing** - the profit schedule a store prices with (a repository setting, else the numbers in its code), a calculator, and
  an editor: Preview (dry run) -> Apply (sets the schedule and re-prices the sheet, backup tab first) -> Push (OnBuy prices).
  Price ranges with their own profit % live here too.
- **Fees** - the fee model, the commission tables (refresh, compare, commit), orders against the sheet, the fee probe, the
  category census and the keyword relabel.
- **Sale** - the running sale, and a form for the next one: a sale % for each price range, the last day, a margin floor;
  Preview, Apply, Cancel, and "Try it on one listing first".
- **Buy Box** - the daily price cuts that win the Buy Box: how the last runs went (share of listings holding the box, lowered, held at the floor), the three settings (daily run on/off, undercut in pence, the profit % the
  price floor keeps), a preview that can try other values, and a live run.
- **Delivery** - which OnBuy delivery template each supplier's listings (eBay, Amazon, AliExpress) should sit on and how many do, the template ids per store (repository variables), and Plan (counts), Test (one listing,
  read back) and Apply (moves every stray) - on all five stores; Arden and Makstore also run it every night on what was created during the day.
- **eBay** - the hourly eBay sync: how the last runs went (rows refreshed, eBay's daily call allowance, a batch cut to fit it), how long the whole sheet really takes to come round (worked out from
  what the syncs did in the last 24 hours), the delivery costs eBay states and what the dead-row purge removed (with the purged listings OnBuy has suspended, to delete by hand). It only reads.
- **Amazon** - the Amazon sync (Keepa): how the last syncs went (rows, Keepa tokens, what the guards took out of stock), the prices the last sync lowered most (a fall of a quarter or more is
  marked), the seller count that helps decide the strict stock rule, and the settings behind the guards and the stock rule (saved as repository variables, only the ones that changed).
- **Pictures** - products whose pictures never load on OnBuy. Paste the SKUs - or upload the browser scan's CSV (`onbuy_image_scan_<Store>.csv`): only the stuck products (page 404, pictures
  that fail, placeholder-only pages) land in the box, the fine ones are left out and the rows the scan could not see are counted - and Build the ticket: the sheet is read (and OnBuy for the OPCs the sheet lacks), every picture link is opened, and you get the CSV for OnBuy
  support, an internal reference sheet and a reply draft. Then OnBuy's workaround: Preview (dry run), Canary (the first 3) and Resubmit the rest - only the SKUs of the ticket, one sheet tab per run. Building changes nothing on OnBuy.
- **Catalogue** - the listings frozen at zero (the nightly freezes a listing whose OnBuy page shows another product): tick them
  and press Same product / Release / Check the delete / Delete for real, freeze listings by hand, and the dead-row purge with
  the list of suspended listings to delete by hand on OnBuy.
- **Delete** - paste a list of SKUs (or load a file): Check the list, Plan (a dry run that shows what would go and what is held
  back), then Delete for real: the sheet rows are copied to a backup tab and removed, and the OnBuy listings are deleted.
  SKUs on open orders and on the hold lists are kept out of the list.
- **Tools** - every manual workflow of a store grouped by area, with its inputs, descriptions and defaults read from the
  workflow file itself; read-only tools run on one press, the others default to a dry run.
- **Help** - what the dashboard is, the live "is it working?" checklist, the steps to run it, how to put it online, the pages in one line each, the words used and what to do when something goes wrong.
- **Settings** - token and access checks per store, repository variables with inline editing (confirmation box; applies to
  the store's next runs), and the log of what was pressed.

## House rules the page enforces

1. A workflow is never started while another run is **waiting** for the store's `onbuy-api` slot: GitHub would cancel the
   waiting run (usually a scheduled sync). Running runs are fine; the new run queues behind them and the page says so. A run
   that has been "pending" for more than two days is a GitHub ghost and is ignored.
2. A workflow that deletes, zeroes, re-prices or changes a sale at scale (`risk: danger` in `app/catalog.py`) needs the apply
   switch (`dry_run=no`, `apply=yes`, `mode=apply` ...) **and** the confirmation box before it is started for real.
3. A real delete only runs for a list whose plan finished well in the last 24 hours, and only with open-order data from the
   last 24 hours.

## Layout

    app/config.py          .env settings and config/stores.json (repo, sheet and tabs per store)
    app/github_client.py   runs, queue, dispatch, logs, variables, workflow definitions, file edits (GitHub REST, httpx)
    app/catalog.py         label, area and risk of every workflow a person runs; status tiles; Run now list
    app/digest.py          the daily check as pure functions: run summaries, stale crons, numbers out of the logs
    app/pricing.py, fees.py, sale.py, buybox.py, amazon.py, ebay.py, delivery.py, catalogue.py, deletion.py, pictures.py, todo.py
                           one module per card: validation and the log parsers as pure functions
    Dockerfile, HOSTING.md  the container for Cloud Run / any Docker host, and the steps to put the dashboard online
    start-dashboard.bat    double-click launcher for Windows
    app/jobs.py            background jobs (the ticket build): steps, progress, result, one at a time per store
    app/db.py              SQLite: settings, audit log, runs started from here
    app/auth.py            optional login + signed cookie (off while DASHBOARD_PASSWORD is empty); employee codes and the view/operate/admin roles
    app/logstore.py        finished run logs kept on disk (data/logs, gzip, pruned): downloaded once ever, so restarts stay fast
    app/main.py            the FastAPI app and its pages / JSON endpoints
    app/templates, static  the pages, the stylesheet and the button script
    tests/                 pytest: parsers on real log excerpts, GitHub client against canned answers, routes against a fake client

## Later

A "Dashboard Status" tab written by the store workflows so the page reads facts instead of logs, a homepage for employees,
nginx + HTTPS on the VPS.

## Branding

The identity lives in a few files and nothing else: `app/static/style.css` (the `:root` palette and the header block at the end),
`app/static/logo.svg` (header, white wordmark), `app/static/logo-dark.svg` (sign-in page) and `app/static/icon.svg` (favicon).
The stores it shows come from `config/stores.json`.
