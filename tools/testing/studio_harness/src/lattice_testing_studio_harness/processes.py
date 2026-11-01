# SPDX-License-Identifier: MPL-2.0
"""The `processes` runner. Fuseki, RabbitMQ, the writers, the service and the workers as local processes, started by the stack script's own functions, on free ports, in a folder of the run's own."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from . import _build
from ._tools import catalogue, stack as stack_module
from .client import Client
from .topology import HarnessError, Studio, Topology, free_ports, new_run_id, queue_consumers

READY_TIMEOUT = 240.0
# Files the developer's own stack downloaded, seeded into the cache so a first run does not download them again.
SEED = ("jena-fuseki-server-*.jar", "rabbitmq-server-*")


def _seed(cache: Path, from_dir: Path) -> None:
    import shutil
    cache.mkdir(parents=True, exist_ok=True)
    for pattern in SEED:
        for source in from_dir.glob(pattern):
            if source.is_file() and not (cache / source.name).exists():
                shutil.copyfile(source, cache / source.name)


class ProcessStudio(Studio):
    def __init__(self, topology: Topology, root: Optional[Path] = None) -> None:
        self.topology = topology
        self.root = catalogue.find_root(root)
        self.run_id = new_run_id()
        self.run_dir = _build.harness_dir(self.root) / self.run_id
        self.pids: Dict[str, int] = {}
        self.url = ""

    # --- start ---------------------------------------------------------------------------------

    def start(self) -> None:
        t = self.topology
        self.run_dir.mkdir(parents=True)
        self.started = True
        try:
            self._start()
        except BaseException as error:
            self.stop()
            if isinstance(error, SystemExit):
                raise HarnessError(f"{t.name} did not start: {error}") from None
            raise

    def _start(self) -> None:
        t = self.topology
        fuseki, amqp, dist, stream, service = free_ports(5)
        cache = _build.cache_dir(self.root)
        _seed(cache, self.root / ".build" / "config-studio" / "infra")
        jars = _build.jars(self.root)
        assets = _build.assets(self.root, self.run_dir / "assets")
        stack = stack_module.Stack(self.root)
        stack.run, stack.infra, stack.data, stack.cache = self.run_dir / "run", self.run_dir / "infra", self.run_dir / "data", cache
        stack.fuseki_port, stack.rabbitmq_port, stack.rabbitmq_dist_port, stack.stream_port = fuseki, amqp, dist, stream
        stack.rabbitmq_node = f"{self.run_id}@localhost"
        stack.memory = t.store == "memory"
        self.stack = stack

        stack.fuseki()
        self._track("fuseki")
        stack.rabbitmq()
        self._track("rabbitmq")
        stack.wait_for("fuseki", fuseki, READY_TIMEOUT)
        stack.wait_for("rabbitmq", amqp, READY_TIMEOUT)
        stack.wait_for("rabbitmq", stream, READY_TIMEOUT)

        env = {
            "LATTICE_FUSEKI_URL": f"http://127.0.0.1:{fuseki}", "LATTICE_FUSEKI_DATASET": "studio",
            "LATTICE_AMQP_URI": f"amqp://guest:guest@127.0.0.1:{amqp}/%2F", "LATTICE_STUDIO_ASSETS": str(assets),
            "LATTICE_ROOT": str(self.root),
        }
        writer_env = {**env, "LATTICE_FUSEKI_WRITE_DATASET": "studio-write", "LATTICE_STREAM_URI": f"rabbitmq-stream://guest:guest@127.0.0.1:{stream}/%2f"}
        service_env = {**env, "LATTICE_STUDIO_PORT": str(service), "LATTICE_STUDIO_BIND": "127.0.0.1", "LATTICE_STUDIO_AUTH": t.auth}
        static = _build.web(self.root, self.run_dir / "web")
        if static is not None:
            service_env["LATTICE_STUDIO_STATIC"] = str(static)
        for i in range(1, t.writers + 1):
            name = f"writer-{i}"
            stack.spawn(name, ["java", "-jar", str(jars["writer"])], writer_env)
            self._track(name)
        for i in range(1, t.writers + 1):
            self._wait_log(f"writer-{i}", "store writer running")
        stack.spawn("service", ["java", "-jar", str(jars["service"])], service_env)
        self._track("service")
        stack.wait_for("service", service, READY_TIMEOUT)
        for i in range(1, t.workers + 1):
            name = f"worker-{i}"
            stack.spawn(name, [sys.executable, "-m", "lattice_workers.config_studio_main"], self._worker_env(env))
            self._track(name)
        self.url = f"http://127.0.0.1:{service}"
        self._wait_health()
        self._wait_workers()

    def _worker_env(self, env: Dict[str, str]) -> Dict[str, str]:
        """The worker's environment. With `LATTICE_STUDIO_HARNESS_WORKER_ROOT` set, that checkout's worker and tool packages come first on `PYTHONPATH` and it is the worker's repository root."""
        other = _build.worker_root(self.root)
        if other is None:
            return env
        path = os.pathsep.join([*_build.python_paths(other), *filter(None, [os.environ.get("PYTHONPATH")])])
        return {**env, "PYTHONPATH": path, "LATTICE_ROOT": str(other)}

    def _track(self, name: str) -> None:
        pid = self.stack.pid(name)
        if pid is not None:
            self.pids[name] = pid

    def _wait_log(self, name: str, text: str) -> None:
        log = self.stack.run / f"{name}.log"
        deadline = time.monotonic() + READY_TIMEOUT
        while time.monotonic() < deadline:
            if log.exists() and text in log.read_text(errors="replace"):
                return
            if self.stack.pid(name) is None:
                break
            time.sleep(0.3)
        tail = "\n".join(log.read_text(errors="replace").splitlines()[-20:]) if log.exists() else ""
        raise HarnessError(f"{name} did not report '{text}'. Last lines of {log}:\n{tail}")

    def _wait_health(self) -> None:
        deadline = time.monotonic() + READY_TIMEOUT
        client = Client(self.url)
        while time.monotonic() < deadline:
            try:
                if client.health().status == 200:
                    return
            except OSError:
                pass
            time.sleep(0.3)
        raise HarnessError(f"the service did not answer {self.url}/api/health")

    def _wait_workers(self) -> None:
        """Waits until the jobs queue has a consumer for each worker, so the first job does not wait for a cold start."""
        want = self.topology.workers
        if not want:
            return
        deadline = time.monotonic() + READY_TIMEOUT
        while time.monotonic() < deadline:
            if self.consumers("lattice.studio.jobs") >= want:
                return
            for name in [n for n in self.pids if n.startswith("worker-")]:
                if self.stack.pid(name) is None:
                    log = self.stack.run / f"{name}.log"
                    raise HarnessError(f"{name} stopped. Last lines of {log}:\n" + "\n".join(log.read_text(errors="replace").splitlines()[-20:]))
            time.sleep(0.5)
        raise HarnessError(f"fewer than {want} workers consume lattice.studio.jobs")

    def consumers(self, queue: str) -> int:
        ctl = self.stack.rabbitmq_home() / "sbin" / ("rabbitmqctl.bat" if stack_module.WINDOWS else "rabbitmqctl")
        out = subprocess.run(stack_module.command([str(ctl), "-n", self.stack.rabbitmq_node, "list_queues", "name", "consumers", "--formatter", "csv", "--silent"]),
                             env={**os.environ, **self.stack.rabbitmq_env()}, capture_output=True, text=True).stdout
        return queue_consumers(out, queue)

    # --- stop ----------------------------------------------------------------------------------

    def stop(self) -> None:
        """Stops what this run started, in reverse order, each through its own shutdown, then removes the run's folder."""
        if not self.started:
            return
        self.started = False
        stack = getattr(self, "stack", None)
        if stack is not None:
            for name in reversed(list(self.pids)):
                stack.stop(name)
        _build.remove(self.run_dir)

    def leftovers(self) -> List[str]:
        """The names of the processes this run started that still run."""
        return [name for name, pid in self.pids.items() if stack_module.alive(pid)]
