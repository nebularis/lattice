# SPDX-License-Identifier: MPL-2.0
"""A browser tab's events, for a test (SVA-R5). It starts `tab_events.mjs`, which connects over the broker's Web MQTT as the studio's app does, and records what the tab receives.

The events key never reaches Python. The helper reads it from the service's session description and keeps it. The helper ends when
this process closes its standard input, so a test that dies leaves none behind."""

from __future__ import annotations

import json
import secrets
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .topology import HarnessError

HELPER = Path(__file__).with_name("tab_events.mjs")
FRAME_TYPE = "org.nebularis.lattice.studio.run.frame"
ALPHABET = "abcdefghijklmnopqrstuvwxyz0123456789"


def new_tab_id() -> str:
    """A tab identifier of the form the contract gives, 1 to 32 of `a-z0-9`."""
    return "".join(secrets.choice(ALPHABET) for _ in range(12))


class Tab:
    """One tab's subscriber. `events` holds each CloudEvent it received, in arrival order, each as `{"at": seconds since this subscriber started, "cloudEvent": {...}}`."""

    def __init__(self, base_url: str, principal: str = "developer", tab: Optional[str] = None) -> None:
        self.base_url, self.principal, self.tab = base_url, principal, tab or new_tab_id()
        self.events: List[Dict[str, Any]] = []
        self.errors: List[str] = []
        self.closed = False
        self._subscribed = threading.Event()
        self._lock = threading.Lock()
        self._process: Optional[subprocess.Popen] = None
        self._started = 0.0

    def start(self, timeout: float = 30.0) -> "Tab":
        node = shutil.which("node")
        if node is None:
            raise HarnessError("a tab's subscriber needs node. Run this through mise, which installs it")
        self.events, self.errors, self.closed = [], [], False
        self._subscribed.clear()
        self._started = time.monotonic()
        self._process = subprocess.Popen([node, str(HELPER), "--base", self.base_url, "--principal", self.principal, "--tab", self.tab],
                                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        threading.Thread(target=self._read, args=(self._process,), daemon=True).start()
        if not self._subscribed.wait(timeout):
            self.stop()
            raise HarnessError(f"the tab {self.tab} did not subscribe within {timeout:.0f} s. Errors: {self.errors}")
        return self

    def _read(self, process: subprocess.Popen) -> None:
        assert process.stdout is not None
        for line in process.stdout:
            try:
                item = json.loads(line)
            except ValueError:
                continue
            with self._lock:
                if item.get("event") == "subscribed":
                    self._subscribed.set()
                elif item.get("event") == "message":
                    self.events.append({"at": item["at"] / 1000.0, "cloudEvent": item["cloudEvent"]})
                elif item.get("event") == "error":
                    self.errors.append(str(item.get("message")))
                elif item.get("event") == "closed":
                    self.closed = True

    def stop(self) -> None:
        """Disconnects, as a tab that closes does, and waits for the helper."""
        process, self._process = self._process, None
        if process is None:
            return
        try:
            process.stdin.close()  # type: ignore[union-attr]
        except OSError:
            pass
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    def __enter__(self) -> "Tab":
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    # --- what it received ------------------------------------------------------------------------

    def frames(self, run: Optional[str] = None) -> List[Dict[str, Any]]:
        """The frame objects of the run frames the tab received, in arrival order, those of `run` only when it is given."""
        with self._lock:
            events = list(self.events)
        out = []
        for e in events:
            ce = e["cloudEvent"]
            if ce.get("type") == FRAME_TYPE and (run is None or ce.get("subject") == run):
                out.append(ce["data"])
        return out

    def wait_for(self, done: Callable[[], bool], timeout: float, interval: float = 0.05) -> bool:
        """True once `done()` is, False when `timeout` seconds pass first."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if done():
                return True
            time.sleep(interval)
        return done()

    def wait_last(self, run: str, timeout: float) -> List[Dict[str, Any]]:
        """The run's frames once one has `last` true, or whatever arrived when `timeout` seconds pass."""
        self.wait_for(lambda: any(f.get("last") for f in self.frames(run)), timeout)
        return self.frames(run)


def settle(frames: List[Dict[str, Any]]) -> Dict[str, Any]:
    """What a client shows for the frames it holds, by the contract's rule (What a client must do): the first frame of each `seq` is kept, a failed last frame settles the
    run whatever is missing before it, a succeeded last frame with every `seq` from 0 is complete and with a gap is partial, and no last frame is not settled.
    Returns `{"state": "failed" | "complete" | "partial" | "open", "message": the failed frame's message or None, "missing": the `seq`s absent below the last}`."""
    first: Dict[int, Dict[str, Any]] = {}
    for frame in frames:
        first.setdefault(frame["seq"], frame)
    last = next((f for f in first.values() if f.get("last")), None)
    if last is None:
        return {"state": "open", "message": None, "missing": []}
    missing = [n for n in range(last["seq"]) if n not in first]
    if last.get("status") == "failed":
        return {"state": "failed", "message": last.get("message"), "missing": missing}
    return {"state": "partial" if missing else "complete", "message": None, "missing": missing}
