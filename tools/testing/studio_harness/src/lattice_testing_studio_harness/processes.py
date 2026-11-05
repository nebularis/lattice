# SPDX-License-Identifier: MPL-2.0
"""The `processes` runner. Fuseki, RabbitMQ, the writers, the service and the workers as local processes, started by the stack script's own functions, on free ports, in a folder of the run's own."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import _build
from ._tools import catalogue, stack as stack_module
from .client import Client
from .topology import HarnessError, Studio, Topology, free_ports, new_run_id, queue_consumers

READY_TIMEOUT = 240.0
# Files the developer's own stack downloaded, seeded into the cache so a first run does not download them again.
SEED = ("jena-fuseki-server-*.jar", "rabbitmq-server-*")


def certificate(into: Path) -> Tuple[Path, Path, Path]:
    """A server certificate, its key and the CA that signed it, in PEM, for the broker's TLS in a run, made by Erlang's `public_key`, which RabbitMQ already needs, so no platform needs openssl. The chain is signed with SHA-256, since TLS libraries refuse the default SHA-1."""
    into.mkdir(parents=True, exist_ok=True)
    cert, key, ca = into / "cert.pem", into / "key.pem", into / "ca.pem"
    program = (
        "K = [{key, {rsa, 2048, 65537}}, {digest, sha256}], "
        "#{server_config := C} = public_key:pkix_test_data(#{server_chain => #{root => K, peer => K}, client_chain => #{root => K, peer => K}}), "
        "{KT, KD} = proplists:get_value(key, C), "
        f"ok = file:write_file(\"{cert.as_posix()}\", public_key:pem_encode([{{'Certificate', proplists:get_value(cert, C), not_encrypted}}])), "
        f"ok = file:write_file(\"{ca.as_posix()}\", public_key:pem_encode([{{'Certificate', D, not_encrypted}} || D <- proplists:get_value(cacerts, C)])), "
        f"ok = file:write_file(\"{key.as_posix()}\", public_key:pem_encode([{{KT, KD, not_encrypted}}])), "
        "halt()."
    )
    erl = shutil.which("erl")
    if erl is None:
        raise HarnessError("making the broker's certificate needs Erlang. Run this through mise, which installs it")
    subprocess.run([erl, "-noshell", "-eval", program], check=True, capture_output=True, timeout=60)
    return cert, key, ca


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
        fuseki, amqp, dist, stream, service, web_mqtt, web_mqtts = free_ports(7)
        cache = _build.cache_dir(self.root)
        _seed(cache, self.root / ".build" / "config-studio" / "infra")
        jars = _build.jars(self.root)
        assets = _build.assets(self.root, self.run_dir / "assets")
        stack = stack_module.Stack(self.root)
        stack.run, stack.infra, stack.data, stack.cache = self.run_dir / "run", self.run_dir / "infra", self.run_dir / "data", cache
        stack.fuseki_port, stack.rabbitmq_port, stack.rabbitmq_dist_port, stack.stream_port = fuseki, amqp, dist, stream
        stack.rabbitmq_node = f"{self.run_id}@localhost"
        # The broker asks the service who a browser is, and serves the browser's events over TLS (PM-Q20 (d)).
        stack.service_port, stack.web_mqtt_port = service, web_mqtt
        stack.web_mqtt_tls = (web_mqtts, *certificate(self.run_dir / "tls"))
        stack.memory = t.store == "memory"
        self.stack = stack

        stack.fuseki()
        self._track("fuseki")
        stack.rabbitmq()
        self._track("rabbitmq")
        stack.wait_for("fuseki", fuseki, READY_TIMEOUT)
        stack.wait_for("rabbitmq", amqp, READY_TIMEOUT)
        stack.wait_for("rabbitmq", stream, READY_TIMEOUT)
        # The broker has the run's own user and no guest, as the stack's does (PM-Q20 (d)).
        stack.ensure_broker_user()
        password, secret = stack.broker_credentials()

        env = {
            "LATTICE_FUSEKI_URL": f"http://127.0.0.1:{fuseki}", "LATTICE_FUSEKI_DATASET": "studio",
            "LATTICE_AMQP_URI": stack.amqp_uri(password), "LATTICE_STUDIO_ASSETS": str(assets),
            "LATTICE_ROOT": str(self.root),
        }
        self.env = env
        self.fuseki_url = env["LATTICE_FUSEKI_URL"]
        writer_env = {**env, "LATTICE_FUSEKI_WRITE_DATASET": "studio-write", "LATTICE_STREAM_URI": stack.stream_uri(password)}
        service_env = {**env, "LATTICE_STUDIO_PORT": str(service), "LATTICE_STUDIO_BIND": "127.0.0.1", "LATTICE_STUDIO_AUTH": t.auth,
                       "LATTICE_STUDIO_EVENTS_URL": f"wss://127.0.0.1:{web_mqtts}/ws", "LATTICE_STUDIO_BROKER_SECRET": secret}
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

    # --- workers of a test's own --------------------------------------------------------------

    WORKER_CODE = "from lattice_workers.config_studio_main import main; main()"

    def start_worker(self, name: str, env: Optional[Dict[str, str]] = None, code: Optional[str] = None) -> None:
        """Starts a worker the topology did not, as the process `name`. `env` is added to the workers' environment, for example
        `LATTICE_AMQP_URI` with `?heartbeat=2` to shorten the broker's timeout, and `code` replaces the worker's entry point with a
        program of the test's own, which a test uses to patch the worker before it runs (a slow job). Stopped with the run."""
        self.stack.spawn(name, [sys.executable, "-c", code or self.WORKER_CODE], self._worker_env({**self.env, **(env or {})}))
        self._track(name)

    def stop_worker(self, name: str, kill: bool = False) -> None:
        """Stops a worker started with `start_worker`, through its shutdown, or with `kill` at once, as a crash would."""
        pid = self.pids.pop(name, None)
        if pid is None:
            return
        if kill:
            os.kill(pid, 9)
            self.stack._pid_file(name).unlink(missing_ok=True)
        else:
            self.stack.stop(name)

    def worker_running(self, name: str) -> bool:
        return self.stack.pid(name) is not None

    def log(self, name: str) -> str:
        """The log of a process of the run, such as `worker-1`, `service` or `writer-1`."""
        path = self.stack.run / f"{name}.log"
        return path.read_text(errors="replace") if path.exists() else ""

    def broker_log(self) -> str:
        """What the run's RabbitMQ node logged, which names a connection it closed for missed heartbeats."""
        folder = self.stack.infra / "rabbitmq" / "log"
        return "\n".join(p.read_text(errors="replace") for p in sorted(folder.glob("*.log"))) if folder.exists() else ""

    def amqp_uri(self, **parameters: str) -> str:
        """The broker's URI for a client of the run, with query `parameters` such as `heartbeat=2`."""
        base = self.env["LATTICE_AMQP_URI"]
        return base + ("?" + "&".join(f"{k}={v}" for k, v in parameters.items()) if parameters else "")

    def ctl(self, *args: str) -> str:
        """The output of `rabbitmqctl` against the run's node."""
        ctl = self.stack.rabbitmq_home() / "sbin" / ("rabbitmqctl.bat" if stack_module.WINDOWS else "rabbitmqctl")
        return subprocess.run(stack_module.command([str(ctl), "-n", self.stack.rabbitmq_node, *args]),
                              env={**os.environ, **self.stack.rabbitmq_env()}, capture_output=True, text=True).stdout

    def consumers(self, queue: str) -> int:
        return queue_consumers(self.ctl("list_queues", "name", "consumers", "--formatter", "csv", "--silent"), queue)

    def close_connections(self, named: str, reason: str = "closed by the test") -> int:
        """Closes the broker's connections whose client-provided name contains `named`, as a network fault or a broker restart would, and
        returns how many."""
        listed = self.ctl("list_connections", "pid", "client_properties", "--silent")
        pids = [line.split("\t", 1)[0] for line in listed.splitlines() if named in line and line.startswith("<")]
        for pid in pids:
            self.ctl("close_connection", pid, reason)
        return len(pids)

    def purge(self, queue: str) -> None:
        """Drops every message of `queue`, so one test's leftovers do not reach the next."""
        self.ctl("purge_queue", queue)

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
