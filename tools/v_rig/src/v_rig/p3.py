# SPDX-License-Identifier: MPL-2.0
"""P3, the test vectors: one JSON document per case and reading, under contracts/v-rig/vectors.schema.json, the inputs
the differential tests between the reference semantics and each compiled implementation take. Every fact is in one of
three states, each its own shape, and an event's inputs are the ones the extension's bindings declare."""

from __future__ import annotations

import json
from pathlib import Path

from rdflib import Graph

from . import canon
from .cases import Case, cases, fact_state, layers_of, placements_on, rig_id
from .lift import VRIG

VECTOR_SCHEMA_VERSION = "lattice-v-rig-vectors/1"


def schema_path() -> Path:
    import lattice_repo_catalogue as reader
    catalogue = reader.load()
    return catalogue.root / catalogue.area("contracts") / "v-rig" / "vectors.schema.json"


def vector(graph: Graph, case: Case, reading, rig_digest: str, bindings: dict[str, str]) -> dict:
    layers = []
    for layer in layers_of(graph, case):
        documents = [str(graph.value(d, VRIG.rigId)) for key in ("document", "documents")
                     for f in graph.subjects(VRIG.of, layer) if str(graph.value(f, VRIG.key)) == key
                     for d in graph.objects(f, VRIG.resolvesTo)]
        layers.append({
            "layer": int(graph.value(layer, VRIG.layerNumber)),
            "documents": sorted(set(documents)),
            "attachment": fact_state(graph, layer, "attachment"),
            "limit": fact_state(graph, layer, "limit"),
            "placements": [{key: fact_state(graph, placement, key) for key in ("name", "share", "role", "document")}
                           for placement in placements_on(graph, layer)],
        })
    events = [{"id": rig_id(graph, event), "inputs": {name: fact_state(graph, event, key) for name, key in sorted(bindings.items())}}
              for event in case.events]
    return {
        "vectorsFormat": VECTOR_SCHEMA_VERSION,
        "case": {"digest": case.digest, "rigDigest": rig_digest, "documents": [rig_id(graph, d) for d in case.documents]},
        "reading": None if reading is None else {"key": reading.key, "token": reading.token, "statedBy": list(reading.stated_by)},
        "programme": {"id": case.programme_id, "currency": fact_state(graph, case.programme, "currency"),
                      "period": fact_state(graph, case.programme, "period")},
        "documents": [{"id": rig_id(graph, d), "limit": fact_state(graph, d, "limit"), "attachment": fact_state(graph, d, "attachment"),
                       "position": fact_state(graph, d, "position"), "layerShare": fact_state(graph, d, "layer_share")} for d in case.documents],
        "layers": layers,
        "events": events,
    }


def vectors(graph: Graph, rig_digest: str, reading_keys: tuple[str, ...], bindings: dict[str, str], file_digests: dict[str, str]) -> dict[str, dict]:
    """Every vector, by its file name under p3/, `<case digest>/<key>=<token>.json` or `<case digest>/no-reading.json`."""
    out: dict[str, dict] = {}
    for case in cases(graph, rig_digest, reading_keys, file_digests):
        readings = case.readings or [None]
        for reading in readings:
            name = "no-reading" if reading is None else f"{canon.percent(reading.key)}={canon.percent(reading.token)}"
            out[f"{case.digest}/{name}.json"] = vector(graph, case, reading, rig_digest, bindings)
    return out


def validate_vectors(found: dict[str, dict]) -> None:
    import jsonschema
    schema = json.loads(schema_path().read_text(encoding="utf-8"))
    for name, document in found.items():
        jsonschema.validate(document, schema)


def write_vectors(found: dict[str, dict], out: Path) -> list[Path]:
    written = []
    for name, document in sorted(found.items()):
        path = out / "p3" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        written.append(path)
    index = out / "p3" / "index.json"
    index.write_text(json.dumps({"vectorsFormat": VECTOR_SCHEMA_VERSION, "vectors": sorted(found)}, indent=2) + "\n", encoding="utf-8", newline="\n")
    return written + [index]
