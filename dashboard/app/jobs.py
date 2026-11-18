"""Small background jobs for the work a page cannot finish inside one request: start a workflow, wait for it, read what it uploaded, open thousands of links.

A job is a worker thread with a step text, a progress count and a result; the page starts it, then polls `view()` every few seconds. Jobs live in memory (a restart forgets a running one;
whatever a finished job wrote to disk stays). A step that goes wrong in a way the user should read raises JobFailed(message); anything else is reported as an unexpected error.
"""
import threading
import time
import uuid


class JobFailed(Exception):
    """An expected failure with a message for the person (a run that failed, a list that gave nothing to work on)."""


class Job:
    def __init__(self, kind, store_id):
        self.id = uuid.uuid4().hex[:12]
        self.kind, self.store_id = kind, store_id
        self.state = "running"                  # running | done | failed
        self.step, self.detail = "Starting", ""
        self.steps = []                         # every step started, with when
        self.done, self.total = 0, 0
        self.result, self.error = None, ""
        self.started, self.finished = time.time(), None

    def set_step(self, text):
        """A new step of the work: the page lists the steps done so far and shows the current one."""
        self.step, self.detail, self.done, self.total = text, "", 0, 0
        self.steps.append({"text": text, "at": round(time.time() - self.started, 1)})

    def set_detail(self, text):
        self.detail = text

    def progress(self, done, total):
        self.done, self.total = done, total

    def view(self):
        return {"id": self.id, "kind": self.kind, "store": self.store_id, "state": self.state, "step": self.step, "detail": self.detail,
                "steps": list(self.steps), "done": self.done, "total": self.total, "error": self.error,
                "seconds": round((self.finished or time.time()) - self.started, 1), "result": self.result if self.state == "done" else None}


class Jobs:
    """The registry. inline=True runs a job to its end inside start() - for tests."""

    def __init__(self, inline=False, keep=60):
        self.inline, self.keep = inline, keep
        self._jobs, self._threads, self._lock = {}, {}, threading.Lock()

    def start(self, kind, store_id, target, *args, **kwargs):
        job = Job(kind, store_id)
        with self._lock:
            self._jobs[job.id] = job
            for old in sorted(self._jobs.values(), key=lambda j: j.started)[:-self.keep]:
                if old.state != "running":
                    self._jobs.pop(old.id, None)

        def work():
            try:
                job.result = target(job, *args, **kwargs)
                job.state = "done"
            except JobFailed as exc:
                job.state, job.error = "failed", str(exc)
            except Exception as exc:  # noqa: BLE001 - a job must never take the server down
                job.state, job.error = "failed", f"Unexpected error: {type(exc).__name__}: {str(exc)[:300]}"
            finally:
                job.finished = time.time()

        if self.inline:
            work()
        else:
            thread = threading.Thread(target=work, name=f"job-{job.kind}-{job.id}", daemon=True)
            self._threads[job.id] = thread
            thread.start()
        return job

    def get(self, job_id):
        return self._jobs.get(job_id)

    def running(self, kind, store_id):
        """The job of this kind already running for the store, if any (one at a time: two ticket builds would race on the same list files and runs)."""
        return next((j for j in self._jobs.values() if j.kind == kind and j.store_id == store_id and j.state == "running"), None)
