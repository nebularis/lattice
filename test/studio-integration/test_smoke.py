# SPDX-License-Identifier: MPL-2.0
"""Each declared topology starts, passes the smoke scenario, stops, and leaves nothing behind. On demand only (SQ-D7)."""

from __future__ import annotations

import socket
import time
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from lattice_testing_studio_harness import Topology, smoke

pytestmark = pytest.mark.studio_integration
TOPOLOGIES = sorted((Path(__file__).parent / "topologies").glob("*.toml"))


@pytest.mark.parametrize("path", TOPOLOGIES, ids=lambda p: p.stem)
def test_a_topology_runs_the_smoke_scenario_and_leaves_nothing(path: Path, request: pytest.FixtureRequest) -> None:
    runner = request.config.getoption("--runner")
    topology = Topology.load(path)
    started = time.perf_counter()
    studio = topology.start(runner=runner)
    up = time.perf_counter() - started
    try:
        steps = smoke(studio.client())
    finally:
        stopping = time.perf_counter()
        studio.stop()
    down = time.perf_counter() - stopping
    print(f"\n{topology.name} on {runner}: up in {up:.1f} s, stopped in {down:.1f} s")
    for step in steps:
        print(f"  {step.name:<24} {step.status}  {step.nanos / 1e6:8.1f} ms")
    assert studio.leftovers() == [], "a process or container it started is still there"
    assert not studio.run_dir.exists(), "its run folder is still there"
    with pytest.raises(OSError), socket.create_connection((urlsplit(studio.url).hostname, urlsplit(studio.url).port), timeout=1):
        pass
