"""The operations of the writer's tests of fan-out within the write (`FanOutTest`), written by the surface compiler and kept equal to it.

`platform/config-studio-service/src/test/resources/fan-out/workspace-current.ttl` is a promotion of the studio's own graphs that reads across
aggregates, from a workspace's description into a lineage's graph. This test writes the partition clear, the fill that reads the world and the
query that names the sources another write reaches, in the layout the studio stages for its own promotions, beside it.

    LATTICE_WRITE_FAN_OUT_FIXTURE=1 mise exec -- python -m pytest workers/tests/test_config_studio_fan_out_fixture.py -q

Without the switch the checked-in files must equal what the compiler gives now, so a change to the compiler fails here until they are written again."""

from __future__ import annotations

import json
import os
from pathlib import Path

from rdflib import Graph

from persistence.ir_render import render
from surface.maintenance import fill_all, partition_clear, reach
from surface.model import read_contracts

ROOT = Path(__file__).resolve().parents[2]
FOLDER = ROOT / "platform" / "config-studio-service" / "src" / "test" / "resources" / "fan-out"
WRITE = os.environ.get("LATTICE_WRITE_FAN_OUT_FIXTURE") == "1"


def operations() -> dict[str, str]:
    contracts = read_contracts(Graph().parse(FOLDER / "workspace-current.ttl"))
    assert [c.key for c in contracts] == ["workspace-current"]
    contract = contracts[0]
    manifest = [{"key": contract.key, "family": "description", "fill": f"{contract.key}-fill-all.rq", "reach": f"{contract.key}-reach.rq"}]
    return {
        "partition-clear.rq": render(partition_clear()),
        f"{contract.key}-fill-all.rq": render(fill_all(contract)),
        f"{contract.key}-reach.rq": render(reach(contract)),
        "manifest.json": json.dumps(manifest, indent=2) + "\n",
    }


def test_the_writers_fan_out_fixtures_are_what_the_compiler_gives():
    wanted = operations()
    if WRITE:
        for name, text in wanted.items():
            (FOLDER / name).write_text(text, encoding="utf-8", newline="\n")
    kept = {p.name: p.read_text(encoding="utf-8") for p in FOLDER.iterdir() if p.suffix in (".rq", ".json")}
    assert kept == wanted
