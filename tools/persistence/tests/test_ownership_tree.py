# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""HO4: the ownership tree and the path compiler (formal-methods track H, slice HO4, ADR-A122).
Validation Pack: docs/developer/validation/FMH-HO4.md. Test IDs are HO4-Tn.

Nothing calls the new code from the compiler yet. HO5 switches the compiler over."""

from __future__ import annotations

import random
import uuid
from pathlib import Path

import pytest
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.collection import Collection
from rdflib.namespace import RDF, XSD

from persistence import paths
from persistence.boundary import OWNED, walk_ownership
from persistence.terms import PropertyPath, SparqlTermError

from conftest import EXAMPLES_DIR

EX = "https://example.org/projects#"
SH = "http://www.w3.org/ns/shacl#"
DAL = "https://www.nebularis.org/neuro-semantic/lattice/persistence#"
PROJECT_EXAMPLE = EXAMPLES_DIR / "composite-project-ownership.ttl"
PROJECT_DATA = Path(__file__).resolve().parent / "fixtures" / "project-data.ttl"
ROOT_SHAPE = URIRef(EX + "ProjectShape")


def _ex(name: str) -> URIRef:
    return URIRef(EX + name)


def _local(term) -> str:
    return str(term).rsplit("#", 1)[-1]


def _project_tree(graph: Graph | None = None):
    graph = graph or Graph().parse(PROJECT_EXAMPLE, format="turtle")
    return walk_ownership(graph, ROOT_SHAPE)


def _members(path_text: str, data: Graph, root: URIRef) -> set[URIRef]:
    rows = data.query(f"SELECT DISTINCT ?s WHERE {{ <{root}> {path_text} ?s }}")
    return {row[0] for row in rows}


def test_ho4_t1_the_reference_shape_is_walked_in_a_fixed_order():
    assert [_local(s) for s in _project_tree().shapes] == [
        "ProjectShape", "MilestoneShape", "PlanShape", "TaskShape", "DocumentShape", "CommentShape",
    ]


def test_ho4_t2_the_owned_edges_are_the_six_in_walk_order():
    edges = [(_local(e.step.predicate), e.step.inverse) for e in _project_tree().owned_edges()]
    assert edges == [
        ("hasMilestone", False), ("hasPlan", False), ("hasTask", False),
        ("attachment", False), ("hasSubtask", False), ("onTask", True),
    ]


def test_ho4_t3_the_member_classes_are_the_five_owned_ones():
    assert {_local(c) for c in _project_tree().member_classes()} == {"Milestone", "Plan", "Task", "Document", "Comment"}


def _relabelled(graph: Graph, seed: int) -> Graph:
    """The same graph with every blank node renamed and the triples added in another order."""
    names: dict[BNode, BNode] = {}

    def rename(term):
        return names.setdefault(term, BNode(f"x{uuid.UUID(int=random.Random(seed).getrandbits(128) ^ len(names))}")) if isinstance(term, BNode) else term

    triples = sorted(graph, key=str)
    random.Random(seed).shuffle(triples)
    out = Graph()
    for s, p, o in triples:
        out.add((rename(s), p, rename(o)))
    return out


def test_ho4_t4_the_tree_and_the_path_do_not_depend_on_how_the_shape_was_written():
    base = Graph().parse(PROJECT_EXAMPLE, format="turtle")
    reference = _project_tree(base)
    reference_path = PropertyPath.encode(reference.owned_path())
    for seed in (1, 2, 3):
        tree = _project_tree(_relabelled(base, seed))
        assert tree.shapes == reference.shapes
        assert [(e.source_shape, e.step, e.kind, e.target_shape, e.target_class) for e in tree.edges] == [
            (e.source_shape, e.step, e.kind, e.target_shape, e.target_class) for e in reference.edges
        ]
        assert PropertyPath.encode(tree.owned_path()) == reference_path


# The path, pinned after the first run and checked by eye against the shape: an optional choice of
# nothing (the project itself), a milestone alone, a milestone then a task, then any depth of subtasks,
# then optionally the task's attachment or a comment about it (an inverse step), or the plan.
GOLDEN_PATH = (
    "(<https://example.org/projects#hasMilestone>"
    "|<https://example.org/projects#hasMilestone>/<https://example.org/projects#hasTask>"
    "/(<https://example.org/projects#hasSubtask>)*"
    "/(<https://example.org/projects#attachment>|^<https://example.org/projects#onTask>)?"
    "|<https://example.org/projects#hasPlan>)?"
)


def test_ho4_t5_the_path_reaches_the_project_and_its_eight_members_and_no_other_node():
    text = PropertyPath.encode(_project_tree().owned_path())
    assert text == GOLDEN_PATH
    data = Graph().parse(PROJECT_DATA, format="turtle")
    reached = {_local(n) for n in _members(text, data, _ex("p1"))}
    assert reached == {"p1", "m1", "m2", "plan1", "t1", "t2", "t3", "docOwned", "c1"}


# ---- a property test: the compiled path against a breadth-first search of the automaton

POOL = [_ex(f"p{k}") for k in range(4)]
OTHER = _ex("other")


def _random_shapes(rng: random.Random) -> Graph:
    graph = Graph()
    count = rng.randint(1, 5)
    shapes = [_ex(f"S{i}") for i in range(count)]
    for i, shape in enumerate(shapes):
        graph.add((shape, RDF.type, URIRef(SH + "NodeShape")))
        graph.add((shape, URIRef(SH + "targetClass"), _ex(f"C{i}")))

    def add(shape, path, kind, node=None, cls=None, value=False):
        ps = BNode()
        graph.add((shape, URIRef(SH + "property"), ps))
        graph.add((ps, URIRef(SH + "path"), path))
        if value:
            graph.add((ps, URIRef(SH + "datatype"), XSD.string))
            return
        graph.add((ps, URIRef(DAL + "ownership"), URIRef(DAL + kind)))
        if node is not None:
            graph.add((ps, URIRef(SH + "node"), node))
        if cls is not None:
            graph.add((ps, URIRef(SH + "class"), cls))

    def path_for(predicate, inverse):
        if not inverse:
            return predicate
        node = BNode()
        graph.add((node, URIRef(SH + "inversePath"), predicate))
        return node

    for _ in range(rng.randint(0, 8)):
        source = rng.choice(shapes)
        target = rng.choice([None, *shapes])
        add(source, path_for(rng.choice(POOL), rng.random() < 0.3), "Owned", node=target, cls=_ex("Leaf") if target is None else None)
    for _ in range(rng.randint(0, 3)):  # references and values never extend the aggregate
        source = rng.choice(shapes)
        add(source, path_for(rng.choice(POOL), rng.random() < 0.3), "Reference", node=rng.choice(shapes))
        add(source, OTHER, "Value", value=True)
    return graph


def _random_data(rng: random.Random) -> tuple[Graph, list[URIRef]]:
    nodes = [_ex(f"n{i}") for i in range(rng.randint(2, 12))]
    data = Graph()
    for _ in range(rng.randint(0, 30)):
        data.add((rng.choice(nodes), rng.choice([*POOL, OTHER]), rng.choice(nodes)))
    return data, nodes


def _breadth_first(tree, data: Graph, root: URIRef) -> set[URIRef]:
    """Nodes reachable from ``root`` by following owned edges in the context of the shape they were reached in."""
    seen = {(root, tree.root_shape)}
    frontier = [(root, tree.root_shape)]
    while frontier:
        node, shape = frontier.pop()
        for edge in tree.owned_edges():
            if edge.source_shape != shape:
                continue
            if edge.step.inverse:
                nxt = set(data.subjects(edge.step.predicate, node))
            else:
                nxt = set(data.objects(node, edge.step.predicate))
            for target in nxt:
                state = (target, edge.target_shape or paths.LEAF)
                if state not in seen:
                    seen.add(state)
                    frontier.append(state)
    return {node for node, _ in seen}


@pytest.mark.parametrize("n", range(200))
def test_ho4_t6_the_compiled_path_reaches_what_a_breadth_first_search_of_the_automaton_does(n):
    rng = random.Random(n)
    shapes = _random_shapes(rng)
    data, nodes = _random_data(rng)
    tree = walk_ownership(shapes, _ex("S0"))
    expected = _breadth_first(tree, data, nodes[0])
    expr = tree.owned_path()
    if expr is None:
        assert not tree.owned_edges() and expected == {nodes[0]}
        return
    assert _members(PropertyPath.encode(expr), data, nodes[0]) == expected | {nodes[0]}


def test_ho4_t7_a_predicate_that_could_break_out_of_the_iri_is_refused():
    with pytest.raises(SparqlTermError):
        PropertyPath.encode(paths.Step(URIRef("urn:a>b")))


def test_ho4_t8_a_self_recursive_edge_compiles_to_a_star():
    graph = Graph()
    shape = _ex("TaskOnly")
    ps = BNode()
    graph.add((shape, URIRef(SH + "property"), ps))
    graph.add((ps, URIRef(SH + "path"), _ex("hasSubtask")))
    graph.add((ps, URIRef(SH + "node"), shape))
    graph.add((ps, URIRef(DAL + "ownership"), URIRef(DAL + "Owned")))
    text = PropertyPath.encode(walk_ownership(graph, shape).owned_path())
    assert ")*" in text
    data = Graph()
    data.add((_ex("t1"), _ex("hasSubtask"), _ex("t2")))
    data.add((_ex("t2"), _ex("hasSubtask"), _ex("t3")))
    reached = _members(text, data, _ex("t1"))
    assert reached - {_ex("t1")} == {_ex("t2"), _ex("t3")}


def test_ho4_t9_a_shape_with_no_owned_edge_has_no_path():
    graph = Graph()
    shape = _ex("Flat")
    for path, kind in ((_ex("a"), "Reference"), (_ex("b"), "Vocabulary")):
        ps = BNode()
        graph.add((shape, URIRef(SH + "property"), ps))
        graph.add((ps, URIRef(SH + "path"), path))
        graph.add((ps, URIRef(SH + "class"), _ex("Thing")))
        graph.add((ps, URIRef(DAL + "ownership"), URIRef(DAL + kind)))
    value = BNode()
    graph.add((shape, URIRef(SH + "property"), value))
    graph.add((value, URIRef(SH + "path"), _ex("c")))
    graph.add((value, URIRef(SH + "datatype"), XSD.string))
    tree = walk_ownership(graph, shape)
    assert tree.owned_path() is None and tree.owned_edges() == []


def test_ho4_t10_a_sequence_path_and_a_missing_classification_are_recorded_and_not_raised():
    graph = Graph()
    shape = _ex("Odd")
    sequence = BNode()
    Collection(graph, sequence, [_ex("a"), _ex("b")])
    first = BNode()
    graph.add((shape, URIRef(SH + "property"), first))
    graph.add((first, URIRef(SH + "path"), sequence))
    second = BNode()
    graph.add((shape, URIRef(SH + "property"), second))
    graph.add((second, URIRef(SH + "path"), _ex("c")))
    graph.add((second, URIRef(SH + "class"), _ex("Thing")))
    value = BNode()
    graph.add((shape, URIRef(SH + "property"), value))
    graph.add((value, URIRef(SH + "path"), _ex("d")))
    graph.add((value, URIRef(SH + "datatype"), XSD.string))
    graph.add((value, URIRef(DAL + "ownership"), URIRef(DAL + "Owned")))
    tree = walk_ownership(graph, shape)
    assert [(s, ps) for s, ps in tree.complex_paths] == [(shape, first)]
    assert tree.unclassified == [(shape, second, _ex("c"))]
    assert tree.ownership_on_values == [(shape, value, _ex("d"))]
    assert OWNED not in {e.kind for e in tree.edges}
