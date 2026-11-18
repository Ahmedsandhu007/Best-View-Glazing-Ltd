"""Who may open the dashboard and who may press what. Off entirely while DASHBOARD_PASSWORD is empty (local use on this PC).

One signed cookie carries the name and the role. DASHBOARD_PASSWORD is the owner's and signs in as admin; DASHBOARD_USERS gives named
people (the client first) a username and password of their own with one of the roles below; employees sign in
with their own code (set up on Settings, stored only as a salted hash) and get one of three roles:
  * view    - sees every page, presses nothing (any button that starts a run or changes anything is refused);
  * operate - may press the run and apply buttons, with the same confirmation boxes as always;
  * admin   - operate plus the settings (repository variables, fee mode, the per-card settings) and the employee accounts.
"""
import hashlib
import hmac
import secrets
import time

from fastapi.responses import JSONResponse, RedirectResponse
from itsdangerous import BadSignature, URLSafeTimedSerializer
from starlette.middleware.base import BaseHTTPMiddleware

COOKIE = "onbuy_dash"
MAX_AGE = 12 * 3600
OPEN_PATHS = ("/login", "/healthz", "/static/")
ROLES = ("view", "operate", "admin")
RANK = {role: n for n, role in enumerate(ROLES)}
ADMIN_SUFFIXES = ("/settings", "/variables", "/fees/mode")      # the POSTs that change how the stores behave rather than run them
THROTTLE_FAILS = 8                                              # wrong tries that fit in the window before sign-in pauses
THROTTLE_WINDOW = 600                                           # seconds


class Throttle:
    """Slows a password-guesser to a crawl once the dashboard faces the internet: after THROTTLE_FAILS wrong sign-ins inside
    THROTTLE_WINDOW seconds, every sign-in waits until the oldest failure leaves the window. One counter for the whole dashboard,
    not per address - a guesser cannot sidestep it by changing addresses, and a family-sized tool can live with everyone pausing
    together for a few minutes. A lock only ever ends by itself; a right password does not lift it, or the guesser could keep
    trying behind one stolen code."""

    def __init__(self, fails=THROTTLE_FAILS, window=THROTTLE_WINDOW, clock=time.monotonic):
        self.fails, self.window, self.clock = fails, window, clock
        self.failures = []

    def wait_seconds(self):
        """0 = a sign-in may be tried now; otherwise the seconds until it may again."""
        now = self.clock()
        self.failures = [t for t in self.failures if now - t < self.window]
        if len(self.failures) < self.fails:
            return 0
        return max(0.0, self.failures[0] + self.window - now)

    def record_failure(self):
        self.failures.append(self.clock())


def new_code():
    """An employee's sign-in code: 12 characters, made here so nobody has to think one up and the plain text is shown exactly once."""
    return secrets.token_hex(6)


def new_salt():
    return secrets.token_hex(16)


def hash_code(code, salt):
    return hashlib.pbkdf2_hmac("sha256", str(code or "").encode("utf-8"), bytes.fromhex(salt), 120_000).hex()


def verify_code(code, salt, code_hash):
    return bool(code) and hmac.compare_digest(hash_code(code, salt), code_hash)


def role_needed(method, path):
    """The role a request needs, or None when any signed-in person (or an open dashboard) may make it. Reading is free: every page stays readable with any role."""
    if method != "POST" or path == "/login":
        return None
    if path.startswith("/api/employees") or path.startswith("/api/stores"):
        return "admin"
    if any(path.endswith(s) for s in ADMIN_SUFFIXES):
        return "admin"
    return "operate"


class SessionAuth:
    def __init__(self, password, secret=None, users=None):
        self.password = password or ""
        self.users = list(users or [])
        self.serializer = URLSafeTimedSerializer(secret or secrets.token_hex(32), salt="onbuy-dashboard")

    @property
    def enabled(self):
        return bool(self.password) or bool(self.users)

    def check_password(self, given):
        return self.enabled and hmac.compare_digest(given or "", self.password)

    def check_user(self, name, given):
        """The role of the named user when the password matches, else None. Every user is compared whatever the name, so a wrong name
        costs the same time as a wrong password."""
        wanted = (name or "").strip().lower()
        found = None
        for u in self.users:
            if hmac.compare_digest(u["password"], given or "") and u["name"] == wanted:
                found = u["role"]
        return found if (wanted and given) else None

    def cookie_value(self, name="owner", role="admin"):
        return self.serializer.dumps({"u": str(name)[:40], "r": role if role in ROLES else "view"})

    def session(self, request):
        """{'u': name, 'r': role} of the signed-in person; the owner with every right while the login is off; None = not signed in."""
        if not self.enabled:
            return {"u": "owner", "r": "admin"}
        raw = request.cookies.get(COOKIE)
        if not raw:
            return None
        try:
            data = self.serializer.loads(raw, max_age=MAX_AGE)
        except BadSignature:
            return None
        if not isinstance(data, dict) or not data.get("u"):
            return None
        return {"u": str(data["u"]), "r": data.get("r") if data.get("r") in ROLES else "admin"}      # a cookie from before the roles is the owner's

    def valid(self, request):
        return self.session(request) is not None

    def actor(self, request):
        return (self.session(request) or {}).get("u", "owner")

    def role(self, request):
        return (self.session(request) or {}).get("r", "admin")


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, auth):
        super().__init__(app)
        self.auth = auth

    async def dispatch(self, request, call_next):
        path = request.url.path
        if self.auth.enabled and not path.startswith(OPEN_PATHS):
            session = self.auth.session(request)
            if session is None:
                if request.headers.get("accept", "").startswith("application/json") or path.startswith("/api/"):
                    return JSONResponse({"error": "sign in first"}, status_code=401)
                return RedirectResponse(url="/login?next=" + path, status_code=303)
            needed = role_needed(request.method, path)
            if needed and RANK[session["r"]] < RANK[needed]:
                what = ("Your code can look but not press - an operate or admin code can." if session["r"] == "view"
                        else "Only an admin code changes settings or accounts.")
                return JSONResponse({"error": what}, status_code=403)
        return await call_next(request)
