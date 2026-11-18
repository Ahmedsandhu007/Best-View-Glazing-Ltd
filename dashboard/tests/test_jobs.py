"""The background job registry: steps, progress, expected and unexpected failures, one job at a time per store."""
import threading

from app.jobs import JobFailed, Jobs


def test_a_job_reports_its_steps_progress_and_result():
    def work(job, number):
        job.set_step("Reading")
        job.progress(2, 5)
        job.set_detail("run 7 queued")
        job.set_step("Writing")
        return {"number": number}

    job = Jobs(inline=True).start("ticket", "gtv", work, 42)
    view = job.view()
    assert view["state"] == "done" and view["result"] == {"number": 42} and view["error"] == ""
    assert [s["text"] for s in view["steps"]] == ["Reading", "Writing"] and view["step"] == "Writing" and (view["done"], view["total"]) == (0, 0)      # a new step starts its own count
    assert view["kind"] == "ticket" and view["store"] == "gtv" and view["seconds"] >= 0


def test_progress_and_detail_belong_to_the_current_step():
    seen = {}

    def work(job):
        job.set_step("Opening links")
        job.progress(30, 100)
        job.set_detail("30 of 100")
        seen.update(job.view())

    Jobs(inline=True).start("ticket", "gtv", work)
    assert (seen["done"], seen["total"], seen["detail"], seen["state"]) == (30, 100, "30 of 100", "running") and seen["result"] is None


def test_an_expected_failure_keeps_its_message_and_an_unexpected_one_is_named():
    def refuses(job):
        raise JobFailed("The sheet run ended with 'failure'.")

    def breaks(job):
        raise KeyError("boom")

    failed = Jobs(inline=True).start("ticket", "gtv", refuses).view()
    assert failed["state"] == "failed" and failed["error"] == "The sheet run ended with 'failure'." and failed["result"] is None
    broken = Jobs(inline=True).start("ticket", "gtv", breaks).view()
    assert broken["state"] == "failed" and broken["error"].startswith("Unexpected error: KeyError")


def test_one_job_of_a_kind_runs_at_a_time_per_store_and_a_thread_job_finishes_by_itself():
    gate, finished = threading.Event(), threading.Event()

    def slow(job):
        job.set_step("Waiting")
        gate.wait(5)
        return "done"

    jobs = Jobs()
    first = jobs.start("ticket", "gtv", slow)
    assert jobs.running("ticket", "gtv") is first and jobs.running("ticket", "yra") is None and jobs.running("other", "gtv") is None
    assert jobs.get(first.id) is first and jobs.get("nope") is None and first.view()["state"] == "running"
    gate.set()
    jobs._threads[first.id].join(5)
    assert first.view()["state"] == "done" and first.view()["result"] == "done" and jobs.running("ticket", "gtv") is None


def test_old_finished_jobs_are_forgotten_but_a_running_one_never_is():
    jobs = Jobs(inline=True, keep=3)
    ids = [jobs.start("ticket", "gtv", lambda job: None).id for _ in range(6)]
    assert jobs.get(ids[-1]) is not None and jobs.get(ids[0]) is None and len(jobs._jobs) <= 4
