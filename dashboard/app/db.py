"""Local state in one SQLite file: settings, what was pressed (audit), and the runs the dashboard started."""
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, actor TEXT NOT NULL, store TEXT NOT NULL,
    action TEXT NOT NULL, detail TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dispatches (
    id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, actor TEXT NOT NULL, store TEXT NOT NULL,
    workflow TEXT NOT NULL, inputs TEXT NOT NULL, run_id INTEGER, run_url TEXT, status TEXT NOT NULL, note TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS dispatches_store ON dispatches(store, id);
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE COLLATE NOCASE, role TEXT NOT NULL,
    salt TEXT NOT NULL, code_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS suspended_marks (
    store TEXT NOT NULL, sku TEXT NOT NULL, actor TEXT NOT NULL, at TEXT NOT NULL, PRIMARY KEY (store, sku));
"""


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class Database:
    def __init__(self, path):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)

    def _run(self, sql, params=(), fetch=False):
        with self._lock:
            cur = self._conn.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()] if fetch else None
            self._conn.commit()
            return rows if fetch else cur.lastrowid

    # settings
    def get(self, key, default=""):
        rows = self._run("SELECT value FROM settings WHERE key = ?", (key,), fetch=True)
        return rows[0]["value"] if rows else default

    def set(self, key, value):
        self._run("INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, str(value)))

    # audit
    def audit(self, actor, store, action, detail=""):
        return self._run("INSERT INTO audit(at, actor, store, action, detail) VALUES(?, ?, ?, ?, ?)",
                         (now_iso(), actor, store, action, detail if isinstance(detail, str) else json.dumps(detail)))

    def recent_audit(self, limit=50, store=None):
        if store:
            return self._run("SELECT * FROM audit WHERE store = ? ORDER BY id DESC LIMIT ?", (store, limit), fetch=True)
        return self._run("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,), fetch=True)

    # dispatches
    def record_dispatch(self, actor, store, workflow, inputs, run=None, status="dispatched", note=""):
        return self._run(
            "INSERT INTO dispatches(at, actor, store, workflow, inputs, run_id, run_url, status, note) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (now_iso(), actor, store, workflow, json.dumps(inputs or {}), (run or {}).get("id"), (run or {}).get("url"), status, note))

    def update_dispatch(self, dispatch_id, run=None, status=None, note=None):
        row = self._run("SELECT * FROM dispatches WHERE id = ?", (dispatch_id,), fetch=True)
        if not row:
            return
        row = row[0]
        self._run("UPDATE dispatches SET run_id = ?, run_url = ?, status = ?, note = ? WHERE id = ?",
                  ((run or {}).get("id", row["run_id"]), (run or {}).get("url", row["run_url"]), status or row["status"],
                   row["note"] if note is None else note, dispatch_id))

    def recent_dispatches(self, store=None, limit=20):
        if store:
            rows = self._run("SELECT * FROM dispatches WHERE store = ? ORDER BY id DESC LIMIT ?", (store, limit), fetch=True)
        else:
            rows = self._run("SELECT * FROM dispatches ORDER BY id DESC LIMIT ?", (limit,), fetch=True)
        for r in rows:
            try:
                r["inputs"] = json.loads(r["inputs"] or "{}")
            except ValueError:
                r["inputs"] = {}
        return rows

    def dispatch(self, dispatch_id):
        rows = self._run("SELECT * FROM dispatches WHERE id = ?", (dispatch_id,), fetch=True)
        return rows[0] if rows else None

    # employees (the codes live here only as salted hashes; the plain code is shown once when it is made)
    def employees(self):
        return self._run("SELECT id, name, role, active, created FROM employees ORDER BY name COLLATE NOCASE", fetch=True)

    def employee_secrets(self):
        """For the sign-in check only: every active employee with the salt and hash the typed code is tried against."""
        return self._run("SELECT id, name, role, salt, code_hash FROM employees WHERE active = 1", fetch=True)

    def add_employee(self, name, role, salt, code_hash):
        return self._run("INSERT INTO employees(name, role, salt, code_hash, active, created) VALUES(?, ?, ?, ?, 1, ?)",
                         (name, role, salt, code_hash, now_iso()))

    def employee(self, emp_id):
        rows = self._run("SELECT id, name, role, active, created FROM employees WHERE id = ?", (emp_id,), fetch=True)
        return rows[0] if rows else None

    def set_employee(self, emp_id, role=None, active=None, salt=None, code_hash=None):
        row = self.employee(emp_id)
        if not row:
            return None
        if role is not None:
            self._run("UPDATE employees SET role = ? WHERE id = ?", (role, emp_id))
        if active is not None:
            self._run("UPDATE employees SET active = ? WHERE id = ?", (1 if active else 0, emp_id))
        if salt is not None and code_hash is not None:
            self._run("UPDATE employees SET salt = ?, code_hash = ? WHERE id = ?", (salt, code_hash, emp_id))
        return self.employee(emp_id)

    def delete_employee(self, emp_id):
        self._run("DELETE FROM employees WHERE id = ?", (emp_id,))

    def backup_to(self, path):
        """A consistent snapshot of the whole database into a new file - sqlite's own backup, safe while the app writes."""
        with self._lock:
            dest = sqlite3.connect(str(path))
            try:
                self._conn.backup(dest)
                dest.commit()
            finally:
                dest.close()

    # suspended listings deleted by hand (keyed by the normalized SKU, so a report with leading zeros meets its mark)
    def suspended_marks(self, store):
        return {r["sku"]: {"actor": r["actor"], "at": r["at"]} for r in
                self._run("SELECT sku, actor, at FROM suspended_marks WHERE store = ?", (store,), fetch=True)}

    def mark_suspended(self, store, sku, actor):
        self._run("INSERT INTO suspended_marks(store, sku, actor, at) VALUES(?, ?, ?, ?) "
                  "ON CONFLICT(store, sku) DO UPDATE SET actor = excluded.actor, at = excluded.at", (store, sku, actor, now_iso()))

    def unmark_suspended(self, store, sku):
        self._run("DELETE FROM suspended_marks WHERE store = ? AND sku = ?", (store, sku))
