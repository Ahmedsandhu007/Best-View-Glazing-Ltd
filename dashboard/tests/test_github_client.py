"""The GitHub client against canned HTTP answers (httpx.MockTransport) - no network."""
import base64
import json
from datetime import datetime, timezone

import httpx
import pytest

from app.github_client import GitHubClient, GitHubError, parse_workflow

WORKFLOW_YML = """
name: Purge Dead eBay Rows (dry run / live)
on:
  schedule:
    - cron: '7 * * * *'
  workflow_dispatch:
    inputs:
      dry_run:
        description: "yes = report only"
        default: "yes"
      max_rows:
        description: "cap"
        required: true
        default: "500"
concurrency:
  group: onbuy-api
  cancel-in-progress: false
jobs:
  purge:
    steps:
      - run: python purge_dead_rows.py
"""


def run_json(rid, path, status="completed", conclusion="success", event="schedule", created="2026-10-23T06:00:00Z"):
    return {"id": rid, "name": path, "path": f".github/workflows/{path}", "status": status, "conclusion": conclusion, "event": event,
            "created_at": created, "updated_at": created, "html_url": f"https://github.com/o/r/actions/runs/{rid}", "run_number": rid,
            "display_title": path}


class Canned:
    """A tiny router for MockTransport; records every request."""

    def __init__(self):
        self.requests = []
        self.variables = {"FEE_MODE": "category"}
        self.dispatch_count = 0

    def __call__(self, request):
        self.requests.append(request)
        path, method = request.url.path, request.method
        params = dict(request.url.params)
        if path == "/repos/o/r/actions/runs":
            status = params.get("status")
            runs = [run_json(3, "run.yml"), run_json(2, "run.yml", conclusion="failure"), run_json(1, "nightly_reconcile.yml", created="2026-10-22T02:40:00Z")]
            if status == "in_progress":
                runs = [run_json(9, "run_amazon.yml", status="in_progress", conclusion=None)]
            elif status in ("queued", "waiting", "pending", "requested"):
                runs = [run_json(8, "watch_recovery.yml", status="pending", conclusion=None)] if status == "pending" else []
            return httpx.Response(200, json={"workflow_runs": runs})
        if path == "/repos/o/r/actions/workflows/orders_lookup.yml/runs":
            created = "2026-10-23T07:00:05Z" if self.dispatch_count else "2026-10-22T07:00:05Z"
            return httpx.Response(200, json={"workflow_runs": [run_json(50, "orders_lookup.yml", status="queued", conclusion=None,
                                                                         event="workflow_dispatch", created=created)]})
        if path == "/repos/o/r/actions/workflows/orders_lookup.yml/dispatches" and method == "POST":
            self.dispatch_count += 1
            return httpx.Response(204)
        if path == "/repos/o/r/actions/variables" and method == "GET":
            return httpx.Response(200, json={"variables": [{"name": k, "value": v, "updated_at": "2026-10-01T00:00:00Z"} for k, v in self.variables.items()]})
        if path.startswith("/repos/o/r/actions/variables/") and method == "PATCH":
            name = path.rsplit("/", 1)[-1]
            if name not in self.variables:
                return httpx.Response(404, json={"message": "Not Found"})
            self.variables[name] = json.loads(request.content)["value"]
            return httpx.Response(204)
        if path == "/repos/o/r/actions/variables" and method == "POST":
            body = json.loads(request.content)
            self.variables[body["name"]] = body["value"]
            return httpx.Response(201)
        if path == "/repos/o/r/contents/.github/workflows/purge_dead_rows.yml":
            return httpx.Response(200, json={"content": base64.b64encode(WORKFLOW_YML.encode()).decode(), "sha": "abc"})
        if path == "/repos/o/r/actions/jobs/77/logs":
            return httpx.Response(200, text="2026-10-23T06:00:00.1234567Z INFO FIX done: 10 corrected, 0 failed\n")
        if path == "/repos/o/r/actions/runs/3/jobs":
            return httpx.Response(200, json={"jobs": [{"id": 77, "name": "build", "status": "completed", "conclusion": "success"}]})
        if path == "/repos/o/r/commits":
            if params.get("path") == "nothing.csv":
                return httpx.Response(200, json=[])
            return httpx.Response(200, json=[{"sha": "60ef441abcdef0123", "html_url": "https://github.com/o/r/commit/60ef441abcdef0123",
                                              "commit": {"message": "OnBuy commission tables from the API\n\nrun 34346220435",
                                                         "committer": {"date": "2026-09-09T11:40:00Z"}}}])
        if path == "/repos/o/r/contents/cleanup":
            return httpx.Response(200, json=[{"name": "image_ticket_skus_2026-10-03.txt", "path": "cleanup/image_ticket_skus_2026-10-03.txt", "type": "file"},
                                             {"name": "sub", "path": "cleanup/sub", "type": "dir"}])
        if path == "/repos/o/r/contents/nowhere":
            return httpx.Response(404, json={"message": "Not Found"})
        if path == "/repos/o/r/contents/a_file.txt":
            return httpx.Response(200, json={"name": "a_file.txt", "content": base64.b64encode(b"x").decode(), "sha": "abc"})
        if path == "/repos/o/r/actions/runs/40/artifacts":
            return httpx.Response(200, json={"artifacts": [{"id": 900, "name": "image-links", "size_in_bytes": 1234, "expired": False},
                                                           {"id": 901, "name": "old", "size_in_bytes": 5, "expired": True}]})
        if path == "/repos/o/r/actions/artifacts/900/zip":
            assert request.headers.get("authorization") == "Bearer token"
            return httpx.Response(302, headers={"location": "https://blob.test/signed/900?sig=abc"})
        if path == "/repos/o/r/actions/artifacts/902/zip":
            return httpx.Response(200, content=b"PK-direct")
        if path == "/repos/o/r/actions/artifacts/903/zip":
            return httpx.Response(302, headers={"location": "https://blob.test/signed/gone"})
        if request.url.host == "blob.test" and path == "/signed/900":
            assert "authorization" not in request.headers                     # the signed address never gets the token
            return httpx.Response(200, content=b"PK-zip-bytes")
        if request.url.host == "blob.test" and path == "/signed/gone":
            return httpx.Response(404, text="expired")
        if path == "/rate":
            return httpx.Response(403, headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1800000000"}, json={"message": "rate"})
        return httpx.Response(404, json={"message": f"no canned answer for {method} {path}"})


@pytest.fixture
def canned():
    return Canned()


@pytest.fixture
def client(canned):
    return GitHubClient("token", api="https://api.github.test", transport=httpx.MockTransport(canned), sleep=lambda s: None)


def test_list_runs_normalises_and_filters_since(client):
    runs = client.list_runs("o/r")
    assert [r["id"] for r in runs] == [3, 2, 1]
    assert runs[0]["path"] == "run.yml" and runs[0]["url"].endswith("/3")
    assert [r["id"] for r in client.list_runs("o/r", since="2026-10-23T00:00:00Z")] == [3, 2]


def test_queue_splits_running_and_waiting(client):
    q = client.queue("o/r")
    assert [r["path"] for r in q["in_progress"]] == ["run_amazon.yml"]
    assert [r["path"] for r in q["pending"]] == ["watch_recovery.yml"]


def test_dispatch_then_find_the_new_run(client, canned):
    started = datetime(2026, 10, 23, 7, 0, 0, tzinfo=timezone.utc)
    assert client.find_dispatched_run("o/r", "orders_lookup.yml", started, attempts=1) is None     # only yesterday's run listed
    client.dispatch("o/r", "orders_lookup.yml", {"sku": "NONE", "list_all": "yes", "days": 14}, ref="main")
    sent = json.loads([r for r in canned.requests if r.method == "POST"][-1].content)
    assert sent == {"ref": "main", "inputs": {"sku": "NONE", "list_all": "yes", "days": "14"}}
    run = client.find_dispatched_run("o/r", "orders_lookup.yml", started, attempts=1)
    assert run and run["id"] == 50 and run["event"] == "workflow_dispatch"


def test_set_variable_patches_or_creates(client, canned):
    client.set_variable("o/r", "FEE_MODE", "flat")
    assert canned.variables["FEE_MODE"] == "flat"
    client.set_variable("o/r", "NEW_KNOB", "1")
    assert canned.variables["NEW_KNOB"] == "1"
    names = [v["name"] for v in client.list_variables("o/r")]
    assert names == ["FEE_MODE", "NEW_KNOB"]


def test_workflow_definition_reads_inputs_schedule_and_group(client):
    d = client.workflow_definition("o/r", "purge_dead_rows.yml")
    assert d["name"].startswith("Purge Dead") and d["manual"] and d["schedule"] == ["7 * * * *"] and d["group"] == "onbuy-api"
    assert d["inputs"]["dry_run"]["default"] == "yes" and d["inputs"]["max_rows"]["required"] is True
    assert d["scripts"] == ["purge_dead_rows.py"]


def test_run_log_strips_timestamps(client):
    assert client.run_log("o/r", 3).strip() == "INFO FIX done: 10 corrected, 0 failed"


def test_last_commit_of_a_path(client, canned):
    c = client.last_commit("o/r", "onbuy_commission_tiers.csv")
    assert c == {"sha": "60ef441", "date": "2026-09-09T11:40:00Z", "message": "OnBuy commission tables from the API",
                 "url": "https://github.com/o/r/commit/60ef441abcdef0123"}
    sent = [r for r in canned.requests if r.url.path == "/repos/o/r/commits"][-1]
    assert dict(sent.url.params) == {"path": "onbuy_commission_tiers.csv", "sha": "main", "per_page": "1"}
    assert client.last_commit("o/r", "nothing.csv") is None


def test_rate_limit_is_a_clear_error(client):
    with pytest.raises(GitHubError) as exc:
        client._json("GET", "/rate")
    assert "rate limit" in str(exc.value)


def test_parse_workflow_handles_yaml_on_key_and_bad_yaml():
    d = parse_workflow("name: X\non:\n  workflow_dispatch: {}\n", "x.yml")
    assert d["manual"] and d["inputs"] == {} and d["schedule"] == []
    bad = parse_workflow("name: [unclosed", "bad.yml")
    assert bad["error"].startswith("yaml")


def test_list_dir_names_the_entries_and_treats_a_missing_directory_as_empty(client):
    assert client.list_dir("o/r", "cleanup") == [{"name": "image_ticket_skus_2026-10-03.txt", "path": "cleanup/image_ticket_skus_2026-10-03.txt", "type": "file"},
                                                  {"name": "sub", "path": "cleanup/sub", "type": "dir"}]
    assert client.list_dir("o/r", "/cleanup/") == client.list_dir("o/r", "cleanup")
    assert client.list_dir("o/r", "nowhere") == [] and client.list_dir("o/r", "a_file.txt") == []                 # a file is not a directory


def test_run_artifacts_lists_what_a_run_uploaded(client):
    assert client.run_artifacts("o/r", 40) == [{"id": 900, "name": "image-links", "size": 1234, "expired": False}, {"id": 901, "name": "old", "size": 5, "expired": True}]


def test_an_artifact_is_fetched_from_its_signed_address_without_the_token(client, canned):
    assert client.download_artifact("o/r", 900) == b"PK-zip-bytes"
    assert any(r.url.host == "blob.test" for r in canned.requests)
    assert client.download_artifact("o/r", 902) == b"PK-direct"                                                      # a host that answers with the file itself
    with pytest.raises(GitHubError) as gone:
        client.download_artifact("o/r", 903)
    assert "404" in str(gone.value)
    with pytest.raises(GitHubError) as big:
        client.download_artifact("o/r", 900, max_bytes=3)
    assert "larger than" in str(big.value) or "MB" in str(big.value)


# ---- conditional requests (2026-10-29): unchanged GitHub answers come back as free 304s -------------------------------------------------
def test_an_unchanged_listing_is_reused_through_its_etag():
    calls = []

    def answer(request):
        calls.append(dict(request.headers))
        if request.headers.get("if-none-match") == 'W/"v1"':
            return httpx.Response(304)
        return httpx.Response(200, json={"workflow_runs": [run_json(5, "run.yml")]}, headers={"ETag": 'W/"v1"'})

    client = GitHubClient("t", transport=httpx.MockTransport(answer))
    first = client.list_runs("o/r", limit=5)
    again = client.list_runs("o/r", limit=5)
    assert [r["id"] for r in first] == [5] and again == first
    assert "if-none-match" not in calls[0] and calls[1]["if-none-match"] == 'W/"v1"'
    assert client.answers_fetched == 1 and client.answers_reused == 1


def test_a_changed_answer_replaces_the_remembered_one():
    state = {"etag": 'W/"v1"', "runs": [run_json(5, "run.yml")]}

    def answer(request):
        if request.headers.get("if-none-match") == state["etag"]:
            return httpx.Response(304)
        return httpx.Response(200, json={"workflow_runs": state["runs"]}, headers={"ETag": state["etag"]})

    client = GitHubClient("t", transport=httpx.MockTransport(answer))
    assert [r["id"] for r in client.list_runs("o/r", limit=5)] == [5]
    state.update(etag='W/"v2"', runs=[run_json(6, "run.yml"), run_json(5, "run.yml")])          # a new run arrived
    assert [r["id"] for r in client.list_runs("o/r", limit=5)] == [6, 5]                        # the stale etag misses and the fresh list is used
    assert [r["id"] for r in client.list_runs("o/r", limit=5)] == [6, 5] and client.answers_reused == 1


def test_different_params_keep_their_own_etags_and_posts_send_none():
    seen = []

    def answer(request):
        seen.append((request.method, str(request.url), request.headers.get("if-none-match", "")))
        if request.method == "POST":
            return httpx.Response(204)
        return httpx.Response(200, json={"workflow_runs": []}, headers={"ETag": 'W/"' + str(request.url) + '"'})

    client = GitHubClient("t", transport=httpx.MockTransport(answer))
    client.list_runs("o/r", limit=5)
    client.list_runs("o/r", limit=5, workflow="run.yml")
    client.dispatch("o/r", "run.yml")
    gets = [s for s in seen if s[0] == "GET"]
    assert gets[0][2] == "" and gets[1][2] == ""                                               # two different listings = two different keys
    assert all(s[2] == "" for s in seen if s[0] == "POST")                                     # a dispatch never carries If-None-Match
