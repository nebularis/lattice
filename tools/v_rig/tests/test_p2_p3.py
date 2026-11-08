# SPDX-License-Identifier: MPL-2.0
"""P2 and P3 on the mini-rig: the cases and their readings, the vectors under the schema with the three fact states as
three shapes, and the generated theory with a value per case and reading and no number the rig did not give."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import jsonschema
import pytest

from v_rig import lift, read_rig
from v_rig.lift import RunInfo
from v_rig import cases as cases_module, p2, p3

HERE = Path(__file__).resolve().parent
MINI_RIG = HERE / "mini-rig"
EXTENSION = HERE / "mini-rig.extension.ttl"
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "tools"))
RUN = RunInfo("0000000000000000000000000000000000000000", "0.0.0", "0.1.0", None)
READING_KEYS = ("drop_down", "exhaustion")


@pytest.fixture(scope="module")
def rig():
    return read_rig(MINI_RIG)


@pytest.fixture(scope="module")
def graph(rig):
    return lift(rig, RUN, READING_KEYS)


@pytest.fixture(scope="module")
def bindings():
    return cases_module.input_bindings([EXTENSION])


@pytest.fixture(scope="module")
def found(graph, rig, bindings):
    return p3.vectors(graph, rig.digest, READING_KEYS, bindings, rig.file_digests)


@pytest.fixture(scope="module")
def theory(graph, rig, bindings):
    return p2.theory(graph, rig.digest, READING_KEYS, bindings, rig.file_digests)


# ---- cases and readings ------------------------------------------------------------------

def test_one_case_with_its_documents_events_and_readings(graph, rig):
    (case,) = cases_module.cases(graph, rig.digest, READING_KEYS, rig.file_digests)
    assert case.programme_id == "prog-001"
    assert [cases_module.rig_id(graph, d) for d in case.documents] == ["prim-001", "xs1-001", "xs2-001", "xs2-002"]
    assert [cases_module.rig_id(graph, e) for e in case.events] == ["ev-001", "ev-002"]
    assert [(r.key, r.token, r.stated_by) for r in case.readings] == [
        ("drop_down", "on-exhaustion-only", ("xs1-001",)),
        ("exhaustion", "payment-by-insurer", ("prim-001", "xs1-001", "xs2-001")),
        ("exhaustion", "payment-or-agreement", ("xs2-002",)),
    ]
    assert len(case.digest) == 64


def test_input_bindings_come_from_the_extension(bindings):
    assert bindings == {"loss": "loss_amount", "prior": "prior_knowledge", "notice": "date_of_first_notice"}


# ---- the vectors ------------------------------------------------------------------------

def test_one_vector_per_case_and_reading_under_the_schema(found):
    assert len(found) == 3
    assert {name.rsplit("/", 1)[-1] for name in found} == {"drop_down=on-exhaustion-only.json", "exhaustion=payment-by-insurer.json", "exhaustion=payment-or-agreement.json"}
    schema = json.loads(p3.schema_path().read_text(encoding="utf-8"))
    for document in found.values():
        jsonschema.validate(document, schema)
        assert document["vectorsFormat"] == "lattice-v-rig-vectors/1"


def test_the_three_fact_states_are_three_shapes(found):
    document = next(v for k, v in found.items() if k.endswith("exhaustion=payment-by-insurer.json"))
    ev1, ev2 = document["events"]
    assert ev1["inputs"]["loss"] == {"state": "stated", "value": 2500000}
    assert ev1["inputs"]["prior"] == {"state": "unknown"}
    assert ev1["inputs"]["notice"] == {"state": "absent"}
    assert ev2["inputs"]["prior"] == {"state": "stated", "value": False}
    assert set(ev1["inputs"]) == {"loss", "prior", "notice"}


def test_structure_shares_formula_and_period_in_the_vector(found):
    document = next(v for k, v in found.items() if k.endswith("exhaustion=payment-or-agreement.json"))
    assert document["reading"] == {"key": "exhaustion", "token": "payment-or-agreement", "statedBy": ["xs2-002"]}
    assert document["programme"]["period"] == {"state": "stated", "value": ["2027-01-01", "2027-12-31"]}
    assert document["programme"]["currency"] == {"state": "stated", "value": "XCD"}
    layer3 = document["layers"][2]
    assert layer3["documents"] == ["xs2-001", "xs2-002"]
    assert layer3["limit"] == {"state": "stated", "value": 3000000}
    assert [p["share"]["value"] for p in layer3["placements"]] == [0.6, 0.4]
    assert layer3["placements"][0]["role"] == {"state": "stated", "value": "lead"}
    assert document["case"]["documents"] == ["prim-001", "xs1-001", "xs2-001", "xs2-002"]
    contracts = {c["id"]: c for c in document["documents"]}
    assert contracts["xs2-001"]["limit"] == {"state": "stated", "formula": "0.6 x layer_limit", "inputs": ["layer_limit"]}
    assert contracts["xs2-001"]["layerShare"] == {"state": "stated", "value": 0.6}
    assert contracts["prim-001"]["layerShare"] == {"state": "absent"}
    assert contracts["prim-001"]["attachment"] == {"state": "stated", "value": 0}


def test_vectors_are_byte_stable(found, rig, bindings):
    again = p3.vectors(lift(read_rig(MINI_RIG), RUN, READING_KEYS), rig.digest, READING_KEYS, bindings, rig.file_digests)
    assert json.dumps(again, sort_keys=True) == json.dumps(found, sort_keys=True)


def test_a_rig_with_no_reading_gives_one_vector_with_reading_null(graph, rig, bindings):
    found = p3.vectors(graph, rig.digest, (), bindings, rig.file_digests)
    assert len(found) == 1 and next(iter(found)).endswith("/no-reading.json")
    assert next(iter(found.values()))["reading"] is None


# ---- the theory -------------------------------------------------------------------------

def test_theory_has_a_section_per_case_and_reading_and_values_over_ledger(theory):
    assert theory.count("section \\<open>Case ") == 3
    assert theory.count("_reading = ''payment-by-insurer''") == 1
    assert theory.count("_reading = ''payment-or-agreement''") == 1
    assert "imports Ledger" in theory
    assert "value \"parts " in theory and "value \"residual " in theory
    assert "layer3_weights = [6, 4]" in theory
    assert theory.count("value \"settle_at_position") == 6, "two events, three readings"


def test_theory_never_reads_a_number_the_rig_did_not_give(theory):
    assert "no input binding" not in theory
    assert "the input prior is unknown" in theory
    assert "the input notice is absent" in theory
    assert "the input prior is stated as False" in theory
    assert "2500000" in theory and "4500000" in theory
    assert "Contract xs2-001's limit is the formula 0.6 x layer_limit, over layer_limit, and binds no number until they do." in theory
    assert theory.count("_xs2_001_limit :: int") == 0 and theory.count("_xs2_002_limit :: int") == 3


def test_theory_is_byte_stable(theory, rig, bindings):
    again = p2.theory(lift(read_rig(MINI_RIG), RUN, READING_KEYS), rig.digest, READING_KEYS, bindings, rig.file_digests)
    assert again == theory


def test_theory_files_are_written_beside_a_copied_ledger(theory, tmp_path):
    out = ROOT / ".local" / "v-rig" / "test-p2"
    try:
        written = p2.write_theory(theory, out)
        assert {p.name for p in written} == {"VRigP2.thy", "ROOT", "Ledger.thy"}
        assert (out / "p2" / "Ledger.thy").read_text() == p2.ledger_theory().read_text()
        assert "session VRigP2 = HOL +" in (out / "p2" / "ROOT").read_text()
    finally:
        import shutil
        shutil.rmtree(out, ignore_errors=True)
