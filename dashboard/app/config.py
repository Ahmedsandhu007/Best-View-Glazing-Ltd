"""Settings (from .env / the environment) and the store registry (config/stores.json)."""
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


@dataclass(frozen=True)
class Store:
    id: str
    name: str
    repo: str
    sheet: str = ""
    product_tab: str = "Sheet1"
    amazon_tab: str = "Amazon"
    sheet_url: str = ""                      # the Google Sheet's link, so the dashboard holds every store's places in one row
    amazon: bool = True                      # False = an eBay-only store: no Amazon sync is expected, so none is judged, listed or planned for it

    @property
    def repo_url(self):
        return f"https://github.com/{self.repo}"


@dataclass
class Settings:
    github_token: str = ""
    github_api: str = "https://api.github.com"
    github_ref: str = "main"
    google_credentials_file: str = ""
    dashboard_password: str = ""
    dashboard_secret: str = ""
    dashboard_users: list = field(default_factory=list)      # [{name, role, password}] from DASHBOARD_USERS
    host: str = "127.0.0.1"
    port: int = 8787
    stores_file: Path = ROOT / "config" / "stores.json"
    data_dir: Path = ROOT / "data"
    stores: list = field(default_factory=list)

    @property
    def login_required(self):
        return bool(self.dashboard_password) or bool(self.dashboard_users)

    def store(self, store_id):
        for s in self.stores:
            if s.id == store_id:
                return s
        raise KeyError(store_id)


def gh_cli_token():
    """The signed-in GitHub CLI's token, so the dashboard needs no extra secret on this PC."""
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=15)
        return out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


STORE_FIELDS = ("id", "name", "repo", "sheet", "product_tab", "amazon_tab", "sheet_url")
_OPTIONAL_WHEN_EMPTY = ("sheet_url",)        # left out of the file when empty, so registries from before the field stay byte-identical


def clean_store_id(value):
    """A store id the URLs and caches can carry -> (id, "") or (None, why): 2-20 chars, a-z 0-9 and dashes, starting with a letter."""
    text = str(value or "").strip().lower()
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,19}", text):
        return None, "The id is 2-20 characters: small letters, digits and dashes, starting with a letter (it goes into every URL)."
    return text, ""


def clean_repo(value):
    """An owner/name GitHub repository -> (repo, "") or (None, why)."""
    text = str(value or "").strip().removeprefix("https://github.com/").strip("/")
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", text):
        return None, "The repository is owner/name (or its github.com link)."
    return text, ""


def save_stores(path, stores):
    """Write the registry back the way load_stores reads it, one store per line (the file's own style - it lives in git)."""
    lines = []
    for s in stores:
        row = {k: getattr(s, k) for k in STORE_FIELDS if getattr(s, k) or k not in _OPTIONAL_WHEN_EMPTY}
        if not s.amazon:
            row["amazon"] = False                # written only when switched off, so every other store's line stays byte-identical
        lines.append(json.dumps(row, ensure_ascii=False))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("[\n  " + ",\n  ".join(lines) + "\n]\n", encoding="utf-8")


def load_stores(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    stores = [Store(**{k: v for k, v in item.items() if k in Store.__dataclass_fields__}) for item in raw]
    ids = [s.id for s in stores]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate store id in " + str(path))
    return stores


USER_ROLES = ("view", "operate", "admin")


def parse_users(text):
    """DASHBOARD_USERS -> [{name, role, password}]. Entries are separated by commas; each is name:role:password, so the password may hold
    colons but not commas. Anything that is not three non-empty parts with a known role is dropped silently - a half-typed entry must
    never become a sign-in - and names are kept lower-case so sign-in is not case-sensitive on the name."""
    users = []
    for entry in (text or "").split(","):
        parts = entry.strip().split(":", 2)
        if len(parts) != 3:
            continue
        name, role, password = parts[0].strip().lower(), parts[1].strip().lower(), parts[2].strip()
        if not name or not password or role not in USER_ROLES or any(u["name"] == name for u in users):
            continue
        users.append({"name": name[:40], "role": role, "password": password})
    return users


def load_settings(env=None):
    env = env if env is not None else os.environ
    stores_file = Path(env.get("STORES_FILE") or (ROOT / "config" / "stores.json"))
    if not stores_file.is_absolute():
        stores_file = ROOT / stores_file
    data_dir = Path(env.get("DATA_DIR") or (ROOT / "data"))
    if not data_dir.is_absolute():
        data_dir = ROOT / data_dir
    token = (env.get("GITHUB_TOKEN") or "").strip() or gh_cli_token()
    return Settings(
        github_token=token,
        github_api=(env.get("GITHUB_API") or "https://api.github.com").rstrip("/"),
        github_ref=(env.get("GITHUB_REF") or "main").strip(),
        google_credentials_file=(env.get("GOOGLE_CREDENTIALS_FILE") or "").strip(),
        dashboard_password=(env.get("DASHBOARD_PASSWORD") or "").strip(),
        dashboard_secret=(env.get("DASHBOARD_SECRET") or "").strip(),
        dashboard_users=parse_users(env.get("DASHBOARD_USERS")),
        host=(env.get("DASHBOARD_HOST") or "127.0.0.1").strip(),
        port=int(env.get("DASHBOARD_PORT") or env.get("PORT") or "8787"),          # PORT: the name most hosts (Cloud Run, Render, Heroku) give the port to listen on
        stores_file=stores_file,
        data_dir=data_dir,
        stores=load_stores(stores_file),
    )
