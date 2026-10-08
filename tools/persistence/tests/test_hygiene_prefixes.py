# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H1.1: the prefix antichain and overlap check (formal-methods track H).

Validation Pack: docs/developer/validation/FMH-H1-1.md. Test IDs are H1.1-Tn.
"""

from __future__ import annotations

import pytest
from rdflib import Graph

from persistence.cli import main
from persistence.hygiene import VIOLATION, WARNING, check_prefix_antichain

from conftest import EXAMPLES_DIR, SPEC_TTL

PREAMBLE = """
@prefix dal: <https://www.nebularis.org/neuro-semantic/lattice/persistence#> .
@prefix ex:  <https://example.org/cfg#> .
"""


def _graph(body: str) -> Graph:
    g = Graph()
    g.parse(data=PREAMBLE + body, format="turtle")
    return g


def _graph_scope(name: str, prefix: str, covers: str) -> str:
    return f'ex:{name} a dal:GraphPatternScope ; dal:graphPrefix "{prefix}" ; dal:coversClass ex:{covers} .\n'


def _ns_scope(name: str, prefix: str) -> str:
    return f'ex:{name} a dal:NamespaceScope ; dal:iriPrefix "{prefix}" .\n'


def test_h1_1_t1_nested_graph_prefixes_over_one_class_are_a_violation():
    g = _graph(
        _graph_scope("Outer", "urn:g:lending/", "Behaviour") + _graph_scope("Inner", "urn:g:lending/behaviour/", "Behaviour")
    )
    (finding,) = check_prefix_antichain(g)
    assert finding.severity == VIOLATION
    assert set(finding.subjects) == {"https://example.org/cfg#Outer", "https://example.org/cfg#Inner"}
    # the counterexample lies under both prefixes
    assert finding.counterexample.startswith("urn:g:lending/behaviour/")
    assert finding.counterexample.startswith("urn:g:lending/")
    assert "Behaviour" in finding.message


def test_h1_1_t2_nested_graph_prefixes_over_disjoint_classes_are_not_a_finding():
    g = _graph(
        _graph_scope("Outer", "urn:g:lending/", "Loan") + _graph_scope("Inner", "urn:g:lending/behaviour/", "Behaviour")
    )
    assert check_prefix_antichain(g) == []


def test_h1_1_t3_disjoint_graph_prefixes_form_an_antichain():
    g = _graph(
        _graph_scope("Lending", "urn:g:lending/behaviour/", "Behaviour")
        + _graph_scope("Credit", "urn:g:credit/behaviour/", "Behaviour")
    )
    assert check_prefix_antichain(g) == []


def test_h1_1_t4_identical_graph_prefixes_over_one_class_are_a_violation():
    g = _graph(_graph_scope("A", "urn:g:x/", "Behaviour") + _graph_scope("B", "urn:g:x/", "Behaviour"))
    (finding,) = check_prefix_antichain(g)
    assert finding.severity == VIOLATION
    assert "equals" in finding.message


def test_h1_1_t5_prefixes_that_only_share_leading_characters_are_not_nested():
    g = _graph(_graph_scope("A", "urn:g:lend/", "Behaviour") + _graph_scope("B", "urn:g:lending/", "Behaviour"))
    assert check_prefix_antichain(g) == []


def test_h1_1_t6_one_shared_class_among_several_is_enough():
    g = _graph(
        "ex:Outer a dal:GraphPatternScope ; dal:graphPrefix \"urn:g:a/\" ; dal:coversClass ex:One, ex:Two .\n"
        "ex:Inner a dal:GraphPatternScope ; dal:graphPrefix \"urn:g:a/b/\" ; dal:coversClass ex:Two, ex:Three .\n"
    )
    (finding,) = check_prefix_antichain(g)
    assert finding.severity == VIOLATION
    assert "cfg#Two" in finding.message
    assert "cfg#One" not in finding.message and "cfg#Three" not in finding.message


def test_h1_1_t7_nested_iri_prefixes_are_a_warning_not_a_violation():
    g = _graph(_ns_scope("Wide", "https://example.org/") + _ns_scope("Narrow", "https://example.org/lending#"))
    (finding,) = check_prefix_antichain(g)
    assert finding.severity == WARNING
    assert finding.counterexample == "https://example.org/lending#"
    assert "dal:priority" in finding.message


def test_h1_1_t8_disjoint_iri_prefixes_are_clean():
    g = _graph(_ns_scope("A", "https://example.org/a#") + _ns_scope("B", "https://example.org/b#"))
    assert check_prefix_antichain(g) == []


def test_h1_1_t9_a_scope_without_a_prefix_cannot_overlap():
    g = _graph(
        "ex:Bare a dal:GraphPatternScope ; dal:coversClass ex:Behaviour .\n" + _graph_scope("A", "urn:g:x/", "Behaviour")
    )
    assert check_prefix_antichain(g) == []


def test_h1_1_t10_the_report_is_independent_of_declaration_order():
    forward = _graph(
        _graph_scope("A", "urn:g:x/", "C") + _graph_scope("B", "urn:g:x/y/", "C") + _graph_scope("D", "urn:g:x/y/z/", "C")
    )
    backward = _graph(
        _graph_scope("D", "urn:g:x/y/z/", "C") + _graph_scope("B", "urn:g:x/y/", "C") + _graph_scope("A", "urn:g:x/", "C")
    )
    assert check_prefix_antichain(forward) == check_prefix_antichain(backward)
    assert len(check_prefix_antichain(forward)) == 3


@pytest.mark.parametrize("example", sorted(p.name for p in EXAMPLES_DIR.glob("*.ttl")))
def test_h1_1_t11_no_shipped_example_has_a_prefix_violation(example):
    g = Graph()
    g.parse(SPEC_TTL, format="turtle")
    g.parse(EXAMPLES_DIR / example, format="turtle")
    assert [f for f in check_prefix_antichain(g) if f.severity == VIOLATION] == []


def test_h1_1_t12_cli_exits_nonzero_and_names_the_pair_on_a_violation(tmp_path, capsys):
    cfg = tmp_path / "overlap.ttl"
    cfg.write_text(
        PREAMBLE + _graph_scope("Outer", "urn:g:lending/", "Behaviour") + _graph_scope("Inner", "urn:g:lending/behaviour/", "Behaviour")
    )
    assert main(["hygiene", str(cfg)]) == 1
    out = capsys.readouterr().out
    assert "Outer" in out and "Inner" in out and "counterexample" in out


def test_h1_1_t13_cli_exits_zero_on_a_clean_configuration_and_on_warnings_only(tmp_path):
    clean = tmp_path / "clean.ttl"
    clean.write_text(PREAMBLE + _graph_scope("A", "urn:g:a/", "C") + _graph_scope("B", "urn:g:b/", "C"))
    assert main(["hygiene", str(clean)]) == 0
    warn = tmp_path / "warn.ttl"
    warn.write_text(PREAMBLE + _ns_scope("Wide", "https://example.org/") + _ns_scope("Narrow", "https://example.org/x#"))
    assert main(["hygiene", str(warn)]) == 0
