"""Named sign-ins from the environment (2026-11-18): DASHBOARD_USERS = "name:role:password,name:role:password" gives the client (and
anyone else) a username and password of their own, next to the owner password and the employee codes. A name alone never signs in,
a wrong password counts against the throttle like any other wrong try, and the role works exactly as an employee's would."""
import pytest
from fastapi.testclient import TestClient

from app import auth as auth_module
from app.config import Settings, parse_users
from app.main import create_app


def test_the_users_setting_is_parsed_and_bad_lines_are_dropped():
    users = parse_users("client:admin:Str0ng:pass, viewer : view : look-only ,broken,noname::x,ghost:nope:pw")
    assert users == [{"name": "client", "role": "admin", "password": "Str0ng:pass"},
                     {"name": "viewer", "role": "view", "password": "look-only"}]
    assert parse_users("") == [] and parse_users(None) == []


def test_users_alone_switch_the_login_on(stores, tmp_path):
    settings = Settings(github_token="t", stores=stores, data_dir=tmp_path, stores_file=tmp_path / "stores.json",
                        dashboard_users=parse_users("client:admin:secret-pw"))
    assert settings.login_required
    auth = auth_module.SessionAuth("", users=settings.dashboard_users)
    assert auth.enabled and auth.check_user("Client", "secret-pw") == "admin"
    assert auth.check_user("client", "wrong") is None and auth.check_user("", "secret-pw") is None and auth.check_user("client", "") is None


@pytest.fixture
def guarded(stores, tmp_path, fake, db, jobs, links):
    settings = Settings(github_token="t", stores=stores, data_dir=tmp_path, stores_file=tmp_path / "stores.json", dashboard_password="owner-pass",
                        dashboard_users=parse_users("bestview:admin:Glazing#2026,office:view:look-only"))
    app = create_app(settings=settings, client=fake, database=db, jobs=jobs, link_fetch=links, sleep=lambda seconds: None)
    return TestClient(app)


def test_the_client_signs_in_with_name_and_password_and_the_header_says_who(guarded):
    web = guarded
    assert web.get("/", follow_redirects=False).status_code == 303
    ok = web.post("/login", data={"username": "bestview", "password": "Glazing#2026", "next": "/settings"}, follow_redirects=False)
    assert ok.status_code == 303 and ok.headers["location"] == "/settings"
    home = web.get("/")
    assert home.status_code == 200 and "bestview · admin" in home.text and "Sign out" in home.text


def test_a_wrong_password_or_unknown_name_is_refused(guarded):
    web = guarded
    assert "do not match" in web.post("/login", data={"username": "bestview", "password": "nope", "next": "/"}).text
    assert "do not match" in web.post("/login", data={"username": "nobody", "password": "Glazing#2026", "next": "/"}).text
    assert web.get("/", follow_redirects=False).status_code == 303


def test_a_view_user_looks_but_presses_nothing(guarded):
    web = guarded
    assert web.post("/login", data={"username": "office", "password": "look-only", "next": "/"}, follow_redirects=False).status_code == 303
    assert web.get("/pricing").status_code == 200
    refused = web.post("/api/stores/gtv/variables", json={"name": "X", "value": "1"})
    assert refused.status_code == 403


def test_the_owner_password_and_a_blank_name_still_work(guarded):
    web = guarded
    assert web.post("/login", data={"username": "", "password": "owner-pass", "next": "/"}, follow_redirects=False).status_code == 303
    assert "owner · admin" in web.get("/").text
