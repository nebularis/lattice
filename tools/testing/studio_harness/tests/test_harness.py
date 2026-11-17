# SPDX-License-Identifier: MPL-2.0
"""The harness's own tests. They start no studio, so `check:config-studio` runs them quickly. Test IDs are SH-Tn."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

from lattice_testing_studio_harness import Client, HarnessError, Reply, Topology, free_ports
from lattice_testing_studio_harness._tools import catalogue, stack
from lattice_testing_studio_harness.compose import Paths, compose_config, fuseki_config
from lattice_testing_studio_harness.processes import ProcessStudio
from lattice_testing_studio_harness.tab import settle
from lattice_testing_studio_harness.topology import new_run_id, queue_consumers, queue_counts

ROOT = catalogue.find_root()
TOPOLOGIES = sorted((ROOT / "test" / "studio-integration" / "topologies").glob("*.toml"))
PATHS = Paths(Path("/d"), Path("/r"), Path("/r/build/service"), Path("/r/build/writer"), Path("/r/build/worker"))


def test_sh_t1_the_shipped_topologies_load() -> None:
    loaded = {t.name: t for t in map(Topology.load, TOPOLOGIES)}
    assert (loaded["single"].writers, loaded["single"].workers) == (1, 1)
    assert (loaded["pair"].writers, loaded["pair"].workers) == (2, 2)
    assert (loaded["single"].long_workers, loaded["pair"].long_workers) == (1, 1), "a topology has a worker for the long queue unless it says not"
    assert all(t.store == "tdb2" and t.auth == "local" and t.runner == "processes" for t in loaded.values())


@pytest.mark.parametrize("text, message", [
    ('name = "x"\nwriters = 0', "at least one writer"),
    ('name = "x"\nstore = "postgres"', "store"),
    ('name = "x"\nauth = "oidc"', "oidc is not supported"),
    ('name = "x"\nrunner = "k8s"', "runner"),
    ('name = "x"\nwriter = 2', "unknown topology keys"),
    ('writers = 1', "has a name"),
    ('name = "x"\nwriters = "2"', "whole number"),
    ('name = "a b"', "topology name"),
])
def test_sh_t2_a_topology_that_cannot_run_is_refused(text: str, message: str) -> None:
    with pytest.raises(HarnessError, match=message):
        Topology.parse(text)


def test_sh_t3_free_ports_are_distinct_and_bindable() -> None:
    ports = free_ports(8)
    assert len(set(ports)) == 8
    for port in ports:
        with socket.socket() as s:
            s.bind(("127.0.0.1", port))


def test_sh_t4_run_ids_are_valid_project_and_node_names() -> None:
    ids = {new_run_id() for _ in range(50)}
    assert len(ids) == 50 and all(i.isalnum() and i.islower() and len(i) == 9 for i in ids)


@pytest.mark.parametrize("path", TOPOLOGIES, ids=lambda p: p.stem)
def test_sh_t5_the_compose_file_of_each_topology(path: Path) -> None:
    topology = Topology.load(path)
    config = json.loads(json.dumps(compose_config(topology, "h12345678", PATHS, 49999)))
    services = config["services"]
    assert set(services) == {"fuseki", "rabbitmq", "service", "proxy"} | {f"writer{i + 1}" for i in range(topology.writers)} | {f"worker{i + 1}" for i in range(topology.workers)} | {f"workerlong{i + 1}" for i in range(topology.long_workers)}
    published = [(n, p) for n, s in services.items() for p in s.get("ports", [])]
    assert published == [("service", "127.0.0.1:49999:8091")], "only the service is published, and on loopback"
    assert services["service"]["environment"]["LATTICE_STUDIO_BIND"] == "127.0.0.1"
    assert services["proxy"]["network_mode"] == "service:service"
    assert all(s["networks"] == ["studio"] for n, s in services.items() if n != "proxy")
    assert services["writer1"]["environment"]["LATTICE_STREAM_URI"].startswith("rabbitmq-stream://guest:guest@rabbitmq:5552")
    assert all(s["environment"]["LATTICE_FUSEKI_URL"] == "http://fuseki:3030" for n, s in services.items() if n.startswith(("writer", "worker", "service")))
    assert "data:/data" in services["fuseki"]["volumes"] and "data" in config["volumes"]
    assert config["name"] == "h12345678"
    assert all(s["image"].endswith(":h12345678") for s in services.values() if "build" in s), "built images carry the run id, so stop removes exactly them"


def test_sh_t6_a_memory_store_has_no_volume_and_its_own_dataset() -> None:
    config = compose_config(Topology(name="m", store="memory"), "h1", PATHS, 1)
    assert config["volumes"] == {} and not any(v.endswith(":/data") for v in config["services"]["fuseki"]["volumes"])
    text = fuseki_config("memory")
    assert "MemoryDataset" in text and "tdb2:location" not in text and 'fuseki:name "studio-write"' in text
    assert 'tdb2:location "/data"' in fuseki_config("tdb2")


def test_sh_t7_the_client_reads_replies() -> None:
    reply = Reply(201, b"x", {"location": "/api/workspaces/abc", "etag": '"7"'}, 5)
    assert Client.workspace_id(reply) == "abc" and reply.revision == 7 and reply.text == "x"
    assert Reply(200, b"", {}, 0).revision is None


def test_sh_t8_queue_consumers_reads_rabbitmqctl_csv() -> None:
    out = '"name","consumers"\n"lattice.studio.jobs","2"\n"lattice.studio.transforms","0"\n'
    assert queue_consumers(out, "lattice.studio.jobs") == 2
    assert queue_consumers(out, "lattice.studio.transforms") == 0
    assert queue_consumers(out, "absent") == 0


def test_sh_t9_a_killed_starter_leaves_no_process_and_no_run_folder(tmp_path: Path) -> None:
    run_dir = tmp_path / "run-id"
    (run_dir / "run").mkdir(parents=True)
    process = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"], **stack.detached())
    (run_dir / "run" / "fuseki.pid").write_text(str(process.pid))
    starter = subprocess.Popen([sys.executable, "-c", "import sys, time; from pathlib import Path; from lattice_testing_studio_harness import reaper; r = reaper.start(Path(sys.argv[1])); print('up', flush=True); time.sleep(120)", str(run_dir)], stdout=subprocess.PIPE, text=True)
    try:
        assert starter.stdout.readline().strip() == "up"
        assert process.poll() is None, "the process stopped while its starter still ran"
        starter.kill()
        starter.wait()
        process.wait(timeout=30)
        deadline = time.monotonic() + 30
        while run_dir.exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        assert not run_dir.exists()
    finally:
        starter.kill()
        starter.stdout.close()
        starter.wait()
        process.kill()
        process.wait()


def test_sh_t10_a_workers_proposer_settings_come_from_the_test_and_never_the_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LATTICE_STUDIO_HARNESS_WORKER_ROOT", raising=False)
    monkeypatch.setenv("LATTICE_PROPOSER_KEY_FILE", "/from/the/shell")
    monkeypatch.setenv("LATTICE_PROPOSER_MODEL", "from-the-shell")
    studio = ProcessStudio(Topology(name="env"), ROOT)
    assert studio._worker_env({"LATTICE_ROOT": "r"}) == {"LATTICE_ROOT": "r", "LATTICE_PROPOSER_KEY_FILE": "", "LATTICE_PROPOSER_MODEL": ""}
    assert studio._worker_env({"LATTICE_PROPOSER_MODEL": "from-the-test"})["LATTICE_PROPOSER_MODEL"] == "from-the-test"


def test_sh_t11_a_topology_declares_run_workers_and_service_instances() -> None:
    runs = Topology.load(ROOT / "test" / "studio-integration" / "topologies" / "runs.toml")
    assert (runs.run_workers, runs.instances) == (1, 2)
    assert (Topology(name="x").run_workers, Topology(name="x").instances) == (0, 1), "a topology has one service and no run worker unless it says so"
    with pytest.raises(HarnessError, match="at least one service instance"):
        Topology.parse('name = "x"\ninstances = 0')
    with pytest.raises(HarnessError, match="whole number"):
        Topology.parse('name = "x"\nrun_workers = "1"')
    with pytest.raises(HarnessError, match="cannot be negative"):
        Topology.parse('name = "x"\nrun_workers = -1')
    with pytest.raises(HarnessError, match="compose runner starts one service instance"):
        runs.start(runner="compose")


def test_sh_t12_queue_counts_reads_rabbitmqctl_csv() -> None:
    out = '"name","messages","messages_unacknowledged"\n"lattice.studio.runs","3","1"\n"lattice.studio.jobs","0","0"\n'
    assert queue_counts(out, "lattice.studio.runs", ("messages", "messages_unacknowledged")) == {"messages": 3, "messages_unacknowledged": 1}
    assert queue_counts(out, "absent", ("messages",)) == {"messages": 0}


def test_sh_t13_a_run_is_read_from_its_reply_and_a_run_request_is_built_from_its_parts() -> None:
    iri = "urn:lattice:studio:run:0b3c7f2e-1111-4222-8333-444455556666"
    assert Client.run_iri(Reply(202, f"<{iri}> a cst:Run .".encode())) == iri
    assert Client.run_iri(Reply(400, b"deadline is in the past")) == ""
    calls = []
    client = Client("http://127.0.0.1:1")
    client.request = lambda method, path, body=b"", headers=None: calls.append((method, path, body, headers)) or Reply(202, b"")  # type: ignore[method-assign]
    client.submit_run("w1", "j1", "tab1", "<x/>", "application/xml", deadline="2026-11-17T10:00:00Z", wait=True)
    method, path, body, headers = calls[0]
    assert method == "POST" and body == "<x/>" and headers == {"Content-Type": "application/xml"}
    assert path == "/api/workspaces/w1/runs?kind=sample&target=mapping&job=j1&tab=tab1&deadline=2026-11-17T10%3A00%3A00Z&wait=true"


def test_sh_t14_a_client_settles_a_run_by_the_contracts_rule() -> None:
    ok = {"seq": 0, "last": False}
    assert settle([]) == {"state": "open", "message": None, "missing": []}
    assert settle([ok, {"seq": 1, "last": True, "status": "succeeded"}])["state"] == "complete"
    assert settle([{"seq": 1, "last": False}, ok, ok, {"seq": 2, "last": True, "status": "succeeded"}])["state"] == "complete", "the first frame of a seq counts and a repeat does not"
    assert settle([ok, {"seq": 2, "last": True, "status": "succeeded"}]) == {"state": "partial", "message": None, "missing": [1]}
    assert settle([ok, {"seq": 3, "last": True, "status": "failed", "message": "it did not finish"}]) == {"state": "failed", "message": "it did not finish", "missing": [1, 2]}
