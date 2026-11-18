"""The GitHub Actions side of a store: runs, the queue, dispatching a workflow, logs, repository variables, workflow definitions.

Everything a store repository exposes to the dashboard goes through here. The client is synchronous (httpx) and small; the
pages call it from a thread pool. A test can hand it an httpx transport that answers from canned data.
"""
import base64
import re
import threading
import time
from datetime import datetime, timezone

import httpx
import yaml

PENDING_STATES = ("queued", "waiting", "pending", "requested")
ACTIVE_STATES = PENDING_STATES + ("in_progress",)


class GitHubError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def utcnow():
    return datetime.now(timezone.utc)


def parse_iso(text):
    return datetime.fromisoformat(str(text).replace("Z", "+00:00"))


PLANNED_MARK = "· plan"          # run_amazon.yml's run-name when the Amazon dispatcher launched it from the plan


def _run_view(r):
    """The few fields a page needs from a workflow run. A sync the Amazon dispatcher launched arrives as a workflow_dispatch but is the
    store's schedule now (the dispatcher IS its clock), so it reports event 'schedule' - failure severity, staleness and the scheduled/manual
    labels all keep meaning what they always meant - and carries planned=True for the pages that want to say so."""
    event = r.get("event") or ""
    title = r.get("display_title") or ""
    planned = event == "workflow_dispatch" and PLANNED_MARK in title
    return {
        "id": r.get("id"),
        "name": r.get("name") or "",
        "path": (r.get("path") or "").rsplit("/", 1)[-1],
        "status": r.get("status") or "",
        "conclusion": r.get("conclusion") or "",
        "event": "schedule" if planned else event,
        "planned": planned,
        "created_at": r.get("created_at") or "",
        "updated_at": r.get("updated_at") or "",
        "url": r.get("html_url") or "",
        "run_number": r.get("run_number"),
        "title": title,
    }


class GitHubClient:
    def __init__(self, token, api="https://api.github.com", transport=None, sleep=time.sleep, cache_ttl=600):
        self.api = api.rstrip("/")
        self.token = token
        self._sleep = sleep
        self._cache = {}
        self._cache_ttl = cache_ttl
        self._etags = {}                    # (path, params) -> (etag, body): GitHub's conditional requests, see _json
        self._etag_lock = threading.Lock()
        self.answers_reused = self.answers_fetched = 0
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "onbuy-dashboard"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self._transport = transport
        self.http = httpx.Client(base_url=self.api, headers=headers, timeout=30, follow_redirects=True, transport=transport)

    # ---- plumbing -------------------------------------------------------------------------------------------------------
    def _request(self, method, path, retry=1, **kw):
        try:
            resp = self.http.request(method, path, **kw)
        except httpx.HTTPError as exc:
            if retry:
                self._sleep(1)
                return self._request(method, path, retry=retry - 1, **kw)
            raise GitHubError(f"GitHub unreachable: {exc}") from exc
        if resp.status_code in (403, 429) and resp.headers.get("X-RateLimit-Remaining") == "0":
            reset = resp.headers.get("X-RateLimit-Reset")
            when = datetime.fromtimestamp(int(reset), tz=timezone.utc).strftime("%H:%MZ") if reset else "later"
            raise GitHubError(f"GitHub API rate limit reached - try again after {when}", resp.status_code)
        if resp.status_code >= 500 and retry:
            self._sleep(1)
            return self._request(method, path, retry=retry - 1, **kw)
        if resp.status_code >= 400:
            try:
                msg = resp.json().get("message") or resp.text[:200]
            except ValueError:
                msg = resp.text[:200]
            raise GitHubError(f"GitHub answered {resp.status_code}: {msg}", resp.status_code)
        return resp

    def _json(self, method, path, **kw):
        if method == "GET":
            return self._json_conditional(path, **kw)
        resp = self._request(method, path, **kw)
        return resp.json() if resp.content else {}

    def _json_conditional(self, path, params=None, **kw):
        """Every GET uses GitHub's conditional requests: the answer's ETag is remembered and sent back as If-None-Match, and an
        unchanged answer comes back as a body-less 304 - much faster than the full JSON, and it does not count against the API
        rate limit. The pages hammer the same run listings over and over, and most of the time nothing has changed.
        Answers are shared between calls: callers treat them as read-only (every page already does)."""
        key = (path, tuple(sorted((params or {}).items())))
        with self._etag_lock:
            known = self._etags.get(key)
        headers = dict(kw.pop("headers", None) or {})
        if known:
            headers["If-None-Match"] = known[0]
        resp = self._request("GET", path, params=params, headers=headers or None, **kw)
        if resp.status_code == 304 and known:
            self.answers_reused += 1
            return known[1]
        self.answers_fetched += 1
        body = resp.json() if resp.content else {}
        etag = resp.headers.get("ETag")
        if etag:
            with self._etag_lock:
                if len(self._etags) > 600:
                    self._etags.clear()
                self._etags[key] = (etag, body)
        return body

    def _cached(self, key, maker):
        hit = self._cache.get(key)
        if hit and hit[0] > time.time():
            return hit[1]
        value = maker()
        self._cache[key] = (time.time() + self._cache_ttl, value)
        return value

    # ---- who am I ---------------------------------------------------------------------------------------------------------
    def whoami(self):
        me = self._json("GET", "/user")
        return {"login": me.get("login", ""), "name": me.get("name") or ""}

    def repo_ok(self, repo):
        """Can this token see the repository's Actions? Returns (ok, message)."""
        try:
            self._json("GET", f"/repos/{repo}/actions/workflows", params={"per_page": 1})
            return True, "ok"
        except GitHubError as exc:
            return False, str(exc)

    # ---- runs and the queue -----------------------------------------------------------------------------------------------
    def list_runs(self, repo, limit=100, since=None, workflow=None):
        """Newest first. `since` (ISO or datetime) stops paging once runs are older. `workflow` = a file name to filter on."""
        since_iso = since.isoformat() if isinstance(since, datetime) else since
        out, page = [], 1
        path = f"/repos/{repo}/actions/workflows/{workflow}/runs" if workflow else f"/repos/{repo}/actions/runs"
        while len(out) < limit:
            per_page = min(100, limit - len(out))
            data = self._json("GET", path, params={"per_page": per_page, "page": page})
            runs = data.get("workflow_runs") or []
            for r in runs:
                v = _run_view(r)
                if since_iso and v["created_at"] < since_iso:
                    return out
                out.append(v)
            if len(runs) < per_page:
                break
            page += 1
        return out

    def queue(self, repo):
        """Runs that are not finished: {'in_progress': [...], 'pending': [...]}."""
        active = {"in_progress": [], "pending": []}
        for status in ("in_progress", "queued", "waiting", "pending", "requested"):
            data = self._json("GET", f"/repos/{repo}/actions/runs", params={"status": status, "per_page": 50})
            for r in data.get("workflow_runs") or []:
                v = _run_view(r)
                (active["in_progress"] if v["status"] == "in_progress" else active["pending"]).append(v)
        return active

    def run(self, repo, run_id):
        return _run_view(self._json("GET", f"/repos/{repo}/actions/runs/{run_id}"))

    def jobs(self, repo, run_id):
        data = self._json("GET", f"/repos/{repo}/actions/runs/{run_id}/jobs", params={"per_page": 50})
        return [{"id": j.get("id"), "name": j.get("name"), "status": j.get("status"), "conclusion": j.get("conclusion") or ""}
                for j in data.get("jobs") or []]

    def job_log(self, repo, job_id):
        """The plain-text log of one job (GitHub redirects to blob storage; the client follows)."""
        resp = self._request("GET", f"/repos/{repo}/actions/jobs/{job_id}/logs")
        return resp.text

    def run_log(self, repo, run_id):
        """All jobs' logs of a run, joined, timestamps stripped."""
        parts = []
        for j in self.jobs(repo, run_id):
            try:
                parts.append(self.job_log(repo, j["id"]))
            except GitHubError as exc:
                parts.append(f"(log of job {j['name']} unavailable: {exc})")
        return strip_timestamps("\n".join(parts))

    def cancel_run(self, repo, run_id):
        self._request("POST", f"/repos/{repo}/actions/runs/{run_id}/cancel")
        return True

    # ---- dispatch -----------------------------------------------------------------------------------------------------------
    def dispatch(self, repo, workflow_file, inputs=None, ref="main"):
        """Start a workflow. GitHub returns nothing but 204; the run is found afterwards with find_dispatched_run."""
        body = {"ref": ref}
        if inputs:
            body["inputs"] = {k: str(v) for k, v in inputs.items() if v is not None}
        started = utcnow()
        self._request("POST", f"/repos/{repo}/actions/workflows/{workflow_file}/dispatches", json=body)
        return started

    def find_dispatched_run(self, repo, workflow_file, started, attempts=8, wait=5):
        """The workflow_dispatch run created at or after `started` (a datetime); None if it has not appeared yet."""
        floor = (started.replace(microsecond=0)).isoformat().replace("+00:00", "Z")
        for _ in range(attempts):
            for r in self.list_runs(repo, limit=10, workflow=workflow_file):
                if r["event"] == "workflow_dispatch" and r["created_at"] >= floor:
                    return r
            self._sleep(wait)
        return None

    # ---- workflows and their inputs -----------------------------------------------------------------------------------------
    def list_workflows(self, repo):
        def make():
            out, page = [], 1
            while True:
                data = self._json("GET", f"/repos/{repo}/actions/workflows", params={"per_page": 100, "page": page})
                items = data.get("workflows") or []
                for w in items:
                    out.append({"id": w.get("id"), "name": w.get("name") or "", "path": (w.get("path") or "").rsplit("/", 1)[-1],
                                "state": w.get("state") or ""})
                if len(items) < 100:
                    return out
                page += 1
        return self._cached(("workflows", repo), make)

    def workflow_definition(self, repo, workflow_file, ref="main"):
        """name, dispatch inputs, schedule crons and the concurrency group of one workflow file."""
        def make():
            data = self._json("GET", f"/repos/{repo}/contents/.github/workflows/{workflow_file}", params={"ref": ref})
            text = base64.b64decode(data.get("content") or "").decode("utf-8", errors="replace")
            return parse_workflow(text, workflow_file)
        return self._cached(("definition", repo, workflow_file), make)

    def get_file(self, repo, path, ref="main", fresh=False):
        """A text file of the repository (cached per process for its cache TTL; fresh=True reads it again, e.g. the sale state right after an apply)."""
        if fresh:
            self._cache.pop(("file", repo, path, ref), None)

        def make():
            data = self._json("GET", f"/repos/{repo}/contents/{path}", params={"ref": ref})
            return base64.b64decode(data.get("content") or "").decode("utf-8", errors="replace")
        return self._cached(("file", repo, path, ref), make)

    def last_commit(self, repo, path, ref="main"):
        """The newest commit that touched a path: short sha, date, first line of the message, link (None when the path has no history)."""
        def make():
            data = self._json("GET", f"/repos/{repo}/commits", params={"path": path, "sha": ref, "per_page": 1})
            if not isinstance(data, list) or not data:
                return None
            c = data[0]
            meta = c.get("commit") or {}
            return {"sha": (c.get("sha") or "")[:7], "date": (meta.get("committer") or meta.get("author") or {}).get("date", ""),
                    "message": (meta.get("message") or "").splitlines()[0][:120] if meta.get("message") else "", "url": c.get("html_url") or ""}
        return self._cached(("commit", repo, path, ref), make)

    def list_dir(self, repo, path, ref="main"):
        """The entries of a directory of the repository -> [{name, path, type}] (an empty list when the directory does not exist)."""
        try:
            data = self._json("GET", f"/repos/{repo}/contents/{path.strip('/')}", params={"ref": ref})
        except GitHubError as exc:
            if exc.status == 404:
                return []
            raise
        if not isinstance(data, list):
            return []
        return [{"name": d.get("name") or "", "path": d.get("path") or "", "type": d.get("type") or ""} for d in data]

    def update_file(self, repo, path, transform, message, ref="main", attempts=3):
        """Change a text file of the repository and commit it on `ref`: read it (a missing file counts as empty and is created), let transform(text) -> new text edit it,
        commit with the file's sha. When somebody committed in between (the nightly appends to the hold lists) GitHub answers 409 / 422: read again and redo the edit.
        -> {changed, commit, url}; changed is False when the edit changed nothing (no commit is made)."""
        last = None
        for _ in range(attempts):
            sha, text = None, ""
            try:
                data = self._json("GET", f"/repos/{repo}/contents/{path}", params={"ref": ref})
                sha = data.get("sha")
                text = base64.b64decode(data.get("content") or "").decode("utf-8", errors="replace")
            except GitHubError as exc:
                if exc.status != 404:
                    raise
            new = transform(text)
            if new == text:
                return {"changed": False, "commit": "", "url": ""}
            body = {"message": message, "content": base64.b64encode(new.encode("utf-8")).decode("ascii"), "branch": ref}
            if sha:
                body["sha"] = sha
            try:
                data = self._json("PUT", f"/repos/{repo}/contents/{path}", json=body)
            except GitHubError as exc:
                if exc.status in (409, 422):
                    last = exc
                    self._sleep(1)
                    continue
                raise
            self._cache.pop(("file", repo, path, ref), None)
            commit = data.get("commit") or {}
            return {"changed": True, "commit": (commit.get("sha") or "")[:7], "url": commit.get("html_url") or ""}
        raise last

    # ---- artifacts ------------------------------------------------------------------------------------------------------------
    def run_artifacts(self, repo, run_id):
        """The files a run uploaded -> [{id, name, size, expired}]."""
        data = self._json("GET", f"/repos/{repo}/actions/runs/{run_id}/artifacts", params={"per_page": 50})
        return [{"id": a.get("id"), "name": a.get("name") or "", "size": a.get("size_in_bytes") or 0, "expired": bool(a.get("expired"))} for a in data.get("artifacts") or []]

    def download_artifact(self, repo, artifact_id, max_bytes=30_000_000):
        """The zip of an artifact. GitHub answers with a redirect to a signed address, which is fetched WITHOUT the token."""
        resp = self._request("GET", f"/repos/{repo}/actions/artifacts/{artifact_id}/zip", follow_redirects=False)
        if resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("location")
            if not location:
                raise GitHubError("GitHub gave no download address for the artifact")
            try:
                with httpx.Client(timeout=120, follow_redirects=True, transport=self._transport) as blob_client:
                    blob = blob_client.get(location)
            except httpx.HTTPError as exc:
                raise GitHubError(f"The artifact download failed: {exc}") from exc
            if blob.status_code >= 400:
                raise GitHubError(f"The artifact download answered {blob.status_code}", blob.status_code)
            content = blob.content
        else:
            content = resp.content
        if len(content) > max_bytes:
            raise GitHubError(f"The artifact is larger than {max_bytes // 1_000_000} MB")
        return content

    # ---- repository variables ----------------------------------------------------------------------------------------------
    def list_secrets(self, repo):
        """The repository's Actions secrets - NAMES and update times only: GitHub never returns a secret's value to anyone."""
        out, page = [], 1
        while True:
            data = self._json("GET", f"/repos/{repo}/actions/secrets", params={"per_page": 30, "page": page})
            items = data.get("secrets") or []
            out.extend({"name": s.get("name"), "updated_at": s.get("updated_at") or s.get("created_at", "")} for s in items)
            if len(items) < 30:
                return sorted(out, key=lambda s: s["name"])
            page += 1

    def set_secret(self, repo, name, value):
        """Create or update one Actions secret: the value is sealed with the repository's public key (libsodium, as GitHub requires)
        on this machine and only the ciphertext leaves it. The value is never stored, logged or echoed anywhere here."""
        from base64 import b64encode

        from nacl import encoding, public

        key = self._json("GET", f"/repos/{repo}/actions/secrets/public-key")
        sealed = public.SealedBox(public.PublicKey(key["key"].encode(), encoding.Base64Encoder())).encrypt(str(value).encode("utf-8"))
        self._request("PUT", f"/repos/{repo}/actions/secrets/{name}",
                      json={"encrypted_value": b64encode(sealed).decode(), "key_id": key["key_id"]})
        return True

    def list_variables(self, repo):
        out, page = [], 1
        while True:
            data = self._json("GET", f"/repos/{repo}/actions/variables", params={"per_page": 30, "page": page})
            items = data.get("variables") or []
            out.extend({"name": v.get("name"), "value": v.get("value", ""), "updated_at": v.get("updated_at", "")} for v in items)
            if len(items) < 30:
                return sorted(out, key=lambda v: v["name"])
            page += 1

    def set_variable(self, repo, name, value):
        try:
            self._request("PATCH", f"/repos/{repo}/actions/variables/{name}", json={"name": name, "value": str(value)})
        except GitHubError as exc:
            if exc.status != 404:
                raise
            self._request("POST", f"/repos/{repo}/actions/variables", json={"name": name, "value": str(value)})
        return True

    def delete_variable(self, repo, name):
        self._request("DELETE", f"/repos/{repo}/actions/variables/{name}")
        return True

    def set_workflow_state(self, repo, workflow_file, enabled):
        """Enable or disable one workflow (GitHub takes the file name in place of the id). The cached workflows list is
        dropped so the next read shows the new state at once."""
        self._request("PUT", f"/repos/{repo}/actions/workflows/{workflow_file}/{'enable' if enabled else 'disable'}")
        self._cache.pop(("workflows", repo), None)
        return True

    # ---- files (list files the batch tools read) --------------------------------------------------------------------------
    def put_file(self, repo, path, content, message, ref="main"):
        """Create or update a text file in the repository (the SKU lists under cleanup/)."""
        sha = None
        try:
            existing = self._json("GET", f"/repos/{repo}/contents/{path}", params={"ref": ref})
            sha = existing.get("sha")
        except GitHubError as exc:
            if exc.status != 404:
                raise
        body = {"message": message, "content": base64.b64encode(content.encode("utf-8")).decode("ascii"), "branch": ref}
        if sha:
            body["sha"] = sha
        data = self._json("PUT", f"/repos/{repo}/contents/{path}", json=body)
        return (data.get("content") or {}).get("path", path)


# ---- pure helpers -------------------------------------------------------------------------------------------------------------
_TS = re.compile(r"^\S*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z ?", re.M)


def strip_timestamps(text):
    return _TS.sub("", text or "")


def parse_workflow(text, workflow_file=""):
    """The parts of a workflow file the dashboard shows: name, dispatch inputs, schedule, concurrency group, scripts run."""
    try:
        y = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        return {"file": workflow_file, "name": workflow_file, "inputs": {}, "schedule": [], "group": "", "scripts": [],
                "error": f"yaml: {str(exc)[:80]}"}
    on = y.get("on")
    if on is None:
        on = y.get(True) or {}           # YAML 1.1 reads a bare `on:` key as the boolean True
    if isinstance(on, list):
        on = {k: {} for k in on}
    if not isinstance(on, dict):
        on = {}
    schedule = []
    for item in on.get("schedule") or []:
        if isinstance(item, dict) and item.get("cron"):
            schedule.append(str(item["cron"]))
    inputs = {}
    wd = on.get("workflow_dispatch")
    if isinstance(wd, dict):
        for key, spec in (wd.get("inputs") or {}).items():
            spec = spec or {}
            inputs[key] = {
                "description": str(spec.get("description", "")),
                "default": "" if spec.get("default") is None else str(spec.get("default")),
                "required": bool(spec.get("required", False)),
                "type": str(spec.get("type", "string")),
                "options": [str(o) for o in (spec.get("options") or [])],
            }
    group = ""
    conc = y.get("concurrency")
    if isinstance(conc, dict):
        group = str(conc.get("group", ""))
    elif isinstance(conc, str):
        group = conc
    scripts = sorted(set(re.findall(r"python3?\s+([A-Za-z0-9_]+\.py)", text)))
    return {"file": workflow_file, "name": str(y.get("name") or workflow_file), "inputs": inputs, "schedule": schedule,
            "group": group, "scripts": scripts, "manual": "workflow_dispatch" in on}
