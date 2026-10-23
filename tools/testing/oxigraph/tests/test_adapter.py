# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The Oxigraph test-support adapter (ADR-A125). Test IDs are OX-Tn."""

from __future__ import annotations

import pytest

from lattice_testing_oxigraph import OxigraphStore, bind_parameters, iri, literal

import pyoxigraph as ox


def test_ox_t1_bind_parameters_replaces_both_spellings_and_leaves_other_names_alone():
    text = "INSERT { ?root <urn:p> $value . ?other <urn:q> ?x } WHERE { $root <urn:r> ?x }"
    bound = bind_parameters(text, {"root": iri("urn:a"), "value": literal(1)})
    assert '<urn:a> <urn:p> "1"^^' in bound and "?other" in bound and "?x" in bound
    assert "$root" not in bound and "?root" not in bound


def test_ox_t2_a_parameter_that_never_appears_is_an_error_unless_not_strict():
    with pytest.raises(ValueError, match="misspelt"):
        bind_parameters("SELECT * WHERE { $root ?p ?o }", {"misspelt": iri("urn:a")})
    assert bind_parameters("SELECT * WHERE { $root ?p ?o }", {"misspelt": iri("urn:a")}, strict=False).startswith("SELECT")


def test_ox_t3_an_update_runs_with_its_parameters_and_the_quads_come_back():
    store = OxigraphStore()
    store.update("INSERT { GRAPH <urn:g> { $root <urn:p> $value } } WHERE {}", {"root": iri("urn:a"), "value": literal("v")})
    (quad,) = store.quads(iri("urn:g"))
    assert (quad.subject, quad.predicate, quad.object) == (iri("urn:a"), iri("urn:p"), literal("v"))
    assert store.count("urn:p") == 1 and store.count("urn:p", iri("urn:other")) == 0


def test_ox_t4_a_parameter_left_out_stays_an_unbound_variable():
    store = OxigraphStore()
    store.update("INSERT { GRAPH <urn:g> { $root <urn:p> $value } } WHERE {}", {"root": iri("urn:a")})
    assert store.quads() == []  # the triple with an unbound variable is skipped


def test_ox_t5_select_returns_bound_variables_only_and_remove_graph_empties_one_graph():
    store = OxigraphStore()
    store.add(iri("urn:a"), iri("urn:p"), literal(1), iri("urn:g"))
    store.add(iri("urn:a"), iri("urn:p"), literal(2))
    rows = store.select("SELECT ?o ?missing WHERE { GRAPH <urn:g> { $s <urn:p> ?o } OPTIONAL { ?s <urn:none> ?missing } }", {"s": iri("urn:a")})
    assert rows == [{"o": literal(1)}]
    store.remove_graph(iri("urn:g"))
    assert store.quads(iri("urn:g")) == [] and len(store.quads(ox.DefaultGraph())) == 1


def _p1_kept(rows: str) -> bool:
    store = ox.Store()
    triple = ox.Quad(ox.NamedNode("urn:s"), ox.NamedNode("urn:p"), ox.NamedNode("urn:o"), ox.NamedNode("urn:g"))
    store.add(triple)
    store.update(
        "DELETE { GRAPH <urn:g> { ?d <urn:p> <urn:o> } } INSERT { GRAPH <urn:g> { ?i <urn:p> <urn:o> } } "
        f"WHERE {{ VALUES (?i ?d) {{ {rows} }} }}"
    )
    return triple in store


def test_ox_t6_each_version_flag_says_what_the_installed_pyoxigraph_does():
    """The flags are read from the version number. This holds them to the behaviour, so a later release that changes either again fails here
    and the triple-store record is revisited (TSD-01, TSD-17)."""
    from lattice_testing_oxigraph import LEFT_GROUPED_ARITHMETIC, SNAPSHOT_UPDATES, VERSION

    assert len(VERSION) == 3 and all(isinstance(n, int) for n in VERSION)
    snapshot = _p1_kept("(<urn:s> UNDEF) (UNDEF <urn:s>)") and _p1_kept("(UNDEF <urn:s>) (<urn:s> UNDEF)")
    assert snapshot is SNAPSHOT_UPDATES
    value = int(next(iter(ox.Store().query("SELECT (10 - 3 + 2 AS ?x) WHERE {}")))["x"].value)
    assert (value == 9) is LEFT_GROUPED_ARITHMETIC
