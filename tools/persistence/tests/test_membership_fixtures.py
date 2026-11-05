# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.6f: the TriG fixtures of E5 and E7 under each membership encoding are what the operations write now, and their stored triples have the
counts the plan states (EX-Q2 (b)). Validation Pack: docs/developer/validation/FMH-H2-6f.md. Test IDs are H2.6f-Fn."""

from __future__ import annotations

import pytest
from rdflib import RDF, Dataset, URIRef

import membership_fixtures as mf

HEADER = {RDF.type, URIRef(mf.PAT + "revision")}


def _data(name: str) -> set:
    ds = Dataset()
    ds.parse(mf.OUT_DIR / name, format="trig")
    return {t for t in ds.graph(mf.DATA)}


def _state(triples: set, n: int) -> set:
    return {t for t in triples if t[0] == mf.version(n) and t[1] not in HEADER}


def test_h2_6f_f1_the_fixture_files_are_what_the_operations_write_now():
    stale = [n for n, t in mf.files().items() if (mf.OUT_DIR / n).read_text(encoding="utf-8") != t]
    assert not stale, f"run mise run build:persistence-membership-fixtures: {stale}"


@pytest.mark.parametrize("scenario,size", sorted(mf.SCENARIOS.items()))
def test_h2_6f_f2_one_change_costs_three_triples_under_delta_and_a_full_list_under_full(scenario, size):
    full, delta = _data(f"{scenario}-full.trig"), _data(f"{scenario}-delta.trig")
    # version 1 is a checkpoint under both: the type, the receipt link, size members and pat:checkpoint
    assert len(_state(full, 1)) == len(_state(delta, 1)) == size + 1
    assert len(_state(delta, 2)) == 3  # previousVersion, addsMember, dropsMember
    assert len(_state(full, 2)) == size + 1  # size members and previousVersion
    assert len(full) - len(delta) == size + 1 - 3  # nothing else differs
    assert len(delta) == 2 * 2 + size + 1 + 3  # two headers, the checkpoint's list and marker, the delta
    assert not [t for t in delta if t[0] == mf.version(2) and t[1] == mf.MEMBER]
