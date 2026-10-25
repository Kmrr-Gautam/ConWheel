"""Sequential batch queue; each job runs convert() in a worker thread."""
from __future__ import annotations
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
from ..converters.base import Options
from .conversion_manager import Result, convert

@dataclass
class Job:
    src: Path
    target: str
    status: str = "queued"       # queued | running | done | failed | cancelled
    message: str = ""
    output: Optional[Path] = None
    progress: float = 0.0

class JobQueue:
    def __init__(self, dest_dir=None, options: Options | None = None, overwrite=False,
                 on_update: Callable[[Job], None] | None = None):
        self.jobs: list[Job] = []
        self.dest_dir, self.options, self.overwrite = dest_dir, options or Options(), overwrite
        self.on_update = on_update or (lambda j: None)
        self._cancel = threading.Event()
        self._pause = threading.Event(); self._pause.set()
        self._thread: threading.Thread | None = None

    def add(self, src, target): self.jobs.append(Job(Path(src), target))
    def remove(self, i):
        if self.jobs[i].status == "queued": del self.jobs[i]
    def move(self, i, j):
        self.jobs.insert(j, self.jobs.pop(i))
    def pause(self): self._pause.clear()
    def resume(self): self._pause.set()
    def cancel(self): self._cancel.set(); self._pause.set()

    def start(self):
        self._cancel.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self._thread

    def _run(self):
        for job in self.jobs:
            if job.status != "queued": continue
            self._pause.wait()
            if self._cancel.is_set():
                job.status = "cancelled"; self.on_update(job); continue
            job.status = "running"; self.on_update(job)
            def prog(f, job=job): job.progress = f; self.on_update(job)
            r: Result = convert(job.src, job.target, self.dest_dir, self.options,
                                overwrite=self.overwrite, cancel=self._cancel, progress=prog)
            job.output, job.message = r.output, r.message
            job.status = "done" if r.ok else ("cancelled" if r.cancelled else "failed")
            self.on_update(job)

    def summary(self):
        s = {"done": 0, "failed": 0, "cancelled": 0}
        for j in self.jobs:
            if j.status in s: s[j.status] += 1
        return s
