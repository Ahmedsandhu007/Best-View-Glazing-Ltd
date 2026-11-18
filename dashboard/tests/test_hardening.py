"""VPS readiness (2026-10-29): the sign-in throttle and the one-zip backup - the two pieces of the move that need no host chosen yet.

Online, nothing stopped a guesser from hammering /login all day; and the dashboard's own memory (accounts, audit, tick-marks, ticket
builds) lived only on this PC's disk with no way to carry it to the VPS.
"""
import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app import auth as auth_module
from app.auth import COOKIE
from app.config import Settings
from app.db import Database
from app.main import create_app


def pw_app(stores, fake, tmp_path, password="pw"):
    settings = Settings(github_token="t", stores=stores, data_dir=tmp_path, dashboard_password=password, stores_file=tmp_path / "stores.json")
    db = Database(":memory:")
    return create_app(settings=settings, client=fake, database=db, sleep=lambda seconds: None), db


def test_the_throttle_fills_waits_and_unlocks_by_itself():
    t = [0.0]
    th = auth_module.Throttle(fails=3, window=100, clock=lambda: t[0])
    assert th.wait_seconds() == 0
    for _ in range(3):
        th.record_failure()
    assert th.wait_seconds() == 100
    t[0] = 60
    assert th.wait_seconds() == 40
    t[0] = 100.5
    assert th.wait_seconds() == 0                        # the oldest failure left the window
    th.record_failure()
    assert th.wait_seconds() == 0                        # one fresh failure is far from the limit


def test_eight_wrong_sign_ins_pause_the_login_even_for_the_right_password(stores, fake, tmp_path):
    app, db = pw_app(stores, fake, tmp_path)
    web = TestClient(app)
    for _ in range(auth_module.THROTTLE_FAILS):
        assert "not the password" in web.post("/login", data={"password": "wrong", "next": "/"}).text
    locked = web.post("/login", data={"password": "pw", "next": "/"}, follow_redirects=False)
    assert locked.status_code == 200 and "paused for another" in locked.text and not locked.cookies.get(COOKIE)
    actions = [a["action"] for a in db.recent_audit(limit=30)]
    assert actions.count("login_failed") == auth_module.THROTTLE_FAILS and "login" not in actions


def test_the_backup_zip_holds_the_database_and_the_small_files_but_never_the_log_store(web, settings, db):
    root = Path(settings.data_dir)
    (root / "logs" / "org_gtv").mkdir(parents=True)
    (root / "logs" / "org_gtv" / "123.txt.gz").write_bytes(b"x" * 10)
    (root / "pictures" / "gtv").mkdir(parents=True)
    (root / "pictures" / "gtv" / "latest.txt").write_text("job1", encoding="utf-8")
    Path(settings.stores_file).write_text("[]", encoding="utf-8")
    r = web.get("/api/backup")
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    assert "best-view-glazing-dashboard-backup-" in r.headers["content-disposition"]
    z = zipfile.ZipFile(io.BytesIO(r.content))
    names = z.namelist()
    assert "data/dashboard.db" in names and "data/pictures/gtv/latest.txt" in names and "README.txt" in names and "stores.json" in names
    assert not any(n.startswith("data/logs/") for n in names) and z.getinfo("data/dashboard.db").file_size > 0
    assert "unzip into DATA_DIR" in z.read("README.txt").decode() or "into the new dashboard's DATA_DIR" in z.read("README.txt").decode()
    assert not list(root.glob(".backup-*.db"))           # the snapshot never lingers on disk
    assert [a["action"] for a in db.recent_audit(limit=3)][0] == "backup"


def test_only_an_admin_downloads_the_backup_once_the_login_is_on(stores, fake, tmp_path):
    app, db = pw_app(stores, fake, tmp_path)
    owner = TestClient(app)
    assert owner.get("/api/backup").status_code == 401                     # not signed in at all
    owner.post("/login", data={"password": "pw", "next": "/"})
    assert owner.get("/api/backup").status_code == 200
    code = owner.post("/api/employees", json={"name": "Vera", "role": "view"}).json()["code"]
    vera = TestClient(app)
    vera.post("/login", data={"password": code, "next": "/"})
    refused = vera.get("/api/backup")
    assert refused.status_code == 403 and "admin code" in refused.json()["error"]
