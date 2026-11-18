"""Employee sign-ins and the three roles (2026-10-28). The owner password stays the admin door; an employee signs in with their own code (stored only as a salted hash, the plain
code shown once) and gets view (looks, presses nothing), operate (presses the run and apply buttons) or admin (also settings and accounts). The middleware enforces the role on
every POST, so a page that still shows a button cannot get around it."""
import pytest
from conftest import Links, Settings, Store
from fastapi.testclient import TestClient

from app import auth as auth_module
from app.db import Database
from app.jobs import Jobs
from app.main import create_app


@pytest.fixture
def guarded(stores, fake, tmp_path):
    settings = Settings(github_token="t", stores=stores, data_dir=tmp_path, stores_file=tmp_path / "stores.json", dashboard_password="owner-pass")
    db = Database(":memory:")
    app = create_app(settings=settings, client=fake, database=db, jobs=Jobs(inline=True), link_fetch=Links(), sleep=lambda s: None)
    return TestClient(app), db


def owner(web):
    assert web.post("/login", data={"password": "owner-pass", "next": "/"}, follow_redirects=False).status_code == 303
    return web


def employee(web, role, name=None):
    """A fresh signed-in client for a new employee of the role (made by the owner, then signed in with the once-shown code)."""
    made = web.post("/api/employees", json={"name": name or f"{role} person", "role": role}).json()
    assert made["ok"] and len(made["code"]) == 12
    web.cookies.clear()
    assert web.post("/login", data={"password": made["code"], "next": "/"}, follow_redirects=False).status_code == 303
    return made


# ---- the pure parts ---------------------------------------------------------------------------------------------------------------------
def test_codes_are_hashed_and_verified_and_never_match_empty():
    salt = auth_module.new_salt()
    code = auth_module.new_code()
    stored = auth_module.hash_code(code, salt)
    assert auth_module.verify_code(code, salt, stored) and not auth_module.verify_code("wrong", salt, stored)
    assert not auth_module.verify_code("", salt, auth_module.hash_code("", salt))      # an empty code signs nobody in

def test_what_each_method_and_path_needs():
    assert auth_module.role_needed("GET", "/pricing") is None and auth_module.role_needed("POST", "/login") is None
    assert auth_module.role_needed("POST", "/api/store/gtv/run") == "operate"
    assert auth_module.role_needed("POST", "/api/store/gtv/pricing/apply") == "operate"
    assert auth_module.role_needed("POST", "/api/store/gtv/buybox/settings") == "admin"
    assert auth_module.role_needed("POST", "/api/store/gtv/variables") == "admin"
    assert auth_module.role_needed("POST", "/api/store/gtv/fees/mode") == "admin"
    assert auth_module.role_needed("POST", "/api/employees") == "admin" and auth_module.role_needed("POST", "/api/employees/3/delete") == "admin"


# ---- signing in -------------------------------------------------------------------------------------------------------------------------
def test_an_employee_signs_in_with_their_code_and_the_header_says_who(guarded):
    web, db = guarded
    emp = employee(owner(web), "operate", name="Sadia")
    page = web.get("/help")
    assert page.status_code == 200 and "Sadia · operate" in page.text
    names = [a["actor"] for a in db.recent_audit(limit=5)]
    assert "Sadia" in names                                                            # the sign-in is audited under the employee's own name

def test_a_wrong_code_and_a_switched_off_employee_are_refused(guarded):
    web, db = guarded
    emp = employee(owner(web), "view", name="Casey")
    web.cookies.clear()
    bad = web.post("/login", data={"password": "not-a-code", "next": "/"})
    assert "not the password or an employee code" in bad.text
    owner(web)
    web.post(f"/api/employees/{emp['employee']['id']}", json={"active": False})
    web.cookies.clear()
    off = web.post("/login", data={"password": emp["code"], "next": "/"})
    assert "not the password or an employee code" in off.text

def test_a_new_code_stops_the_old_one_at_once(guarded):
    web, db = guarded
    emp = employee(owner(web), "operate")
    web.cookies.clear()
    owner(web)
    fresh = web.post(f"/api/employees/{emp['employee']['id']}/code", json={}).json()
    assert fresh["ok"] and fresh["code"] != emp["code"]
    web.cookies.clear()
    assert "not the password" in web.post("/login", data={"password": emp["code"], "next": "/"}).text
    assert web.post("/login", data={"password": fresh["code"], "next": "/"}, follow_redirects=False).status_code == 303


# ---- what each role may press -----------------------------------------------------------------------------------------------------------
def test_view_sees_every_page_and_presses_nothing(guarded):
    web, db = guarded
    employee(owner(web), "view")
    assert web.get("/pricing?store=gtv").status_code == 200 and web.get("/settings").status_code == 200
    refused = web.post("/api/store/gtv/run", json={"workflow": "run.yml"})
    assert refused.status_code == 403 and "can look but not press" in refused.json()["error"]
    assert web.post("/api/store/gtv/pictures/scan", json={"text": "123"}).status_code == 403

def test_operate_presses_the_buttons_but_not_the_settings(guarded, fake):
    web, db = guarded
    employee(owner(web), "operate", name="Riley")
    ran = web.post("/api/store/gtv/run", json={"workflow": "orders_lookup.yml", "inputs": {"sku": "NONE", "list_all": "yes"}})
    assert ran.status_code == 200 and "error" not in ran.json()
    assert fake.dispatched and db.recent_dispatches()[0]["actor"] == "Riley"           # what they press runs under their name
    for path, body in (("/api/store/gtv/variables", {"name": "X", "value": "1"}), ("/api/store/gtv/fees/mode", {"mode": "category"}),
                       ("/api/store/gtv/buybox/settings", {}), ("/api/employees", {"name": "x", "role": "view"})):
        refused = web.post(path, json=body)
        assert refused.status_code == 403 and "admin code" in refused.json()["error"], path

def test_admin_changes_settings_and_accounts(guarded, fake):
    web, db = guarded
    employee(owner(web), "admin", name="Alex")
    assert web.post("/api/store/gtv/variables", json={"name": "PURGE_DEAD_ROWS", "value": "0", "confirm": True}).json().get("ok")
    made = web.post("/api/employees", json={"name": "Nour", "role": "view"}).json()
    assert made["ok"] and db.employee(made["employee"]["id"])["role"] == "view"


# ---- managing the accounts ----------------------------------------------------------------------------------------------------------------
def test_the_owner_manages_employees_and_every_change_is_audited(guarded):
    web, db = guarded
    owner(web)
    made = web.post("/api/employees", json={"name": "  Sam  Jones ", "role": "operate"}).json()
    assert made["employee"]["name"] == "Sam Jones"
    twice = web.post("/api/employees", json={"name": "sam jones", "role": "view"})
    assert twice.status_code == 400 and "already is an employee" in twice.json()["error"]
    assert web.post("/api/employees", json={"name": "x", "role": "boss"}).status_code == 400
    assert web.post("/api/employees", json={"name": "", "role": "view"}).status_code == 400
    emp_id = made["employee"]["id"]
    assert web.post(f"/api/employees/{emp_id}", json={"role": "admin"}).json()["employee"]["role"] == "admin"
    assert web.post(f"/api/employees/{emp_id}", json={}).status_code == 400
    assert web.post("/api/employees/999", json={"role": "view"}).status_code == 404
    assert web.post(f"/api/employees/{emp_id}/delete", json={}).json()["ok"] and db.employee(emp_id) is None
    actions = [a["action"] for a in db.recent_audit(limit=10)]
    assert {"employee_added", "employee_changed", "employee_removed"} <= set(actions)

def test_the_settings_page_shows_the_employees_to_the_admin(guarded):
    web, db = guarded
    owner(web)
    web.post("/api/employees", json={"name": "Sadia", "role": "operate"})
    page = web.get("/settings").text
    assert "Employees" in page and "Sadia" in page and "Add and make the code" in page

def test_while_the_login_is_off_everything_stays_open_as_before(web):
    assert web.get("/settings").status_code == 200                                    # the plain fixture app has no password
    assert "error" not in web.post("/api/store/gtv/run", json={"workflow": "orders_lookup.yml", "inputs": {"sku": "NONE", "list_all": "yes"}}).json()
