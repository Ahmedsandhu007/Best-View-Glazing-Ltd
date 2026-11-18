"""The run-log disk store (2026-10-28): a finished run's log is downloaded from GitHub once EVER, not once per restart - the user restarts the dashboard for every
update, and the first To do page of a session used to download tens of megabytes again. Running runs are never kept; the oldest files prune themselves."""
import gzip

from conftest import NOW, iso, make_run
from fastapi.testclient import TestClient

from app import logstore
from app.jobs import Jobs
from app.logstore import LogStore
from app.main import create_app


# ---- the store itself -------------------------------------------------------------------------------------------------------------------
def test_a_log_is_kept_and_read_back_and_a_miss_is_counted(tmp_path):
    store = LogStore(tmp_path / "logs")
    assert store.get("org/gtv", 11) is None and store.misses == 1
    store.put("org/gtv", 11, "INFO OnBuy: 1 created\nLISTING|x\n")
    assert store.get("org/gtv", 11) == "INFO OnBuy: 1 created\nLISTING|x\n" and store.hits == 1
    assert (tmp_path / "logs" / "org__gtv" / "11.txt.gz").exists()                   # the repository name cannot escape the folder
    assert store.stats()["files"] == 1 and store.stats()["bytes"] > 0


def test_a_broken_or_half_written_file_reads_as_a_miss(tmp_path):
    store = LogStore(tmp_path / "logs")
    path = tmp_path / "logs" / "org__gtv" / "7.txt.gz"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not gzip at all")
    assert store.get("org/gtv", 7) is None                                           # a corrupt file costs a download, never a crash


def test_the_oldest_files_prune_beyond_the_count_and_size_caps(tmp_path, monkeypatch):
    monkeypatch.setattr(logstore, "KEEP_FILES", 3)
    store = LogStore(tmp_path / "logs")
    for n in range(1, 6):
        store.put("org/gtv", n, f"log {n} " + "x" * 50)
        fp = tmp_path / "logs" / "org__gtv" / f"{n}.txt.gz"
        import os
        os.utime(fp, (1_000_000 + n, 1_000_000 + n))                                 # older runs have older files
    store.prune("org/gtv")
    left = sorted(int(p.name.split(".")[0]) for p in (tmp_path / "logs" / "org__gtv").glob("*.txt.gz"))
    assert left == [3, 4, 5]                                                          # the newest three stay
    monkeypatch.setattr(logstore, "KEEP_BYTES", 10)
    store.prune("org/gtv")
    left = sorted(int(p.name.split(".")[0]) for p in (tmp_path / "logs" / "org__gtv").glob("*.txt.gz"))
    assert left == [5]                                                                # the size cap keeps only the newest


def test_gzip_on_disk_is_much_smaller_than_the_log(tmp_path):
    store = LogStore(tmp_path / "logs")
    store.put("org/gtv", 9, "INFO the same sync line again and again\n" * 5000)
    size = (tmp_path / "logs" / "org__gtv" / "9.txt.gz").stat().st_size
    assert size < 20000                                                               # ~200 KB of log in a few KB


# ---- wired into the pages ---------------------------------------------------------------------------------------------------------------
NIGHTLY = "Nightly reconcile: 3 price(s) corrected\nSTORE SALE ACTIVE\n"


def web_app(settings, fake, db):
    return TestClient(create_app(settings=settings, client=fake, database=db, jobs=Jobs(inline=True), link_fetch=None, sleep=lambda s: None))


def count_downloads(fake):
    calls = {"n": 0}
    original = fake.run_log
    def counting(repo, run_id):
        calls["n"] += 1
        return original(repo, run_id)
    fake.run_log = counting
    return calls


def test_a_finished_runs_log_is_downloaded_once_ever_even_across_a_restart(settings, fake, db):
    run = make_run(61, "run.yml", "Generate OnBuy Feed", NOW)
    fake.runs["org/gtv"] = [run]
    fake.logs[61] = NIGHTLY
    calls = count_downloads(fake)
    web = web_app(settings, fake, db)
    first = web.get("/api/store/gtv/run/61").json()
    assert first["run"]["id"] == 61 and calls["n"] == 1
    web.get("/api/store/gtv/run/61")
    assert calls["n"] == 1                                                            # the in-process cache answers the second look
    again = web_app(settings, fake, db)                                               # the restart: a fresh app over the SAME data dir
    again.get("/api/store/gtv/run/61")
    assert calls["n"] == 1                                                            # the disk store answers - nothing downloaded again


def test_a_running_run_is_never_kept(settings, fake, db):
    run = make_run(62, "run.yml", "Generate OnBuy Feed", NOW, status="in_progress", conclusion="")
    fake.runs["org/gtv"] = [run]
    fake.logs[62] = "half a log"
    calls = count_downloads(fake)
    web = web_app(settings, fake, db)
    web.get("/api/store/gtv/run/62?facts=0")
    assert calls["n"] == 0 or not list((settings.data_dir / "logs").rglob("62.txt.gz"))   # nothing on disk for a run still going


def test_the_settings_page_says_how_many_logs_are_kept(settings, fake, db):
    run = make_run(63, "run.yml", "Generate OnBuy Feed", NOW)
    fake.runs["org/gtv"] = [run]
    fake.logs[63] = NIGHTLY
    web = web_app(settings, fake, db)
    web.get("/api/store/gtv/run/63")
    page = web.get("/settings").text
    assert "Run logs kept" in page and "1 run(s)" in page and "downloaded" in page
