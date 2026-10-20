# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""The expected compiled profiles (formal-methods track H, slice H2.6, plan 4.4).

An expected profile is what the compiler of H2.7 will emit for an example: today's compiled profile, with the contract of each
generated operation added (``persistence.contract``). The terms the contract uses (:data:`NEW_PREDICATES`, and the individuals of
:data:`ENUMERATIONS`) do not exist in the ontology yet. Their names are proposals, and the maintainer settles them when the files
are reviewed. The structure is fixed by two rules (design review 2.6):

* no blank node in a new part. Every declaration node has an IRI derived from the target, the operation and the part
  (:func:`mint`), so two compiles give the same IRIs and a reviewer can read a diff,
* no SPARQL text in any value. Kinds, modes and resources are individuals, a caller-named graph's rule refers to the family's
  ``dal:graphIriTemplate`` and never repeats it, and the owned path stays in the ``ownedPath`` binding.

``mise run build:persistence-expected-profiles`` regenerates the files, and ``mise run check:persistence-expected-profiles`` (part of ``check:persistence``) fails with the names of the stale ones. A change to ``compile`` output, or to a builder, regenerates
them in the same commit (the base-profile and agreement tests fail until it does).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from rdflib import RDF, RDFS, BNode, Graph, Literal, URIRef
from rdflib.namespace import XSD

from persistence import witness
from persistence.builders import BUILDERS, build
from persistence.compiler import add_edge_facts, compile_to_graph
from persistence.contract import (
    HAND_DECLARED, LOGICAL_KEYS, AccessMode, DeclarationSource, GraphNaming, GuardStatus, OperationContract, OperationKind,
    ResourceKind, contract_of, edge_contracts, stem_of,
)
from persistence.instantiate import operation_context
from persistence.ir import Kind
from persistence.namespaces import DAL

REPO_ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = REPO_ROOT / "ontology" / "persistence" / "examples"
OUT_DIR = REPO_ROOT / "ontology" / "persistence" / "test" / "expected-profiles"

# The twelve files: eleven examples, and a variant of the first with the guards off and the caller naming each graph.
CONFIGURATIONS: list[tuple[str, str, dict]] = [
    ("baseline-single-class", "baseline-single-class", {}),
    ("epoch-dataset-level-guard", "epoch-dataset-level-guard", {}),
    ("composite-project-ownership", "composite-project-ownership", {}),
    ("append-stream-dataset-guard", "append-stream-dataset-guard", {}),
    ("uniqueness-merge-policy", "uniqueness-merge-policy", {}),
    ("uniqueness-quarantine-policy", "uniqueness-quarantine-policy", {}),
    ("claim-scheme-dual-rotation", "claim-scheme-dual-rotation", {}),
    ("value-based-cas", "value-based-cas", {}),
    ("baseline-single-class.caller-named", "baseline-single-class", {"guards": False, "graph_names": "caller"}),
    # H2.6c: the two families that append versions, a composite one and one with no boundary under the dataset-level guard.
    ("write-discipline-composite-append-versions", "write-discipline-composite-append-versions", {}),
    ("write-discipline-noboundary-append-versions", "write-discipline-noboundary-append-versions", {}),
    # H2.6f: a family that appends versions and states each version's members as changes.
    ("write-discipline-delta-membership", "write-discipline-delta-membership", {}),
]
KINDS_FILE = "kinds"

NEW_PREDICATES = {
    DAL[n] for n in (
        "operationKind", "templateVersion", "guardStatus", "graphNaming", "declarationSource", "parameter", "access",
        "payloadContract", "digestContract", "resultColumn",
    )
}
"""The predicates a generated operation gains. The base-profile test removes them (and the declaration nodes) to compare with `compile`."""

def mint(target: URIRef, operation: str, part: str) -> URIRef:
    """The IRI of a declaration node: derived from the target, the operation's name and the part, never from an order."""
    base = str(target).replace("#", "/")
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", operation).strip("-")
    return URIRef(f"{base}/compiled/{slug}#{part}")


def is_declaration(node) -> bool:
    return isinstance(node, URIRef) and "/compiled/" in str(node)


# ---- enumerations ------------------------------------------------------------------------------------------------------

_REALISATION = {
    ResourceKind.AGGREGATE: "the root's data graph (named-graph family) or the owned members in the family's data graph (composite)",
    ResourceKind.VERSION_ROW: "the version row of a root or stream, in its meta graph",
    ResourceKind.TRANSACTION_CLAIM: "the claim recorded for a transaction id, in the transaction graph",
    ResourceKind.RECEIPT: "a receipt in its monthly log bucket, and in the pinned graph for a retained head. The pinned graph is how retention is realised",
    ResourceKind.EVENT: "an event in its monthly event bucket",
    ResourceKind.KEY_CLAIM: "the claim node and its owner, constraint and retirement, in the keys graph",
    ResourceKind.MERGE_RECORD: "a link from a non-canonical owner to the canonical one, in the keys graph, by the adopter's merge relation",
    ResourceKind.KEY_QUARANTINE: "an owner recorded against a duplicated claim, in the quarantine graph",
    ResourceKind.DATASET_EPOCH: "the dataset's epoch, in the dataset graph",
    ResourceKind.RETENTION_MARK: "a target's retention low-water mark, in the retention graph",
    ResourceKind.PROPERTY_VALUE: "the value of one property of a root, in the default graph today (TD-43)",
    ResourceKind.PATCH_CONTENT: "the triples a write added or removed, in a graph named from its receipt, newRev followed by /add or /del, one per direction",
}


def _kind_name(kind: str) -> str:
    return f"{kind}Kind"


def _column_name(kind: str) -> str:
    return f"{kind}Column"


def kinds_graph() -> Graph:
    """The closed enumerations the contract names, with the logical key and realisation of each resource."""
    g = Graph()
    g.bind("dal", DAL)
    g.bind("rdfs", RDFS)

    def members(cls: str, names, comment=None) -> None:
        for name in names:
            g.add((DAL[name], RDF.type, DAL[cls]))
            if comment and name in comment:
                g.add((DAL[name], RDFS.comment, Literal(comment[name])))

    for cls in (
        "ParameterDeclaration", "ResourceAccess", "ResultColumn", "PayloadContract", "DigestContract", "DigestPart", "OperationKind",
        "ResourceKind", "AccessMode", "ParameterKind", "ColumnKind", "GuardStatus", "GraphNaming", "DeclarationSource", "DigestPartRole",
        "Rule", "Source", "PayloadEncoding", "BoundaryShapeAbsence", "ReferenceEdge", "ReferenceMode", "OwnershipKind",
    ):
        g.add((DAL[cls], RDF.type, RDFS.Class))
    members("OperationKind", (k.value for k in OperationKind))
    members("ResourceKind", (k.value for k in ResourceKind), {k.value: _REALISATION[k] for k in ResourceKind})
    for resource, key in LOGICAL_KEYS.items():
        g.add((DAL[resource.value], DAL.logicalKey, Literal(", ".join(key))))
    members("AccessMode", (m.value for m in AccessMode))
    members("ParameterKind", sorted({_kind_name(k.value) for k in Kind}))
    members("ColumnKind", sorted({_column_name(n) for n in ("Iri", "Position", "String", "Term", "Count", "Concatenation")}))
    members("GuardStatus", (s.value for s in GuardStatus))
    members("GraphNaming", (n.value for n in GraphNaming))
    members("DeclarationSource", (s.value for s in DeclarationSource))
    members("DigestPartRole", ("OperationKindPart", "TargetPart", "ExpectedSeqPart", "PayloadPart", "EventPart", "AddPart", "DelPart"))
    members("Rule", ("GraphNameOfRoot",), {"GraphNameOfRoot": "the graph IRI the family's dal:graphIriTemplate gives for the value of the root parameter"})
    members("Source", ("RegistryGraph", "NoSource"), {"RegistryGraph": "the family's dal:registryGraph, a caller obligation"})
    members("PayloadEncoding", ("GroundNTriples",))
    members("ReferenceMode", ("ByIdentity", "Pinned"))
    members("OwnershipKind", ("Owned", "Reference", "Vocabulary"))
    members("BoundaryShapeAbsence", ("NoBoundaryShape",), {"NoBoundaryShape": "the family names no boundary shape, so a payload is not checked against one"})
    return g


# ---- one operation -----------------------------------------------------------------------------------------------------


def _shape_of(target) -> URIRef | None:
    extra = target.dimensions["aggregateBoundary"].extra
    shape = extra.get("boundaryShape")
    return URIRef(str(shape)) if shape is not None else None


def designed(contract: OperationContract, receipt_model: str) -> OperationContract:
    """What the expected profile says for an operation: the builder's contract. H2.6d closed the one difference there was, that
    `$assertGraph` and `$retractGraph` are required under `dal:PatchLog`, by having the patch-log variants name their delta graphs from the receipt."""
    return contract


def contract_for(compiled: Graph, node, *, guards: bool, graph_names: str, edges: tuple = ()) -> OperationContract | None:
    stem = str(compiled.value(compiled.value(node, DAL.usesTemplate), DAL.templateId)).removesuffix(".mustache")
    if stem in BUILDERS:
        return contract_of(build(stem, operation_context(compiled, node), guards=guards, graph_names=graph_names), edges)
    return HAND_DECLARED.get(stem)


def _emit_operation(g: Graph, node, target_iri: URIRef, name: str, c: OperationContract, shape: URIRef | None) -> None:
    def m(part: str) -> URIRef:
        return mint(target_iri, name, part)

    g.add((node, DAL.operationKind, DAL[c.kind.value]))
    g.add((node, DAL.templateVersion, Literal(c.version, datatype=XSD.integer)))
    g.add((node, DAL.guardStatus, DAL[c.guard_status.value]))
    if c.graph_naming is not None:
        g.add((node, DAL.graphNaming, DAL[c.graph_naming.value]))
    g.add((node, DAL.declarationSource, DAL[c.source.value]))
    for p in c.parameters:
        pn = m(f"param-{p.name}")
        g.add((node, DAL.parameter, pn))
        g.add((pn, RDF.type, DAL.ParameterDeclaration))
        g.add((pn, DAL.parameterName, Literal(p.name)))
        g.add((pn, DAL.parameterKind, DAL[_kind_name(p.kind)]))
        g.add((pn, DAL.required, Literal(p.required)))
        if p.equals_graph_name:
            g.add((pn, DAL.mustEqual, DAL.GraphNameOfRoot))
            g.add((pn, DAL.mustEqualFor, m("param-root")))
        if p.sourced_from_registry:
            g.add((pn, DAL.sourcedFrom, DAL.RegistryGraph))
    for i, a in enumerate(c.accesses, 1):
        an = m(f"access-{i}")
        g.add((node, DAL.access, an))
        g.add((an, RDF.type, DAL.ResourceAccess))
        g.add((an, DAL.resourceKind, DAL[a.resource]))
        g.add((an, DAL.accessMode, DAL[a.mode]))
        if a.keyed_by:
            g.add((an, DAL.keyedBy, m(f"param-{a.keyed_by}")))
    for i, col in enumerate(c.results, 1):
        cn = m(f"result-{col.name}")
        g.add((node, DAL.resultColumn, cn))
        g.add((cn, RDF.type, DAL.ResultColumn))
        g.add((cn, DAL.columnName, Literal(col.name)))
        g.add((cn, DAL.columnPosition, Literal(i, datatype=XSD.integer)))
        g.add((cn, DAL.columnKind, DAL[_column_name(col.kind)]))
        if col.separator is not None:
            g.add((cn, DAL.columnSeparator, Literal(col.separator)))
    if c.payload is not None:
        pc = m("payload")
        g.add((node, DAL.payloadContract, pc))
        g.add((pc, RDF.type, DAL.PayloadContract))
        g.add((pc, DAL.payloadParameter, m(f"param-{c.payload.parameter}")))
        if c.payload.root:
            g.add((pc, DAL.payloadRoot, m(f"param-{c.payload.root}")))
        g.add((pc, DAL.payloadEncoding, DAL.GroundNTriples))
        g.add((pc, DAL.boundaryShape, shape if shape is not None else DAL.NoBoundaryShape))
        for i, edge in enumerate(c.payload.edges):
            en = m(f"edge-{i:02d}")
            g.add((pc, DAL.referenceEdge, en))
            g.add((en, RDF.type, DAL.ReferenceEdge))
            add_edge_facts(g, en, edge)
    if c.digest is not None:
        dc = m("digest")
        g.add((node, DAL.digestContract, dc))
        g.add((dc, RDF.type, DAL.DigestContract))
        g.add((dc, DAL.digestAlgorithm, Literal("SHA-256")))
        parts = [
            ("OperationKindPart", ()),
            ("TargetPart", (c.digest.target,) if c.digest.target else ()),
            ("ExpectedSeqPart", (c.digest.expected,) if c.digest.expected else ()),
            # the content of the request, one part: the payload of a write, or the events of an append (H2.6b, Q5)
            ("EventPart", c.digest.event) if c.digest.event else ("PayloadPart", (c.digest.payload,) if c.digest.payload else ()),
            # a replace under a patch log adds the asserted and the retracted triples, in that order (H2.6d)
            *((("AddPart", (c.digest.add,)),) if c.digest.add else ()),
            *((("DelPart", (c.digest.delete,)),) if c.digest.delete else ()),
        ]
        for i, (role, sources) in enumerate(parts, 1):
            dp = m(f"digest-part-{i}")
            g.add((dc, DAL.digestPart, dp))
            g.add((dp, RDF.type, DAL.DigestPart))
            g.add((dp, DAL.partOrder, Literal(i, datatype=XSD.integer)))
            g.add((dp, DAL.partRole, DAL[role]))
            if sources:
                for source in sources:
                    g.add((dp, DAL.partSource, m(f"param-{source}")))
            else:
                g.add((dp, DAL.partSource, DAL.NoSource))


def emit(example: str, *, guards: bool = True, graph_names: str = "query", source: Graph | None = None) -> Graph:
    """The expected compiled profile of ``examples/<example>.ttl`` under the given run choices."""
    config = source if source is not None else witness._load_fixture(EXAMPLES / f"{example}.ttl")
    compiled, targets = compile_to_graph(config)
    compiled.bind("dal", DAL)
    by_target = {URIRef(str(t.target.cls)): t for t in targets}
    for profile in compiled.subjects(RDF.type, DAL.CompiledProfile):
        target_iri = compiled.value(profile, DAL.forTarget)
        target = by_target[target_iri]
        receipt_model = str(target.dimensions["receiptModel"].value).rsplit("#", 1)[-1]
        shape = _shape_of(target)
        for node in list(compiled.objects(profile, DAL.generatedOperation)):
            contract = contract_for(compiled, node, guards=guards, graph_names=graph_names, edges=edge_contracts(target.dimensions["aggregateBoundary"].extra.get("ownershipTree")))
            if contract is None:
                raise KeyError(f"{example}: no builder and no hand declaration for {compiled.value(compiled.value(node, DAL.usesTemplate), DAL.templateId)}")
            name = str(compiled.value(node, DAL.forOperation))
            _emit_operation(compiled, node, target_iri, name, designed(contract, receipt_model), shape)
    return compiled


HEADER = """\
# SPDX-License-Identifier: CC-BY-SA-4.0
# Expected compiled profile of examples/{example}.ttl{variant}.
#
# What the compiler of formal-methods H2.7 will emit: today's compiled profile (without dal:templatePath, and with a dal:templateId that has no
# .mustache suffix), and for each generated
# operation its kind, builder version, guard status, parameters, resource accesses, payload and digest contracts and result
# columns. The names of the new terms are proposals. Generated by tools/persistence/tests/expected_profiles.py, and held to the
# builders by the tests under mise run check:persistence. Regenerate with:
#   mise run build:persistence-expected-profiles
"""


TEMPLATE_SUFFIX = ".mustache"


def as_expected(graph: Graph) -> Graph:
    """Today's compiled profile as the expected profile states its base: without ``dal:templatePath``, and with a ``dal:templateId`` that is
    the builder's identity and no longer names a Mustache file (decided 2026-10-13, H2.6 review question 2). The base-profile test applies the same
    two changes to the output of ``compile``, so they are the only differences it allows."""
    out = Graph()
    for s, p, o in graph:
        if p == DAL.templatePath:
            continue
        if p == DAL.templateId and isinstance(o, Literal) and str(o).endswith(TEMPLATE_SUFFIX):
            o = Literal(str(o).removesuffix(TEMPLATE_SUFFIX))
        out.add((s, p, o))
    return out


def serialise(graph: Graph) -> str:
    out = as_expected(graph)
    out.bind("dal", DAL)
    out.bind("xsd", XSD)
    return out.serialize(format="turtle")


def render_file(name: str, example: str, options: dict) -> str:
    if name == KINDS_FILE:
        g = kinds_graph()
        g.bind("xsd", XSD)
        header = HEADER.format(example="(none)", variant="").replace("Expected compiled profile of examples/(none).ttl.", "The closed enumerations the expected compiled profiles name.")
        return header + "\n" + g.serialize(format="turtle")
    variant = ""
    if options:
        variant = f", with the parameter guards {'on' if options.get('guards', True) else 'off'} and graphs named by the {options.get('graph_names', 'query')}"
    return HEADER.format(example=example, variant=variant) + "\n" + serialise(emit(example, **options))


def files() -> dict[str, str]:
    out = {f"{name}.expected.ttl": render_file(name, example, options) for name, example, options in CONFIGURATIONS}
    out[f"{KINDS_FILE}.expected.ttl"] = render_file(KINDS_FILE, KINDS_FILE, {})
    return out


def main(argv: list[str]) -> int:
    rendered = files()
    if "--write" in argv:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        for filename, text in rendered.items():
            (OUT_DIR / filename).write_text(text, encoding="utf-8")
        print(f"wrote {len(rendered)} files to {OUT_DIR}")
        return 0
    stale = [name for name, text in rendered.items() if not (OUT_DIR / name).exists() or (OUT_DIR / name).read_text(encoding="utf-8") != text]
    if stale:
        print("stale:", ", ".join(stale))
        return 1
    print("expected profiles are current")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
