# SPDX-License-Identifier: MPL-2.0
"""The `compose` runner. Each component in its own container on a network of the run's own, from a compose file generated for the topology and run under a project named by the run id."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import _build
from ._tools import catalogue, stack as stack_module
from .client import Client
from .topology import HarnessError, Studio, Topology, free_ports, new_run_id, queue_consumers

BUILD_TIMEOUT = 1800
WAIT_TIMEOUT = 300
SERVICE_PORT = 8090
PROXY_PORT = 8091
FUSEKI_DOCKERFILE = "fuseki.Dockerfile"
# What the worker image copies from the checkout, and leaves out of those copies.
WORKER_PARTS = ("workers", "tools", "ontology", "contracts", "packages/persistence/python", "packages/minting/python")
WORKER_FILES = ("pyproject.toml", "requirements-lock.txt", "repository-catalogue.md")
WORKER_IGNORE = shutil.ignore_patterns("__pycache__", "node_modules", "*.egg-info", ".venv", "build", "dist", ".pytest_cache", ".build")


@dataclass(frozen=True)
class Paths:
    """Where the generated file finds what it builds and mounts. All absolute."""
    deployment: Path
    run_dir: Path
    service_context: Path
    writer_context: Path
    worker_context: Path


def compose_config(topology: Topology, run_id: str, paths: Paths, published_port: int) -> Dict[str, Any]:
    """The compose file for `topology`, as a dictionary. It is written as JSON, which compose reads as YAML. Components reach each other by service name on the network `studio`, and only the service's port is published, on loopback."""
    def image(component: str) -> str:
        return f"lattice-studio-harness/{component}:{run_id}"

    healthy = {"condition": "service_healthy"}
    infra = {"fuseki": healthy, "rabbitmq": healthy}
    env = {
        "LATTICE_FUSEKI_URL": "http://fuseki:3030", "LATTICE_FUSEKI_DATASET": "studio",
        "LATTICE_AMQP_URI": "amqp://guest:guest@rabbitmq:5672/%2F",
    }
    java_env = {**env, "LATTICE_STUDIO_ASSETS": "/assets"}
    assets = f"{paths.run_dir / 'assets'}:/assets:ro"
    services: Dict[str, Any] = {
        "fuseki": {
            "build": {"context": str(paths.deployment), "dockerfile": FUSEKI_DOCKERFILE}, "image": image("fuseki"),
            "volumes": [f"{paths.run_dir / 'fuseki.ttl'}:/opt/fuseki/studio.ttl:ro"] + (["data:/data"] if topology.store == "tdb2" else []),
            "healthcheck": {"test": ["CMD-SHELL", "wget -qO- http://localhost:3030/$$/ping || exit 1"], "interval": "2s", "timeout": "3s", "retries": 60},
            "networks": ["studio"],
        },
        "rabbitmq": {
            "image": "rabbitmq:4.4-management-alpine",
            "environment": {"RABBITMQ_DEFAULT_USER": "guest", "RABBITMQ_DEFAULT_PASS": "guest", "RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS": "-rabbit loopback_users []"},
            "volumes": [f"{paths.deployment / 'enabled_plugins'}:/etc/rabbitmq/enabled_plugins:ro", f"{paths.run_dir / 'rabbitmq-stream.conf'}:/etc/rabbitmq/conf.d/20-stream.conf:ro"],
            "healthcheck": {"test": ["CMD", "rabbitmq-diagnostics", "-q", "ping"], "interval": "2s", "timeout": "5s", "retries": 60},
            "networks": ["studio"],
        },
        "service": {
            "build": {"context": str(paths.service_context), "dockerfile": str(paths.deployment / "java.Dockerfile")}, "image": image("service"),
            # The local authentication refuses an address but loopback, so the service listens on loopback inside its container and `proxy`, which shares that network namespace, is what the published port reaches.
            "environment": {**java_env, "LATTICE_STUDIO_PORT": str(SERVICE_PORT), "LATTICE_STUDIO_BIND": "127.0.0.1", "LATTICE_STUDIO_AUTH": topology.auth},
            "volumes": [assets], "depends_on": infra, "ports": [f"127.0.0.1:{published_port}:{PROXY_PORT}"],
            "healthcheck": {"test": ["CMD-SHELL", f"wget -qO- http://127.0.0.1:{SERVICE_PORT}/api/health || exit 1"], "interval": "2s", "timeout": "3s", "retries": 60},
            "networks": ["studio"],
        },
        "proxy": {
            "image": "caddy:2.10-alpine", "network_mode": "service:service", "depends_on": {"service": healthy},
            "command": ["caddy", "reverse-proxy", "--from", f":{PROXY_PORT}", "--to", f"127.0.0.1:{SERVICE_PORT}"],
            "healthcheck": {"test": ["CMD-SHELL", f"wget -qO- http://127.0.0.1:{PROXY_PORT}/api/health || exit 1"], "interval": "2s", "timeout": "3s", "retries": 30},
        },
    }
    for i in range(1, topology.writers + 1):
        services[f"writer{i}"] = {
            "build": {"context": str(paths.writer_context), "dockerfile": str(paths.deployment / "java.Dockerfile")}, "image": image("writer"),
            "environment": {**java_env, "LATTICE_FUSEKI_WRITE_DATASET": "studio-write", "LATTICE_STREAM_URI": "rabbitmq-stream://guest:guest@rabbitmq:5552/%2f"},
            "volumes": [assets], "depends_on": infra, "networks": ["studio"],
        }
    for i in range(1, topology.workers + 1):
        services[f"worker{i}"] = {
            "build": {"context": str(paths.worker_context), "dockerfile": str(paths.deployment / "worker.Dockerfile")}, "image": image("worker"),
            "environment": env, "depends_on": infra, "networks": ["studio"],
        }
    return {"name": run_id, "services": services, "networks": {"studio": {}}, "volumes": {"data": {}} if topology.store == "tdb2" else {}}


def fuseki_config(store: str) -> str:
    """The same two Fuseki services as the stack script's, over the volume `/data` or a dataset in memory."""
    if store == "memory":
        return stack_module.FUSEKI_CONFIG.split("\n<#store>")[0] + "\n" + stack_module.FUSEKI_MEMORY_STORE
    return stack_module.FUSEKI_CONFIG.replace("{location}", "/data")


# The stream protocol advertised as the broker's service name, which the writers reach on the network.
STREAM_CONF = "stream.listeners.tcp.1 = 5552\nstream.advertised_host = rabbitmq\nstream.advertised_port = 5552\n"


class ComposeStudio(Studio):
    def __init__(self, topology: Topology, root: Optional[Path] = None) -> None:
        self.topology = topology
        self.root = catalogue.find_root(root)
        self.run_id = new_run_id()
        self.run_dir = _build.harness_dir(self.root) / self.run_id
        self.url = ""
        self.file = self.run_dir / "compose.yaml"

    def docker(self, *args: str, check: bool = True, timeout: Optional[float] = None) -> subprocess.CompletedProcess:
        argv = ["docker", "compose", "-p", self.run_id, "-f", str(self.file), *args]
        if check:
            return _checked(argv, self.run_dir, timeout)
        return subprocess.run(argv, cwd=self.run_dir, capture_output=True, text=True)

    def start(self) -> None:
        self.run_dir.mkdir(parents=True)
        self.started = True
        try:
            self._start()
        except BaseException:
            self.stop()
            raise

    def _start(self) -> None:
        if shutil.which("docker") is None or subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
            raise HarnessError("the compose runner needs Docker, which is not running")
        jars = _build.jars(self.root)
        _build.assets(self.root, self.run_dir / "assets")
        contexts = {}
        for name in ("service", "writer"):
            contexts[name] = self.run_dir / "build" / name
            contexts[name].mkdir(parents=True)
            _link(jars[name], contexts[name] / "app.jar")
        contexts["worker"] = self._worker_context()
        deployment = self.root / catalogue.load(self.root).area("deployment") / "compose" / "config-studio"
        paths = Paths(deployment, self.run_dir, contexts["service"], contexts["writer"], contexts["worker"])
        (self.run_dir / "fuseki.ttl").write_text(fuseki_config(self.topology.store), encoding="utf-8", newline="\n")
        (self.run_dir / "rabbitmq-stream.conf").write_text(STREAM_CONF, encoding="utf-8", newline="\n")
        (published,) = free_ports(1)
        self.file.write_text(json.dumps(compose_config(self.topology, self.run_id, paths, published), indent=2), encoding="utf-8", newline="\n")
        self.url = f"http://127.0.0.1:{published}"
        try:
            self.docker("up", "-d", "--build", "--wait", "--wait-timeout", str(WAIT_TIMEOUT), timeout=BUILD_TIMEOUT)
        except HarnessError as error:
            logs = self.docker("logs", "--tail", "30", check=False).stdout
            raise HarnessError(f"{error}\n--- logs ---\n{logs}") from None
        self._wait_health()
        self._wait_workers()

    def _worker_context(self) -> Path:
        context = self.run_dir / "build" / "worker"
        for name in WORKER_FILES:
            (context / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.root / name, context / name)
        for part in WORKER_PARTS:
            shutil.copytree(self.root / part, context / part, ignore=WORKER_IGNORE)
        return context

    def _wait_health(self) -> None:
        client = Client(self.url)
        deadline = time.monotonic() + WAIT_TIMEOUT
        while time.monotonic() < deadline:
            try:
                if client.health().status == 200:
                    return
            except OSError:
                pass
            time.sleep(0.3)
        raise HarnessError(f"the service did not answer {self.url}/api/health")

    def _wait_workers(self) -> None:
        want = self.topology.workers
        deadline = time.monotonic() + WAIT_TIMEOUT
        while want and time.monotonic() < deadline:
            out = self.docker("exec", "-T", "rabbitmq", "rabbitmqctl", "list_queues", "name", "consumers", "--formatter", "csv", "--silent", check=False).stdout
            if queue_consumers(out, "lattice.studio.jobs") >= want:
                return
            time.sleep(0.5)
        if want:
            raise HarnessError(f"fewer than {want} workers consume lattice.studio.jobs")

    def stop(self) -> None:
        """Removes the containers, the network, the volume and the images this run built, then the run's folder."""
        if not self.started:
            return
        self.started = False
        if self.file.exists():
            self.docker("down", "-v", "--remove-orphans", "--timeout", "30", check=False)
            for component in ("fuseki", "service", "writer", "worker"):
                subprocess.run(["docker", "rmi", f"lattice-studio-harness/{component}:{self.run_id}"], capture_output=True)
        _build.remove(self.run_dir)

    def leftovers(self) -> List[str]:
        """The containers of this run's project that still exist, running or not."""
        out = subprocess.run(["docker", "ps", "-a", "--filter", f"label=com.docker.compose.project={self.run_id}", "--format", "{{.Names}}"], capture_output=True, text=True).stdout
        return out.split()


def _link(source: Path, target: Path) -> None:
    try:
        os.link(source, target)
    except OSError:
        shutil.copyfile(source, target)


def _checked(argv: List[str], cwd: Path, timeout: Optional[float]) -> subprocess.CompletedProcess:
    try:
        done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise HarnessError(f"{' '.join(argv[:6])} did not finish within {timeout:.0f} s") from None
    if done.returncode != 0:
        raise HarnessError(f"{' '.join(argv[:7])} failed ({done.returncode}):\n{(done.stdout + done.stderr)[-3000:]}")
    return done
