# SPDX-License-Identifier: MPL-2.0
"""Starts and stops the Configuration Studio's stack in the background, on every platform (ADR-A136).

    python tools/config_studio_stack.py up [--docker] [--dev]
    python tools/config_studio_stack.py down
    python tools/config_studio_stack.py status

`up` starts Fuseki and RabbitMQ, from releases it downloads once and checks against the SHA-256
pinned here, or with `--docker` from the compose file. It then builds and starts the service and
the worker, and with `--dev` the browser code with hot reload. Each process writes its log and its
process id under `.build/config-studio/run`, which `down` reads. Workspaces are kept on disk, in a
TDB2 database under the user's data folder (`data_dir`), so they outlive the stack and the checkout. Run it through mise, as
`mise run studio:up`, so Java, Maven, Node, Python and Erlang are on the path.
"""

from __future__ import annotations

import argparse
import hashlib
import os
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
from typing import Dict, List, Optional

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
FUSEKI_PORT, RABBITMQ_PORT, SERVICE_PORT, WEB_PORT = 3130, 5673, 8090, 4175
STUDIO_ENV = {
    "LATTICE_FUSEKI_URL": f"http://127.0.0.1:{FUSEKI_PORT}",
    "LATTICE_FUSEKI_DATASET": "studio",
    "LATTICE_AMQP_URI": f"amqp://guest:guest@127.0.0.1:{RABBITMQ_PORT}/%2F",
    "LATTICE_STUDIO_STATIC": "apps/config-studio/dist",
}

# RabbitMQ's plugins, so the writes exchange can be a consistent-hash exchange (ADR-A136, partitioned writers).
RABBITMQ_PLUGINS = "[rabbitmq_consistent_hash_exchange].\n"

# Stopped in reverse, so the worker and service go before the store and the broker.
ORDER = ("fuseki", "rabbitmq", "service", "worker", "web")


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
        self._pid_file(name).write_text(str(process.pid))
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
            subprocess.run(command([str(ctl), "-n", RABBITMQ_NODE, "shutdown"]), env={**os.environ, **self.rabbitmq_env()}, check=False)
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
        jar = download(FUSEKI_URL, FUSEKI_SHA256, self.infra)
        base = self.infra / "fuseki-base"
        base.mkdir(parents=True, exist_ok=True)
        store = self.data / "tdb2"
        store.mkdir(parents=True, exist_ok=True)
        print(f"fuseki: workspaces kept in {store}")
        self.spawn("fuseki", ["java", "-jar", str(jar), "--localhost", "--port", str(FUSEKI_PORT), "--tdb2", "--loc", str(store), "--update", "/studio"], {"FUSEKI_BASE": str(base)})

    def rabbitmq_home(self) -> Path:
        return self.infra / f"rabbitmq_server-{RABBITMQ_VERSION}"

    def rabbitmq_env(self) -> Dict[str, str]:
        data = self.infra / "rabbitmq"
        data.mkdir(parents=True, exist_ok=True)
        plugins = data / "enabled_plugins"
        plugins.write_text(RABBITMQ_PLUGINS)
        env = {
            "RABBITMQ_ENABLED_PLUGINS_FILE": str(plugins),
            "RABBITMQ_MNESIA_BASE": str(data / "mnesia"), "RABBITMQ_LOG_BASE": str(data / "log"),
            "RABBITMQ_NODENAME": RABBITMQ_NODE, "RABBITMQ_NODE_IP_ADDRESS": "127.0.0.1",
            "RABBITMQ_NODE_PORT": str(RABBITMQ_PORT), "RABBITMQ_DIST_PORT": str(RABBITMQ_PORT + 20000),
        }
        erl = shutil.which("erl")
        if erl is None:
            raise SystemExit("RabbitMQ needs Erlang. Run this through mise, which installs it")
        env["ERLANG_HOME"] = str(Path(erl).resolve().parent.parent)
        return env

    def rabbitmq(self) -> None:
        archive = download(f"{RABBITMQ_RELEASE}/{RABBITMQ_ARCHIVE[0]}", RABBITMQ_ARCHIVE[1], self.infra)
        home = self.rabbitmq_home()
        if not home.exists():
            extract(archive, self.infra)
        self.spawn("rabbitmq", [str(home / "sbin" / ("rabbitmq-server.bat" if WINDOWS else "rabbitmq-server"))], self.rabbitmq_env())

    # --- the stack -------------------------------------------------------------------------------

    def up(self, docker: bool, dev: bool) -> None:
        if docker:
            run(["docker", "compose", "-f", str(self.compose), "up", "-d", "--wait"], self.root)
            self.run.mkdir(parents=True, exist_ok=True)
            (self.run / "docker").write_text(str(self.compose))
        else:
            for name, start, port in (("fuseki", self.fuseki, FUSEKI_PORT), ("rabbitmq", self.rabbitmq, RABBITMQ_PORT)):
                if listening(port):
                    print(f"{name}: already listening on {port}")
                    continue
                start()
                self.wait_for(name, port)
                print(f"{name}: up on 127.0.0.1:{port}")
        if not dev:
            run(["yarn", "workspace", "@lattice/config-studio", "run", "build"], self.root)
        run(["mvn", "-q", "-f", str(self.platform / "pom.xml"), "-pl", "config-studio-service", "-am", "package", "-DskipTests"], self.root)
        jar = self.platform / "config-studio-service" / "target" / "config-studio-service.jar"
        if self.claim("service", SERVICE_PORT):
            self.spawn("service", ["java", "-jar", str(jar)], STUDIO_ENV)
            self.wait_for("service", SERVICE_PORT)
        if self.pid("worker") is None:
            self.spawn("worker", [sys.executable, "-m", "lattice_workers.config_studio_main"], STUDIO_ENV)
        url = f"http://127.0.0.1:{SERVICE_PORT}"
        if dev and self.claim("web", WEB_PORT):
            self.spawn("web", ["yarn", "workspace", "@lattice/config-studio", "run", "dev"])
            self.wait_for("web", WEB_PORT)
            url = f"http://127.0.0.1:{WEB_PORT}"
        print(f"Configuration Studio: {url}. Logs in {self.run}. Stop it with `mise run studio:down`")

    def down(self) -> None:
        for name in reversed(ORDER):
            if self.stop(name):
                print(f"{name}: stopped")
        marker = self.run / "docker"
        if marker.exists():
            run(["docker", "compose", "-f", marker.read_text().strip(), "down", "--timeout", "60"], self.root)
            marker.unlink()
            print("docker: Fuseki and RabbitMQ stopped")

    def status(self) -> None:
        ports = {"fuseki": FUSEKI_PORT, "rabbitmq": RABBITMQ_PORT, "service": SERVICE_PORT, "web": WEB_PORT}
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
    except ProcessLookupError:
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
    parser.add_argument("action", choices=("up", "down", "status"))
    parser.add_argument("--docker", action="store_true", help="run Fuseki and RabbitMQ with docker compose")
    parser.add_argument("--dev", action="store_true", help="also serve the browser code with hot reload on 4175")
    parser.add_argument("--root", default=None)
    args = parser.parse_args(argv)
    stack = Stack(lattice_repo_catalogue.find_root(args.root))
    if args.action == "up":
        stack.up(args.docker, args.dev)
    elif args.action == "down":
        stack.down()
    else:
        stack.status()


if __name__ == "__main__":
    main()
