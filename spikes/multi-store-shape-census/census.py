# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""MSA-I1, the shape census. Run with ``python spikes/multi-store-shape-census/census.py`` from inside the repository.

Reads every SHACL shape the ontology tree declares, classifies each node shape by whether it could map to table rows,
then measures how many subjects of the example graphs those shapes target. Writes ``results/census.json`` and
``results/summary.md`` next to this file's directory name under the repository's ``spikes`` area, and prints the summary.
Needs rdflib only. The README states the rules and the limits.
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS
import rdflib

SPIKE = "multi-store-shape-census"
READER = Path("tools") / "lattice_repo_catalogue.py"

SH = Namespace("http://www.w3.org/ns/shacl#")
SH_NS = str(SH)

RDF_FORMATS = {".ttl": "turtle", ".trig": "trig", ".owl": "xml", ".rdf": "xml", ".nt": "nt"}
SKIP_DIRS = {"node_modules", "__pycache__", "build", "dist", "target"}
TEST_ROLES = {"test"}
SAMPLE_ROLES = {"examples", "cases"}
THRESHOLD = 80.0

TARGET_PREDICATES = [SH["targetClass"], SH["targetNode"], SH["targetSubjectsOf"], SH["targetObjectsOf"], SH["target"]]
NODE_SHAPE_PREDICATES = TARGET_PREDICATES + [
    SH["property"], SH["closed"], SH["ignoredProperties"], SH["sparql"], SH["and"], SH["or"], SH["xone"],
    SH["not"], SH["node"], SH["rule"],
]
SIMPLE_PATH_KINDS = {"predicate", "inverse"}
CRITERIA = ["not_closed", "non_simple_path", "unbounded_property", "has_or", "has_xone", "has_not", "has_sparql"]
ROW_MAPPABLE, BOUNDED_OPEN, OTHER = "row-mappable", "bounded-but-open", "other"
RANK = {ROW_MAPPABLE: 2, BOUNDED_OPEN: 1, OTHER: 0}


def import_reader():
    """The catalogue reader (STD-273), found by walking up from ``LATTICE_ROOT`` or the working directory to the
    checkout that holds it. The reader is a stand-alone file in ``tools/``, not a package, so this walk is the one place
    the spike writes a path itself. Everything after it asks the reader."""
    start = Path(os.environ.get("LATTICE_ROOT") or Path.cwd()).resolve()
    for candidate in (start, *start.parents):
        if (candidate / READER).is_file():
            sys.path.insert(0, str((candidate / READER).parent))
            import lattice_repo_catalogue  # noqa: E402
            return lattice_repo_catalogue
    raise SystemExit(f"no {READER.as_posix()} at or above {start}: run from inside the repository, or set LATTICE_ROOT")


# ---------------------------------------------------------------------------------------------------------------
# Reading files


def module_and_role(parts: Tuple[str, ...], module_names: Iterable[str]) -> Tuple[str, str]:
    """The catalogue module a path under ``ontology/`` belongs to (the longest module path that prefixes it) and the
    role directory below it. A path under no module gets a label of its own, so nothing is dropped."""
    best: Tuple[str, ...] = ()
    best_name = ""
    for name in module_names:
        wanted = tuple(name.split("/"))
        if parts[:len(wanted)] == wanted and len(wanted) > len(best):
            best, best_name = wanted, name
    if best_name:
        rest = parts[len(best):]
        return best_name, (rest[0] if len(rest) > 1 else "(root)")
    if len(parts) > 1:
        return f"ontology/{parts[0]} (no module)", parts[0]
    return "ontology (no module)", "(root)"


def walk(directory: Path) -> Iterable[Path]:
    for base, names, files in os.walk(directory):
        names[:] = sorted(n for n in names if not n.startswith(".") and n not in SKIP_DIRS and not n.endswith(".egg-info"))
        for name in sorted(files):
            if Path(name).suffix.lower() in RDF_FORMATS:
                yield Path(base) / name


def parse(path: Path) -> Graph:
    """One flat graph. A TriG file's named graphs are merged, because the census counts subjects, not graphs."""
    fmt = RDF_FORMATS[path.suffix.lower()]
    if fmt == "trig":
        dataset = rdflib.Dataset(default_union=True)
        dataset.parse(str(path), format="trig")
        flat = Graph()
        for triple in dataset.triples((None, None, None)):
            flat.add(triple)
        return flat
    g = Graph()
    g.parse(str(path), format=fmt)
    return g


# ---------------------------------------------------------------------------------------------------------------
# Reading shapes


def is_true(g: Graph, node, predicate) -> bool:
    return any(isinstance(v, Literal) and v.toPython() is True for v in g.objects(node, predicate))


def integers(g: Graph, node, predicate) -> List[int]:
    found = []
    for value in g.objects(node, predicate):
        python = value.toPython() if isinstance(value, Literal) else None
        if isinstance(python, int) and not isinstance(python, bool):
            found.append(python)
    return sorted(found)


def terms(g: Graph, node, predicate) -> List[str]:
    return sorted(str(v) if not isinstance(v, BNode) else "(blank)" for v in g.objects(node, predicate))


def count(g: Graph, node, predicate) -> int:
    return len(list(g.objects(node, predicate)))


def members(g: Graph, head) -> List[Any]:
    try:
        return list(Collection(g, head))
    except Exception:
        return []


def path_kind(g: Graph, path) -> str:
    if isinstance(path, URIRef) and path != RDF.nil:
        return "predicate"
    if g.value(path, SH["inversePath"]) is not None:
        return "inverse" if isinstance(g.value(path, SH["inversePath"]), URIRef) else "inverse-of-complex"
    if g.value(path, SH["alternativePath"]) is not None:
        return "alternative"
    if g.value(path, SH["zeroOrMorePath"]) is not None:
        return "zero-or-more"
    if g.value(path, SH["oneOrMorePath"]) is not None:
        return "one-or-more"
    if g.value(path, SH["zeroOrOnePath"]) is not None:
        return "zero-or-one"
    if g.value(path, RDF.first) is not None:
        return "sequence"
    return "unrecognised"


def path_string(g: Graph, path) -> str:
    if isinstance(path, URIRef) and path != RDF.nil:
        return str(path)
    for key, suffix in (("zeroOrMorePath", "*"), ("oneOrMorePath", "+"), ("zeroOrOnePath", "?")):
        inner = g.value(path, SH[key])
        if inner is not None:
            return f"({path_string(g, inner)}){suffix}"
    inner = g.value(path, SH["inversePath"])
    if inner is not None:
        return f"^({path_string(g, inner)})"
    inner = g.value(path, SH["alternativePath"])
    if inner is not None:
        return "(" + " | ".join(path_string(g, m) for m in members(g, inner)) + ")"
    if g.value(path, RDF.first) is not None:
        return "(" + " / ".join(path_string(g, m) for m in members(g, path)) + ")"
    return "(unrecognised)"


def shape_predicates(g: Graph, node) -> List[str]:
    """The local names of the ``sh:`` predicates a shape uses, which shows the constraint components in play."""
    return sorted({str(p)[len(SH_NS):] for p in g.predicates(node, None) if str(p).startswith(SH_NS)})


def logical_counts(g: Graph, node) -> Dict[str, int]:
    return {
        "or": count(g, node, SH["or"]), "xone": count(g, node, SH["xone"]), "not": count(g, node, SH["not"]),
        "and": count(g, node, SH["and"]), "sparql": count(g, node, SH["sparql"]),
    }


def describe_property(g: Graph, ps) -> Dict[str, Any]:
    paths = list(g.objects(ps, SH["path"]))
    if len(paths) == 1:
        kind, text = path_kind(g, paths[0]), path_string(g, paths[0])
    else:
        kind, text = ("missing" if not paths else "several"), ""
    minimum, maximum = integers(g, ps, SH["minCount"]), integers(g, ps, SH["maxCount"])
    return {
        "path": text, "path_kind": kind,
        "min_count": max(minimum) if minimum else None,
        "max_count": min(maximum) if maximum else None,
        "bounded": bool(maximum),
        "datatype": terms(g, ps, SH["datatype"]), "class": terms(g, ps, SH["class"]),
        "node_kind": terms(g, ps, SH["nodeKind"]), "node": terms(g, ps, SH["node"]),
        "has_in": (ps, SH["in"], None) in g, "has_value": (ps, SH["hasValue"], None) in g,
        "qualified": count(g, ps, SH["qualifiedValueShape"]),
        "logical": logical_counts(g, ps), "components": shape_predicates(g, ps),
        "deactivated": is_true(g, ps, SH["deactivated"]),
    }


def has_target(g: Graph, node) -> bool:
    return any((node, p, None) in g for p in TARGET_PREDICATES)


def top_level_shapes(g: Graph) -> Tuple[Set[Any], Set[Any]]:
    """The node shapes and the stand-alone property shapes of a graph. A shape counts as top level when it is an IRI or has
    a target, so the anonymous shapes inside ``sh:or``, ``sh:node`` and ``sh:property`` are not counted twice."""
    candidates = set(g.subjects(RDF.type, SH["NodeShape"]))
    for predicate in NODE_SHAPE_PREDICATES:
        candidates |= set(g.subjects(predicate, None))
    referenced_as_property = set(g.objects(None, SH["property"]))
    node_shapes, property_shapes = set(), set()
    for s in candidates:
        if isinstance(s, Literal):
            continue
        if (s, SH["path"], None) in g:
            continue
        if isinstance(s, BNode) and not has_target(g, s):
            continue
        node_shapes.add(s)
    for s in set(g.subjects(SH["path"], None)):
        if s not in referenced_as_property and has_target(g, s):
            property_shapes.add(s)
    return node_shapes, property_shapes


def facets(g: Graph, shape, unresolved: Set[Any], seen: Optional[Set[Any]] = None) -> List[Any]:
    """The shape and the shapes that also constrain its focus node: members of ``sh:and`` and values of ``sh:node``.
    A reference to an IRI that has no triples in the shapes graph is recorded as unresolved."""
    seen = seen if seen is not None else set()
    if shape in seen:
        return []
    seen.add(shape)
    found = [shape]
    referenced = []
    for head in g.objects(shape, SH["and"]):
        referenced += members(g, head)
    referenced += list(g.objects(shape, SH["node"]))
    for member in referenced:
        if isinstance(member, URIRef) and (member, None, None) not in g:
            unresolved.add(member)
            continue
        found += facets(g, member, unresolved, seen)
    return found


def targets_of(g: Graph, shape, classes: Set[str]) -> List[Dict[str, str]]:
    found = []
    for kind in ("targetClass", "targetNode", "targetSubjectsOf", "targetObjectsOf"):
        for value in g.objects(shape, SH[kind]):
            found.append({"kind": kind, "value": str(value)})
    for value in g.objects(shape, SH["target"]):
        sparql = (value, SH["select"], None) in g or (value, RDF.type, SH["SPARQLTarget"]) in g
        found.append({"kind": "target-sparql" if sparql else "target-other", "value": "(blank)" if isinstance(value, BNode) else str(value)})
    if isinstance(shape, URIRef) and str(shape) in classes:
        found.append({"kind": "implicitClass", "value": str(shape)})
    return sorted(found, key=lambda t: (t["kind"], t["value"]))


def analyse_node_shape(g: Graph, shape, classes: Set[str]) -> Dict[str, Any]:
    unresolved: Set[Any] = set()
    fs = facets(g, shape, unresolved)
    property_nodes: List[Any] = []
    for f in fs:
        for ps in sorted(g.objects(f, SH["property"]), key=lambda n: (isinstance(n, BNode), str(n))):
            if ps not in property_nodes:
                property_nodes.append(ps)
    properties = [describe_property(g, ps) for ps in property_nodes]
    properties.sort(key=lambda p: (p["path"], str(p["max_count"]), str(p["min_count"])))
    totals = Counter()
    for f in fs:
        totals.update(logical_counts(g, f))
        totals["rule"] += count(g, f, SH["rule"])
        totals["node"] += count(g, f, SH["node"])
    for p in properties:
        totals.update(p["logical"])
    closed = is_true(g, shape, SH["closed"])
    ignored = [str(i) for i in members(g, g.value(shape, SH["ignoredProperties"]))] if g.value(shape, SH["ignoredProperties"]) is not None else []
    fails = []
    if not closed:
        fails.append("not_closed")
    if any(p["path_kind"] not in SIMPLE_PATH_KINDS for p in properties):
        fails.append("non_simple_path")
    if any(not p["bounded"] for p in properties):
        fails.append("unbounded_property")
    if totals["or"]:
        fails.append("has_or")
    if totals["xone"]:
        fails.append("has_xone")
    if totals["not"]:
        fails.append("has_not")
    if totals["sparql"]:
        fails.append("has_sparql")
    if not fails:
        classification = ROW_MAPPABLE
    elif fails == ["not_closed"]:
        classification = BOUNDED_OPEN
    else:
        classification = OTHER
    return {
        "targets": targets_of(g, shape, classes),
        "closed": closed, "ignored_properties": sorted(ignored),
        "deactivated": is_true(g, shape, SH["deactivated"]),
        "facet_count": len(fs), "unresolved_references": sorted(str(u) for u in unresolved),
        "properties": properties, "property_count": len(properties),
        "logical": {k: totals[k] for k in ("or", "xone", "not", "and", "sparql", "rule", "node")},
        "components": shape_predicates(g, shape),
        "failing": fails, "classification": classification,
        "vacuous": not properties,
    }


# ---------------------------------------------------------------------------------------------------------------
# The census


class Estate:
    """Everything read from the files that are not test fixtures and not sample data."""

    def __init__(self) -> None:
        self.graph = Graph()
        self.files: Dict[str, Dict[str, Any]] = {}
        self.declared_in: Dict[Any, Set[str]] = defaultdict(set)
        self.typed_in: Dict[Any, Set[str]] = defaultdict(set)
        self.classes: Set[str] = set()
        self.supers: Dict[str, Set[str]] = defaultdict(set)


def collect(root: Path, catalogue) -> Dict[str, Any]:
    ontology = root / catalogue.area("ontology")
    module_names = sorted(catalogue.modules)
    estate = Estate()
    excluded: List[Dict[str, Any]] = []
    failures: List[Dict[str, str]] = []
    samples: List[Dict[str, Any]] = []
    scanned = 0
    for path in walk(ontology):
        rel = path.relative_to(root).as_posix()
        parts = path.relative_to(ontology).parts
        module, role = module_and_role(parts, module_names)
        info = {"file": rel, "module": module, "role": role}
        scanned += 1
        if catalogue.is_generated(rel):
            excluded.append({**info, "reason": "generated path named in the catalogue", "shapes_declared": None})
            continue
        if role in TEST_ROLES or role in SAMPLE_ROLES:
            samples.append(info)
            continue
        try:
            g = parse(path)
        except Exception as error:  # a parse failure is data, not a crash
            # The parser names the file by its absolute location, which says where this checkout sits. The repository root is cut out.
            said = str(error).replace(root.resolve().as_uri() + "/", "").replace(str(root.resolve()), "")
            failures.append({"file": rel, "error": f"{type(error).__name__}: {said[:200]}"})
            continue
        estate.files[rel] = {**info, "triples": len(g)}
        for s, p, o in g:
            estate.graph.add((s, p, o))
            if str(p).startswith(SH_NS):
                estate.declared_in[s].add(rel)
            elif p == RDF.type:
                if o in (SH["NodeShape"], SH["PropertyShape"]):
                    estate.declared_in[s].add(rel)
                    estate.typed_in[s].add(rel)
                elif o in (RDFS.Class, OWL.Class) and isinstance(s, URIRef):
                    estate.classes.add(str(s))
            elif p == RDFS.subClassOf and isinstance(s, URIRef) and isinstance(o, URIRef):
                estate.supers[str(s)].add(str(o))
    return {"estate": estate, "excluded": excluded, "failures": failures, "samples": samples, "scanned": scanned,
            "module_names": module_names}


def analyse_estate(estate: Estate, module_names: List[str]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    g = estate.graph
    node_set, property_set = top_level_shapes(g)

    def where(shape) -> Tuple[str, List[str], List[str]]:
        files = sorted(estate.declared_in.get(shape, ()))
        typed = sorted(estate.typed_in.get(shape, ()))
        primary = (typed or files or ["(unknown)"])[0]
        return primary, files, sorted({module_and_role(Path(f).relative_to("ontology").parts, module_names)[0] for f in files})

    shapes = []
    for s in node_set:
        primary, files, spanned = where(s)
        module = module_and_role(Path(primary).relative_to("ontology").parts, module_names)[0] if files else "(unknown)"
        record = analyse_node_shape(g, s, estate.classes)
        shapes.append({
            "id": str(s) if isinstance(s, URIRef) else None, "anonymous": isinstance(s, BNode),
            "module": module, "file": primary, "files": files, "modules_spanned": spanned, **record,
        })
    # An anonymous shape has no IRI. It gets an index from its content, so that the output does not depend on parser labels.
    shapes.sort(key=lambda r: (r["module"], r["file"], r["id"] or "", json.dumps(r["targets"], sort_keys=True),
                               json.dumps(r["properties"], sort_keys=True)))
    anonymous = 0
    for r in shapes:
        if r["anonymous"]:
            anonymous += 1
            r["id"] = f"(anonymous {anonymous} in {r['file']})"

    property_shapes = []
    for s in property_set:
        primary, files, spanned = where(s)
        module = module_and_role(Path(primary).relative_to("ontology").parts, module_names)[0] if files else "(unknown)"
        property_shapes.append({
            "id": str(s) if isinstance(s, URIRef) else "(anonymous)", "module": module, "file": primary,
            "targets": targets_of(g, s, estate.classes), "property": describe_property(g, s),
            "deactivated": is_true(g, s, SH["deactivated"]),
        })
    property_shapes.sort(key=lambda r: (r["module"], r["file"], r["id"], r["property"]["path"]))
    return shapes, property_shapes


class Index:
    """What each shape targets, reduced to the best classification among the shapes that share a target."""

    def __init__(self, shapes: List[Dict[str, Any]], property_shapes: List[Dict[str, Any]], ignore_vacuous: bool = False) -> None:
        """``ignore_vacuous`` ranks a shape with no property shapes as an ordinary shape, whatever else it passes."""
        self.table: Dict[str, Dict[str, int]] = {k: {} for k in ("targetClass", "targetNode", "targetSubjectsOf", "targetObjectsOf")}
        self.unevaluated = 0
        entries = [(0 if ignore_vacuous and s["vacuous"] else RANK[s["classification"]], s) for s in shapes if not s["deactivated"]]
        entries += [(0, s) for s in property_shapes if not s["deactivated"]]
        for rank, shape in entries:
            sparql = False
            for t in shape["targets"]:
                kind = "targetClass" if t["kind"] == "implicitClass" else t["kind"]
                if kind in self.table:
                    self.table[kind][t["value"]] = max(rank, self.table[kind].get(t["value"], -1))
                else:
                    sparql = True
            self.unevaluated += sparql


def ancestors(start: Iterable[str], global_supers: Dict[str, Set[str]], local_supers: Dict[str, Set[str]]) -> Set[str]:
    seen: Set[str] = set()
    stack = list(start)
    while stack:
        c = stack.pop()
        if c in seen:
            continue
        seen.add(c)
        stack.extend(global_supers.get(c, ()))
        stack.extend(local_supers.get(c, ()))
    return seen


def best_rank(index: Index, s, classes: Iterable[str], outgoing: Dict[Any, Set[str]], incoming: Dict[Any, Set[str]]) -> int:
    return max(
        [index.table["targetNode"].get(str(s), -1)]
        + [index.table["targetSubjectsOf"].get(p, -1) for p in outgoing[s]]
        + [index.table["targetObjectsOf"].get(p, -1) for p in incoming[s]]
        + [index.table["targetClass"].get(t, -1) for t in classes]
    )


def evaluate_graph(g: Graph, index: Index, supers: Dict[str, Set[str]], index_filled: Index) -> Dict[str, Any]:
    typed: Set[Any] = set()
    types: Dict[Any, Set[str]] = defaultdict(set)
    outgoing: Dict[Any, Set[str]] = defaultdict(set)
    incoming: Dict[Any, Set[str]] = defaultdict(set)
    local_supers: Dict[str, Set[str]] = defaultdict(set)
    for s, p, o in g:
        outgoing[s].add(str(p))
        if isinstance(o, (URIRef, BNode)):
            incoming[o].add(str(p))
        if p == RDF.type:
            typed.add(s)
            if isinstance(o, URIRef):
                types[s].add(str(o))
        elif p == RDFS.subClassOf and isinstance(s, URIRef) and isinstance(o, URIRef):
            local_supers[str(s)].add(str(o))
    counts = {v: Counter() for v in ("direct", "subclass")}
    unshaped_types: Counter = Counter()
    for s in sorted(typed, key=str):
        followed_types = ancestors(types[s], supers, local_supers)
        direct = best_rank(index, s, types[s], outgoing, incoming)
        followed = best_rank(index, s, followed_types, outgoing, incoming)
        filled = best_rank(index_filled, s, followed_types, outgoing, incoming)
        for variant, rank in (("direct", direct), ("subclass", followed)):
            counts[variant]["row_mappable"] += rank >= 2
            counts[variant]["bounded_or_better"] += rank >= 1
            counts[variant]["any_shape"] += rank >= 0
        counts["subclass"]["bounded_or_better_with_properties"] += filled >= 1
        if followed < 0:
            unshaped_types.update(sorted(types[s]) or ["(no named type)"])
    subjects = len(typed)
    result = {"subjects": subjects}
    for variant in ("direct", "subclass"):
        c = counts[variant]
        result[variant] = {k: c[k] for k in ("row_mappable", "bounded_or_better", "any_shape")}
        result[variant]["no_shape"] = subjects - c["any_shape"]
    result["subclass"]["bounded_or_better_with_properties"] = counts["subclass"]["bounded_or_better_with_properties"]
    return {"result": result, "unshaped_types": unshaped_types}


def aggregate_shapes(shapes: List[Dict[str, Any]], names: List[str]) -> Dict[str, Dict[str, Any]]:
    table: Dict[str, Dict[str, Any]] = {}
    for name in names:
        table[name] = {
            "node_shapes": 0, ROW_MAPPABLE: 0, BOUNDED_OPEN: 0, OTHER: 0, "closed": 0,
            "fail": {c: 0 for c in CRITERIA}, "sole_blocker": {c: 0 for c in CRITERIA},
            "properties": 0, "properties_bounded": 0, "no_properties": 0, "untargeted": 0, "sparql_targets": 0,
            "deactivated_skipped": 0,
        }
    for s in shapes:
        row = table.setdefault(s["module"], aggregate_shapes([], [s["module"]])[s["module"]])
        if s["deactivated"]:
            row["deactivated_skipped"] += 1
            continue
        row["node_shapes"] += 1
        row[s["classification"]] += 1
        row["closed"] += s["closed"]
        for c in s["failing"]:
            row["fail"][c] += 1
        if len(s["failing"]) == 1:
            row["sole_blocker"][s["failing"][0]] += 1
        row["properties"] += s["property_count"]
        row["properties_bounded"] += sum(p["bounded"] for p in s["properties"])
        row["no_properties"] += s["vacuous"]
        row["untargeted"] += not s["targets"]
        row["sparql_targets"] += any(t["kind"] == "target-sparql" for t in s["targets"])
    return table


def run() -> Dict[str, Any]:
    reader = import_reader()
    root = reader.find_root()
    catalogue = reader.load(root)
    collected = collect(root, catalogue)
    estate: Estate = collected["estate"]
    shapes, property_shapes = analyse_estate(estate, collected["module_names"])
    index = Index(shapes, property_shapes)
    index_filled = Index(shapes, property_shapes, ignore_vacuous=True)

    shape_files = sorted({f for s in shapes for f in s["files"]} | {s["file"] for s in property_shapes})
    estate_files = []
    for rel in sorted(estate.files):
        info = estate.files[rel]
        estate_files.append({
            **info,
            "node_shapes": sum(rel in s["files"] for s in shapes),
            "stand_alone_property_shapes": sum(rel == s["file"] for s in property_shapes),
        })

    graphs: List[Dict[str, Any]] = []
    module_unshaped: Dict[str, Counter] = defaultdict(Counter)
    test_files, sample_declaring = [], []
    for info in collected["samples"]:
        path = root / info["file"]
        try:
            g = parse(path)
        except Exception as error:
            collected["failures"].append({"file": info["file"], "error": f"{type(error).__name__}: {str(error)[:200]}"})
            continue
        nodes, props = top_level_shapes(g)
        declared = len(nodes) + len(props)
        if info["role"] in TEST_ROLES:
            test_files.append({**info, "shapes_declared": declared})
            continue
        if declared:
            sample_declaring.append({**info, "shapes_declared": declared})
        evaluated = evaluate_graph(g, index, estate.supers, index_filled)
        module_unshaped[info["module"]].update(evaluated["unshaped_types"])
        graphs.append({**info, **evaluated["result"], "shapes_declared": declared})
    graphs.sort(key=lambda r: (r["module"], r["file"]))

    module_order = sorted(set(collected["module_names"]) | {s["module"] for s in shapes} | {g["module"] for g in graphs})
    shape_table = aggregate_shapes(shapes, module_order)

    coverage: Dict[str, Dict[str, Any]] = {}
    for name in module_order:
        mine = [g for g in graphs if g["module"] == name]
        row: Dict[str, Any] = {"example_graphs": len(mine), "subjects": sum(g["subjects"] for g in mine)}
        for variant in ("direct", "subclass"):
            row[variant] = {k: sum(g[variant][k] for g in mine) for k in ("row_mappable", "bounded_or_better", "any_shape", "no_shape")}
        row["subclass"]["bounded_or_better_with_properties"] = sum(g["subclass"]["bounded_or_better_with_properties"] for g in mine)
        row["empty_example_graphs"] = sum(g["subjects"] == 0 for g in mine)
        row["top_unshaped_types"] = [{"type": t, "subjects": n} for t, n in sorted(module_unshaped[name].items(), key=lambda kv: (-kv[1], kv[0]))[:10]]
        coverage[name] = row
    total = {"example_graphs": len(graphs), "subjects": sum(g["subjects"] for g in graphs)}
    for variant in ("direct", "subclass"):
        total[variant] = {k: sum(g[variant][k] for g in graphs) for k in ("row_mappable", "bounded_or_better", "any_shape", "no_shape")}
    total["subclass"]["bounded_or_better_with_properties"] = sum(g["subclass"]["bounded_or_better_with_properties"] for g in graphs)
    total["empty_example_graphs"] = sum(g["subjects"] == 0 for g in graphs)

    kinds: Counter = Counter()
    bounded_kinds: Counter = Counter()
    for s in shapes:
        if s["deactivated"]:
            continue
        for p in s["properties"]:
            kinds[p["path_kind"]] += 1
            bounded_kinds[p["path_kind"]] += p["bounded"]

    live = [s for s in shapes if not s["deactivated"]]
    summary_totals = {"node_shapes": len(live), "stand_alone_property_shapes": len(property_shapes)}
    for key in (ROW_MAPPABLE, BOUNDED_OPEN, OTHER):
        summary_totals[key] = sum(s["classification"] == key for s in live)
    summary_totals["vacuous_by_class"] = {key: sum(s["vacuous"] and s["classification"] == key for s in live) for key in (ROW_MAPPABLE, BOUNDED_OPEN, OTHER)}
    summary_totals["closed"] = sum(s["closed"] for s in live)
    summary_totals["fail"] = {c: sum(c in s["failing"] for s in live) for c in CRITERIA}
    summary_totals["sole_blocker"] = {c: sum(s["failing"] == [c] for s in live) for c in CRITERIA}
    summary_totals["properties"] = sum(s["property_count"] for s in live)
    summary_totals["properties_bounded"] = sum(p["bounded"] for s in live for p in s["properties"])
    summary_totals["no_properties"] = sum(s["vacuous"] for s in live)
    summary_totals["untargeted"] = sum(not s["targets"] for s in live)
    summary_totals["sparql_targets"] = sum(any(t["kind"] == "target-sparql" for t in s["targets"]) for s in live)
    summary_totals["multi_file"] = sum(len(s["files"]) > 1 for s in live)
    summary_totals["multi_module"] = sum(len(s["modules_spanned"]) > 1 for s in live)
    summary_totals["unresolved_references"] = sum(len(s["unresolved_references"]) for s in live)
    summary_totals["deactivated_skipped"] = len(shapes) - len(live)

    return {
        "census": "MSA-I1",
        "rdflib": rdflib.__version__,
        "rules": {
            "row_mappable": "closed, every path a predicate or inverse predicate, every property has maxCount, no sh:or, sh:xone, sh:not or sh:sparql",
            "bounded_but_open": "fails only the closed criterion",
            "failing_criteria": CRITERIA,
            "threshold_percent": THRESHOLD,
        },
        "files": {
            "rdf_files_scanned": collected["scanned"],
            "estate_files": estate_files,
            "shape_files": shape_files,
            "test_fixtures_excluded": sorted(test_files, key=lambda r: r["file"]),
            "generated_excluded": collected["excluded"],
            "sample_graph_count": len(graphs),
            "sample_graphs_that_declare_shapes": sorted(sample_declaring, key=lambda r: r["file"]),
            "parse_failures": sorted(collected["failures"], key=lambda r: r["file"]),
        },
        "totals": summary_totals,
        "modules": {name: {"shapes": shape_table[name], "coverage": coverage[name]} for name in module_order},
        "coverage_total": total,
        "path_kinds": {k: {"properties": kinds[k], "bounded": bounded_kinds[k]} for k in sorted(kinds)},
        "node_shapes": shapes,
        "stand_alone_property_shapes": property_shapes,
        "sample_graphs": graphs,
        "_root": root,
        "_spike_directory": root / catalogue.area("spikes") / SPIKE,
    }


# ---------------------------------------------------------------------------------------------------------------
# Output


def percent(part: int, whole: int) -> str:
    return "n/a" if whole == 0 else f"{100.0 * part / whole:.1f}"


def table(header: List[str], rows: List[List[Any]]) -> List[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return lines


def render_summary(r: Dict[str, Any]) -> str:
    t = r["totals"]
    f = r["files"]
    c = r["coverage_total"]
    lines = ["<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->", "", "# Shape census results", ""]
    lines += [
        "Produced by `census.py`. The README states what is measured and what the method cannot show. Percentages are of subjects with an `rdf:type`, summed over the example graphs of a module.",
        "",
        "## Estate",
        "",
    ]
    lines += table(["Item", "Count"], [
        ["RDF files scanned under ontology", f["rdf_files_scanned"]],
        ["Files read as shapes estate (not test, not sample)", len(f["estate_files"])],
        ["Files that declare at least one shape", len(f["shape_files"])],
        ["Test fixture files excluded", len(f["test_fixtures_excluded"])],
        ["Example graphs used as samples", f["sample_graph_count"]],
        ["Sample graphs with no typed subject", c["empty_example_graphs"]],
        ["Example graphs that also declare shapes", len(f["sample_graphs_that_declare_shapes"])],
        ["Parse failures", len(f["parse_failures"])],
        ["Node shapes counted", t["node_shapes"]],
        ["Stand-alone property shapes (not classified)", t["stand_alone_property_shapes"]],
        ["Deactivated node shapes skipped", t["deactivated_skipped"]],
    ])
    lines += ["", "## Classification of node shapes", ""]
    lines += table(["Module", "Shapes", "Row-mappable", "Bounded but open", "Other", "Closed", "Not closed", "Non-simple path", "Unbounded property", "or", "xone", "not", "sparql"], [
        [name, m["shapes"]["node_shapes"], m["shapes"][ROW_MAPPABLE], m["shapes"][BOUNDED_OPEN], m["shapes"][OTHER], m["shapes"]["closed"]]
        + [m["shapes"]["fail"][k] for k in CRITERIA]
        for name, m in r["modules"].items() if m["shapes"]["node_shapes"]
    ] + [["all", t["node_shapes"], t[ROW_MAPPABLE], t[BOUNDED_OPEN], t[OTHER], t["closed"]] + [t["fail"][k] for k in CRITERIA]])
    lines += [
        "",
        "The criterion columns count the shapes that fail that criterion, so a shape that fails two is counted in both.",
        "",
        "Shapes whose only failing criterion is the one named:",
        "",
    ]
    lines += table(["Criterion", "Shapes failing it", "Shapes failing only it"], [[k, t["fail"][k], t["sole_blocker"][k]] for k in CRITERIA])
    lines += ["", "## Property shapes", ""]
    lines += table(["Path kind", "Property shapes", "With maxCount"], [[k, v["properties"], v["bounded"]] for k, v in r["path_kinds"].items()])
    lines += [
        "",
        f"Of {t['properties']} property shapes inside node shapes, {t['properties_bounded']} carry a `sh:maxCount`. {t['no_properties']} node shapes have no property shapes, and {t['vacuous_by_class'][BOUNDED_OPEN]} of the bounded-but-open shapes are among them. Those carry no constraint on the shape of a row, so a second coverage figure below leaves them out.",
        "",
        "## Coverage of example subjects",
        "",
        "The columns give the share of subjects targeted by a shape of the class named. Subclass following uses the `rdfs:subClassOf` triples of the ontology files and of the example graph itself. The direct columns do not follow subclasses.",
        "",
    ]
    rows = []
    for name, m in r["modules"].items():
        cv = m["coverage"]
        if not cv["example_graphs"]:
            continue
        n = cv["subjects"]
        rows.append([name, cv["example_graphs"], n, percent(cv["direct"]["row_mappable"], n), percent(cv["subclass"]["row_mappable"], n),
                     percent(cv["subclass"]["bounded_or_better"], n), percent(cv["subclass"]["bounded_or_better_with_properties"], n), percent(cv["direct"]["any_shape"], n),
                     percent(cv["subclass"]["any_shape"], n), percent(cv["subclass"]["no_shape"], n)])
    n = c["subjects"]
    rows.append(["all", c["example_graphs"], n, percent(c["direct"]["row_mappable"], n), percent(c["subclass"]["row_mappable"], n),
                 percent(c["subclass"]["bounded_or_better"], n), percent(c["subclass"]["bounded_or_better_with_properties"], n), percent(c["direct"]["any_shape"], n),
                 percent(c["subclass"]["any_shape"], n), percent(c["subclass"]["no_shape"], n)])
    lines += table(["Module", "Graphs", "Subjects", "Row-mappable, direct %", "Row-mappable, subclass %", "Bounded or better, subclass %",
                    "Bounded or better, with properties, subclass %", "Any shape, direct %", "Any shape, subclass %", "No shape, subclass %"], rows)
    meeting = [name for name, m in r["modules"].items() if m["coverage"]["subjects"] and 100.0 * m["coverage"]["subclass"]["row_mappable"] / m["coverage"]["subjects"] >= THRESHOLD]
    lines += [
        "",
        f"The proposed threshold is {THRESHOLD:.0f}% of subjects covered by row-mappable shapes, per module. "
        + ("Modules at or above it with subclasses followed: " + ", ".join(meeting) + "." if meeting else "No module reaches it with subclasses followed."),
        "",
        "## Limits seen in this run",
        "",
        "Counts for the run, each of which bears on how far the figures can be trusted:",
        "",
    ]
    lines += table(["Item", "Count"], [
        ["Node shapes with no target of their own, reached only through other shapes", t["untargeted"]],
        ["Node shapes with a SPARQL target, not evaluated, so no-shape shares are upper bounds", t["sparql_targets"]],
        ["Node shapes declared in more than one file, analysed as the union of the declarations", t["multi_file"]],
        ["Node shapes declared across more than one module", t["multi_module"]],
        ["References through sh:and or sh:node to an IRI with no triples in any file read", t["unresolved_references"]],
    ])
    if f["parse_failures"]:
        lines += ["", "Files that did not parse:", ""] + [f"- `{p['file']}`, {p['error']}" for p in f["parse_failures"]]
    if f["sample_graphs_that_declare_shapes"]:
        lines += ["", "Example graphs that declare shapes of their own, counted as sample data and not as shapes estate:", ""]
        lines += [f"- `{p['file']}`, {p['shapes_declared']} shapes" for p in f["sample_graphs_that_declare_shapes"]]
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    result = run()
    directory: Path = result.pop("_spike_directory")
    result.pop("_root")
    out = directory / "results"
    out.mkdir(parents=True, exist_ok=True)
    (out / "census.json").write_text(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8", newline="\n")
    summary = render_summary(result)
    (out / "summary.md").write_text(summary, encoding="utf-8", newline="\n")
    print(summary)
    print(f"wrote {out.as_posix()}/census.json and summary.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
