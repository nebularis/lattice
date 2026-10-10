# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""Checks for the spike. Not part of any ``mise`` task. Run from the repository root with:

    python -m pytest spikes/persistence-aggregate-ownership -q
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import concurrency_model as cm  # noqa: E402
import payload_graph  # noqa: E402
import placement as pl  # noqa: E402

EX = pl.EX
TABLE = cm.matrix()
D0, D1, D2, D3, D4 = (d.name for d in cm.DISCIPLINES)


def names(result) -> set[str]:
    return set(result.short())


# ---- which nodes a delete takes

def test_the_first_property_alone_reaches_only_the_tower():
    # the compiler before H1.4a (review S1). Since H1.4a it refuses this shape
    g = pl.placement_graph()
    assert names(pl.first_property_path(g)) == {"T"}  # sorts before marketsContacted; none of the layers: hasLayer is not followed either


def test_the_per_class_tree_takes_the_tower_the_markets_and_the_owned_document_only():
    g = pl.placement_graph()
    got = names(pl.unrolled_paths(g))
    assert {"T", "L1", "L2", "L3", "LCB1", "S1", "Mc1", "Mc2", "DocOwned"} <= got
    assert got.isdisjoint({"C", "Axa", "Chubb", "TypeCarrier", "PolBound", "DocShared", "Pol1"})
    assert len(pl.unrolled_paths(g).members) == 11  # a policy is a reference (AO-Q1)


def test_the_tree_as_sparql_paths_equals_the_typed_walk():
    g = pl.placement_graph()
    assert pl.unrolled_sparql(g).members == pl.unrolled_paths(g).members


def test_a_flat_alternation_cannot_tell_an_owned_attachment_from_a_shared_one():
    g = pl.placement_graph()
    flat = names(pl.flat_alternation(g))
    assert {"DocOwned", "DocShared"} <= flat  # takes the shared library wording with it


def test_a_deny_list_that_forgets_one_reference_takes_other_peoples_data():
    g = pl.placement_graph()
    forgot = pl.deny_list(g, references=pl.REFERENCES_FORGETTING_ONE)
    assert {EX.Axa, EX.Chubb} <= forgot.members


def test_a_vocabulary_guard_catches_a_forgotten_vocabulary_link():
    g = pl.placement_graph()
    forgot = pl.REFERENCES - {EX.marketType, EX.status, EX.connectsPolicy}
    assert pl.vocabulary_hit(g, pl.deny_list(g, references=forgot)) == {EX.TypeCarrier, EX.PolBound}
    assert pl.vocabulary_hit(g, pl.deny_list(g, references=forgot, guard_vocabulary=True)) == set()


def test_the_guard_does_not_help_with_an_ordinary_entity():
    g = pl.placement_graph()
    assert not pl.is_vocabulary(g, EX.Axa) and not pl.is_vocabulary(g, EX.C)


def test_a_delete_set_holds_the_outgoing_triples_of_the_root_and_every_member():
    g = pl.placement_graph()
    result = pl.unrolled_paths(g)
    triples = pl.delete_set(g, result)
    assert (EX.P, EX.forClient, EX.C) in triples  # the edge goes, the client stays
    assert not any(s == EX.C for s, _, _ in triples)
    assert not any(s in {EX.TypeCarrier, EX.PolBound} for s, _, _ in triples)


def test_a_shared_policy_is_a_reference_so_it_has_no_second_owner():
    g = pl.placement_graph(shared_policy=True, inbound_quote=True)
    assert pl.owners(g, [EX.P, EX.P2]) == {}
    assert pl.inbound_from_outside(g, pl.unrolled_paths(g)) == set()


def test_a_document_owned_by_layers_of_two_placements_has_two_owners():
    g = pl.placement_graph(shared_document=True)
    assert pl.owners(g, [EX.P, EX.P2]) == {EX.DocOwned: {EX.P, EX.P2}}
    assert {s for s, _, _ in pl.inbound_from_outside(g, pl.unrolled_paths(g))} == {EX.L9}


# ---- two writers

def cell(pair: str, discipline: str) -> str:
    return TABLE[pair][discipline].label()


def test_today_every_pair_meets_on_the_root_row_including_independent_ones():
    for pair in TABLE:
        assert cell(pair, D0) == "one conflicts" or cell(pair, D0) == "refused", pair
    assert cell("root edit  vs deep edit", D0) == "one conflicts"


def test_one_row_per_level_lets_independent_edits_commit():
    for pair in ("root edit  vs deep edit", "deep edit  vs deep edit, other branch", "remove L1  vs edit in L2"):
        assert cell(pair, D1) == "both commit", pair


def test_one_row_per_level_loses_a_deep_write_to_a_removal_above_it():
    assert cell("remove L1  vs deep edit below L1", D1) == "ANOMALY orphan"
    assert cell("delete root vs deep edit", D1) == "ANOMALY orphan"


def test_marking_the_sub_units_on_removal_closes_it_and_keeps_independent_edits_free():
    assert cell("remove L1  vs deep edit below L1", D2) == "one conflicts"
    assert cell("delete root vs deep edit", D2) == "one conflicts"
    assert cell("root edit  vs deep edit", D2) == "both commit"
    assert cell("remove L1  vs edit in L2", D2) == "both commit"


def test_touching_every_ancestor_closes_it_by_making_every_pair_conflict():
    assert cell("root edit  vs deep edit", D3) == "one conflicts"
    assert cell("deep edit  vs deep edit, other branch", D3) == "one conflicts"


def test_a_cross_level_invariant_is_broken_by_per_level_rows_and_needs_its_own_row():
    pair = "two bindings, limit of 3 (L1 / L2)"
    assert cell(pair, D1) == cell(pair, D2) == "ANOMALY invariant"
    assert cell(pair, D4) == "one conflicts"
    assert cell("root edit  vs deep edit", D4) == "both commit"


def test_same_unit_edits_always_meet():
    for d in cm.DISCIPLINES:
        assert cell("deep edit  vs deep edit, same unit", d.name) == "one conflicts"


# ---- the payload

def test_the_composite_replace_writes_the_new_payload_to_the_data_graph():
    found = payload_graph.payload_destination()
    assert list(found) == ["urn:g:orders"]
