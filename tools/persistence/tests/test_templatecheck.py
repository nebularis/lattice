# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H1.3: static S-3 and S-4 checks over the generated SPARQL (formal-methods
track H). Validation Pack: docs/developer/validation/FMH-H1-3.md. Test IDs are H1.3-Tn."""

from __future__ import annotations

import collections
import functools

import pytest

from persistence import templatecheck as tc
from persistence import witness
from persistence.cli import main
from persistence.compiler import CompileError, compile_to_graph
from persistence.hygiene import VIOLATION

from conftest import EXAMPLES_DIR, SPEC_TTL

H = "PREFIX p: <https://example.org/p#>\n"


def _checks(update: str) -> list[tuple[str, str]]:
    return [(i.check, i.variable) for i in tc.analyse(H + update)]


# ---- S-3: variables an INSERT template uses -------------------------------------------------------


def test_h1_3_t1_variables_bound_in_every_solution_are_clean():
    assert _checks("INSERT { <urn:a> p:a ?x ; p:b ?y } WHERE { ?s p:c ?x ; p:d ?y }") == []


def test_h1_3_t2_a_variable_bound_only_in_an_optional_is_reported_by_name():
    assert _checks("INSERT { <urn:a> p:a ?x } WHERE { ?s p:b ?y OPTIONAL { ?s p:c ?x } }") == [("S-3", "x")]


def test_h1_3_t3_a_dollar_parameter_is_bound_by_the_caller():
    assert _checks("INSERT { <urn:a> p:a $x } WHERE { ?s p:b ?y }") == []


def test_h1_3_t4_a_bind_counts_only_when_its_inputs_are_bound():
    assert _checks("INSERT { <urn:a> p:a ?x } WHERE { ?s p:b ?y BIND(STR(?y) AS ?x) }") == []
    assert _checks("INSERT { <urn:a> p:a ?x } WHERE { ?s p:b ?y BIND(STR(?z) AS ?x) }") == [("S-3", "x")]


def test_h1_3_t5_a_union_binds_a_variable_only_if_both_branches_do():
    assert _checks("INSERT { <urn:a> p:a ?x } WHERE { { ?s p:b ?x } UNION { ?s p:c ?x } }") == []
    assert _checks("INSERT { <urn:a> p:a ?x } WHERE { { ?s p:b ?x } UNION { ?s p:c ?y } }") == [("S-3", "x")]


def test_h1_3_t6_values_binds_unless_a_row_is_undef():
    assert _checks("INSERT { <urn:a> p:a ?x } WHERE { VALUES ?x { 1 2 } }") == []
    assert _checks("INSERT { <urn:a> p:a ?x } WHERE { VALUES ?x { 1 UNDEF } }") == [("S-3", "x")]


def test_h1_3_t7_a_group_by_subselect_is_understood():
    assert _checks(
        "INSERT { ?o p:m ?c } WHERE { { SELECT ?k (MIN(?v) AS ?c) WHERE { ?k p:by ?v } GROUP BY ?k "
        "HAVING (COUNT(?v) > 1) } ?k p:by ?o }"
    ) == []


def test_h1_3_t8_a_construct_it_cannot_analyse_is_reported_and_never_passed():
    ((check, _),) = _checks("INSERT { <urn:a> p:a ?x } WHERE { SERVICE <urn:svc> { ?s p:b ?x } }")
    assert check == "S-3"
    assert "cannot analyse" in tc.analyse(H + "INSERT { <urn:a> p:a ?x } WHERE { SERVICE <urn:svc> { ?s p:b ?x } }")[0].message


# ---- S-4: blank nodes ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "update",
    [
        "INSERT { GRAPH <urn:g> { [] p:a ?x } } WHERE { ?s p:b ?x }",
        "INSERT { GRAPH <urn:g> { _:b p:a ?x } } WHERE { ?s p:b ?x }",
        "INSERT DATA { GRAPH <urn:g> { _:b p:a 1 } }",
    ],
    ids=["anonymous", "labelled", "insert-data"],
)
def test_h1_3_t9_a_blank_node_in_an_insert_template_is_reported(update):
    assert [check for check, _ in _checks(update)] == ["S-4"]


def test_h1_3_t10_a_blank_node_in_a_delete_template_is_reported():
    issues = tc.analyse(H + "DELETE { GRAPH <urn:g> { _:b p:a ?x } } WHERE { ?s p:b ?x }")
    assert [i.check for i in issues] == ["S-4"] and "DELETE" in issues[0].message


def test_h1_3_t11_a_blank_node_in_the_where_clause_is_fine():
    assert _checks("INSERT { <urn:a> p:a ?x } WHERE { [] p:b ?x }") == []


# ---- other cases -----------------------------------------------------------------------------------


def test_h1_3_t12_a_read_only_audit_has_no_templates_and_a_broken_update_does_not_parse():
    assert _checks("SELECT ?s WHERE { ?s p:a ?o }") == []
    assert [i.check for i in tc.analyse("INSERT { oops")] == ["S-0"]


# ---- allowances ------------------------------------------------------------------------------------

OPTIONAL_UPDATE = "INSERT { <urn:a> p:a ?x ; p:b ?y } WHERE { ?s p:c ?z OPTIONAL { ?s p:d ?x } OPTIONAL { ?s p:e ?y } }"


def test_h1_3_t13_an_allowance_excuses_only_the_named_variable_of_the_named_template():
    allow = {"t": {"x": "first write has no previous value"}}
    names = lambda template: sorted(f.message.split("?")[1].split(",")[0] for f in tc.check_text(H + OPTIONAL_UPDATE, template, "L", allow))
    assert names("t") == ["y"]
    assert names("other") == ["x", "y"]


def test_h1_3_t14_an_allowance_for_a_variable_nothing_leaves_unbound_is_stale():
    stale = tc.stale_allowances({"t": {"y"}}, {"t": {"x": "r", "y": "r"}, "gone": {"z": "r"}})
    assert sorted(f.message.split(":")[0] for f in stale) == ["gone", "t"]
    assert tc.stale_allowances({"t": {"x"}}, {"t": {"x": "r"}}) == []


def test_h1_3_t15_every_shipped_allowance_has_a_reason():
    assert tc.OPTIONAL_INSERT_VARIABLES
    assert all(reason.strip() for variables in tc.OPTIONAL_INSERT_VARIABLES.values() for reason in variables.values())


# ---- the real templates ----------------------------------------------------------------------------


@functools.lru_cache(maxsize=1)
def _compiled_corpus() -> tuple:
    """Every fixture that compiles, compiled once for the whole module."""
    out = []
    for path in witness.compile_fixtures():
        try:
            compiled, _ = compile_to_graph(witness._load_fixture(path))
        except CompileError:
            continue
        out.append((path.name, compiled))
    return tuple(out)


def test_h1_3_t16_every_template_the_compiler_can_generate_is_checked_by_some_fixture():
    generated = {op.template for _, compiled in _compiled_corpus() for op in tc.operations(compiled)}
    library = {p.name.removesuffix(".mustache") for p in witness.TEMPLATE_DIR.glob("*.mustache")}
    assert library == generated, f"never generated by any fixture: {sorted(library - generated)}"


def test_h1_3_t17_no_generated_operation_in_the_corpus_has_an_s3_or_s4_finding():
    findings = [(name, f) for name, compiled in _compiled_corpus() for f in tc.check_compiled(compiled)]
    assert findings == [], "\n".join(f"{name}: {f}" for name, f in findings)


def test_h1_3_t18_no_allowance_in_the_shipped_list_is_stale_across_the_corpus():
    unbound: dict[str, set[str]] = collections.defaultdict(set)
    for _, compiled in _compiled_corpus():
        for template, variables in tc.unbound_by_template(compiled).items():
            unbound[template] |= variables
    assert tc.stale_allowances(unbound) == []


def _real_text(template: str) -> str:
    """A real generated update, as the first fixture that uses its template produces it."""
    for _, compiled in _compiled_corpus():
        for op in tc.operations(compiled):
            if op.template == template:
                return op.text
    raise AssertionError(template)


def test_h1_3_t19_a_variable_seeded_unbound_in_a_copy_of_a_real_template_is_reported_by_name():
    """The plan's seeded check. The real templates are untouched."""
    text = _real_text("cas-replace-named-graph")
    assert "BIND(NOW() AS ?now)" in text
    seeded = text.replace("BIND(NOW() AS ?now)", "")
    assert tc.check_text(text, "cas-replace-named-graph", "real") == []
    findings = tc.check_text(seeded, "cas-replace-named-graph", "seeded")
    assert len(findings) == 1 and "?now" in findings[0].message


def test_h1_3_t20_a_blank_node_seeded_into_a_copy_of_a_real_template_is_reported():
    text = _real_text("cas-replace-named-graph")
    seeded = text.replace("$newRev a pat:Revision ;", "[] a pat:Revision ;", 1)
    assert seeded != text
    findings = tc.check_text(seeded, "cas-replace-named-graph", "seeded")
    assert any(f.check == "S-4" for f in findings)


# ---- the command -----------------------------------------------------------------------------------


def test_h1_3_t21_hygiene_runs_the_template_checks_when_the_configuration_compiles(capsys):
    assert main(["hygiene", str(SPEC_TTL), str(EXAMPLES_DIR / "baseline-single-class.ttl")]) == 0
    assert "templates:" in capsys.readouterr().err


def test_h1_3_t22_hygiene_says_so_when_it_cannot_compile_and_so_cannot_check_templates(capsys):
    assert main(["hygiene", str(SPEC_TTL), str(EXAMPLES_DIR / "invalid-lagwindow-missing.ttl")]) == 0
    assert "templates: not checked" in capsys.readouterr().err


def test_h1_3_t23_hygiene_exits_one_when_a_template_check_fails(monkeypatch, capsys):
    monkeypatch.setattr(tc, "OPTIONAL_INSERT_VARIABLES", {})
    assert main(["hygiene", str(SPEC_TTL), str(EXAMPLES_DIR / "baseline-single-class.ttl")]) == 1
    assert "S-3" in capsys.readouterr().out
