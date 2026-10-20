# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.8b: the payload check, the audit outcome in the contract, the INFO diagnostics and the two compile checks of the slice. The generated
`payload-check` query and the caller library's walk are held equal over random payloads on every engine. Validation Pack:
docs/developer/validation/FMH-H2-8b.md. Test IDs are H2.8b-Tn."""

from __future__ import annotations

import random

import pytest
from rdflib import RDF, Graph, Literal, URIRef

import engines
from expected_profiles import emit
from lattice_persistence import Iri, Lit, Payload, Triple, outside_bound, read_contracts
from persistence import witness
from persistence.compiler import CompileError, compile_targets, compile_to_graph
from persistence.instantiate import instantiate_by_target
from persistence.namespaces import DAL
from persistence.operations import PAYLOAD_GRAPH

from conftest import EXAMPLES_DIR

LEND = "https://example.org/lending#"
SHAPED_NAMED = f"""
@prefix dal: <{DAL}> .
@prefix ex:  <{LEND}> .
@prefix sh:  <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:LoanApplicationStrongProfile dal:boundaryShape ex:LoanShape .
ex:LoanShape a sh:NodeShape ; sh:targetClass ex:LoanApplication ;
    sh:property [ sh:path ex:amount ; sh:datatype xsd:decimal ] ,
                [ sh:path ex:applicant ; sh:node ex:ApplicantShape ; dal:ownership dal:Owned ] ,
                [ sh:path ex:branch ; sh:class ex:Branch ; dal:ownership dal:Reference ] .
ex:ApplicantShape a sh:NodeShape ; sh:targetClass ex:Applicant ;
    sh:property [ sh:path ex:address ; sh:node ex:AddressShape ; dal:ownership dal:Owned ] .
ex:AddressShape a sh:NodeShape ; sh:targetClass ex:Address .
"""
VALUES_ONLY = SHAPED_NAMED.replace('[ sh:path ex:applicant ; sh:node ex:ApplicantShape ; dal:ownership dal:Owned ] ,\n', "")


def named_graph_config(shape: str = SHAPED_NAMED) -> Graph:
    graph = witness._load_fixture(EXAMPLES_DIR / "baseline-single-class.ttl")
    graph.parse(data=shape, format="turtle")
    return graph


def profile_of(graph: Graph, **options) -> Graph:
    compiled, _ = compile_to_graph(graph, **options)
    return compiled


def operations_named(compiled: Graph, name: str) -> list:
    return [o for o in read_contracts(compiled) if o.template_id == name]


# ---- which families get the operation

def test_h2_8b_t1_a_composite_family_and_a_shaped_named_graph_family_get_a_payload_check_and_an_unshaped_one_does_not():
    assert len(operations_named(emit("composite-project-ownership"), "payload-check")) == 1
    assert len(operations_named(profile_of(named_graph_config()), "payload-check")) == 1
    assert operations_named(emit("baseline-single-class"), "payload-check") == []  # no boundary shape
    assert operations_named(emit("write-discipline-noboundary-append-versions"), "payload-check") == []
    assert operations_named(emit("append-stream-dataset-guard"), "payload-check") == []  # an append has events and no payload of the aggregate
    assert len(operations_named(emit("write-discipline-composite-append-versions"), "payload-check")) == 1


def test_h2_8b_t2_the_operation_is_a_read_of_the_local_payload_with_one_parameter_and_one_column_and_no_payload_of_its_own():
    (check,) = operations_named(emit("composite-project-ownership"), "payload-check")
    assert check.kind.value == "PayloadCheck" and check.payload is None and check.digest is None
    assert [(p.name, p.kind, p.required) for p in check.parameters] == [("root", "Iri", True)]
    compiled = emit("composite-project-ownership")
    columns = [(str(compiled.value(c, DAL.columnName)), compiled.value(c, DAL.columnKind)) for c in compiled.objects(check.node, DAL.resultColumn)]
    assert columns == [("s", DAL.IriColumn)]
    assert check.binding("payloadGraph") == f"<{PAYLOAD_GRAPH}>"


def test_h2_8b_t3_the_payload_of_a_new_version_is_rooted_at_the_version():
    for example in ("write-discipline-composite-append-versions", "write-discipline-noboundary-append-versions", "write-discipline-delta-membership"):
        (append,) = [o for o in operations_named(emit(example), "append-version-dataset-guard") + operations_named(emit(example), "append-version-delta-dataset-guard")]
        assert append.payload.root == "newVersion", example
    (replace,) = operations_named(emit("composite-project-ownership"), "cas-replace-composite-property-patch-log")
    assert replace.payload.root == "root"


def test_h2_8b_t4_the_contract_names_the_shape_and_the_target_shape_of_each_owned_edge():
    (replace,) = operations_named(emit("composite-project-ownership"), "cas-replace-composite-property-patch-log")
    assert replace.payload.shape == "https://example.org/projects#ProjectShape"
    owned = {(e.predicate.rsplit("#", 1)[-1], (e.target_shape or "").rsplit("#", 1)[-1]) for e in replace.payload.edges if e.ownership == "Owned"}
    assert ("hasSubtask", "TaskShape") in owned and ("onTask", "CommentShape") in owned
    (create,) = operations_named(emit("baseline-single-class"), "create-if-absent-named-graph-patch-log")
    assert create.payload.shape is None


# ---- the query and the library agree

POOL = [f"urn:n:{i}" for i in range(10)]


def project(prefix="https://example.org/projects#"):
    return prefix, ["name", "forClient", "hasMilestone", "hasPlan", "due", "hasTask", "status", "assignee", "hasSubtask", "attachment", "onTask", "title", "text", "other"]


def lending():
    return LEND, ["amount", "applicant", "branch", "address", "other"]


def random_payload(rng: random.Random, prefix: str, predicates: list, root: str) -> Payload:
    """Mostly triples that grow from the root, so that many payloads are inside the aggregate, and some that do not."""
    triples, known = set(), [root]
    for _ in range(rng.randint(1, 14)):
        s = Iri.encode(rng.choice(known) if rng.random() < 0.85 else rng.choice(POOL))
        p = Iri.encode(prefix + rng.choice(predicates))
        if rng.random() < 0.75:
            node = rng.choice(POOL)
            known.append(node)
            o = Iri.encode(node)
        else:
            o = Lit(rng.choice(["x", "} } ; DROP ALL", "42"]))
        triples.add(Triple(s, p, o))
    return Payload(frozenset(triples))


def run_query(text: str, payload: Payload, root: str):
    ds = engines.dataset()
    graph = ds.graph(URIRef(PAYLOAD_GRAPH))
    for t in payload.triples:
        obj = URIRef(str(t.object)[1:-1]) if isinstance(t.object, Iri) else Literal(t.object.value)
        graph.add((URIRef(str(t.subject)[1:-1]), URIRef(str(t.predicate)[1:-1]), obj))
    rows = ds.query(text.replace("$root", f"<{root}>"))
    return sorted(str(r[0]) for r in rows)


def check_text(compiled: Graph) -> tuple:
    (name, text), = [(n, t) for target in instantiate_by_target(compiled).values() for n, t in target.items() if n == "payload-check"]
    (check,) = operations_named(compiled, "payload-check")
    replace = next(o for o in read_contracts(compiled) if o.payload is not None)
    return text, replace.payload


@engines.each_engine
@pytest.mark.parametrize("name,compiled,family", [
    ("composite", lambda: emit("composite-project-ownership"), project),
    ("named-graph", lambda: profile_of(named_graph_config()), lending),
    ("named-graph-values-only", lambda: profile_of(named_graph_config(VALUES_ONLY)), lending),
], ids=["composite", "named-graph", "named-graph-values-only"])
def test_h2_8b_t5_the_generated_query_and_the_library_walk_return_the_same_subjects_on_random_payloads(engine, name, compiled, family):
    text, contract = check_text(compiled())
    prefix, predicates = family()
    rng, outside_seen, inside_seen = random.Random(86), 0, 0
    for _ in range(200):
        root = rng.choice(POOL)
        payload = random_payload(rng, prefix, predicates, root)
        by_query = run_query(text, payload, root)
        by_library = sorted(str(s)[1:-1] for s in outside_bound(contract, Iri.encode(root), payload))
        assert by_query == by_library, (name, root, sorted(payload.lines()))
        outside_seen += bool(by_library)
        inside_seen += not by_library
    assert outside_seen > 5 and inside_seen > 5  # the generator exercises both outcomes


@engines.each_engine
def test_h2_8b_t6_a_payload_with_a_subject_outside_the_aggregate_is_returned_and_a_literal_that_looks_like_a_query_is_a_literal(engine):
    text, contract = check_text(emit("composite-project-ownership"))
    ex = "https://example.org/projects#"
    root = "urn:p:1"
    evil = "} } ; DROP ALL ; INSERT { {"
    payload = Payload.of(
        Triple(Iri.encode(root), Iri.encode(ex + "name"), Lit(evil)), Triple(Iri.encode(root), Iri.encode(ex + "hasMilestone"), Iri.encode("urn:m:1")),
        Triple(Iri.encode("urn:m:1"), Iri.encode(ex + "due"), Lit("2026-01-01")), Triple(Iri.encode("urn:other:9"), Iri.encode(ex + "name"), Lit("stray")),
    )
    assert run_query(text, payload, root) == ["urn:other:9"] and [str(s) for s in outside_bound(contract, Iri.encode(root), payload)] == ["<urn:other:9>"]
    clean = Payload(frozenset(t for t in payload.triples if str(t.subject) != "<urn:other:9>"))
    assert run_query(text, clean, root) == []
    # the literal reaches the store as one literal, through the slot text the library builds
    ds = engines.dataset()
    ds.update("INSERT DATA { GRAPH <urn:g:x> { " + clean.sparql() + " } }")
    values = {str(o) for o in ds.graph(URIRef("urn:g:x")).objects(URIRef(root), URIRef(ex + "name"))}
    assert values == {evil} and len(ds.graph(URIRef("urn:g:x"))) == len(clean)


def test_h2_8b_t7_an_initial_binding_for_root_and_the_substituted_text_give_the_same_rows_on_rdflib():
    text, _ = check_text(emit("composite-project-ownership"))
    ex = "https://example.org/projects#"
    ds = engines.dataset()
    g = ds.graph(URIRef(PAYLOAD_GRAPH))
    g.add((URIRef("urn:p:1"), URIRef(ex + "hasMilestone"), URIRef("urn:m:1")))
    g.add((URIRef("urn:z"), URIRef(ex + "name"), Literal("x")))
    bound = sorted(str(r[0]) for r in ds.query(text, initBindings={"root": URIRef("urn:p:1")}))
    assert bound == sorted(str(r[0]) for r in ds.query(text.replace("$root", "<urn:p:1>"))) == ["urn:z"]


# ---- audits state their outcomes

def test_h2_8b_t8_every_audit_declares_its_three_outcomes_and_the_parameter_it_examines():
    compiled = emit("baseline-single-class")
    audits = [o for o in read_contracts(compiled) if o.kind.value == "Audit"]
    assert len(audits) == 5 and all(a.outcomes == ("Clean", "Failed", "NothingExamined") for a in audits)
    assert {a.template_id: a.examines for a in audits} == {
        "fork-detection-audit": None, "key-claim-duplicate-audit": None, "gap-scan-audit": "logGraphs", "revision-multi-txn-audit": "logGraphs", "txn-multi-revision-audit": "logGraphs",
    }
    assert all(o.outcomes == () and o.examines is None for o in read_contracts(compiled) if o.kind.value != "Audit")


# ---- the diagnostics

def diagnostics(graph: Graph, **options) -> list:
    return [(d.kind, d.severity) for ct in compile_targets(graph, **options) for d in ct.diagnostics]


def test_h2_8b_t9_an_unshaped_named_graph_family_is_told_by_information_and_by_a_warning_under_the_option_and_a_shaped_one_not_at_all():
    baseline = witness._load_fixture(EXAMPLES_DIR / "baseline-single-class.ttl")
    assert ("UnboundedPayload", "INFO") in diagnostics(baseline)
    assert ("UnboundedPayload", "WARNING") in diagnostics(baseline, warn_unbounded_payload=True)
    assert [s for k, s in diagnostics(baseline, warn_unbounded_payload=True) if k == "UnboundedPayload"] == ["WARNING"]
    shaped = named_graph_config()
    assert not any(k == "UnboundedPayload" for k, _ in diagnostics(shaped)) and not any(k == "UnboundedPayload" for k, _ in diagnostics(shaped, warn_unbounded_payload=True))
    composite = witness._load_fixture(EXAMPLES_DIR / "composite-project-ownership.ttl")
    assert not any(k == "UnboundedPayload" for k, _ in diagnostics(composite))


def test_h2_8b_t10_a_family_with_no_payload_operation_has_no_unbounded_payload():
    assert not any(k == "UnboundedPayload" for k, _ in diagnostics(witness._load_fixture(EXAMPLES_DIR / "append-stream-dataset-guard.ttl")))


def test_h2_8b_t11_guards_off_is_reported_once_per_target_with_the_obligation_and_guards_on_is_not():
    baseline = witness._load_fixture(EXAMPLES_DIR / "baseline-single-class.ttl")
    assert ("ParameterGuardsOff", "INFO") in diagnostics(baseline, guards=False) and not any(k == "ParameterGuardsOff" for k, _ in diagnostics(baseline))
    (ct,) = compile_targets(baseline, guards=False)
    message = next(d.message for d in ct.diagnostics if d.kind == "ParameterGuardsOff")
    assert "caller must check every one" in message and "xsd:long exactly" in message


def test_h2_8b_t12_the_diagnostics_are_in_the_compiled_profile_with_their_severity_and_the_command_line_raises_one(tmp_path):
    from persistence.cli import main

    out = tmp_path / "p.ttl"
    base = str(EXAMPLES_DIR / "baseline-single-class.ttl")
    spec = str(witness.SPEC_TTL)
    assert main(["compile", spec, base, "--out", str(out)]) == 0
    seen = {(str(g.value(d, DAL.diagnosticKind)), str(g.value(d, DAL.diagnosticSeverity))) for g in [Graph().parse(out)] for d in g.subjects(RDF.type, DAL.Diagnostic)}
    assert ("UnboundedPayload", "INFO") in seen
    assert main(["compile", spec, base, "--out", str(out), "--warn-unbounded-payload", "--no-parameter-guards"]) == 0
    g = Graph().parse(out)
    seen = {(str(g.value(d, DAL.diagnosticKind)), str(g.value(d, DAL.diagnosticSeverity))) for d in g.subjects(RDF.type, DAL.Diagnostic)}
    assert {("UnboundedPayload", "WARNING"), ("ParameterGuardsOff", "INFO")} <= seen and ("UnboundedPayload", "INFO") not in seen


# ---- D-10 and D-11

def test_h2_8b_t13_a_patch_log_that_nothing_writes_is_told_and_one_that_is_written_is_not():
    kinds = lambda name: {k for k, _ in diagnostics(witness._load_fixture(EXAMPLES_DIR / name))}
    assert "PatchLogNotWritten" in kinds("append-stream-dataset-guard.ttl")
    for written in ("baseline-single-class.ttl", "composite-project-ownership.ttl", "epoch-dataset-level-guard.ttl"):
        assert "PatchLogNotWritten" not in kinds(written), written


def _two_families(second_receipt: str, shards: int = 64, name: str = "Mortgage58") -> Graph:
    graph = witness._load_fixture(EXAMPLES_DIR / "baseline-single-class.ttl")
    graph.set((URIRef(LEND + "LoanApplicationStrongProfile"), DAL.receiptModel, DAL.NoReceipt))
    graph.parse(data=f"""
@prefix dal: <{DAL}> . @prefix ex: <{LEND}> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:{name}Class a dal:ClassScope ; dal:targetClass ex:{name} ; dal:priority "20"^^xsd:integer .
ex:{name}Profile a dal:DataAccessProfile ; dal:appliesTo ex:{name}Class ; dal:strategy dal:NamedGraphBoundary ;
    dal:graphIriTemplate "urn:g:{name.lower()}/{{id}}" ; dal:concurrencyProfile dal:Optimistic ; dal:minConcurrencyLevel dal:Linearizable ;
    dal:orderingGrain dal:EventGrain ; dal:receiptModel {second_receipt} ; dal:metaTopology dal:SharedSharded ; dal:metaShards "{shards}"^^xsd:long .
""", format="turtle")
    return graph


def test_h2_8b_t14_a_family_that_writes_no_receipt_may_not_share_a_meta_graph_with_one_whose_receipts_a_gap_scan_reads():
    with pytest.raises(CompileError) as caught:
        compile_targets(_two_families("dal:ReceiptOnly"))
    assert caught.value.cause.kind == "NoReceiptSharesMetaShard" and "gap" in str(caught.value.cause)


def test_h2_8b_t15_the_refusal_does_not_apply_to_other_shards_or_to_two_families_that_write_no_receipt_or_two_that_do():
    assert len(compile_targets(_two_families("dal:ReceiptOnly", name="Mortgage0"))) == 2  # another meta shard
    assert len(compile_targets(_two_families("dal:NoReceipt"))) == 2  # neither is gap-scanned
    graph = witness._load_fixture(EXAMPLES_DIR / "baseline-single-class.ttl")
    graph.parse(data=f"""
@prefix dal: <{DAL}> . @prefix ex: <{LEND}> . @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
ex:M58Class a dal:ClassScope ; dal:targetClass ex:Mortgage58 ; dal:priority "20"^^xsd:integer .
ex:M58Profile a dal:DataAccessProfile ; dal:appliesTo ex:M58Class ; dal:strategy dal:NamedGraphBoundary ; dal:graphIriTemplate "urn:g:mortgage58/{{id}}" ;
    dal:concurrencyProfile dal:Optimistic ; dal:minConcurrencyLevel dal:Linearizable ; dal:orderingGrain dal:EventGrain ; dal:receiptModel dal:ReceiptOnly ;
    dal:metaTopology dal:SharedSharded ; dal:metaShards "64"^^xsd:long .
""", format="turtle")
    assert len(compile_targets(graph)) == 2  # both write receipts


def test_h2_8b_t16_no_shipped_example_is_refused_by_the_new_checks():
    for path in sorted(EXAMPLES_DIR.glob("*.ttl")):
        if path.name.startswith("invalid-") or path.name == "capability-spec-example.ttl":
            continue
        try:
            compile_targets(witness._load_fixture(path))
        except CompileError as error:
            assert getattr(error.cause, "kind", "") != "NoReceiptSharesMetaShard", path.name
