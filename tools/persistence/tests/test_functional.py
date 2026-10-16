# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""TD-25 (formal-methods track H, H1.2d): a single-valued ``dal:`` property
with two values is refused, never resolved by triple order. Validation Pack:
docs/developer/validation/FMH-H1-2d.md. Test IDs are H1.2d-Tn."""

from __future__ import annotations

import ast

import pytest
from rdflib import Graph, Literal, URIRef

from persistence.cli import main
from persistence.compiler import CompileError, compile_targets
from persistence.functional import functional_value
from persistence.model import CrossAxisViolation

from conftest import EXAMPLES_DIR, SPEC_TTL
from test_architecture import SRC

PREFIXES = """
@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .
@prefix ex:  <https://example.org/lending#> .
"""
EX = "https://example.org/lending#"
KIND = "MultiValuedFunctionalProperty"


def _graph(body: str) -> Graph:
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(data=PREFIXES + body, format="turtle")
    return g


def _refusal(body: str) -> CrossAxisViolation:
    with pytest.raises(CompileError) as error:
        compile_targets(_graph(body))
    assert isinstance(error.value.cause, CrossAxisViolation)
    return error.value.cause


def _competing_scopes(priorities: str) -> str:
    return f"""
    ex:A a dal:ClassScope ; dal:targetClass ex:Thing ; dal:priority {priorities} .
    ex:B a dal:ClassScope ; dal:targetClass ex:Thing ; dal:priority 2 .
    ex:PA a dal:ConcurrencyProfile ; dal:appliesTo ex:A ; dal:concurrencyProfile dal:Optimistic .
    ex:PB a dal:ConcurrencyProfile ; dal:appliesTo ex:B ; dal:concurrencyProfile dal:ProvidedConcurrency .
    """


def test_h1_2d_t1_the_helper_returns_the_one_value_none_or_refuses_a_second():
    g = Graph()
    s, p = URIRef(EX + "s"), URIRef(EX + "p")
    assert functional_value(g, s, p) is None
    assert functional_value(g, None, p) is None
    g.add((s, p, Literal(1)))
    assert functional_value(g, s, p) == Literal(1)
    g.add((s, p, Literal(3)))
    with pytest.raises(CrossAxisViolation) as error:
        functional_value(g, s, p)
    assert error.value.kind == KIND and "'1', '3'" in str(error.value)


def test_h1_2d_t2_the_refusal_names_the_subject_the_property_and_the_values():
    cause = _refusal(_competing_scopes("1, 3"))
    assert cause.kind == KIND
    assert cause.target == EX + "A"
    assert "priority" in str(cause) and "'1', '3'" in str(cause)


@pytest.mark.parametrize("order", ["1, 3", "3, 1"])
def test_h1_2d_t3_the_outcome_does_not_depend_on_the_order_the_values_were_written_in(order):
    """TD-25: before, '1, 3' resolved to ProvidedConcurrency and '3, 1' to Optimistic."""
    assert str(_refusal(_competing_scopes(order))) == str(_refusal(_competing_scopes("1, 3")))


def test_h1_2d_t4_a_single_priority_still_resolves_as_before():
    (ct,) = compile_targets(_graph(_competing_scopes("1").replace("dal:priority 1", "dal:priority 3")))
    assert str(ct.dimensions["concurrencyProfile"].value).endswith("Optimistic")


def test_h1_2d_t5_a_profile_with_two_values_for_its_own_dimension_is_refused():
    body = """
    ex:S a dal:ClassScope ; dal:targetClass ex:Thing .
    ex:P a dal:ConcurrencyProfile ; dal:appliesTo ex:S ;
        dal:concurrencyProfile dal:Optimistic, dal:ProvidedConcurrency .
    """
    assert _refusal(body).kind == KIND


def test_h1_2d_t6_a_scope_attribute_with_two_values_is_refused():
    body = """
    ex:S a dal:NamespaceScope ; dal:iriPrefix "https://a.example/", "https://b.example/" .
    ex:C a dal:ClassScope ; dal:targetClass ex:Thing .
    ex:P a dal:ConcurrencyProfile ; dal:appliesTo ex:S ; dal:concurrencyProfile dal:Optimistic .
    """
    # a scope no profile refers to is never read, so it cannot change the output
    assert _refusal(body).kind == KIND


def test_h1_2d_t7_a_uniqueness_constraint_naming_two_scopes_is_refused_not_silently_narrowed():
    """TD-15 used to apply such a constraint to one scope without a word. It is now refused."""
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(EXAMPLES_DIR / "uniqueness-merge-policy.ttl", format="turtle")
    constraint = next(g.subjects(URIRef("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), URIRef(
        "https://www.nebularis.org/neuro-semantic/lattice/persistence#UniquenessConstraint")))
    other = URIRef(EX + "SecondScope")
    g.parse(data=PREFIXES + "ex:SecondScope a dal:ClassScope ; dal:targetClass ex:Elsewhere .", format="turtle")
    g.add((constraint, URIRef("https://www.nebularis.org/neuro-semantic/lattice/persistence#appliesTo"), other))
    with pytest.raises(CompileError) as error:
        compile_targets(g)
    assert error.value.cause.kind == KIND


def test_h1_2d_t8_a_recipe_member_with_two_values_is_refused():
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(EXAMPLES_DIR / "identity-minting-anchors.ttl", format="turtle")
    g.add((URIRef(EX + "ProductIdentity"), URIRef(
        "https://www.nebularis.org/neuro-semantic/lattice/persistence#mintedIriTemplate"), Literal("urn:ex:other:{digest}")))
    with pytest.raises(CompileError) as error:
        compile_targets(g)
    assert error.value.cause.kind == KIND


def test_h1_2d_t9_every_shipped_example_still_compiles_or_is_refused_as_before():
    """None of the shipped examples has a multi-valued single-valued property."""
    for path in sorted(EXAMPLES_DIR.glob("*.ttl")):
        g = Graph()
        g.parse(SPEC_TTL, format="turtle")
        if path.name == "capability-spec-example.ttl":
            g.parse(EXAMPLES_DIR / "baseline-single-class.ttl", format="turtle")
        g.parse(path, format="turtle")
        try:
            compile_targets(g)
        except CompileError as error:
            assert getattr(error.cause, "kind", "") != KIND, path.name


def test_h1_2d_t10_the_cli_reports_the_refusal_and_exits_one(tmp_path, capsys):
    config = tmp_path / "multi.ttl"
    config.write_text(PREFIXES + _competing_scopes("1, 3"))
    code = main(["compile", str(SPEC_TTL), str(config), "--out", str(tmp_path / "out.ttl")])
    assert code == 1
    assert "MultiValuedFunctionalProperty" in capsys.readouterr().err


def _dal_reads_through_graph_value() -> list[str]:
    """Calls ``<graph>.value(subject, DAL.x)`` or with a variable predicate in
    the compile path, other than reads of the compiler's own output."""
    offenders: list[str] = []
    for name in ("scopes", "resolver", "capability", "validator", "recipes"):
        tree = ast.parse((SRC / f"{name}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "value"):
                continue
            receiver = ast.unparse(node.func.value)
            if receiver in {"compiled", "compiled_profile", "out"} or len(node.args) < 2:
                continue
            predicate = ast.unparse(node.args[1])
            if predicate.startswith("DAL.") or predicate in {"prop", "value_prop"}:
                offenders.append(f"{name}.py:{node.lineno} {receiver}.value(..., {predicate})")
    return offenders


def test_h1_2d_t11_no_dal_property_in_the_compile_path_is_read_with_graph_value():
    """A bare ``Graph.value`` returns whichever triple comes first. Reads of a
    dal: property go through ``functional_value`` (TD-25)."""
    assert _dal_reads_through_graph_value() == []
