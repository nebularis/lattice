# SPDX-License-Identifier: MPL-2.0
"""A topology, declared in TOML, and the helpers every runner shares."""

from __future__ import annotations

import secrets
import socket
import tomllib
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from .client import Client

STORES = ("tdb2", "memory")
AUTHS = ("local",)
RUNNERS = ("processes", "compose")
KEYS = {"name", "writers", "workers", "store", "auth", "runner"}


class HarnessError(RuntimeError):
    """A topology that cannot start, or a studio that did not behave."""


@dataclass(frozen=True)
class Topology:
    name: str
    writers: int = 1
    workers: int = 1
    store: str = "tdb2"
    auth: str = "local"
    runner: str = "processes"

    def __post_init__(self) -> None:
        if not self.name or not all(c.isalnum() or c in "-_" for c in self.name):
            raise HarnessError(f"topology name {self.name!r} is letters, digits, hyphens and underscores")
        if self.writers < 1:
            raise HarnessError("a topology has at least one writer")
        if self.workers < 0:
            raise HarnessError("workers cannot be negative")
        for field, value, allowed in (("store", self.store, STORES), ("auth", self.auth, AUTHS), ("runner", self.runner, RUNNERS)):
            if value not in allowed:
                note = " (oidc is not supported by the harness yet)" if field == "auth" and value == "oidc" else ""
                raise HarnessError(f"{field} {value!r} is not one of {', '.join(allowed)}{note}")

    @classmethod
    def parse(cls, text: str) -> "Topology":
        data = tomllib.loads(text)
        unknown = set(data) - KEYS
        if unknown:
            raise HarnessError(f"unknown topology keys {sorted(unknown)}")
        if "name" not in data:
            raise HarnessError("a topology has a name")
        for key in ("writers", "workers"):
            if key in data and (type(data[key]) is not int):
                raise HarnessError(f"{key} is a whole number")
        return cls(**data)

    @classmethod
    def load(cls, path: Path | str) -> "Topology":
        return cls.parse(Path(path).read_text(encoding="utf-8"))

    def start(self, runner: Optional[str] = None, root: Optional[Path] = None) -> "Studio":
        """Starts the studio with `runner` (the topology's own by default) and returns it once it answers. Stop it with `stop()` or by using it in a `with`."""
        chosen = runner or self.runner
        if chosen == "processes":
            from .processes import ProcessStudio
            studio: Studio = ProcessStudio(self, root)
        elif chosen == "compose":
            from .compose import ComposeStudio
            studio = ComposeStudio(self, root)
        else:
            raise HarnessError(f"runner {chosen!r} is not one of {', '.join(RUNNERS)}")
        studio.start()
        return studio


class Studio:
    """A running studio. Subclasses start and stop what the runner runs."""

    topology: Topology
    run_id: str
    run_dir: Path
    url: str
    started: bool = False

    def start(self) -> None:  # pragma: no cover - runners implement it
        raise NotImplementedError

    def stop(self) -> None:  # pragma: no cover - runners implement it
        raise NotImplementedError

    def leftovers(self) -> List[str]:  # pragma: no cover - runners implement it
        """What this run started that still exists after `stop()`: process names, or container names."""
        raise NotImplementedError

    def client(self, principal: str = "developer") -> "Client":
        from .client import Client
        return Client(self.url, principal)

    def __enter__(self) -> "Studio":
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()


def new_run_id() -> str:
    """Lower-case letters and digits, valid as a compose project name and a RabbitMQ node name."""
    return "h" + secrets.token_hex(4)


def free_ports(count: int) -> List[int]:
    """`count` distinct free loopback ports. All are bound at once, then released, so none repeats. Another process could take one before it is used, which a start that fails on a port would show."""
    with ExitStack() as stack:
        sockets = []
        for _ in range(count):
            s = stack.enter_context(socket.socket())
            s.bind(("127.0.0.1", 0))
            sockets.append(s)
        return [s.getsockname()[1] for s in sockets]


def queue_consumers(csv_text: str, queue: str) -> int:
    """The consumer count of `queue` in the output of `rabbitmqctl list_queues name consumers --formatter csv --silent`."""
    for line in csv_text.splitlines():
        name, _, count = line.partition(",")
        count = count.strip().strip('"')
        if name.strip('"') == queue and count.isdigit():
            return int(count)
    return 0
