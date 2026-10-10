# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""HO8: a named graph's IRI is injective in its root (formal-methods track H, slice HO8, ADR-A122
decision 8, technical debt TD-38).
Validation Pack: docs/developer/validation/FMH-HO8.md. Test IDs are HO8-Tn.

The generated create runs on rdflib's in-memory ``Dataset``. The expected graph IRI is computed here in
Python, with percent-encoding of every byte but the unreserved characters, which is what SPARQL's
``ENCODE_FOR_URI`` does."""

from __future__ import annotations

import warnings
from urllib.parse import quote

import pytest
from rdflib import RDF, Dataset, Graph, Literal, URIRef, Variable
from rdflib.namespace import XSD

from persistence import templatecheck, witness
from persistence.compiler import CompileError, compile_targets, compile_to_graph

from conftest import EXAMPLES_DIR

EX = "https://example.org/lending#"
DAL = "https://www.nebularis.org/neuro-semantic/lattice/persistence#"
PAT = "https://example.org/lattice/patterns#"
PROFILE = URIRef(EX + "LoanApplicationStrongProfile")


def _baseline(template: str | None = "urn:g:loan-application/{id}") -> Graph:
    graph = witness._load_fixture(EXAMPLES_DIR / "baseline-single-class.ttl")
    graph.remove((PROFILE, URIRef(DAL + "graphIriTemplate"), None))
    if template is not None:
        graph.add((PROFILE, URIRef(DAL + "graphIriTemplate"), Literal(template)))
    return graph


def _create(graph: Graph, template: str = "create-if-absent-named-graph") -> str:
    compiled, _ = compile_to_graph(graph)
    return next(o for o in templatecheck.operations(compiled) if o.template == template).text


def _graphs_after_creating(graph: Graph, roots: list[str], prefix: str = "urn:g:loan-application/") -> dict[str, set]:
    text = _create(graph).replace(templatecheck._SLOT_STAND_INS["payloadTriples"], "<urn:x:s> <urn:x:p> <urn:x:o> .")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ds = Dataset()
        for number, root in enumerate(roots):
            values = {
                "root": URIRef(root), "epoch": Literal(1), "newRev": URIRef(f"urn:rev:{number}"),
                "txnId": URIRef(f"urn:txn:{number}"), "requestDigest": Literal("d"),
            }
            ds.update(text.replace("<urn:x:s> <urn:x:p> <urn:x:o>", f"<{root}> <urn:x:p> <urn:x:o>"), initBindings={Variable(k): v for k, v in values.items()})
        out: dict[str, set] = {}
        for s, p, o, g in ds.quads((None, None, None, None)):
            name = str(getattr(g, "identifier", g))
            if name.startswith(prefix):
                out.setdefault(name, set()).add((s, p, o))
        return out


def _expected(prefix: str, root: str, suffix: str = "") -> str:
    return prefix + quote(root, safe="-._~") + suffix


def test_ho8_t1_two_roots_with_one_local_name_name_two_graphs():
    roots = ["https://example.org/a/1", "https://example.org/b/1"]
    graphs = _graphs_after_creating(_baseline(), roots)
    prefix = "urn:g:loan-application/"
    assert set(graphs) == {_expected(prefix, r) for r in roots}
    assert all(len(triples) == 1 for triples in graphs.values())


def test_ho8_t2_text_after_the_id_is_kept():
    graphs = _graphs_after_creating(_baseline("urn:g:loan-application/{id}/data"), ["https://example.org/a/1"])
    assert set(graphs) == {_expected("urn:g:loan-application/", "https://example.org/a/1", "/data")}


def test_ho8_t2b_a_root_with_reserved_characters_is_encoded_and_a_family_with_no_template_gets_a_token():
    root = "https://example.org/a?x=1#frag"
    graphs = _graphs_after_creating(_baseline(None), [root], prefix="urn:g:loanapplication/")
    assert set(graphs) == {_expected("urn:g:loanapplication/", root)}
    assert "?" not in next(iter(graphs)).removeprefix("urn:g:loanapplication/")


def _refusal(graph: Graph):
    with pytest.raises(CompileError) as error:
        compile_targets(graph)
    return error.value.cause


@pytest.mark.parametrize("template", ["urn:g:loan-application/all", "urn:g:{id}/{id}"])
def test_ho8_t3_a_template_without_exactly_one_id_is_refused(template):
    assert _refusal(_baseline(template)).kind == "GraphIriTemplateInvalid"


@pytest.mark.parametrize("suffix", ["data", "-x", ".x", "_x", "~x", "9", "%41"])
def test_ho8_t4_a_suffix_that_could_continue_the_encoded_root_is_refused(suffix):
    assert _refusal(_baseline("urn:g:loan-application/{id}" + suffix)).kind == "GraphIriTemplateInvalid"


@pytest.mark.parametrize("suffix", ["/data", ":x", "#x", "?x", "@x"])
def test_ho8_t4b_a_suffix_that_starts_with_a_character_the_encoding_never_emits_is_accepted(suffix):
    assert compile_targets(_baseline("urn:g:loan-application/{id}" + suffix))


def _two_families(first: str, second: str) -> Graph:
    graph = _baseline(first)
    graph.parse(
        data=f"""
        @prefix dal: <{DAL}> . @prefix ex: <{EX}> .
        ex:ArchiveClass a dal:ClassScope ; dal:targetClass ex:ArchivedApplication .
        ex:ArchiveProfile a dal:AggregateBoundaryProfile ; dal:appliesTo ex:ArchiveClass ;
            dal:strategy dal:NamedGraphBoundary ; dal:graphIriTemplate "{second}" .
        """,
        format="turtle",
    )
    return graph


def test_ho8_t5_two_families_with_nested_prefixes_are_refused_naming_both():
    cause = _refusal(_two_families("urn:g:{id}", "urn:g:orders/{id}"))
    assert cause.kind == "GraphIriTemplateOverlap"
    assert "LoanApplicationStrongProfile" in str(cause) and "ArchiveProfile" in str(cause)


def test_ho8_t5b_equal_prefixes_are_refused_and_disjoint_ones_are_not():
    assert _refusal(_two_families("urn:g:x/{id}", "urn:g:x/{id}")).kind == "GraphIriTemplateOverlap"
    assert len(compile_targets(_two_families("urn:g:lend/{id}", "urn:g:lending/{id}"))) == 2


def test_ho8_t5c_two_classes_with_one_local_name_and_no_template_are_refused():
    graph = witness._load_fixture(EXAMPLES_DIR / "baseline-single-class.ttl")
    graph.remove((PROFILE, URIRef(DAL + "graphIriTemplate"), None))
    graph.parse(
        data=f"""
        @prefix dal: <{DAL}> . @prefix ex: <{EX}> . @prefix other: <https://example.org/other#> .
        ex:OtherClass a dal:ClassScope ; dal:targetClass other:LoanApplication .
        ex:OtherProfile a dal:AggregateBoundaryProfile ; dal:appliesTo ex:OtherClass ; dal:strategy dal:NamedGraphBoundary .
        """,
        format="turtle",
    )
    assert _refusal(graph).kind == "GraphIriTemplateOverlap"


@pytest.mark.parametrize("kind", ["GraphIriTemplateInvalid", "GraphIriTemplateOverlap"])
def test_ho8_t6_each_new_witness_triggers_exactly_its_own_refusal(kind):
    observed = witness.observe_compile([witness.WITNESS_DIR / f"refusal-{kind}.ttl"])
    assert set(observed) == {witness.Rule(witness.REFUSAL, kind)}


def test_ho8_t7_the_shipped_examples_all_keep_compiling_or_keep_their_refusal():
    for path in sorted(EXAMPLES_DIR.glob("*.ttl")):
        if path.name == "capability-spec-example.ttl":
            continue
        try:
            compile_targets(witness._load_fixture(path))
        except CompileError as error:
            assert getattr(error.cause, "kind", "") not in {"GraphIriTemplateInvalid", "GraphIriTemplateOverlap"}, path.name


def test_ho8_t8_every_template_that_names_a_graph_from_a_root_encodes_the_whole_root_and_keeps_the_suffix():
    templates = sorted(p for p in witness.TEMPLATE_DIR.glob("*.mustache") if "graphPrefix" in p.read_text(encoding="utf-8"))
    assert len(templates) == 7
    for path in templates:
        text = path.read_text(encoding="utf-8")
        body = text[text.index("}}") + 2:]
        assert "ENCODE_FOR_URI(STR($root))" in body and "{{{graphSuffix}}}" in body, path.name
        assert 'REPLACE(STR($root)' not in body, path.name
