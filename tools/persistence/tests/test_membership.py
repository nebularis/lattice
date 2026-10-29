# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""H2.6f: how a root version lists its members (formal-methods track H, plan 4.12). `dal:membershipEncoding` picks `dal:FullMembership` or
`dal:DeltaMembership`, and `dal:checkpointEvery` the interval of full lists. These tests cover the resolution and the refusals, the contract of
the delta write and of the generated `members` query, what the write stores, what the query returns against a reference model on each engine,
and the domain-shape procedure over the resolved members. Validation Pack: docs/developer/validation/FMH-H2-6f.md. Test IDs are H2.6f-Tn."""

from __future__ import annotations

import random

import pyshacl
import pytest
from rdflib import RDF, Graph, Literal as RdfLiteral, URIRef
from rdflib.namespace import XSD

import engines
from persistence import witness
from persistence.builders import build
from persistence.compiler import CompileError, compile_targets
from persistence.contract import OperationKind, contract_of
from persistence.ir_render import render
from persistence.members import is_checkpoint, materialise
from persistence.namespaces import DAL, PAT as PAT_NS
from persistence.terms import Iri

U = URIRef
PAT = str(PAT_NS)
EXAMPLES = witness.EXAMPLES_DIR
DELTA = EXAMPLES / "write-discipline-delta-membership.ttl"
FULL = EXAMPLES / "write-discipline-composite-append-versions.ttl"
WITNESSES = witness.WITNESS_DIR

DATA, META, TXN = U("urn:g:quotes"), U("urn:g:meta"), U("urn:g:txn")
CONTEXT = {
    "metaGraphPrefix": Iri.encode(str(META)), "txnGraph": Iri.encode(str(TXN)), "logGraphPrefix": Iri.encode("urn:g:txlog/"),
    "dataGraph": Iri.encode(str(DATA)), "datasetGraph": Iri.encode("urn:g:dataset"), "datasetNode": Iri.encode("urn:g:dataset-node"),
}
IDENTITY = U("urn:quote:1")
LONG = lambda n: RdfLiteral(n, datatype=XSD.long)
EX = "https://example.org/quoting#"
LINE = U(EX + "hasLine")
CHECKPOINT, ADDS, DROPS, PREVIOUS = (U(PAT + n) for n in ("checkpoint", "addsMember", "dropsMember", "previousVersion"))
TRUE = RdfLiteral(True)


def version(n: int) -> URIRef:
    return U(f"urn:quote:1/v{n}")


def line(n: int) -> URIRef:
    return U(f"urn:quote:1/line{n}")


def _nt(triples) -> str:
    return " ".join(f"<{s}> <{p}> {o.n3() if not isinstance(o, URIRef) else '<' + str(o) + '>'} ." for s, p, o in triples)


def store(*, dataset_epoch: int | None = None):
    ds = engines.dataset()
    meta = ds.graph(META)
    meta.add((IDENTITY, RDF.type, U(PAT + "VersionRow")))
    meta.add((IDENTITY, U(PAT + "epoch"), LONG(1)))
    meta.add((IDENTITY, U(PAT + "seq"), LONG(0)))
    if dataset_epoch is not None:
        ds.graph(U("urn:g:dataset")).add((U("urn:g:dataset-node"), U(PAT + "epoch"), LONG(dataset_epoch)))
    return ds


def write(ds, n: int, *, members=None, added=(), dropped=(), every: int = 4, stem: str = "append-version-delta", guards=None, txn=None):
    """Write version ``n`` (the row is at seq n - 1). A checkpoint version lists ``members`` in full and carries pat:checkpoint, and any other
    version states ``added`` and ``dropped``, as the caller of H2.8 will."""
    v = version(n)
    payload = [(v, RDF.type, U(EX + "Quote"))]
    adds, drops = [], []
    if is_checkpoint(n, every):
        payload += [(v, LINE, m) for m in sorted(members, key=str)] + [(v, CHECKPOINT, TRUE)]
    else:
        adds = [(v, ADDS, m) for m in sorted(added, key=str)]
        drops = [(v, DROPS, m) for m in sorted(dropped, key=str)]
    text = render(build(stem, CONTEXT, guards=engines.guards(guards)))
    text = text.replace("{{{payloadTriples}}}", _nt(payload)).replace("{{{addedMembers}}}", _nt(adds)).replace("{{{droppedMembers}}}", _nt(drops))
    ds.update(text, initBindings={
        "root": IDENTITY, "epoch": LONG(1), "expectedSeq": LONG(n - 1), "nextSeq": LONG(n), "newRev": U(f"urn:rev:quote/1/{n}"),
        "txnId": U(txn or f"urn:txn:{n}"), "requestDigest": RdfLiteral("ab" * 32), "newVersion": v,
    })
    return ds


def members_of(ds, n: int, *, guards=None) -> set:
    text = render(build("members", {"dataGraph": CONTEXT["dataGraph"]}, guards=engines.guards(guards)))
    rows = ds.query(text, initBindings={"version": version(n), "membershipProperty": LINE})
    return {row[0] for row in rows}


def history(ds, steps, *, every: int = 4, **kw):
    """Write ``steps`` (a list of (added, dropped) per version after the first, the first being the initial set) and return the reference
    model: the members each version should have."""
    initial, *changes = steps
    state = set(initial[0])
    model = [set(state)]
    write(ds, 1, members=state, every=every, **kw)
    for n, (added, dropped) in enumerate(changes, 2):
        state = (state - set(dropped)) | set(added)
        model.append(set(state))
        write(ds, n, members=state, added=added, dropped=dropped, every=every, **kw)
    return model


def triples(ds, graph: URIRef) -> set:
    return {(s, p, o) for s, p, o in ds.graph(graph)}


L = line

# ---- what the delta write stores ----------------------------------------------------------------------------------------


@engines.each_engine_and_guards
def test_h2_6f_t1_a_checkpoint_lists_every_member_and_a_delta_states_only_what_changed():
    ds = engines.dataset()
    ds = store()
    write(ds, 1, members={L(1), L(2), L(3)})
    write(ds, 2, added={L(4)}, dropped={L(1)})
    data = triples(ds, DATA)
    assert {(version(1), LINE, L(i)) for i in (1, 2, 3)} <= data and (version(1), CHECKPOINT, TRUE) in data
    assert (version(2), ADDS, L(4)) in data and (version(2), DROPS, L(1)) in data and (version(2), PREVIOUS, version(1)) in data
    assert not any(s == version(2) and p == LINE for s, p, o in data), "the domain's membership property is not written for a delta version"
    assert not any(s == version(2) and p == CHECKPOINT for s, p, o in data)
    assert not any(s == version(1) and p in (ADDS, DROPS) for s, p, o in data)


@engines.each_engine_and_guards
def test_h2_6f_t2_an_empty_delta_writes_the_version_and_the_link_alone():
    ds = store()
    write(ds, 1, members={L(1)})
    write(ds, 2)
    data = {t for t in triples(ds, DATA) if t[0] == version(2)}
    assert data == {(version(2), RDF.type, U(EX + "Quote")), (version(2), U(PAT + "revision"), U("urn:rev:quote/1/2")), (version(2), PREVIOUS, version(1))}
    assert members_of(ds, 2) == {L(1)}


@engines.each_engine_and_guards
def test_h2_6f_t3_the_dataset_guard_variant_writes_the_delta_only_while_the_dataset_epoch_matches():
    stem = "append-version-delta-dataset-guard"
    ds = store(dataset_epoch=2)
    write(ds, 1, members={L(1)}, stem=stem)
    assert not triples(ds, DATA)
    ds = store(dataset_epoch=1)
    write(ds, 1, members={L(1), L(2)}, stem=stem)
    write(ds, 2, added={L(3)}, dropped={L(1)}, stem=stem)
    assert (version(2), ADDS, L(3)) in triples(ds, DATA) and members_of(ds, 2) == {L(2), L(3)}


@engines.each_engine_and_guards
def test_h2_6f_t4_a_stale_seq_or_a_retried_transaction_writes_nothing_and_no_delta():
    ds = store()
    write(ds, 1, members={L(1)})
    before = sorted(f"{g.identifier} {t}" for g in ds.graphs() for t in g)
    write(ds, 2, added={L(2)}, txn="urn:txn:1")  # the transaction id of the first write
    ds.update(render(build("append-version-delta", CONTEXT, guards=engines.guards(None))).replace("{{{payloadTriples}}}", "").replace("{{{addedMembers}}}", _nt([(version(9), ADDS, L(9))])).replace("{{{droppedMembers}}}", ""), initBindings={
        "root": IDENTITY, "epoch": LONG(1), "expectedSeq": LONG(5), "nextSeq": LONG(6), "newRev": U("urn:rev:x"), "txnId": U("urn:txn:x"),
        "requestDigest": RdfLiteral("ab" * 32), "newVersion": version(9),
    })
    assert sorted(f"{g.identifier} {t}" for g in ds.graphs() for t in g) == before


# ---- what the members query returns --------------------------------------------------------------------------------------


@engines.each_engine_and_guards
def test_h2_6f_t5_the_members_of_a_checkpoint_are_its_list_and_of_a_delta_the_list_with_the_changes_applied():
    ds = store()
    model = history(ds, [({L(1), L(2), L(3)}, ()), ({L(4)}, {L(1)}), ({L(5), L(6)}, {L(2), L(4)})])
    assert [members_of(ds, n) for n in (1, 2, 3)] == model == [{L(1), L(2), L(3)}, {L(2), L(3), L(4)}, {L(3), L(5), L(6)}]


@engines.each_engine_and_guards
def test_h2_6f_t6_a_version_reads_its_own_members_and_not_those_of_a_later_version():
    ds = store()
    model = history(ds, [({L(1), L(2)}, ()), ({L(3)}, ()), (set(), {L(1)}), ({L(1)}, {L(3)})])
    for n in (4, 1, 3, 2):  # an order other than the write order
        assert members_of(ds, n) == model[n - 1]


@engines.each_engine_and_guards
def test_h2_6f_t7_a_member_dropped_and_added_again_is_a_member_and_one_added_and_dropped_is_not():
    ds = store()
    model = history(ds, [({L(1)}, ()), (set(), {L(1)}), ({L(1)}, ()), (set(), {L(1)})])
    assert [members_of(ds, n) for n in (1, 2, 3, 4)] == model == [{L(1)}, set(), {L(1)}, set()]


@engines.each_engine_and_guards
def test_h2_6f_t8_the_chain_stops_at_the_nearest_checkpoint():
    """Nine versions with a checkpoint every 4, at versions 1, 4 and 8. A stray add at version 2, which no later list restates, must not
    reach a version after the checkpoint at 4, and a stray add at 5 must not reach a version after the checkpoint at 8."""
    ds = store()
    model = history(ds, [({L(1), L(2)}, ())] + [({L(10 + n)}, ()) for n in range(1, 9)])
    # the chain from version 9 reaches version 8 only
    ds.graph(DATA).add((version(2), ADDS, L(900)))
    ds.graph(DATA).add((version(5), ADDS, L(901)))
    assert members_of(ds, 9) == model[8] and L(900) not in members_of(ds, 9) and L(901) not in members_of(ds, 9)
    assert L(900) in members_of(ds, 3) and L(900) not in members_of(ds, 4)  # a checkpoint ends the chain behind it, and 3 is before it
    assert L(901) in members_of(ds, 7) and L(901) not in members_of(ds, 8)
    for n in range(1, 10):
        assert members_of(ds, n) - {L(900), L(901)} == model[n - 1]


@engines.each_engine_and_guards
def test_h2_6f_t9_every_version_of_a_longer_history_matches_a_reference_model_at_the_default_interval_of_sixteen():
    rng = random.Random(6)
    state = {L(i) for i in range(30)}
    steps = [(set(state), ())]
    for _ in range(40):
        drop = set(rng.sample(sorted(state, key=str), 3))
        add = set(rng.sample(sorted({L(i) for i in range(100, 200)} - state, key=str), 3))
        state = (state - drop) | add
        steps.append((add, drop))
    ds = store()
    model = history(ds, steps, every=16)
    checkpoints = [n for n in range(1, len(steps) + 1) if is_checkpoint(n, 16)]
    assert checkpoints == [1, 16, 32]
    for n in (1, 2, 15, 16, 17, 31, 32, 33, len(steps)):  # each side of every checkpoint, which is where a chain read goes wrong
        assert members_of(ds, n) == model[n - 1], f"version {n}"


@engines.each_engine_and_guards
def test_h2_6f_t10_a_version_with_no_checkpoint_before_it_has_no_members_and_a_missing_parameter_returns_nothing_where_the_guard_is_on():
    ds = store()
    ds.graph(DATA).add((version(1), ADDS, L(1)))  # a delta with nothing to be a delta against
    assert members_of(ds, 1) == set()
    ds = store()
    write(ds, 1, members={L(1)})
    text = render(build("members", {"dataGraph": CONTEXT["dataGraph"]}, guards=True))
    assert ds.query(text, initBindings={"version": version(1)}) == [] or list(ds.query(text, initBindings={"version": version(1)})) == []


def test_h2_6f_t11_the_caller_knows_a_checkpoint_from_the_sequence_alone():
    assert [n for n in range(1, 40) if is_checkpoint(n, 16)] == [1, 16, 32]
    assert [n for n in range(1, 10) if is_checkpoint(n, 4)] == [1, 4, 8]
    assert all(is_checkpoint(n, 1) for n in range(1, 10))
    for bad in (0, -1, 2.5, True, "16"):
        with pytest.raises(ValueError):
            is_checkpoint(3, bad)


# ---- domain shapes over the resolved members -----------------------------------------------------------------------------

SHAPE = """
@prefix sh: <http://www.w3.org/ns/shacl#> . @prefix ex: <https://example.org/quoting#> .
ex:LineSetShape a sh:NodeShape ; sh:targetSubjectsOf ex:hasLine ;
    sh:property [ sh:path ex:hasLine ; sh:nodeKind sh:IRI ; sh:pattern "^urn:quote:1/line[0-9]+$" ; sh:minCount 1 ] .
"""


def _conforms(data: Graph) -> bool:
    return pyshacl.validate(data, shacl_graph=Graph().parse(data=SHAPE, format="turtle"), inference="none")[0]


@engines.each_engine_and_guards
def test_h2_6f_t12_a_domain_shape_runs_over_the_resolved_members_and_finds_what_it_would_find_in_the_full_list():
    ds = store()
    history(ds, [({L(1), L(2)}, ()), ({L(3)}, {L(1)})])
    resolved = materialise(version(2), LINE, members_of(ds, 2))
    assert len(resolved) == 2 and _conforms(resolved)
    ds.graph(DATA).add((version(2), ADDS, U("urn:other:thing")))  # a member the shape forbids, in the delta
    bad = materialise(version(2), LINE, members_of(ds, 2))
    assert not _conforms(bad)


@engines.each_engine_and_guards
def test_h2_6f_t13_a_shape_over_the_stored_delta_has_nothing_to_validate_which_is_why_it_runs_over_the_resolved_members():
    ds = store()
    history(ds, [({L(1), L(2)}, ()), ({U("urn:other:thing")}, {L(1)})])
    stored = Graph()
    for s, p, o in triples(ds, DATA):
        if s == version(2):
            stored.add((s, p, o))
    assert _conforms(stored), "the delta holds no hasLine triple, so the shape passes vacuously over it"
    assert not _conforms(materialise(version(2), LINE, members_of(ds, 2)))


# ---- the declaration, resolution and selection ---------------------------------------------------------------------------


def _target(path):
    (ct,) = compile_targets(witness._load_fixture(path))
    return ct


def test_h2_6f_t14_the_encoding_is_full_and_the_interval_sixteen_where_none_is_declared():
    count = 0
    for path in sorted(EXAMPLES.glob("*.ttl")):
        try:
            targets = compile_targets(witness._load_fixture(path))
        except CompileError:
            continue
        for ct in targets:
            if path.name == DELTA.name:
                continue
            assert ct.dimensions["membershipEncoding"].value == "FullMembership" and ct.dimensions["membershipEncoding"].won_by is None
            assert ct.dimensions["checkpointEvery"].value == RdfLiteral(16, datatype=XSD.long) and ct.dimensions["checkpointEvery"].won_by is None
            assert "members" not in {o.operation for o in ct.operations}
            count += 1
    assert count >= 20


def test_h2_6f_t15_a_delta_family_resolves_its_declarations_and_selects_the_delta_write_and_the_members_query():
    ct = _target(DELTA)
    assert str(ct.dimensions["membershipEncoding"].value).endswith("DeltaMembership")
    assert ct.dimensions["checkpointEvery"].value.toPython() == 4
    operations = {o.operation: o for o in ct.operations}
    assert operations["append-version"].template_id == "append-version-delta-dataset-guard"
    assert operations["members"].template_id == "members"
    assert [b.name for b in operations["members"].bindings] == ["dataGraph"]
    assert [o.operation for o in ct.operations if o.operation in ("bootstrap-version-row", "append-version", "members")] == ["bootstrap-version-row", "append-version", "members"]
    row_guard = _target(WITNESSES / "write-discipline-delta-membership-row-guard.ttl")
    assert {o.operation: o.template_id for o in row_guard.operations}["append-version"] == "append-version-delta"
    assert {o.operation: o.template_id for o in _target(FULL).operations}["append-version"] == "append-version-dataset-guard"


def test_h2_6f_t16_the_profile_records_both_declarations_with_the_interval_as_a_literal():
    from persistence.compiler import compile_to_graph

    out, _ = compile_to_graph(witness._load_fixture(DELTA))
    by_dim = {str(out.value(n, DAL.dimension)): n for n in out.subjects(DAL.dimension, None)}
    assert out.value(by_dim["membershipEncoding"], DAL.resolvedValue) == DAL.DeltaMembership
    assert out.value(by_dim["checkpointEvery"], DAL.resolvedLiteral).toPython() == 4
    assert out.value(by_dim["checkpointEvery"], DAL.resolvedValue) is None


def _refusal(graph) -> str | None:
    try:
        compile_targets(graph)
    except CompileError as error:
        return getattr(error.cause, "kind", type(error.cause).__name__)
    return None


@pytest.mark.parametrize("name,kind", [
    ("refusal-DeltaMembershipNeedsAppendVersions", "DeltaMembershipNeedsAppendVersions"),
    ("refusal-MembershipEncodingUnknown", "MembershipEncodingUnknown"),
    ("refusal-CheckpointEveryInvalid", "CheckpointEveryInvalid"),
])
def test_h2_6f_t17_each_refusal_is_raised_by_its_witness(name, kind):
    assert _refusal(witness._load_fixture(WITNESSES / f"{name}.ttl")) == kind
    assert _refusal(witness._load_fixture(DELTA)) is None


def test_h2_6f_t18_a_non_integer_interval_is_refused_and_an_interval_of_one_is_not():
    base = Graph()
    for t in witness._load_fixture(DELTA):
        base.add(t)
    profile = U(EX + "QuoteWriteProfile")
    for bad in (RdfLiteral("often"), RdfLiteral(2.5), RdfLiteral(-3, datatype=XSD.long)):
        g = Graph()
        for t in base:
            g.add(t)
        g.set((profile, DAL.checkpointEvery, bad))
        assert _refusal(g) == "CheckpointEveryInvalid", bad
    g = Graph()
    for t in base:
        g.add(t)
    g.set((profile, DAL.checkpointEvery, RdfLiteral(1, datatype=XSD.long)))
    assert _refusal(g) is None


def test_h2_6f_t19_a_full_membership_declaration_changes_nothing_and_an_interval_without_a_delta_is_not_an_error():
    full = Graph()
    for t in witness._load_fixture(FULL):
        full.add(t)
    plain = [o.template_id for o in compile_targets(full)[0].operations]
    full.add((U(EX + "QuoteWriteProfile"), DAL.membershipEncoding, DAL.FullMembership))
    full.add((U(EX + "QuoteWriteProfile"), DAL.checkpointEvery, RdfLiteral(8, datatype=XSD.long)))
    assert [o.template_id for o in compile_targets(full)[0].operations] == plain


# ---- the contract --------------------------------------------------------------------------------------------------------


def test_h2_6f_t20_the_members_query_is_a_read_of_the_data_graph_with_one_result_column_and_no_write():
    operation = build("members", {"dataGraph": CONTEXT["dataGraph"]})
    c = contract_of(operation)
    assert c.kind is OperationKind.MEMBERS_READ and c.kind.value == "MembersRead" and c.version == 4  # 3 since H2.8c (TD-68), 4 since the store vocabulary moved to its published namespace (OR-6)
    assert {a.mode for a in c.accesses} <= {"WholeAggregateRead", "AbsenceRead", "ScanRead", "PointRead"}
    assert {a.resource for a in c.accesses} == {"Aggregate"}
    assert [(p.name, p.kind, p.required) for p in c.parameters] == [("membershipProperty", "Iri", True), ("version", "Iri", True)]
    assert [(r.name, r.kind) for r in c.results] == [("member", "Iri")]
    assert c.payload is None and c.digest is None


def test_h2_6f_t21_the_delta_write_has_the_kind_of_append_version_and_declares_the_member_slots_as_the_add_and_del_parts_of_its_digest():
    c = contract_of(build("append-version-delta", CONTEXT))
    assert c.kind is OperationKind.APPEND_VERSION and c.id == "append-version-delta"
    assert {p.name for p in c.parameters} == {
        "root", "epoch", "expectedSeq", "nextSeq", "newRev", "txnId", "requestDigest", "newVersion", "payloadTriples", "addedMembers", "droppedMembers",
    }
    assert c.payload is not None and c.payload.parameter == "payloadTriples"
    assert (c.digest.payload, c.digest.add, c.digest.delete) == ("payloadTriples", "addedMembers", "droppedMembers")
    assert contract_of(build("append-version-delta-dataset-guard", CONTEXT)).digest == c.digest
    full = contract_of(build("append-version", CONTEXT))
    assert (full.digest.add, full.digest.delete) == (None, None) and {p.name for p in full.parameters}.isdisjoint({"addedMembers", "droppedMembers"})


# ---- H2.8c: the faster form of the members read (plan 4.18 step 2, TD-68). Test IDs are H2.8c-Tn -------------------------


def test_h2_8c_t5_the_nearest_checkpoint_is_found_in_a_sub_select_whose_not_exists_names_its_graph():
    """The sub-select gives the one nearest checkpoint before the chain and the members are joined, which is what makes the read fast on rdflib.
    Both `NOT EXISTS` bodies name their graph, which this form needs on rdflib (TSD-34)."""
    from persistence.ir import GraphBlock, NotExists, SubSelect

    operation = build("members", {"dataGraph": CONTEXT["dataGraph"]})
    (block,) = operation.where.elements
    assert isinstance(block, GraphBlock) and isinstance(block.elements[0], SubSelect)
    sub = block.elements[0]
    assert [v.name for v in sub.select.projection] == ["cp"]
    inner = [e for e in sub.where.elements if isinstance(e, NotExists)] + [e for e in block.elements if isinstance(e, NotExists)]
    assert len(inner) == 2 and all(isinstance(n.group.elements[0], GraphBlock) for n in inner)


@engines.rdflib_only
def test_h2_8c_t6_random_histories_read_right_at_every_version_on_sixteen_hash_seeds():
    """24 random histories (checkpoints every 2, 3 and 4), with stray adds, against the reference model at every version, each hash seed in a child
    process on rdflib. Which checkpoint a store meets first follows the seed (TSD-34)."""
    import tsd34_support as support

    assert support.sweep_random_histories(range(16)) == {"[]"}


@engines.each_engine
def test_h2_8c_t7_random_histories_read_right_on_each_engine():
    import tsd34_support as support

    assert support.random_histories_probe() == []
