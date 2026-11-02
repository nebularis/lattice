# SPDX-License-Identifier: MPL-2.0
"""Starts and stops the Configuration Studio's stack in the background, on every platform (ADR-A136).

    python tools/config_studio_stack.py up [--docker] [--dev]
    python tools/config_studio_stack.py infra
    python tools/config_studio_stack.py down
    python tools/config_studio_stack.py status

`up` starts Fuseki and RabbitMQ, from releases it downloads once and checks against the SHA-256
pinned here, or with `--docker` from the compose file. It then builds and starts the store writer, the service, the
worker, the transforms worker and the Word add-in's development server, and with `--dev` the browser code with hot reload. With `--docker`
the compose file also serves the built add-in over HTTPS on 3443, which Word needs. Each process writes its log and its
process id under `.build/config-studio/run`, which `down` reads. Workspaces are kept on disk, in a
TDB2 database under the user's data folder (`data_dir`), so they outlive the stack and the checkout. Run it through mise, as
`mise run studio:up`, so Java, Maven, Node, Python and Erlang are on the path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lattice_repo_catalogue  # noqa: E402

WINDOWS = os.name == "nt"

FUSEKI_VERSION = "6.2.0"
FUSEKI_URL = f"https://repo1.maven.org/maven2/org/apache/jena/jena-fuseki-server/{FUSEKI_VERSION}/jena-fuseki-server-{FUSEKI_VERSION}.jar"
FUSEKI_SHA256 = "2c92c598e65ab69d99820052e05f4277ed1d77980a8845f87545ad35b71a76ee"

RABBITMQ_VERSION = "4.4.0"
RABBITMQ_NODE = "studio@localhost"
RABBITMQ_RELEASE = f"https://github.com/rabbitmq/rabbitmq-server/releases/download/v{RABBITMQ_VERSION}"
# The archive for each platform and its SHA-256, as the GitHub release publishes it.
RABBITMQ_ARCHIVE = {
    True: (f"rabbitmq-server-windows-{RABBITMQ_VERSION}.zip", "c077a084890e57e1498e479913d4d5bda77e88647e153b433e97f72a31431542"),
    False: (f"rabbitmq-server-generic-unix-{RABBITMQ_VERSION}.tar.xz", "68c22d5dafa15c0911463aeca73c362d638cd6fb8e407ad39512959c6cc37f0f"),
}[WINDOWS]

# The same addresses as the studio:service and studio:worker tasks in mise.toml.
FUSEKI_PORT, RABBITMQ_PORT, SERVICE_PORT, WEB_PORT, ADDIN_PORT = 3130, 5673, 8090, 4175, 4176
STREAM_PORT = 5553
# The broker's MQTT over WebSockets, which carries the studio's events to the browser (PM-Q20 (d)).
WEB_MQTT_PORT = 15675
# Every process's settings but the broker's URIs, which carry the stack's password (`Stack.env`).
STUDIO_ENV = {
    "LATTICE_FUSEKI_URL": f"http://127.0.0.1:{FUSEKI_PORT}",
    "LATTICE_FUSEKI_DATASET": "studio",
    "LATTICE_STUDIO_STATIC": "apps/config-studio/dist",
}
# The broker's one user, for the studio's own processes, with a password made once for each stack. The broker has no `guest`,
# since Web MQTT checks no Origin and no CORS rule guards a WebSocket, so any page a browser opens could connect as a default user.
BROKER_USER = "studio"

# RabbitMQ's stream plugin, for the writes super stream (ADR-A136), on its own port, advertised as the loopback address
# so a client on this machine reaches the partitions' leader there.
# Web MQTT carries the studio's events to the browser, and the HTTP auth backend asks the service who a browser is and what
# topics it may use, after the broker's own users (PM-Q20 (d)). The plain MQTT listener is not opened.
RABBITMQ_PLUGINS = "[rabbitmq_stream,rabbitmq_web_mqtt,rabbitmq_auth_backend_http].\n"
# The broker's user, its checks of a browser at the service under the stack's secret, and Web MQTT, for both kinds of stack.
BROKER_CONF = """default_user = {user}
default_pass = {password}
auth_backends.1 = internal
auth_backends.2 = http
auth_http.http_method = post
auth_http.user_path = http://{host}:{service}/api/broker/{secret}/user
auth_http.vhost_path = http://{host}:{service}/api/broker/{secret}/vhost
auth_http.resource_path = http://{host}:{service}/api/broker/{secret}/resource
auth_http.topic_path = http://{host}:{service}/api/broker/{secret}/topic
mqtt.allow_anonymous = false
mqtt.listeners.tcp = none
web_mqtt.tcp.port = {web_mqtt}
"""
RABBITMQ_CONF = """stream.listeners.tcp.1 = 127.0.0.1:{port}
stream.advertised_host = 127.0.0.1
stream.advertised_port = {port}
web_mqtt.tcp.ip = 127.0.0.1
"""
# A broker in Docker on the host's network, as on Docker Engine, where a container cannot reach the host's loopback, so each
# listener binds loopback on the stack's own ports, as the published ports do under Docker Desktop.
COMPOSE_HOST_NETWORK_CONF = """listeners.tcp.default = 127.0.0.1:{amqp}
management.tcp.ip = 127.0.0.1
management.tcp.port = {management}
prometheus.tcp.ip = 127.0.0.1
stream.listeners.tcp.1 = 127.0.0.1:{stream}
stream.advertised_host = 127.0.0.1
stream.advertised_port = {stream}
web_mqtt.tcp.ip = 127.0.0.1
distribution.listener.interface = 127.0.0.1
distribution.listener.port_range.min = {dist}
distribution.listener.port_range.max = {dist}
"""
# Web MQTT over TLS as well, with a certificate the caller made, as a test harness does.
RABBITMQ_TLS_CONF = """web_mqtt.ssl.ip = 127.0.0.1
web_mqtt.ssl.port = {port}
web_mqtt.ssl.certfile = {cert}
web_mqtt.ssl.keyfile = {key}
web_mqtt.ssl.cacertfile = {ca}
"""

# One TDB2 database behind two services: `studio` reads only, for the service and the worker, and `studio-write`
# updates, for the store writer alone.
FUSEKI_CONFIG = """PREFIX fuseki: <http://jena.apache.org/fuseki#>
PREFIX tdb2:   <http://jena.apache.org/2016/tdb#>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

<#read> rdf:type fuseki:Service ;
    fuseki:name "studio" ;
    fuseki:endpoint [ fuseki:operation fuseki:query ] , [ fuseki:operation fuseki:query ; fuseki:name "query" ] ,
        [ fuseki:operation fuseki:query ; fuseki:name "sparql" ] , [ fuseki:operation fuseki:gsp-r ; fuseki:name "data" ] ;
    fuseki:dataset <#store> .

<#write> rdf:type fuseki:Service ;
    fuseki:name "studio-write" ;
    fuseki:endpoint [ fuseki:operation fuseki:query ] , [ fuseki:operation fuseki:query ; fuseki:name "query" ] ,
        [ fuseki:operation fuseki:query ; fuseki:name "sparql" ] , [ fuseki:operation fuseki:update ] ,
        [ fuseki:operation fuseki:update ; fuseki:name "update" ] , [ fuseki:operation fuseki:gsp-rw ; fuseki:name "data" ] ;
    fuseki:dataset <#store> .

<#store> rdf:type tdb2:DatasetTDB2 ;
    tdb2:location "{location}" .
"""
# The same two services over a dataset held in memory, which a test harness uses.
FUSEKI_MEMORY_STORE = """<#store> rdf:type <http://jena.hpl.hp.com/2005/11/Assembler#MemoryDataset> .
"""

# Stopped in reverse, so the worker and service go before the store and the broker.
ORDER = ("fuseki", "rabbitmq", "writer", "service", "worker", "transforms", "addin", "web")


class Stack:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.home = root / ".build" / "config-studio"
        self.run = self.home / "run"
        self.infra = self.home / "infra"
        catalogue = lattice_repo_catalogue.load(root)
        self.compose = root / catalogue.area("deployment") / "compose" / "config-studio" / "docker-compose.yml"
        self.platform = root / catalogue.area("platform")
        self.data = data_dir(os.environ)
        # The test harness (tools/testing/studio_harness) points these at a run of its own, on its own ports.
        self.cache = self.infra
        self.fuseki_port, self.rabbitmq_port, self.stream_port, self.rabbitmq_node = FUSEKI_PORT, RABBITMQ_PORT, STREAM_PORT, RABBITMQ_NODE
        self.rabbitmq_dist_port = RABBITMQ_PORT + 20000
        self.service_port, self.web_mqtt_port = SERVICE_PORT, WEB_MQTT_PORT
        # Web MQTT's TLS listener as (port, certificate, key, CA), or None for none.
        self.web_mqtt_tls: Optional[Tuple[int, Path, Path, Path]] = None
        self.memory = False

    # --- processes -------------------------------------------------------------------------------

    def _pid_file(self, name: str) -> Path:
        return self.run / f"{name}.pid"

    def pid(self, name: str) -> Optional[int]:
        try:
            pid = int(self._pid_file(name).read_text().strip())
        except (OSError, ValueError):
            return None
        return pid if alive(pid) else None

    def spawn(self, name: str, argv: List[str], env: Optional[Dict[str, str]] = None) -> int:
        self.run.mkdir(parents=True, exist_ok=True)
        with open(self.run / f"{name}.log", "ab") as log:
            process = subprocess.Popen(
                command(argv), cwd=self.root, env={**os.environ, **(env or {})},
                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, **detached(),
            )
        self._pid_file(name).write_text(str(process.pid), encoding="utf-8", newline="\n")
        return process.pid

    def stop(self, name: str) -> bool:
        """Stops a process the way its tool supports: `rabbitmqctl shutdown` for RabbitMQ, which
        waits for the node to stop its applications and its metadata store, and a termination request for the
        rest, whose shutdown hooks close the HTTP server, the AMQP connection and the store."""
        pid = self.pid(name)
        if pid is None:
            self._pid_file(name).unlink(missing_ok=True)
            return False
        if name == "rabbitmq":
            ctl = self.rabbitmq_home() / "sbin" / ("rabbitmqctl.bat" if WINDOWS else "rabbitmqctl")
            subprocess.run(command([str(ctl), "-n", self.rabbitmq_node, "shutdown"]), env={**os.environ, **self.rabbitmq_env()}, check=False)
        stop_tree(pid)
        self._pid_file(name).unlink(missing_ok=True)
        return True

    def claim(self, name: str, port: int) -> bool:
        """True when the port is free to start `name` on, false when `name` already runs there, and
        an exit when another process holds it, since a service that cannot bind may stay alive."""
        if not listening(port):
            return True
        if self.pid(name) is not None:
            print(f"{name}: already running on {port}")
            return False
        raise SystemExit(f"{name}: port {port} is in use by another process. Stop it, then run `mise run studio:up` again")

    def wait_for(self, name: str, port: int, timeout: float = 180.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if listening(port):
                return
            if self.pid(name) is None:
                break
            time.sleep(0.5)
        log = self.run / f"{name}.log"
        tail = log.read_text(errors="replace").splitlines()[-20:] if log.exists() else []
        raise SystemExit(f"{name} did not listen on 127.0.0.1:{port}. Last lines of {log}:\n" + "\n".join(tail))

    # --- infrastructure --------------------------------------------------------------------------

    def fuseki(self) -> None:
        jar = download(FUSEKI_URL, FUSEKI_SHA256, self.cache)
        base = self.infra / "fuseki-base"
        base.mkdir(parents=True, exist_ok=True)
        config = base / "studio.ttl"
        if self.memory:
            text = FUSEKI_CONFIG.split("\n<#store>")[0] + "\n" + FUSEKI_MEMORY_STORE
        else:
            store = self.data / "tdb2"
            store.mkdir(parents=True, exist_ok=True)
            print(f"fuseki: workspaces kept in {store}")
            text = FUSEKI_CONFIG.replace("{location}", store.resolve().as_posix())
        config.write_text(text, encoding="utf-8", newline="\n")
        self.spawn("fuseki", ["java", "-jar", str(jar), "--localhost", "--port", str(self.fuseki_port), "--config", str(config)], {"FUSEKI_BASE": str(base)})

    def rabbitmq_home(self) -> Path:
        return self.cache / f"rabbitmq_server-{RABBITMQ_VERSION}"

    def rabbitmq_env(self) -> Dict[str, str]:
        data = self.infra / "rabbitmq"
        data.mkdir(parents=True, exist_ok=True)
        plugins = data / "enabled_plugins"
        plugins.write_text(RABBITMQ_PLUGINS, encoding="utf-8", newline="\n")
        conf = data / "rabbitmq.conf"
        text = RABBITMQ_CONF.format(port=self.stream_port) + self.broker_conf("127.0.0.1")
        if self.web_mqtt_tls is not None:
            port, cert, key, ca = self.web_mqtt_tls
            # The broker's configuration takes forward slashes on every platform.
            text += RABBITMQ_TLS_CONF.format(port=port, cert=cert.resolve().as_posix(), key=key.resolve().as_posix(), ca=ca.resolve().as_posix())
        conf.write_text(text, encoding="utf-8", newline="\n")
        env = {
            "RABBITMQ_ENABLED_PLUGINS_FILE": str(plugins),
            "RABBITMQ_CONFIG_FILE": str(conf),
            "RABBITMQ_MNESIA_BASE": str(data / "mnesia"), "RABBITMQ_LOG_BASE": str(data / "log"),
            "RABBITMQ_NODENAME": self.rabbitmq_node, "RABBITMQ_NODE_IP_ADDRESS": "127.0.0.1",
            "RABBITMQ_NODE_PORT": str(self.rabbitmq_port), "RABBITMQ_DIST_PORT": str(self.rabbitmq_dist_port),
        }
        erl = shutil.which("erl")
        if erl is None:
            raise SystemExit("RabbitMQ needs Erlang. Run this through mise, which installs it")
        env["ERLANG_HOME"] = str(Path(erl).resolve().parent.parent)
        return env

    # --- the broker's user and the service's secret ----------------------------------------------

    def broker_credentials(self) -> Tuple[str, str]:
        """The broker user's password and the secret the broker names in its checks at the service, each made once for the stack
        and kept in `infra/broker`, with the AMQP and stream URIs, which the studio:* tasks of mise.toml read as `*_FILE`."""
        folder = self.infra / "broker"
        folder.mkdir(parents=True, exist_ok=True)
        values = []
        for name in ("password", "secret"):
            path = folder / name
            if not path.exists():
                write_private(path, secrets.token_urlsafe(24))
            values.append(path.read_text(encoding="utf-8").strip())
        password, secret = values
        write_private(folder / "amqp-uri", self.amqp_uri(password))
        write_private(folder / "stream-uri", self.stream_uri(password))
        return password, secret

    def amqp_uri(self, password: str) -> str:
        return f"amqp://{BROKER_USER}:{password}@127.0.0.1:{self.rabbitmq_port}/%2F"

    def stream_uri(self, password: str) -> str:
        return f"rabbitmq-stream://{BROKER_USER}:{password}@127.0.0.1:{self.stream_port}/%2f"

    def broker_conf(self, host: str) -> str:
        """The broker's user and its checks at the service on `host`, as the broker reaches it."""
        password, secret = self.broker_credentials()
        return BROKER_CONF.format(user=BROKER_USER, password=password, host=host, service=self.service_port, secret=secret, web_mqtt=self.web_mqtt_port)

    def env(self) -> Dict[str, str]:
        """Every process's settings, with the broker's URI."""
        return {**STUDIO_ENV, "LATTICE_AMQP_URI": self.amqp_uri(self.broker_credentials()[0])}

    def writer_env(self) -> Dict[str, str]:
        """The writer alone gets the update service and the stream protocol."""
        return {**self.env(), "LATTICE_FUSEKI_WRITE_DATASET": "studio-write", "LATTICE_STREAM_URI": self.stream_uri(self.broker_credentials()[0])}

    def service_env(self) -> Dict[str, str]:
        """The service also offers events over the broker's Web MQTT, and answers the broker's checks under the stack's secret."""
        return {**self.env(), "LATTICE_STUDIO_EVENTS_URL": f"ws://127.0.0.1:{self.web_mqtt_port}/ws",
                "LATTICE_STUDIO_BROKER_SECRET": self.broker_credentials()[1]}

    def ctl(self, *args: str) -> subprocess.CompletedProcess:
        ctl = self.rabbitmq_home() / "sbin" / ("rabbitmqctl.bat" if WINDOWS else "rabbitmqctl")
        return subprocess.run(command([str(ctl), "-n", self.rabbitmq_node, *args]), env={**os.environ, **self.rabbitmq_env()},
                              capture_output=True, text=True, check=True)

    def broker_users(self) -> List[str]:
        return [u["user"] for u in json.loads(self.ctl("list_users", "--silent", "--formatter", "json").stdout or "[]")]

    def ensure_broker_user(self) -> None:
        """Gives a broker this script started the stack's user and removes `guest`. A new broker has the user from its
        configuration and never had `guest`. One whose data an older stack made has `guest` until this runs."""
        users = self.broker_users()
        if BROKER_USER not in users:
            self.ctl("add_user", BROKER_USER, self.broker_credentials()[0])
            self.ctl("set_permissions", "-p", "/", BROKER_USER, ".*", ".*", ".*")
        if "guest" in users:
            self.ctl("delete_user", "guest")

    # --- the compose stack -----------------------------------------------------------------------

    def compose_files(self) -> List[Path]:
        """The compose file and the override for the kind of Docker: Docker Desktop on every platform forwards
        `host.docker.internal` to the host's loopback, where the service listens, and Docker Engine does not, so there the
        broker shares the host's network."""
        override = "docker-compose.host-network.yml" if docker_engine_on_linux() else "docker-compose.desktop.yml"
        return [self.compose, self.compose.parent / override]

    def compose_up(self) -> List[Path]:
        """Writes the broker's configuration under `infra/compose`, which the compose file mounts, and starts the compose stack."""
        files = self.compose_files()
        host_network = files[1].name == "docker-compose.host-network.yml"
        text = self.broker_conf("127.0.0.1" if host_network else "host.docker.internal")
        if host_network:
            text += COMPOSE_HOST_NETWORK_CONF.format(amqp=self.rabbitmq_port, management=self.rabbitmq_port + 10000,
                                                     stream=self.stream_port, dist=self.rabbitmq_dist_port)
        folder = self.infra / "compose"
        folder.mkdir(parents=True, exist_ok=True)
        write_private(folder / "rabbitmq-studio.conf", text)
        run(["docker", "compose", *[a for f in files for a in ("-f", str(f))], "up", "-d", "--build", "--wait"], self.root)
        return files

    def infra_only(self) -> None:
        """Fuseki and RabbitMQ in Docker alone, for the studio:* tasks of mise.toml, which run the rest on the host."""
        files = self.compose_up()
        self.run.mkdir(parents=True, exist_ok=True)
        (self.run / "docker").write_text("\n".join(str(f) for f in files), encoding="utf-8", newline="\n")

    def rabbitmq(self) -> None:
        archive = download(f"{RABBITMQ_RELEASE}/{RABBITMQ_ARCHIVE[0]}", RABBITMQ_ARCHIVE[1], self.cache)
        home = self.rabbitmq_home()
        if not home.exists():
            extract(archive, self.cache)
        self.spawn("rabbitmq", [str(home / "sbin" / ("rabbitmq-server.bat" if WINDOWS else "rabbitmq-server"))], self.rabbitmq_env())

    # --- the stack -------------------------------------------------------------------------------

    def up(self, docker: bool, dev: bool) -> None:
        if docker:
            # The proxy serves the add-in's built files, so they are built before it starts.
            run(["yarn", "workspace", "@lattice/word-authoring-addin", "run", "build"], self.root)
            files = self.compose_up()
            self.run.mkdir(parents=True, exist_ok=True)
            (self.run / "docker").write_text("\n".join(str(f) for f in files), encoding="utf-8", newline="\n")
        else:
            for name, start, port in (("fuseki", self.fuseki, FUSEKI_PORT), ("rabbitmq", self.rabbitmq, RABBITMQ_PORT)):
                if listening(port):
                    print(f"{name}: already listening on {port}")
                    if name == "rabbitmq" and "guest" in self.broker_users():
                        print("rabbitmq: an older stack started it, and it still has the user guest. Run studio:down, then studio:up")
                    continue
                start()
                self.wait_for(name, port)
                if name == "rabbitmq":
                    self.ensure_broker_user()
                print(f"{name}: up on 127.0.0.1:{port}")
        if not dev:
            run(["yarn", "workspace", "@lattice/config-studio", "run", "build"], self.root)
        run(["mvn", "-q", "-f", str(self.platform / "pom.xml"), "-pl", "config-studio-service,config-studio-writer,config-studio-transforms", "-am", "package", "-DskipTests"], self.root)
        built = lambda module: self.platform / module / "target" / f"{module}.jar"
        if self.pid("writer") is None:
            self.spawn("writer", ["java", "-jar", str(self.pinned("writer", built("config-studio-writer")))], self.writer_env())
        if self.claim("service", SERVICE_PORT):
            static = {} if dev else {"LATTICE_STUDIO_STATIC": str(self.pinned("web", self.root / STUDIO_ENV["LATTICE_STUDIO_STATIC"]))}
            self.spawn("service", ["java", "-jar", str(self.pinned("service", built("config-studio-service")))], {**self.service_env(), **static})
            self.wait_for("service", SERVICE_PORT)
        if self.pid("worker") is None:
            self.spawn("worker", [sys.executable, "-m", "lattice_workers.config_studio_main"], self.env())
        if self.pid("transforms") is None:
            self.spawn("transforms", ["java", "-jar", str(self.pinned("transforms", built("config-studio-transforms")))], self.env())
        if self.claim("addin", ADDIN_PORT):
            self.spawn("addin", ["yarn", "workspace", "@lattice/word-authoring-addin", "run", "dev"])
            self.wait_for("addin", ADDIN_PORT)
        url = f"http://127.0.0.1:{SERVICE_PORT}"
        if dev and self.claim("web", WEB_PORT):
            self.spawn("web", ["yarn", "workspace", "@lattice/config-studio", "run", "dev"])
            self.wait_for("web", WEB_PORT)
            url = f"http://127.0.0.1:{WEB_PORT}"
        addin = "https://localhost:3443/addin/taskpane.html for Word" if docker else f"http://127.0.0.1:{ADDIN_PORT}/addin/harness.html"
        print(f"Configuration Studio: {url}. Word add-in: {addin}. Logs in {self.run}. Stop it with `mise run studio:down`")

    def pinned(self, name: str, built: Path) -> Path:
        """A copy of a build output for one component to run from, made just before it starts. A JVM reads its jar for as
        long as it runs, so a build that rewrote the jar in `target`, as `mise run check` does, would break it (STD-308)."""
        copy = self.run / "pinned" / name / built.name
        if copy.is_dir():
            shutil.rmtree(copy)
        copy.parent.mkdir(parents=True, exist_ok=True)
        if built.is_dir():
            shutil.copytree(built, copy)
        else:
            shutil.copy2(built, copy)
        return copy

    def migrate(self, dry_run: bool) -> None:
        """Runs the one-off migration of a store written before phase D, with the writer's environment, against the running Fuseki.
        It backs the dataset up first, to the assets folder, and prints the path."""
        run(["mvn", "-q", "-f", str(self.platform / "pom.xml"), "-pl", "config-studio-writer", "-am", "package", "-DskipTests"], self.root)
        jar = self.platform / "config-studio-writer" / "target" / "config-studio-writer.jar"
        argv = ["java", "-cp", str(jar), "org.nebularis.lattice.studio.writer.MigrateMain", *(["--dry-run"] if dry_run else [])]
        subprocess.run(command(argv), cwd=self.root, env={**os.environ, **self.writer_env()}, check=True)

    def down(self) -> None:
        for name in reversed(ORDER):
            if self.stop(name):
                print(f"{name}: stopped")
        marker = self.run / "docker"
        if marker.exists():
            files = [line for line in marker.read_text().splitlines() if line.strip()]
            run(["docker", "compose", *[a for f in files for a in ("-f", f)], "down", "--timeout", "60"], self.root)
            marker.unlink()
            print("docker: Fuseki and RabbitMQ stopped")

    def status(self) -> None:
        ports = {"fuseki": FUSEKI_PORT, "rabbitmq": RABBITMQ_PORT, "service": SERVICE_PORT, "addin": ADDIN_PORT, "web": WEB_PORT}
        for name in ORDER:
            pid = self.pid(name)
            port = ports.get(name)
            serving = "" if port is None else (f", listening on {port}" if listening(port) else f", not listening on {port}")
            print(f"{name}: {'running as ' + str(pid) if pid else 'not started here'}{serving}")


# --- platform helpers ----------------------------------------------------------------------------

def data_dir(env: Dict[str, str], platform: str = sys.platform) -> Path:
    """Where the studio keeps its workspaces: `LATTICE_STUDIO_DATA` if set, otherwise the platform's
    own folder for an application's data, so the workspaces survive `mise run clean` and a new
    checkout."""
    if env.get("LATTICE_STUDIO_DATA"):
        return Path(env["LATTICE_STUDIO_DATA"])
    home = Path(env.get("HOME") or env.get("USERPROFILE") or Path.home())
    if platform == "win32":
        return Path(env.get("LOCALAPPDATA") or home / "AppData" / "Local") / "LATTICE" / "studio"
    if platform == "darwin":
        return home / "Library" / "Application Support" / "LATTICE" / "studio"
    return Path(env.get("XDG_DATA_HOME") or home / ".local" / "share") / "lattice" / "studio"


def write_private(path: Path, text: str) -> None:
    """Writes a secret readable by its owner alone, where the platform has such permissions."""
    path.write_text(text, encoding="utf-8", newline="\n")
    if not WINDOWS:
        path.chmod(0o600)


def docker_engine_on_linux() -> bool:
    """Whether Docker here is Docker Engine on Linux, whose containers cannot reach the host's loopback, rather than Docker Desktop,
    on any platform, which forwards `host.docker.internal` there."""
    if not sys.platform.startswith("linux"):
        return False
    out = subprocess.run(["docker", "info", "--format", "{{.OperatingSystem}}"], capture_output=True, text=True, check=False).stdout
    return "Docker Desktop" not in out


def command(argv: List[str]) -> List[str]:
    """Resolves the program on the path, and runs a Windows batch file through cmd, which
    CreateProcess cannot run directly."""
    program = shutil.which(argv[0]) or argv[0]
    if WINDOWS and program.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", program, *argv[1:]]
    return [program, *argv[1:]]


def detached() -> dict:
    """Starts a process in its own group, so it outlives this script and `down` can stop its children."""
    if WINDOWS:
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS}
    return {"start_new_session": True}


def alive(pid: int) -> bool:
    # ponytail: trusts the pid file, so a pid the OS has reused since is taken for ours. Record the
    # process start time with the pid if that ever bites.
    if WINDOWS:
        listing = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True).stdout
        return str(pid) in listing
    try:
        # Reaps the process if it is this script's own exited child, which would otherwise linger as a zombie.
        if os.waitpid(pid, os.WNOHANG)[0] == pid:
            return False
    except ChildProcessError:
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def stop_tree(pid: int, grace: float = 60.0) -> None:
    """Asks a process to stop and waits for it, forcing it only if it has not stopped within the
    grace period. On POSIX that is SIGTERM to its group, which runs a JVM's shutdown hooks and the
    worker's handler. Windows has no termination request a detached console process can receive,
    so there `taskkill /T /F` stops the tree at once: RabbitMQ has already been shut down by
    `rabbitmqctl` by then, the service holds no state outside the store, and a job the worker had
    not acknowledged is redelivered. TDB2 commits each update before Fuseki answers it, so a forced
    stop loses no committed write, and the next open recovers the journal."""
    if WINDOWS:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        return
    try:
        os.killpg(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        # The group has gone, or the pid is another user's after the process exited and its number was reused.
        return
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline and alive(pid):
        time.sleep(0.2)
    if alive(pid):
        print(f"process {pid} did not stop within {grace:.0f} s of SIGTERM, so it is killed")
        try:
            os.killpg(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def listening(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def run(argv: List[str], cwd: Path) -> None:
    subprocess.run(command(argv), cwd=cwd, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, expected: str, into: Path) -> Path:
    """Downloads a release once, and refuses it unless its SHA-256 is the one pinned."""
    target = into / url.rsplit("/", 1)[1]
    if target.exists() and sha256(target) == expected:
        return target
    into.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    print(f"downloading {url}")
    with urllib.request.urlopen(url, timeout=120) as response, open(partial, "wb") as out:
        shutil.copyfileobj(response, out)
    actual = sha256(partial)
    if actual != expected:
        partial.unlink()
        raise SystemExit(f"{url} has SHA-256 {actual}, not the pinned {expected}. Refused")
    partial.replace(target)
    return target


def extract(archive: Path, into: Path) -> None:
    if archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zipped:
            for member in zipped.namelist():
                if not (into / member).resolve().is_relative_to(into.resolve()):
                    raise SystemExit(f"{archive} holds a path outside its folder: {member}")
            zipped.extractall(into)
    else:
        with tarfile.open(archive) as tarred:
            tarred.extractall(into, filter="data")


def main(argv: Optional[List[str]] = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("action", choices=("up", "infra", "down", "status", "migrate"))
    parser.add_argument("--dry-run", action="store_true", help="with migrate: write nothing and print what it would do")
    parser.add_argument("--docker", action="store_true", help="run Fuseki and RabbitMQ with docker compose")
    parser.add_argument("--dev", action="store_true", help="also serve the browser code with hot reload on 4175")
    parser.add_argument("--root", default=None)
    args = parser.parse_args(argv)
    stack = Stack(lattice_repo_catalogue.find_root(args.root))
    if args.action == "up":
        stack.up(args.docker, args.dev)
    elif args.action == "infra":
        stack.infra_only()
    elif args.action == "migrate":
        stack.migrate(args.dry_run)
    elif args.action == "down":
        stack.down()
    else:
        stack.status()


if __name__ == "__main__":
    main()
