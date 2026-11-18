"""Finished run logs, kept on disk so a dashboard restart does not download them again.

The pages read facts out of the stores' run logs (the daily check, To do, Amazon, eBay, the tiles). The logs
themselves never change once a run is finished, but the in-process cache forgets them at every restart - and the
user restarts the dashboard for every update - so the first To do page of a session used to download tens of
megabytes again. This keeps each finished run's log as one gzip file under data/logs/<owner__repo>/<run id>.txt.gz:
written once, read forever, pruned oldest-first so a store never holds more than a few weeks of runs.

Only COMPLETED runs land here (a running run's log is still growing), exactly like the in-memory layer in front.
"""
import gzip
import os
import re
import threading
import time
from pathlib import Path

KEEP_FILES = 150                 # newest runs kept per repository - the pages look at the last 10-20
KEEP_BYTES = 120 * 1024 * 1024   # and never more than this per repository (Amazon sync logs are the big ones)
PRUNE_EVERY = 25                 # writes between prunes


class LogStore:
    def __init__(self, root):
        self.root = Path(root)
        self._lock = threading.Lock()
        self._writes = 0
        self.hits = self.misses = 0                    # since this process started; the Settings page shows them

    def _folder(self, repo):
        return self.root / re.sub(r"[^A-Za-z0-9_.-]", "__", str(repo))

    def _path(self, repo, run_id):
        return self._folder(repo) / f"{int(run_id)}.txt.gz"

    def get(self, repo, run_id):
        """The stored log text, or None. Counted as a hit or a miss for the Settings line."""
        try:
            with gzip.open(self._path(repo, run_id), "rt", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except (OSError, ValueError, EOFError):
            self.misses += 1
            return None
        self.hits += 1
        return text

    def put(self, repo, run_id, text):
        """Write one finished run's log (write to a side file, then move into place: a reader never sees half a file). Never raises - a full disk costs the cache, not the page."""
        path = self._path(repo, run_id)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            side = path.with_suffix(".tmp")
            with gzip.open(side, "wt", encoding="utf-8", compresslevel=6) as f:
                f.write(text)
            os.replace(side, path)
        except OSError:
            return
        with self._lock:
            self._writes += 1
            due = self._writes % PRUNE_EVERY == 1
        if due:
            self.prune(repo)

    def prune(self, repo):
        """Drop the oldest files of the repository beyond the count and size caps."""
        try:
            files = sorted(((p.stat().st_mtime, p.stat().st_size, p) for p in self._folder(repo).glob("*.txt.gz")), reverse=True)
        except OSError:
            return
        total = 0
        for n, (_, size, path) in enumerate(files):
            total += size
            if n >= KEEP_FILES or (n > 0 and total > KEEP_BYTES):      # the newest file always survives, however big one sync's log is
                try:
                    path.unlink()
                except OSError:
                    pass

    def stats(self):
        """{files, bytes} over every repository - the Settings page's one line."""
        files = total = 0
        try:
            folders = [d for d in self.root.iterdir() if d.is_dir()]
        except OSError:
            folders = []
        for folder in folders:
            for p in folder.glob("*.txt.gz"):
                try:
                    total += p.stat().st_size
                except OSError:
                    continue
                files += 1
        return {"files": files, "bytes": total, "hits": self.hits, "misses": self.misses}
