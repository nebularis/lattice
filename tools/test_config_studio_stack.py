# SPDX-License-Identifier: MPL-2.0
"""Tests the stack script's process and download handling, which `up` and `down` rest on."""

from __future__ import annotations

import hashlib
import socket
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_studio_stack as stack  # noqa: E402
import lattice_repo_catalogue  # noqa: E402


def test_a_spawned_process_and_its_children_stop(tmp_path: Path) -> None:
    studio = stack.Stack(lattice_repo_catalogue.find_root())
    studio.run = tmp_path
    child = "import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); time.sleep(60)"
    pid = studio.spawn("sleeper", [sys.executable, "-c", child])
    assert studio.pid("sleeper") == pid
    assert studio.stop("sleeper")
    deadline = time.monotonic() + 10
    while stack.alive(pid) and time.monotonic() < deadline:
        time.sleep(0.1)
    assert not stack.alive(pid)
    assert studio.pid("sleeper") is None
    assert not studio.stop("sleeper")


def test_a_download_with_the_wrong_checksum_is_refused(tmp_path: Path) -> None:
    source = tmp_path / "release.bin"
    source.write_bytes(b"release")
    url = source.as_uri()
    with pytest.raises(SystemExit, match="Refused"):
        stack.download(url, "0" * 64, tmp_path / "into")
    assert not list((tmp_path / "into").iterdir())
    good = hashlib.sha256(b"release").hexdigest()
    assert stack.download(url, good, tmp_path / "into").read_bytes() == b"release"


def test_a_port_another_process_holds_is_refused_before_anything_starts(tmp_path: Path) -> None:
    studio = stack.Stack(lattice_repo_catalogue.find_root())
    studio.run = tmp_path
    with socket.socket() as other:
        other.bind(("127.0.0.1", 0))
        other.listen()
        port = other.getsockname()[1]
        with pytest.raises(SystemExit, match="in use by another process"):
            studio.claim("service", port)
        assert not (tmp_path / "service.pid").exists()
    assert studio.claim("service", port)


def test_a_component_runs_from_a_copy_that_a_later_build_leaves_alone(tmp_path: Path) -> None:
    studio = stack.Stack(lattice_repo_catalogue.find_root())
    studio.run = tmp_path / "run"
    jar, dist = tmp_path / "target" / "service.jar", tmp_path / "dist"
    jar.parent.mkdir()
    dist.mkdir()
    jar.write_bytes(b"first build")
    (dist / "index.html").write_text("first", encoding="utf-8")
    pinned_jar, pinned_dist = studio.pinned("service", jar), studio.pinned("web", dist)
    jar.write_bytes(b"second build")
    (dist / "index.html").write_text("second", encoding="utf-8")
    assert pinned_jar.read_bytes() == b"first build" and (pinned_dist / "index.html").read_text(encoding="utf-8") == "first"
    assert studio.pinned("web", dist) == pinned_dist and (pinned_dist / "index.html").read_text(encoding="utf-8") == "second"


def test_workspaces_live_in_the_platform_data_folder_unless_told_otherwise() -> None:
    home = {"HOME": "/h", "USERPROFILE": "C:/Users/a"}
    assert stack.data_dir({"LATTICE_STUDIO_DATA": "/x", **home}) == Path("/x")
    assert stack.data_dir(home, "darwin") == Path("/h/Library/Application Support/LATTICE/studio")
    assert stack.data_dir({**home, "LOCALAPPDATA": "C:/L"}, "win32") == Path("C:/L/LATTICE/studio")
    assert stack.data_dir(home, "linux") == Path("/h/.local/share/lattice/studio")
    assert stack.data_dir({**home, "XDG_DATA_HOME": "/d"}, "linux") == Path("/d/lattice/studio")


def test_the_compose_files_fuseki_configuration_is_the_stacks() -> None:
    root = lattice_repo_catalogue.find_root(None)
    mounted = (root / "deployment" / "compose" / "config-studio" / "fuseki-studio.ttl").read_text()
    assert stack.FUSEKI_CONFIG.replace("{location}", "/data") in mounted


def _stack(tmp_path: Path) -> "stack.Stack":
    studio = stack.Stack(lattice_repo_catalogue.find_root())
    studio.infra = tmp_path / "infra"
    return studio


def test_the_broker_has_one_user_with_a_password_made_once_and_kept_private(tmp_path: Path) -> None:
    studio = _stack(tmp_path)
    password, secret = studio.broker_credentials()
    assert len(password) >= 32 and len(secret) >= 32 and password != secret
    assert studio.broker_credentials() == (password, secret), "made once for the stack"
    assert stack.Stack.broker_credentials(_stack(tmp_path / "other"))[0] != password, "and once for each stack"
    folder = tmp_path / "infra" / "broker"
    assert (folder / "amqp-uri").read_text() == f"amqp://studio:{password}@127.0.0.1:{stack.RABBITMQ_PORT}/%2F"
    assert (folder / "stream-uri").read_text().startswith(f"rabbitmq-stream://studio:{password}@127.0.0.1:")
    if not stack.WINDOWS:
        assert all((folder / f).stat().st_mode & 0o077 == 0 for f in ("password", "secret", "amqp-uri", "stream-uri"))
    env = {**studio.service_env(), **studio.writer_env()}
    assert "guest" not in " ".join(env.values())
    assert env["LATTICE_STUDIO_BROKER_SECRET"] == secret


def test_the_brokers_configuration_names_its_user_and_asks_the_service_under_the_secret(tmp_path: Path) -> None:
    studio = _stack(tmp_path)
    password, secret = studio.broker_credentials()
    conf = studio.broker_conf("host.docker.internal")
    assert f"default_user = studio\ndefault_pass = {password}\n" in conf
    assert f"auth_http.user_path = http://host.docker.internal:{stack.SERVICE_PORT}/api/broker/{secret}/user" in conf
    assert "auth_backends.1 = internal\nauth_backends.2 = http" in conf and "mqtt.allow_anonymous = false" in conf
    assert "guest" not in conf


def test_the_compose_override_follows_the_kind_of_docker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    studio = _stack(tmp_path)
    for engine, override in ((False, "docker-compose.desktop.yml"), (True, "docker-compose.host-network.yml")):
        monkeypatch.setattr(stack, "docker_engine_on_linux", lambda engine=engine: engine)
        files = studio.compose_files()
        assert files[0] == studio.compose and files[1].name == override and files[1].exists()


def test_docker_desktop_is_told_apart_from_docker_engine_on_linux_only(monkeypatch: pytest.MonkeyPatch) -> None:
    class Done:
        def __init__(self, out: str) -> None:
            self.stdout = out
    for platform, out, engine in (("darwin", "Ubuntu", False), ("win32", "Ubuntu", False), ("linux", "Docker Desktop", False), ("linux", "Ubuntu 24.04 LTS", True)):
        monkeypatch.setattr(stack.sys, "platform", platform)
        monkeypatch.setattr(stack.subprocess, "run", lambda *a, out=out, **k: Done(out))
        assert stack.docker_engine_on_linux() is engine, (platform, out)


def test_the_compose_broker_publishes_on_loopback_alone_and_never_has_guest() -> None:
    root = lattice_repo_catalogue.find_root(None) / "deployment" / "compose" / "config-studio"
    text = "\n".join((root / f).read_text() for f in ("docker-compose.yml", "docker-compose.desktop.yml", "docker-compose.host-network.yml"))
    assert "guest" not in text and "loopback_users" not in text
    ports = [line.strip() for line in (root / "docker-compose.desktop.yml").read_text().splitlines() if line.strip().startswith('- "')]
    assert ports and all(p.startswith('- "127.0.0.1:') for p in ports)
    assert "network_mode: host" in (root / "docker-compose.host-network.yml").read_text()


def test_a_process_that_ended_on_its_own_is_reported_with_the_last_line_of_its_log(tmp_path: Path) -> None:
    studio = stack.Stack(lattice_repo_catalogue.find_root())
    studio.run = tmp_path
    dies = "import sys; print('starting'); print('ValueError: the job names no workspace'); sys.exit(1)"
    pid = studio.spawn("worker", [sys.executable, "-c", dies])
    deadline = time.monotonic() + 10
    while stack.alive(pid) and time.monotonic() < deadline:
        time.sleep(0.1)
    said = studio.describe("worker", studio.pid("worker"))
    assert said == "exited, last line of its log: ValueError: the job names no workspace"
    assert studio.describe("transforms", studio.pid("transforms")) == "not started here"
    assert studio.describe("worker", 123) == "running as 123"


def test_the_last_line_skips_blank_ones_and_says_when_there_is_no_log(tmp_path: Path) -> None:
    (tmp_path / "x.log").write_text("one\n\ntwo\n\n", encoding="utf-8")
    assert stack.last_line(tmp_path / "x.log") == "two"
    (tmp_path / "empty.log").write_text("\n", encoding="utf-8")
    assert stack.last_line(tmp_path / "empty.log") == "(empty)"
    assert stack.last_line(tmp_path / "none.log") == "(no log)"
