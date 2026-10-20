# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The expected compiled profiles are what `compile` emits (formal-methods track H, slices H2.6 and H2.7, plan 4.4 and 4.7).
The files are under ontology/persistence/test/expected-profiles/ and are produced by `expected_profiles.py`. Since H2.7 they are compared
with the output of `compile` by graph isomorphism (H2.7-Q4), which replaced H2.6's base-profile and agreement tests. Validation Packs:
docs/developer/validation/FMH-H2-6.md and FMH-H2-7.md. Test IDs are H2.6-Tn and H2.7-Tn."""

from __future__ import annotations

import dataclasses
import random
import re
from pathlib import Path

import pytest
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.compare import isomorphic

import expected_profiles as ep
from persistence import witness
from persistence.builders import BUILDERS, build
from persistence.contract import DATASET_GUARD_SUFFIX, HAND_DECLARED, AccessContract, DeclarationSource, contract_of
from persistence.ir import SLOT_KINDS
from persistence.namespaces import DAL

from test_builders import _first

FILES = sorted(ep.OUT_DIR.glob("*.expected.ttl"))
CONFIG = {name: (example, options) for name, example, options in ep.CONFIGURATIONS}


def _name(path: Path) -> str:
    return path.name.removesuffix(".expected.ttl")


@pytest.fixture(scope="module")
def parsed() -> dict:
    return {_name(p): Graph().parse(p, format="turtle") for p in FILES}


# ---- the files ---------------------------------------------------------------------------------------------------------


def test_h2_6_t1_the_expected_profiles_exist_and_parse_and_carry_no_template_path_and_no_suffix(parsed):
    """Since H2.7 there is no `kinds.expected.ttl`: the enumerations are individuals of the spec."""
    assert len(FILES) == len(ep.CONFIGURATIONS) == 12 and set(parsed) == set(CONFIG)
    assert all(len(g) > 0 for g in parsed.values())
    assert not any(str(p).endswith("#templatePath") for g in parsed.values() for _, p, _ in g)  # dal:templatePath is gone
    ids = [str(o) for g in parsed.values() for o in g.objects(None, DAL.templateId)]
    assert ids and not any(i.endswith(".mustache") for i in ids)  # the builder's identity, not a file name


def test_h2_6_t2_no_declaration_holds_a_blank_node_or_sparql_text(parsed):
    """The rules the shapes enforce (`test_contract_shapes.py`), checked here once over the files without a validator."""
    checked = 0
    for name, graph in parsed.items():
        for s, p, o in graph:
            if not (ep.is_declaration(s) or p in ep.NEW_PREDICATES):
                continue
            assert not isinstance(o, BNode), (name, s, p)
            if ep.is_declaration(s):
                assert isinstance(s, URIRef)
            if isinstance(o, Literal):
                assert re.fullmatch(r"[A-Za-z0-9 ._-]*", str(o)), (name, s, p, str(o))  # a name, a number or a separator, never a query
            checked += 1
    assert checked > 1000


# ---- the emitted profile is the expected profile -------------------------------------------------------------------------


@pytest.mark.parametrize("path", FILES, ids=_name)
def test_h2_7_t1_the_profile_compile_emits_is_isomorphic_to_the_expected_file(path, parsed):
    """Isomorphic and not byte identical (H2.7-Q4): parsing gives a blank node a fresh label, and an editor lays a file out as it likes.
    A change to `compile` output regenerates the files in the same commit (`mise run build:persistence-expected-profiles`)."""
    example, options = CONFIG[_name(path)]
    assert isomorphic(parsed[_name(path)], ep.emit(example, **options)), f"{path.name} is stale: mise run build:persistence-expected-profiles"


def test_h2_7_t2_no_operation_is_declared_by_hand_since_every_operation_has_a_builder(parsed):
    """TD-43 gave the value guard the last builder, so `HAND_DECLARED` is empty and every contract is derived."""
    assert HAND_DECLARED == {}
    sources = {str(o).rsplit("#", 1)[-1] for g in parsed.values() for o in g.objects(None, DAL.declarationSource)}
    assert sources == {"BuilderDerived"}
    g = parsed["value-based-cas"]
    ops = {str(o) for o in g.objects(None, DAL.forOperation)}
    assert "cas-replace" in ops


@pytest.mark.parametrize("stem", ["create-if-absent-composite", "cas-replace-composite-property", "tombstone-delete-composite"])
def test_h2_6_t6_a_composite_dataset_guard_variant_differs_from_its_base_by_the_dataset_read_alone(stem):
    """The expected profiles have no composite dataset-guard variant, so this is the claim that makes the omission acceptable."""
    _, _, _, context = _first(stem)
    base = contract_of(build(stem, context))
    variant = contract_of(build(stem + DATASET_GUARD_SUFFIX, context))
    assert set(variant.accesses) - set(base.accesses) == {AccessContract("DatasetEpoch", "PointRead", None)}
    assert set(base.accesses) <= set(variant.accesses)
    assert dataclasses.replace(variant, id=base.id, accesses=base.accesses) == base


# ---- the names ------------------------------------------------------------------------------------------------------------

_DOLLAR = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


@pytest.mark.parametrize("graph_names", ["query", "caller"])
@pytest.mark.parametrize("stem", sorted(BUILDERS))
def test_h2_6_t7_the_declared_parameter_names_are_the_dollar_names_of_the_rendered_query(stem, graph_names):
    from persistence.ir_render import render

    _, _, _, context = _first(stem)
    operation = build(stem, context, graph_names=graph_names)
    declared = {p.name for p in operation.params if p.kind not in SLOT_KINDS}
    text = re.sub(r"\{\{\{.*?\}\}\}", "", render(operation))
    assert declared == set(_DOLLAR.findall(text))
    assert {p.name for p in contract_of(operation).parameters} == {p.name for p in operation.params}


