"""The Help page and its live checklist, the short brief every page opens with, a hint at every function, and the settings a host needs (PORT, DASHBOARD_SECRET)."""
import re

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, load_settings
from app.db import Database
from app.main import create_app

PAGES = ["/", "/store/gtv", "/todo", "/daily", "/orders", "/pricing?store=gtv", "/fees?store=gtv", "/sale?store=gtv", "/buybox?store=gtv", "/ebay?store=gtv", "/amazon?store=gtv", "/delivery?store=gtv", "/pictures?store=gtv", "/catalogue?store=gtv", "/delete?store=gtv",
         "/tools?store=gtv", "/settings", "/help"]

# a phrase from the hint of each function (a button, a form, a table): when a page loses it, the function is no longer explained
HINTS = {
    "/": ["What each job does", "Hourly (GitHub often runs it every 3-5 hours)"],
    "/store/gtv": ["Tags:", "What you started from this dashboard", "Every GitHub run of this store"],
    "/todo": ["Reads every store again", "Act now</strong> = wrong or late right now", "For your information</strong> = what last night's check did"],
    "/daily": ["How often each job ran", "Runs that failed or were cancelled", "eBay calls left for the day", "orange = due today, red = overdue",
               "Rows that keep failing", "refused night after night is a dead row"],
    "/orders": ["Starts a new read-only orders lookup", "never buyer details"],
    "/pricing?store=gtv": ["Type a cost + shipping", "Preview</strong> changes nothing", "Apply</strong> saves this schedule", "Push</strong> writes the sheet's prices"],
    "/fees?store=gtv": ["Save</strong> sets the store's fee variables", "OnBuy takes a commission that depends on the product's category"],
    "/sale?store=gtv": ["Cancel</strong> ends the sale", "Preview</strong> reads the whole account", "Apply</strong> sends the sale prices", 'title="Add an empty row', 'title="Put this sale % into every row'],
    "/buybox?store=gtv": ["Off = the scheduled run does nothing", "How far under the winner's price to go", "Sorts every listing and writes the \"BuyBox\" tab", "Uses the <strong>saved</strong> settings"],
    "/ebay?store=gtv": ["These are repository variables: change them on the Settings page", "A scheduled run that was cancelled is one the next run replaced", "The Amazon rows are not part of this"],
    "/amazon?store=gtv": ["Reads the sheet only (no Keepa, no OnBuy, nothing changes)", "Only needed to switch the strict stock rule ON", "Keepa charges about a token per product", "Off: a product is in stock when Amazon sells it OR any third-party seller does"],
    "/delivery?store=gtv": ["Counts where every supplier's listings sit", "Moves ONE listing to its supplier's template", "Moves every listing that is off its supplier's template", "An id is the number of a delivery template",
                            "so the template alone decides", "never moved"],
    "/pictures?store=gtv": ["The SKUs exactly as they are on the sheet", "Only the reply draft uses these two names", "It saves your list in the store's repository, then takes a few minutes",
                            "Build a ticket first", "No list in the repository yet: the first build saves the first one"],
    "/catalogue?store=gtv": ["Same product</strong> - the page IS", "Release</strong> - the page or the row", "Check the delete</strong> - a dry run", "Delete for real</strong> - copies the row", "Freeze</strong> writes the SKUs"],
    "/delete?store=gtv": ["Only \"Delete for real\" changes anything", "the plan saves the list in the repository and changes nothing else", "What it does",
                          "only you can delete these", "tick it off - the dashboard remembers"],
    "/tools?store=gtv": ["only looks and runs on one press", "Unfilled inputs keep the job's defaults"],
    "/settings": ["Hover a name for what it is", "Every action taken from this dashboard that changed something",
                  "Download a backup", "take one before moving to another computer or the VPS",
                  "Add a store", "Onboards a store to this dashboard only", "its jobs keep running, the dashboard just stops watching",
                  "sealed with the repository's public key", "the list shows names and dates only"],
    "/help": ["Is it working?", "Run it on your PC", "Put it online", "Words used", "If something goes wrong"],
}


@pytest.mark.parametrize("path", PAGES)
def test_every_page_opens_with_a_brief_that_says_what_it_does(web, path):
    """The brief is one quiet line now (2026-10-29, 'to the point'): a collapsed details box whose summary names it and whose body keeps the full explanation."""
    r = web.get(path)
    assert r.status_code == 200
    brief = re.search(r'<details class="brief"><summary>What this (page|dashboard) (does|shows|is)</summary>', r.text)
    assert brief, path


@pytest.mark.parametrize("path", sorted(HINTS))
def test_every_function_of_a_page_has_its_hint(web, path):
    text = web.get(path).text
    for phrase in HINTS[path]:
        assert phrase in text, (path, phrase)


def test_the_script_and_the_stylesheet_carry_a_version_so_a_cached_old_copy_never_runs_a_new_page(web):
    """A browser that had cached the old app.js left the Amazon card's buttons dead (Dash.amzSave is not a function) until a hard refresh."""
    text = web.get("/").text
    assert re.search(r'<script src="/static/app\.js\?v=\d+"></script>', text) and re.search(r'<link rel="stylesheet" href="/static/style\.css\?v=\d+">', text)
    assert web.get("/static/app.js?v=1").status_code == 200


def test_the_menu_links_every_card_and_the_help_page(web):
    text = web.get("/").text
    for link in ("/todo", "/daily", "/orders", "/pricing", "/fees", "/sale", "/buybox", "/ebay", "/amazon", "/delivery", "/pictures", "/catalogue", "/delete", "/tools", "/settings", "/help"):
        assert f'href="{link}' in text, link
    assert '<a href="/help">Help</a>' in text                    # the footer's own Help link (the nav one carries a class)


def test_help_page_gives_the_steps_to_run_it_the_hosting_options_and_the_answer_on_apps_script(web):
    r = web.get("/help")
    assert r.status_code == 200
    for phrase in ("Install Python", "gh auth login", "start-dashboard.bat", "python run.py", "http://127.0.0.1:8787", ".env.example", "DASHBOARD_PASSWORD",
                   "A small rented server (VPS)", "Google Cloud Run", "HOSTING.md", "Google Apps Script", "not as it is", "cannot be pasted in", "Dockerfile"):
        assert phrase in r.text, phrase
    assert r.text.count("<li><strong>") >= 12                                                         # the seven steps and the five troubleshooting lines


def test_help_checklist_shows_the_token_and_every_store_live(web, fake):
    r = web.get("/help")
    assert "signed in as tester" in r.text and r.text.count('<span class="pill ok">ok</span>') == 2 and "Access to <strong>GTV</strong>" in r.text and "Access to <strong>YRA</strong>" in r.text
    assert "Set one (step 7) before it is ever put online" in r.text
    fake.fail_repo = "org/gtv"
    broken = web.get("/help")
    assert broken.status_code == 200 and 'class="pill failed">no</span>' in broken.text and "no access" in broken.text and "must be allowed to read and start GitHub Actions jobs" in broken.text


def test_help_checklist_says_so_when_there_is_no_token(stores, fake, tmp_path):
    client = TestClient(create_app(settings=Settings(github_token="", stores=stores, data_dir=tmp_path), client=fake, database=Database(":memory:")))
    page = client.get("/help").text
    assert 'class="pill failed">missing</span>' in page and "gh auth login" in page


def test_a_host_can_set_the_port_by_either_name(tmp_path):
    base = {"GITHUB_TOKEN": "t"}
    assert load_settings(base).port == 8787
    assert load_settings({**base, "PORT": "8080"}).port == 8080
    assert load_settings({**base, "PORT": "8080", "DASHBOARD_PORT": "9001"}).port == 9001                # the dashboard's own name wins
    assert load_settings({**base, "DASHBOARD_SECRET": " s3cret "}).dashboard_secret == "s3cret" and load_settings(base).dashboard_secret == ""


def test_a_fixed_secret_keeps_a_sign_in_valid_on_another_instance_while_a_random_one_does_not(stores, fake, tmp_path):
    def app(secret, name):
        settings = Settings(github_token="t", stores=stores, data_dir=tmp_path, dashboard_password="pw", dashboard_secret=secret)
        return TestClient(create_app(settings=settings, client=fake, database=Database(":memory:")))

    first = app("same-long-secret", "a")
    cookie = first.post("/login", data={"password": "pw", "next": "/"}, follow_redirects=False).cookies.get("onbuy_dash")
    assert cookie
    second = app("same-long-secret", "b")
    assert second.get("/", cookies={"onbuy_dash": cookie}, follow_redirects=False).status_code == 200
    other = app("", "c")                                                                              # no secret: each instance makes its own, so the cookie means nothing there
    assert other.get("/", cookies={"onbuy_dash": cookie}, follow_redirects=False).status_code == 303
