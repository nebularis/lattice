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


def test_the_brokers_main_configuration_holds_no_secret_and_the_secret_part_is_private(tmp_path: Path) -> None:
    studio = _stack(tmp_path)
    password, secret = studio.broker_credentials()
    conf = studio.broker_conf()
    assert "default_user = studio\n" in conf and "auth_backends.1 = internal\nauth_backends.2 = http" in conf and "mqtt.allow_anonymous = false" in conf
    assert "default_pass" not in conf and "/api/broker/" not in conf and "guest" not in conf
    assert password not in conf and secret not in conf
    held = studio.broker_secret_conf("host.docker.internal")
    assert f"default_pass = {password}\n" in held
    assert f"auth_http.user_path = http://host.docker.internal:{stack.SERVICE_PORT}/api/broker/{secret}/user" in held
    assert all(f"auth_http.{name}_path" in held for name in ("vhost", "resource", "topic"))


def test_a_stack_the_script_starts_loads_the_secret_part_beside_a_main_file_that_names_none(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    studio = _stack(tmp_path)
    monkeypatch.setattr(stack.shutil, "which", lambda name: str(tmp_path / "erlang" / "bin" / name))
    env = studio.rabbitmq_env()
    password, secret = studio.broker_credentials()
    main, loaded = Path(env["RABBITMQ_CONFIG_FILE"]), Path(env["RABBITMQ_CONFIG_FILES"])
    text = main.read_text(encoding="utf-8")
    assert not any(value in text for value in (password, secret)) and "default_pass" not in text
    assert loaded == (tmp_path / "infra" / "broker" / "rabbitmq-secret.conf").resolve() and loaded.read_text(encoding="utf-8").startswith(f"default_pass = {password}\n")
    if not stack.WINDOWS:
        assert loaded.stat().st_mode & 0o077 == 0
    assert "\\" not in env["RABBITMQ_CONFIG_FILES"], "a glob in forward slashes"


def test_redaction_hides_each_secret_a_uri_and_leaves_a_text_without_one_alone() -> None:
    password, secret = "p" * 8 + "Aa-_" + "q" * 20, "s" * 8 + "Bb-_" + "r" * 20
    uri = f"amqp://studio:{password}@127.0.0.1:5673/%2F"
    values = [password, secret, uri]
    for text in (f"pass {password} end", f"/api/broker/{secret}/user", f"x{password}{secret}y", f"{password}\n{secret}"):
        out = stack.redact(text, values)
        assert password not in out and secret not in out and "<redacted>" in out
    assert stack.redact(f"x{password}y", values) == "x<redacted>y", "a secret with nothing around it to split it"
    assert stack.redact("stream rabbitmq-stream://other:hunter2@host:5553/%2f, amqps://u:w0rd@h/", []) == "stream rabbitmq-stream://other:<redacted>@host:5553/%2f, amqps://u:<redacted>@h/"
    assert stack.redact(f"amqp://studio:{password}@h", values) == "amqp://studio:<redacted>@h"
    assert stack.redact("quote " + stack.urllib.parse.quote("a/b c+d", safe=""), ["a/b c+d"]) == "quote <redacted>"
    plain = "listeners.tcp.default = 127.0.0.1:5673\nhttp://example.org:8080/path with : and @ but no password"
    assert stack.redact(plain, values) == plain and stack.redact(plain) == plain
    assert stack.redact("kept", ["", ""]) == "kept", "an empty value would match everywhere"


def test_a_uri_is_described_without_its_password() -> None:
    said = stack.describe_uri("rabbitmq-stream://studio:hunter2@127.0.0.1:5553/%2f")
    assert said == "scheme rabbitmq-stream, user studio, password <redacted>, host 127.0.0.1, port 5553, path /%2f"
    assert "hunter2" not in said


def test_the_config_command_prints_the_settings_and_no_secret(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    studio = _stack(tmp_path)
    studio.run = tmp_path / "run"
    studio.rabbitmq_port = 1  # nothing listens there, so the limits are reported as not read
    password, secret = studio.broker_credentials()
    (tmp_path / "infra" / "rabbitmq").mkdir()
    (tmp_path / "infra" / "rabbitmq" / "rabbitmq.conf").write_text(studio.broker_conf() + f"leaked = {password}\n", encoding="utf-8")
    studio.broker_secret_conf("127.0.0.1")
    stack.write_private(tmp_path / "infra" / "broker" / "rabbitmq-secret.conf", studio.broker_secret_conf("127.0.0.1"))
    studio.config()
    out = capsys.readouterr().out
    held = [password, secret, studio.amqp_uri(password), studio.stream_uri(password), (tmp_path / "infra" / "broker" / "rabbitmq-secret.conf").read_text(encoding="utf-8")]
    assert not any(value.strip() in out for value in held) and "default_pass" not in out
    assert "default_user = studio" in out and "leaked = <redacted>" in out
    assert f"password: " in out and f"<redacted, {len(password)} characters>" in out
    assert "scheme amqp, user studio, password <redacted>, host 127.0.0.1, port 1, path /%2F" in out
    assert f"events URL: ws://127.0.0.1:{stack.WEB_MQTT_PORT}/ws" in out and "the broker is not running" in out


def test_the_config_command_makes_no_secret_and_says_so_when_there_is_none(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    studio = _stack(tmp_path)
    studio.run = tmp_path / "run"
    studio.config()
    out = capsys.readouterr().out
    assert "not made yet" in out and "(not written yet" in out and not (tmp_path / "infra" / "broker").exists()


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
