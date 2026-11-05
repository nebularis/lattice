# SPDX-License-Identifier: MPL-2.0
"""LATTICE's extractor for Вивід (ADR-A152 decision 1, plan vyvid-migration, VM-3): run on this checkout as `vyd build`
runs it, its quads sit in the index graph alone, its quanta include modules under the IRI Вивід gives a declared unit,
and its units name every module of the catalogue."""

from __future__ import annotations

import sys
from pathlib import Path

import pyoxigraph as ox

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import extractor  # noqa: E402
import lattice_repo_catalogue  # noqa: E402

ROOT = lattice_repo_catalogue.find_root()
INDEX = "https://www.nebularis.org/vyvid/knowledge#index/lattice"


def request() -> dict:
    return {"protocol": 1, "kind": "lattice-quanta", "scope": "lattice", "root": str(ROOT), "settings": {},
            "paths": [f"{ROOT}/ontology/**/*.ttl", f"{ROOT}/deployment/**/docker-compose.yml"], "output": "",
            "graphs": {"index": INDEX, "terms": "https://www.nebularis.org/vyvid/knowledge#terms/lattice"}}


def test_vm3_01_every_quad_is_in_the_index_graph_and_the_result_is_protocol_1():
    quads, result = extractor.extract(request())
    assert quads and all(q.graph_name == ox.NamedNode(INDEX) for q in quads)
    assert result["protocol"] == 1 and result["version"] and not result["problems"]
    assert set(result["texts"]) <= {q.subject.value for q in quads}


def test_vm3_02_the_substrate_is_one_data_quantum_of_modules_under_the_unit_iri():
    quads, _ = extractor.extract(request())
    substrate = ox.NamedNode("https://www.nebularis.org/vyvid/knowledge#node/lattice/DATASUBSTRATE")
    parts = [q.object.value for q in quads if q.subject == substrate and q.predicate.value.endswith("#includes")]
    assert parts and all(p.startswith("https://www.nebularis.org/vyvid/knowledge#module/lattice/") for p in parts)


def test_vm3_03_the_units_name_every_module_tool_package_and_kind():
    _, result = extractor.extract(request())
    catalogue = lattice_repo_catalogue.load(ROOT)
    units = result["units"]
    assert all(units.get(name) == [name] for name in catalogue.modules)
    # A module of the same name wins the bare name, so a tool package is always reachable by its path.
    assert all(units.get(tool.path) == [tool.path] for tool in catalogue.tools)
    assert all(units.get(tool.name) == [tool.path] for tool in catalogue.tools if tool.name not in catalogue.modules)
    assert set(units["substrate"]) == {m.name for m in catalogue.modules_of_kind("substrate")}


def test_vm3_04_every_unit_path_names_a_declared_unit_and_a_module_sits_under_its_root():
    _, result = extractor.extract(request())
    declared = {unit for listed in result["units"].values() for unit in listed}
    assert result["unit_paths"] and set(result["unit_paths"].values()) <= declared
    assert result["unit_paths"]["ontology"] == "ontology" and result["unit_paths"]["ontology/foundation"] == "foundation"
    assert result["unit_paths"]["tools/mork"] == "tools/mork"
