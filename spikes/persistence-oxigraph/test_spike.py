# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Checks for the spike. Not part of any ``mise`` task. Run from the repository root with:

    python -m pytest spikes/persistence-oxigraph -q

Skipped where ``pyoxigraph`` is not installed."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
pytest.importorskip("pyoxigraph", reason="pip install -r spikes/persistence-oxigraph/requirements.txt")

from oxigraph_backend import OxigraphBackend, bind_parameters, iri, literal  # noqa: E402
from rdflib_comparison import compare  # noqa: E402
from scenarios import append_event_runs, composite_sweep, project_sweep  # noqa: E402


def test_bind_parameters_replaces_both_spellings_and_leaves_other_names_alone():
    text = "INSERT { ?root <urn:p> $value . ?other <urn:q> ?x } WHERE { $root <urn:r> ?x }"
    bound = bind_parameters(text, {"root": iri("urn:a"), "value": literal(1)})
    assert "<urn:a> <urn:p> \"1\"^^" in bound and "?other" in bound and "?x" in bound
    assert "$root" not in bound and "?root" not in bound


def test_bind_parameters_refuses_a_name_that_is_not_in_the_text():
    with pytest.raises(ValueError, match="misspelt"):
        bind_parameters("INSERT DATA { <urn:a> <urn:p> <urn:o> }", {"misspelt": iri("urn:x")})


def test_a_backend_runs_an_update_and_a_select():
    backend = OxigraphBackend()
    backend.update("INSERT DATA { <urn:a> <urn:p> 1 }")
    assert backend.select("SELECT ?o WHERE { <urn:a> <urn:p> ?o }")[0]["o"].value == "1"


def test_the_composite_sweep_removes_what_the_shape_owns_and_leaves_what_it_does_not():
    assert composite_sweep(owns_payment=False, with_payment=False) == []
    assert composite_sweep(owns_payment=False, with_payment=True) == ["urn:pay:1"]  # a payment the shape does not own stays
    assert composite_sweep(owns_payment=True, with_payment=True) == []


def test_the_project_fixture_keeps_every_node_outside_the_aggregate_and_removes_the_project_and_its_members():
    left = project_sweep()
    assert left == sorted({"acme", "alice", "docShared", "InProgress", "Done", "TaskStatuses", "report1", "p2", "m9"})


def test_a_missing_parameter_advances_the_counter_and_writes_no_revision():
    a, b, c = append_event_runs()
    assert (a.sequence, a.revision_records, a.head_pointers) == (["1"], 1, 1)
    assert (b.sequence, b.revision_records, b.head_pointers) == (["1"], 0, 0)
    assert (c.sequence, c.revision_records) == (["2"], 1)


def test_rdflib_and_oxigraph_agree_on_every_scenario():
    disagreements = [(label, a, b) for label, a, b in compare() if a != b]
    assert disagreements == []
