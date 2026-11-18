"""Onboarding a store through the dashboard (2026-10-31, built for Kiddomi, the sixth store): the Settings page adds a store after
proving the token reaches its repository, every page grows the chip at once, and the registry file keeps it for the next start.
Removing one changes nothing on GitHub or OnBuy - the dashboard just stops watching."""
from app import auth as auth_module
from app import config as config_module


def add(web, **over):
    body = {"id": "kiddomi", "name": "Kiddomi", "repo": "org/kiddomi", "sheet": "Kiddomi_Feed_Master"}
    body.update(over)
    return web.post("/api/stores", json=body)


def test_adding_a_store_checks_the_repo_writes_the_file_and_grows_the_chips_at_once(web, settings, db):
    r = add(web)
    assert r.status_code == 200 and r.json()["store"] == {"id": "kiddomi", "name": "Kiddomi", "repo": "org/kiddomi"}
    assert [s.id for s in settings.stores] == ["gtv", "yra", "kiddomi"]
    saved = config_module.load_stores(settings.stores_file)                     # the file is what the next start reads
    assert [s.id for s in saved] == ["gtv", "yra", "kiddomi"] and saved[2].sheet == "Kiddomi_Feed_Master" and saved[2].product_tab == "Sheet1"
    assert 'href="/store/kiddomi"' in web.get("/").text                        # the chip is there without a restart
    assert web.get("/store/kiddomi").status_code == 200
    assert db.recent_audit(limit=3)[0]["action"] == "store_added"


def test_the_add_refuses_bad_ids_bad_repos_doubles_and_a_repo_the_token_cannot_reach(web, fake, settings):
    assert "small letters" in add(web, id="Kiddomi!").json()["error"]
    assert "owner/name" in add(web, repo="not-a-repo").json()["error"]
    assert "already a store" in add(web, id="gtv").json()["error"]
    assert "already belongs to the store 'yra'" in add(web, repo="org/yra").json()["error"]
    fake.fail_repo = "org/kiddomi"
    refused = add(web)
    assert refused.status_code == 400 and "token cannot use org/kiddomi" in refused.json()["error"]
    assert [s.id for s in settings.stores] == ["gtv", "yra"]                   # nothing half-added


def test_a_github_link_is_accepted_as_the_repo(web, settings):
    assert add(web, repo="https://github.com/org/kiddomi").status_code == 200
    assert settings.stores[-1].repo == "org/kiddomi"


def test_removing_a_store_needs_the_box_updates_file_and_pages_and_the_last_store_stays(web, settings, db):
    assert web.post("/api/stores/nope/remove", json={}).status_code == 404
    assert "confirmation box" in web.post("/api/stores/yra/remove", json={}).json()["error"]
    assert web.post("/api/stores/yra/remove", json={"confirm": True}).json() == {"ok": True}
    assert [s.id for s in settings.stores] == ["gtv"] and [s.id for s in config_module.load_stores(settings.stores_file)] == ["gtv"]
    assert web.get("/store/yra", follow_redirects=False).status_code == 303   # an unknown store's page sends you home
    assert 'href="/store/yra"' not in web.get("/").text
    assert db.recent_audit(limit=3)[0]["action"] == "store_removed"
    assert "The last store stays" in web.post("/api/stores/gtv/remove", json={"confirm": True}).json()["error"]


def test_the_registry_is_admin_only_once_the_login_is_on():
    assert auth_module.role_needed("POST", "/api/stores") == "admin"
    assert auth_module.role_needed("POST", "/api/stores/kiddomi/remove") == "admin"
    assert auth_module.role_needed("GET", "/api/stores") is None               # reading stays free for every role


# ---- repository secrets through the dashboard (2026-10-31: the keys never open GitHub's settings page again) ------------------------
def test_the_secrets_panel_lists_names_only_and_names_what_is_missing(web):
    data = web.get("/api/stores/gtv/secrets").json()
    assert data["repo"] == "org/gtv" and data["missing"] == []
    assert {s["name"] for s in data["secrets"]} >= {"ONBUY_CONSUMER_KEY", "GOOGLE_CREDENTIALS"}
    assert "x" not in str(data)                                                # names and dates only - never a value
    yra = web.get("/api/stores/yra/secrets").json()
    assert yra["missing"][0] == "ONBUY_CONSUMER_KEY" and len(yra["missing"]) == 6
    assert web.get("/api/stores/nope/secrets").status_code == 404


def test_setting_a_secret_reaches_github_but_the_value_reaches_nothing_else(web, fake, db):
    r = web.post("/api/stores/yra/secrets", json={"name": "onbuy_consumer_key", "value": "very-secret-123"})
    assert r.json() == {"ok": True, "name": "ONBUY_CONSUMER_KEY"}              # the name is uppercased on the way
    assert fake.secrets["org/yra"]["ONBUY_CONSUMER_KEY"] == "very-secret-123"  # the client call carried it...
    row = db.recent_audit(limit=1)[0]
    assert row["action"] == "secret_set" and "ONBUY_CONSUMER_KEY" in row["detail"] and "very-secret-123" not in str(row)
    assert "very-secret-123" not in r.text                                     # ...and nothing echoed it
    assert "ONBUY_CONSUMER_KEY" not in web.get("/api/stores/yra/secrets").json()["missing"]


def test_the_secret_set_refuses_bad_names_and_empty_values(web):
    assert "capital letters" in web.post("/api/stores/gtv/secrets", json={"name": "bad name!", "value": "x"}).json()["error"]
    assert "empty" in web.post("/api/stores/gtv/secrets", json={"name": "GOOD_NAME", "value": "  "}).json()["error"]
    assert auth_module.role_needed("POST", "/api/stores/gtv/secrets") == "admin"


def test_a_sheet_link_is_kept_in_the_registry_and_left_out_of_the_file_when_empty(web, settings):
    assert add(web, sheet_url="https://docs.google.com/spreadsheets/d/abc").status_code == 200
    saved = {s.id: s for s in config_module.load_stores(settings.stores_file)}
    assert saved["kiddomi"].sheet_url.endswith("/abc")
    assert "sheet_url" not in [line for line in settings.stores_file.read_text(encoding="utf-8").splitlines() if '"id": "gtv"' in line][0]
