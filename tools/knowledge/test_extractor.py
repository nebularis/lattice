# SPDX-License-Identifier: MPL-2.0
"""LATTICE's extractor for Вивід (ADR-A152 decision 1, plan vyvid-migration, VM-3 and VM-9): run on this checkout as `vyd build`
runs it, it writes no quads, and its units name every module of the catalogue. The quanta are Вивід's own kind, and
test_knowledge_base.py proves them against the index `vyd build` writes."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import extractor  # noqa: E402
import lattice_repo_catalogue  # noqa: E402

ROOT = lattice_repo_catalogue.find_root()
INDEX = "https://www.nebularis.org/vyvid/knowledge#index/lattice"


def request() -> dict:
    return {"protocol": 1, "kind": "lattice-units", "scope": "lattice", "root": str(ROOT), "settings": {},
            "paths": [f"{ROOT}/ontology/**/*.ttl", f"{ROOT}/deployment/**/docker-compose.yml"], "output": "",
            "graphs": {"index": INDEX, "terms": "https://www.nebularis.org/vyvid/knowledge#terms/lattice"}}


def test_vm3_01_the_result_is_protocol_1_and_writes_no_quads_and_no_problems():
    result = extractor.extract(request())
    assert result["protocol"] == 1 and result["version"] and not result["problems"] and not result["texts"]


def test_vm3_03_the_units_name_every_module_tool_package_and_kind():
    result = extractor.extract(request())
    catalogue = lattice_repo_catalogue.load(ROOT)
    units = result["units"]
    assert all(units.get(name) == [name] for name in catalogue.modules)
    # A module of the same name wins the bare name, so a tool package is always reachable by its path.
    assert all(units.get(tool.path) == [tool.path] for tool in catalogue.tools)
    assert all(units.get(tool.name) == [tool.path] for tool in catalogue.tools if tool.name not in catalogue.modules)
    assert set(units["substrate"]) == {m.name for m in catalogue.modules_of_kind("substrate")}


def test_vm3_04_every_unit_path_names_a_declared_unit_and_a_module_sits_under_its_root():
    result = extractor.extract(request())
    declared = {unit for listed in result["units"].values() for unit in listed}
    assert result["unit_paths"] and set(result["unit_paths"].values()) <= declared
    assert result["unit_paths"]["ontology"] == "ontology" and result["unit_paths"]["ontology/foundation"] == "foundation"
    assert result["unit_paths"]["tools/mork"] == "tools/mork"
