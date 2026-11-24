# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""MSA-I10, two families in one mapping vocabulary. Run with ``python spikes/multi-store-mapping/mapping.py`` from inside
the repository.

Reads the two R2RML mappings beside this file, the ledger's records and one promotion's derived family, each with its
relational place stated in the spike's place terms (``place.ttl``). Emits each family's places from its mapping, checks
that both are written in one vocabulary, that every column holds a key part of a logical resource, a field or a derived
value, that the ledger's mapping covers every record its runtime vocabulary declares but the supersession, which is held,
and that each family reads both ways: the records of every example encoded to rows by inverting the mapping, the rows
checked against the place's keys, and decoded by R2RML's rules to the same triples. Writes ``results/places.md`` and
prints the report. Needs rdflib only. Interprets the subset of R2RML the two mappings use and refuses the rest.
"""

from __future__ import annotations

import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, XSD
from rdflib.paths import InvPath, SequencePath
from rdflib.term import Node

SPIKE = "multi-store-mapping"
READER = Path("tools") / "lattice_repo_catalogue.py"

RR = Namespace("http://www.w3.org/ns/r2rml#")
RP = Namespace("https://example.org/lattice/spike/relational-place#")
DAL = Namespace("https://www.nebularis.org/neuro-semantic/lattice/persistence#")
LDG = Namespace("https://www.nebularis.org/neuro-semantic/lattice/ledger#")
SRF = Namespace("https://www.nebularis.org/neuro-semantic/lattice/surface#")

R2RML_TERMS = frozenset(RR[n] for n in (
    "BaseTableOrView", "BlankNode", "GraphMap", "IRI", "Join", "Literal", "LogicalTable", "ObjectMap", "PredicateMap",
    "PredicateObjectMap", "R2RMLView", "RefObjectMap", "SQL2008", "SubjectMap", "TermMap", "TriplesMap", "child", "class",
    "column", "constant", "datatype", "defaultGraph", "graph", "graphMap", "inverseExpression", "joinCondition", "language",
    "logicalTable", "object", "objectMap", "parent", "parentTriplesMap", "predicate", "predicateMap", "predicateObjectMap",
    "sqlQuery", "sqlVersion", "subject", "subjectMap", "tableName", "template", "termType",
))
"""Every term of the R2RML vocabulary, so a term outside it and outside the place terms is reported."""

UNSUPPORTED = frozenset(RR[n] for n in (
    "sqlQuery", "joinCondition", "parentTriplesMap", "graphMap", "graph", "language", "predicateMap", "subject", "object",
    "inverseExpression",
))
"""The R2RML constructs this interpreter does not implement. A mapping that uses one is refused, never half read."""

HELD_CLASSES = frozenset({LDG.Supersession})
"""Held until the ledger's LG-Q58 decides whether a supersession names its owner or an account."""

ANNOTATIONS = frozenset({RDFS.comment, RDFS.label})

SQL_TYPES = {XSD.decimal: "numeric", XSD.integer: "numeric", XSD.nonNegativeInteger: "bigint", XSD.boolean: "boolean",
             XSD.string: "text"}
INTEGER_TYPES = frozenset({XSD.integer, XSD.nonNegativeInteger})
KEY_PART_RECORD, KEY_PART_VALUE = "record", "value"


class MappingRefused(ValueError):
    """A mapping that uses a construct this interpreter does not implement."""


class NotRepresentable(ValueError):
    """A term that the column a mapping gives it cannot hold."""


# ---------------------------------------------------------------------------------------------------------------
# Reading a mapping and its places


@dataclass(frozen=True)
class TermMap:
    column: Optional[str] = None
    template: Optional[str] = None
    constant: Optional[Node] = None
    term_type: URIRef = RR.IRI
    datatype: Optional[URIRef] = None

    def columns(self) -> Tuple[str, ...]:
        if self.column:
            return (self.column,)
        if self.template:
            return tuple(re.findall(r"\{([^{}]+)\}", self.template))
        return ()


@dataclass(frozen=True)
class PredicateObject:
    predicate: URIRef
    obj: TermMap


@dataclass(frozen=True)
class TriplesMap:
    node: Node
    table: str
    subject: TermMap
    classes: Tuple[URIRef, ...]
    poms: Tuple[PredicateObject, ...]


@dataclass(frozen=True)
class Derived:
    column: str
    sql_type: str
    rule: str
    from_column: str
    via_path: Optional[str] = None
    value_class: Optional[URIRef] = None
    from_template: Optional[str] = None
    same_as: Optional[str] = None


@dataclass(frozen=True)
class ForeignKey:
    columns: Tuple[str, ...]
    table: str
    ref_columns: Tuple[str, ...]


@dataclass
class Column:
    name: str
    sql_type: str = "text"
    not_null: bool = False
    key_parts: List[Tuple[URIRef, str]] = field(default_factory=list)
    fields: List[str] = field(default_factory=list)
    derived: Optional[Derived] = None
    datatype: Optional[URIRef] = None


@dataclass
class Place:
    table: str
    primary_key: Tuple[str, ...]
    uniques: List[Tuple[str, ...]]
    uniques_nulls_not_distinct: List[Tuple[str, ...]]
    not_null: Tuple[str, ...]
    key_parts: List[Tuple[str, URIRef, str]]
    derived: Dict[str, Derived]
    foreign_keys: List[ForeignKey]
    columns: Dict[str, Column] = field(default_factory=dict)

    def identity(self) -> Tuple[str, ...]:
        """The key columns that name a row within its root: the record, and a value where a field holds several."""
        parts = {c for c, _, part in self.key_parts if part in (KEY_PART_RECORD, KEY_PART_VALUE)}
        return tuple(c for c in self.primary_key if c in parts)

    def record_column(self) -> Optional[str]:
        return next((c for c, _, part in self.key_parts if part == KEY_PART_RECORD), None)


@dataclass
class Mapping:
    name: str
    graph: Graph
    maps: List[TriplesMap]
    places: Dict[str, Place]

    def qname(self, term: Node) -> str:
        if not isinstance(term, URIRef):
            return term.n3() if isinstance(term, Literal) else str(term)
        try:
            return self.graph.namespace_manager.normalizeUri(term)
        except Exception:  # noqa: BLE001 - a term with no prefix is shown whole
            return str(term)

    def record_class(self, table: str) -> Optional[URIRef]:
        record = self.places[table].record_column()
        for tm in self.maps:
            if tm.table == table and tm.classes and tm.subject.column == record:
                return tm.classes[0]
        return None

    def subject_class(self, tm: TriplesMap) -> Optional[URIRef]:
        """The class of the records a map's subjects are: its own class, its table's record class where the subject is the
        record column, or the record class a foreign key from the subject column reaches."""
        if tm.classes:
            return tm.classes[0]
        place, column = self.places[tm.table], tm.subject.column
        if column is not None and column == place.record_column() and self.record_class(tm.table):
            return self.record_class(tm.table)
        for fk in place.foreign_keys:
            if column in fk.columns:
                ref = fk.ref_columns[fk.columns.index(column)]
                if ref == self.places[fk.table].record_column() and self.record_class(fk.table):
                    return self.record_class(fk.table)
        return None


def _list(g: Graph, node: Node) -> Tuple[str, ...]:
    return tuple(str(x) for x in Collection(g, node))


def _one(g: Graph, s: Node, p: URIRef) -> Optional[Node]:
    values = list(g.objects(s, p))
    if len(values) > 1:
        raise MappingRefused(f"{s} has {len(values)} values of {p}, expected at most one")
    return values[0] if values else None


def _term_map(g: Graph, node: Node, default_type: URIRef) -> TermMap:
    column, template, constant = _one(g, node, RR.column), _one(g, node, RR.template), _one(g, node, RR.constant)
    datatype = _one(g, node, RR.datatype)
    term_type = _one(g, node, RR.termType)
    if term_type is None:
        # R2RML: an object map is a literal by default where it reads a column or states a datatype, and an IRI otherwise.
        # Every other term map is an IRI by default.
        is_literal = default_type == RR.Literal and (column is not None or datatype is not None)
        term_type = RR.Literal if is_literal else RR.IRI
    return TermMap(column=str(column) if column else None, template=str(template) if template else None, constant=constant,
                   term_type=URIRef(term_type), datatype=URIRef(datatype) if datatype else None)


def load_mapping(name: str, g: Graph) -> Mapping:
    used = set(g.predicates())
    refused = sorted(str(t) for t in used & UNSUPPORTED)
    if refused:
        raise MappingRefused(f"{name} uses R2RML constructs this interpreter does not implement: {', '.join(refused)}")
    places: Dict[str, Place] = {}
    table_of: Dict[Node, str] = {}
    for lt in sorted(g.subjects(RR.tableName, None), key=str):
        table = str(_one(g, lt, RR.tableName))
        table_of[lt] = table
    for lt, table in table_of.items():
        pk = _one(g, lt, RP.primaryKey)
        nn = _one(g, lt, RP.notNull)
        key_parts = sorted(
            (str(_one(g, kp, RP.column)), URIRef(_one(g, kp, RP.resource)), str(_one(g, kp, RP.part)))
            for kp in g.objects(lt, RP.keyPart)
        )
        derived = {}
        for d in g.objects(lt, RP.derived):
            item = Derived(
                column=str(_one(g, d, RP.column)), sql_type=str(_one(g, d, RP.sqlType) or "text"), rule=str(_one(g, d, RP.rule) or ""),
                from_column=str(_one(g, d, RP.fromColumn)),
                via_path=str(_one(g, d, RP.viaPath)) if _one(g, d, RP.viaPath) else None,
                value_class=URIRef(_one(g, d, RP.valueClass)) if _one(g, d, RP.valueClass) else None,
                from_template=str(_one(g, d, RP.fromIriTemplate)) if _one(g, d, RP.fromIriTemplate) else None,
                same_as=str(_one(g, d, RP.sameAsColumn)) if _one(g, d, RP.sameAsColumn) else None,
            )
            derived[item.column] = item
        fks = sorted(
            (ForeignKey(_list(g, _one(g, fk, RP.columns)), table_of[_one(g, fk, RP.references)], _list(g, _one(g, fk, RP.refColumns)))
             for fk in g.objects(lt, RP.foreignKey)),
            key=lambda f: (f.columns, f.table),
        )
        places[table] = Place(
            table=table, primary_key=_list(g, pk) if pk else (),
            uniques=sorted(_list(g, u) for u in g.objects(lt, RP.unique)),
            uniques_nulls_not_distinct=sorted(_list(g, u) for u in g.objects(lt, RP.uniqueNullsNotDistinct)),
            not_null=_list(g, nn) if nn else (), key_parts=key_parts, derived=derived, foreign_keys=fks,
        )
    maps = []
    for tm in sorted(g.subjects(RR.logicalTable, None), key=str):
        lt = _one(g, tm, RR.logicalTable)
        if lt not in table_of:
            raise MappingRefused(f"{tm}'s logical table names no table")
        sm = _one(g, tm, RR.subjectMap)
        subject = _term_map(g, sm, RR.IRI)
        classes = tuple(sorted(URIRef(c) for c in g.objects(sm, RR["class"])))
        poms = []
        for pom in g.objects(tm, RR.predicateObjectMap):
            om = _one(g, pom, RR.objectMap)
            for p in g.objects(pom, RR.predicate):
                poms.append(PredicateObject(URIRef(p), _term_map(g, om, RR.Literal)))
        maps.append(TriplesMap(tm, table_of[lt], subject, classes, tuple(sorted(poms, key=lambda x: str(x.predicate)))))
    return Mapping(name, g, maps, places)


def build_columns(mapping: Mapping, minimum: Dict[Tuple[URIRef, URIRef], int]) -> None:
    """Emit each place's columns from the mapping: a column for each column a term map reads, typed by the term map, and
    one for each derived column. The place's annotations give only what R2RML cannot say."""
    for place in mapping.places.values():
        place.columns = {}

    def column(table: str, name: str) -> Column:
        return mapping.places[table].columns.setdefault(name, Column(name))

    for tm in mapping.maps:
        subject_class = mapping.subject_class(tm)
        for name in tm.subject.columns():
            col = column(tm.table, name)
            if tm.classes:
                col.fields.append(f"the {', '.join(mapping.qname(c) for c in tm.classes)} record")
            else:
                col.fields.extend(f"subject of {mapping.qname(p.predicate)}" for p in tm.poms)
        for pom in tm.poms:
            for name in pom.obj.columns():
                col = column(tm.table, name)
                col.fields.append(mapping.qname(pom.predicate))
                if pom.obj.term_type == RR.Literal and pom.obj.datatype is not None:
                    col.sql_type = SQL_TYPES.get(pom.obj.datatype, "text")
                    col.datatype = pom.obj.datatype
                if subject_class is not None and minimum.get((subject_class, pom.predicate), 0) >= 1:
                    col.not_null = True
    for place in mapping.places.values():
        for d in place.derived.values():
            col = column(place.table, d.column)
            col.derived, col.sql_type, col.not_null = d, d.sql_type, True
        for name, resource, part in place.key_parts:
            column(place.table, name).key_parts.append((resource, part))
        for name in (*place.primary_key, *place.not_null):
            column(place.table, name).not_null = True


# ---------------------------------------------------------------------------------------------------------------
# What the vocabularies hold


def vocabulary_terms(g: Graph) -> Set[URIRef]:
    """The mapping-language terms a mapping uses: its predicates, its classes and its term types. Lists are RDF's."""
    terms = {p for p in g.predicates() if p not in (RDF.type, RDF.first, RDF.rest)}
    terms |= {o for o in g.objects(None, RDF.type)}
    terms |= {o for o in g.objects(None, RR.termType)}
    return {URIRef(t) for t in terms}


def declared_place_terms(g: Graph) -> Set[URIRef]:
    return {URIRef(s) for s in g.subjects(RDF.type, RDF.Property) if str(s).startswith(str(RP))}


@dataclass
class Ontology:
    classes: Set[URIRef]
    properties: Dict[URIRef, Set[URIRef]]
    minimum: Dict[Tuple[URIRef, URIRef], int]


def read_runtime_ontology(g: Graph) -> Ontology:
    """The records the ledger's runtime vocabulary declares, the domain of each property, and the least count of each
    property on each class its restrictions state."""
    classes = {URIRef(c) for c in g.subjects(RDF.type, OWL.Class) if str(c).startswith(str(LDG))}
    properties: Dict[URIRef, Set[URIRef]] = {}
    for kind in (OWL.ObjectProperty, OWL.DatatypeProperty):
        for p in g.subjects(RDF.type, kind):
            if not str(p).startswith(str(LDG)):
                continue
            domains = set()
            for d in g.objects(p, RDFS.domain):
                members = g.value(d, OWL.unionOf)
                domains |= {URIRef(x) for x in Collection(g, members)} if members is not None else {URIRef(d)}
            properties[URIRef(p)] = domains
    minimum: Dict[Tuple[URIRef, URIRef], int] = {}
    for c in classes:
        for r in g.objects(c, RDFS.subClassOf):
            p = g.value(r, OWL.onProperty)
            if p is None:
                continue
            n = g.value(r, OWL.cardinality) or g.value(r, OWL.minCardinality)
            if n is not None:
                minimum[(c, URIRef(p))] = int(n)
    return Ontology(classes, properties, minimum)


def coverage(mapping: Mapping, ontology: Ontology) -> Tuple[List[str], List[str]]:
    """What the runtime vocabulary declares that the mapping does not map, and what it holds back on purpose."""
    missing, held = [], []
    mapped_classes = {c for tm in mapping.maps for c in tm.classes}
    pairs = {(mapping.subject_class(tm), pom.predicate) for tm in mapping.maps for pom in tm.poms}
    for c in sorted(ontology.classes, key=str):
        if c in HELD_CLASSES:
            held.append(f"{mapping.qname(c)}, the record")
        elif c not in mapped_classes:
            missing.append(f"{mapping.qname(c)} has no map")
    for p, domains in sorted(ontology.properties.items(), key=lambda x: str(x[0])):
        for c in sorted(domains & ontology.classes, key=str):
            if c in HELD_CLASSES:
                held.append(f"{mapping.qname(p)} on {mapping.qname(c)}")
            elif (c, p) not in pairs:
                missing.append(f"{mapping.qname(p)} on {mapping.qname(c)} has no column")
    return missing, held


def column_problems(mapping: Mapping) -> List[str]:
    """A column that holds nothing a profile could name, or a key column that holds no key part."""
    problems = []
    for place in mapping.places.values():
        for col in place.columns.values():
            if not (col.key_parts or col.fields or col.derived):
                problems.append(f"{place.table}.{col.name} holds no key part, field or derived value")
            if col.name in place.primary_key and not col.key_parts:
                problems.append(f"{place.table}.{col.name} is a key column and holds no key part of a logical resource")
        for name in (*place.primary_key, *place.not_null, *[c for u in place.uniques for c in u]):
            if name not in place.columns:
                problems.append(f"{place.table} names a column {name} that no term map reads and no rule derives")
        for fk in place.foreign_keys:
            if fk.table not in mapping.places or any(c not in mapping.places[fk.table].columns for c in fk.ref_columns):
                problems.append(f"{place.table}'s key {fk.columns} references columns {fk.table} does not have")
    return problems


# ---------------------------------------------------------------------------------------------------------------
# Encoding a graph to rows, and decoding rows by R2RML's rules


def canonical_decimal(value: Decimal) -> str:
    if value == value.to_integral_value():
        return str(int(value))
    return format(value.normalize(), "f")


def sql_value(term: Node, tm: TermMap):
    if tm.term_type == RR.IRI:
        if not isinstance(term, URIRef):
            raise NotRepresentable(f"{term!r} is not an IRI")
        return str(term)
    if not isinstance(term, Literal) or term.language is not None:
        raise NotRepresentable(f"{term!r} is not a literal without a language")
    datatype = tm.datatype or XSD.string
    if (term.datatype or XSD.string) != datatype:
        raise NotRepresentable(f"{term!r} is not of the column's datatype {datatype}")
    lexical = str(term)
    try:
        if datatype in INTEGER_TYPES:
            return int(lexical)
        if datatype == XSD.decimal:
            return Decimal(lexical)
    except (ValueError, InvalidOperation) as error:
        raise NotRepresentable(f"{term!r} is not a value of {datatype}") from error
    return lexical


def iri_safe(value: str) -> str:
    """R2RML's IRI-safe form of a value inserted into a template: every character outside iunreserved percent-encoded."""
    out = []
    for ch in value:
        if ch.isalnum() and ord(ch) < 128 or ch in "-._~" or ord(ch) >= 128:
            out.append(ch)
        else:
            out.extend(f"%{b:02X}" for b in ch.encode("utf-8"))
    return "".join(out)


def generated_term(tm: TermMap, row: Dict[str, object]) -> Optional[Node]:
    if tm.constant is not None:
        return tm.constant
    if tm.template is not None:
        values = {c: row.get(c) for c in tm.columns()}
        if any(v is None for v in values.values()):
            return None
        text = re.sub(r"\{([^{}]+)\}", lambda m: iri_safe(_lexical(values[m.group(1)])) if tm.term_type == RR.IRI
                      else _lexical(values[m.group(1)]), tm.template)
        return URIRef(text) if tm.term_type == RR.IRI else Literal(text, datatype=tm.datatype)
    value = row.get(tm.column)
    if value is None:
        return None
    if tm.term_type == RR.IRI:
        return URIRef(str(value))
    return Literal(_lexical(value), datatype=tm.datatype) if tm.datatype else Literal(_lexical(value))


def _lexical(value: object) -> str:
    if isinstance(value, Decimal):
        return canonical_decimal(value)
    return str(value)


@dataclass
class Encoding:
    rows: Dict[str, Dict[Tuple, Dict[str, object]]]
    problems: List[str]
    excluded: Counter
    mapped: Set[Tuple[Node, Node, Node]]


def encode(mapping: Mapping, triples: Iterable[Tuple[Node, Node, Node]], source: Graph) -> Encoding:
    """The rows a set of triples is stored as, found by inverting the mapping: each triple goes to the one column whose
    predicate and subject class match, in the row its record, and its value where a field holds several, identify. The
    derived columns are filled after, by the rules the place states."""
    rows: Dict[str, Dict[Tuple, Dict[str, object]]] = defaultdict(dict)
    problems: List[str] = []
    excluded: Counter = Counter()
    mapped: Set[Tuple[Node, Node, Node]] = set()
    triples = sorted(set(triples), key=lambda t: tuple(str(x) for x in t))

    def put(table: str, values: Dict[str, object], what: str) -> bool:
        place = mapping.places[table]
        identity = place.identity()
        if any(c not in values for c in identity):
            problems.append(f"{what}: no row of {table} is identified, its key {identity} is not bound")
            return False
        key = tuple(values[c] for c in identity)
        row = rows[table].setdefault(key, {})
        for c, v in values.items():
            if c in row and row[c] != v:
                problems.append(f"{what}: {table}.{c} already holds {row[c]!r}, so the property is not functional here")
                return False
            row[c] = v
        return True

    typed = {(s, o) for s, p, o in triples if p == RDF.type}
    for s, p, o in triples:
        what = f"{mapping.qname(s)} {mapping.qname(p)} {mapping.qname(o)}"
        if p == RDF.type:
            maps = [tm for tm in mapping.maps if o in tm.classes]
            if not maps:
                excluded["a type no map states"] += 1
                continue
            for tm in maps:
                if put(tm.table, {tm.subject.column: str(s)}, what):
                    mapped.add((s, p, o))
            continue
        candidates = [
            (tm, pom) for tm in mapping.maps for pom in tm.poms
            if pom.predicate == p and (mapping.subject_class(tm) is None or (s, mapping.subject_class(tm)) in typed)
        ]
        if not candidates:
            excluded[f"an annotation, {mapping.qname(p)}" if p in ANNOTATIONS else "a property no map states"] += 1
            if p not in ANNOTATIONS:
                problems.append(f"{what}: no column holds it")
            continue
        if len(candidates) > 1:
            problems.append(f"{what}: {len(candidates)} columns could hold it")
            continue
        tm, pom = candidates[0]
        try:
            values = {tm.subject.column: sql_value(s, tm.subject)}
            if pom.obj.constant is not None:
                if o != pom.obj.constant:
                    raise NotRepresentable(f"{o!r} is not the constant {pom.obj.constant!r}")
            else:
                values[pom.obj.column] = sql_value(o, pom.obj)
        except NotRepresentable as error:
            problems.append(f"{what}: {error}")
            continue
        if put(tm.table, values, what):
            mapped.add((s, p, o))

    for table, place in mapping.places.items():
        for row in rows[table].values():
            for d in place.derived.values():
                value, problem = derive(d, row, source, mapping)
                if problem:
                    problems.append(f"{table}.{d.column} of {row.get(d.from_column)}: {problem}")
                row[d.column] = value
    problems.extend(constraint_problems(mapping, rows))
    return Encoding(dict(rows), problems, excluded, mapped)


def derive(d: Derived, row: Dict[str, object], source: Graph, mapping: Mapping) -> Tuple[Optional[str], Optional[str]]:
    start = row.get(d.from_column)
    if start is None:
        return None, f"the column {d.from_column} the rule starts from is empty"
    if d.same_as is not None:
        return row.get(d.same_as), None
    if d.from_template is not None:
        names = re.findall(r"\{([^{}]+)\}", d.from_template)
        pattern = "^" + re.sub(r"\\\{([^{}]+)\\\}", lambda m: f"(?P<{m.group(1)}>.+?)" if m.group(1) != names[-1] else f"(?P<{m.group(1)}>[^/]+)",
                               re.escape(d.from_template)) + "$"
        found = re.match(pattern, str(start))
        return (found.group(d.column), None) if found else (None, f"{start} was not built by {d.from_template}")
    query = f"SELECT DISTINCT ?v WHERE {{ ?s {d.via_path} ?v . " + ("?v a ?class . }" if d.value_class else "}")
    bindings = {"s": URIRef(str(start))}
    if d.value_class:
        bindings["class"] = d.value_class
    namespaces = dict(mapping.graph.namespace_manager.namespaces())
    values = sorted(str(r[0]) for r in source.query(query, initNs=namespaces, initBindings=bindings))
    if len(values) != 1:
        return (values[0] if values else None), f"{d.via_path} reaches {len(values)} values, expected one"
    return values[0], None


def constraint_problems(mapping: Mapping, rows: Dict[str, Dict[Tuple, Dict[str, object]]]) -> List[str]:
    """The place's constraints checked on the encoded rows, as the store would check them at commit."""
    problems = []
    for table, place in mapping.places.items():
        table_rows = list(rows.get(table, {}).values())
        for row in table_rows:
            for col in place.columns.values():
                value = row.get(col.name)
                if col.not_null and value is None:
                    problems.append(f"{table}.{col.name} is empty on {row.get(place.record_column() or '')}")
                if col.datatype == XSD.nonNegativeInteger and value is not None and value < 0:
                    problems.append(f"{table}.{col.name} is below 0")

        def check_unique(cols: Sequence[str], nulls_distinct: bool, label: str) -> None:
            seen = Counter()
            for row in table_rows:
                values = tuple(row.get(c) for c in cols)
                if nulls_distinct and any(v is None for v in values):
                    continue
                seen[values] += 1
            for values, n in seen.items():
                if n > 1:
                    problems.append(f"{table} {label} {cols} holds {values} {n} times")

        check_unique(place.primary_key, False, "primary key")
        for u in place.uniques:
            check_unique(u, True, "unique")
        for u in place.uniques_nulls_not_distinct:
            check_unique(u, False, "unique, nulls not distinct,")
        for fk in place.foreign_keys:
            targets = {tuple(r.get(c) for c in fk.ref_columns) for r in rows.get(fk.table, {}).values()}
            for row in table_rows:
                values = tuple(row.get(c) for c in fk.columns)
                if any(v is None for v in values):
                    continue
                if values not in targets:
                    problems.append(f"{table} {fk.columns} = {values} has no row of {fk.table} {fk.ref_columns}")
    return problems


def decode(mapping: Mapping, rows: Dict[str, Dict[Tuple, Dict[str, object]]]) -> Graph:
    """The triples the rows decode to, by R2RML's rules for the subset the mappings use."""
    g = Graph()
    for tm in mapping.maps:
        for row in rows.get(tm.table, {}).values():
            s = generated_term(tm.subject, row)
            if s is None:
                continue
            for c in tm.classes:
                g.add((s, RDF.type, c))
            for pom in tm.poms:
                o = generated_term(pom.obj, row)
                if o is not None:
                    g.add((s, pom.predicate, o))
    return g


# ---------------------------------------------------------------------------------------------------------------
# The families


def ledger_triples(g: Graph, mapping: Mapping) -> Tuple[List[Tuple[Node, Node, Node]], int]:
    """The triples of the ledger's records in an example, and the count held back with the supersession."""
    classes = {c for tm in mapping.maps for c in tm.classes}
    records = {s for c in classes for s in g.subjects(RDF.type, c)}
    held = {s for c in HELD_CLASSES for s in g.subjects(RDF.type, c)}
    family = [t for t in g if t[0] in records and t[0] not in held]
    return family, sum(1 for t in g if t[0] in held)


def promotion_triples(g: Graph) -> Tuple[URIRef, List[Tuple[Node, Node, Node]]]:
    """The derived family of the one promotion contract in the graph: its promoted property on each carrier, read
    along the contract's path."""
    contracts = list(g.subjects(RDF.type, SRF.PromotionContract))
    if len(contracts) != 1:
        raise ValueError(f"expected one promotion contract, found {len(contracts)}")
    contract = contracts[0]
    steps = sorted(g.objects(contract, SRF.hasPathStep), key=lambda s: int(g.value(s, SRF.stepIndex)))
    parts = [InvPath(g.value(s, SRF.stepProperty)) if g.value(s, SRF.stepDirection) == SRF.Inverse else g.value(s, SRF.stepProperty)
             for s in steps]
    path = parts[0] if len(parts) == 1 else SequencePath(*parts)
    promoted = URIRef(g.value(contract, SRF.promotesTo))
    carrier = g.value(contract, SRF.carrier)
    triples = [(c, promoted, v) for c in g.subjects(RDF.type, carrier) for v in g.objects(c, path)]
    return promoted, triples


@dataclass
class RoundTrip:
    example: str
    triples: int
    rows: Dict[str, int]
    excluded: Counter
    held: int
    problems: List[str]
    missing: List[str]
    extra: List[str]
    lexical: List[str]

    @property
    def holds(self) -> bool:
        return not (self.problems or self.missing or self.extra)


def round_trip(mapping: Mapping, example: str, triples: List[Tuple[Node, Node, Node]], source: Graph, held: int = 0) -> RoundTrip:
    encoding = encode(mapping, triples, source)
    decoded = set(decode(mapping, encoding.rows))
    expected = encoding.mapped
    missing, extra = expected - decoded, decoded - expected
    lexical = []
    for t in sorted(missing, key=str):
        s, p, o = t
        if isinstance(o, Literal):
            twins = [x for x in extra if x[0] == s and x[1] == p and isinstance(x[2], Literal) and x[2].eq(o)]
            if twins:
                lexical.append(f"{mapping.qname(p)} {o!s} became {twins[0][2]!s}")
                missing.discard(t)
                extra.discard(twins[0])
    return RoundTrip(
        example=example, triples=len(expected), rows={t: len(r) for t, r in sorted(encoding.rows.items()) if r},
        excluded=encoding.excluded, held=held, problems=encoding.problems,
        missing=sorted(" ".join(mapping.qname(x) for x in t) for t in missing),
        extra=sorted(" ".join(mapping.qname(x) for x in t) for t in extra), lexical=lexical,
    )


# ---------------------------------------------------------------------------------------------------------------
# The run


def import_reader():
    """The catalogue reader (STD-273), found by walking up from ``LATTICE_ROOT`` or the working directory, as the shape
    census does. Everything after it asks the reader."""
    start = Path(os.environ.get("LATTICE_ROOT") or Path.cwd()).resolve()
    for candidate in (start, *start.parents):
        if (candidate / READER).is_file():
            sys.path.insert(0, str((candidate / READER).parent))
            import lattice_repo_catalogue  # noqa: E402
            return lattice_repo_catalogue
    raise SystemExit(f"no {READER.as_posix()} at or above {start}: run from inside the repository, or set LATTICE_ROOT")


@dataclass
class Inputs:
    spike: Path
    runtime: Graph
    ledger_examples: List[Tuple[str, Graph]]
    promotion_example: Tuple[str, Graph]


def read_inputs() -> Inputs:
    reader = import_reader()
    catalogue = reader.load(reader.find_root())
    root = catalogue.root
    ledger = catalogue.module("ledger")
    runtime = Graph()
    for path in ledger.files("spec"):
        if path.stem.endswith("-runtime"):
            runtime.parse(root / path)
    examples = []
    for path in sorted((root / ledger.directory("examples")).glob("*.ttl")):
        examples.append((path.name, Graph().parse(path)))
    surface = root / catalogue.module("surface").directory("examples")
    promotion = surface / "saas-subscription-currency.ttl"
    return Inputs(root / catalogue.area("spikes") / SPIKE, runtime, examples, (promotion.name, Graph().parse(promotion)))


@dataclass
class Result:
    ledger: Mapping
    promotion: Mapping
    vocabulary: Dict[str, Set[URIRef]]
    outside: Dict[str, List[str]]
    columns: Dict[str, List[str]]
    missing: List[str]
    held: List[str]
    trips: Dict[str, List[RoundTrip]]

    @property
    def one_vocabulary(self) -> bool:
        return not any(self.outside.values())

    @property
    def mapping_holds(self) -> bool:
        return not any(self.columns.values()) and not self.missing and all(t.holds for ts in self.trips.values() for t in ts)


def run(inputs: Inputs, ledger_graph: Optional[Graph] = None, promotion_graph: Optional[Graph] = None,
        ledger_examples: Optional[List[Tuple[str, Graph]]] = None) -> Result:
    place_terms = declared_place_terms(Graph().parse(inputs.spike / "place.ttl"))
    ontology = read_runtime_ontology(inputs.runtime)
    graphs = {
        "ledger": ledger_graph if ledger_graph is not None else Graph().parse(inputs.spike / "ledger.r2rml.ttl"),
        "promotion": promotion_graph if promotion_graph is not None else Graph().parse(inputs.spike / "promotion.r2rml.ttl"),
    }
    mappings = {name: load_mapping(name, g) for name, g in graphs.items()}
    build_columns(mappings["ledger"], ontology.minimum)
    build_columns(mappings["promotion"], {})
    known = R2RML_TERMS | place_terms
    vocabulary = {name: vocabulary_terms(g) for name, g in graphs.items()}
    outside = {name: sorted(mappings[name].qname(t) for t in terms - known) for name, terms in vocabulary.items()}
    columns = {name: column_problems(m) for name, m in mappings.items()}
    missing, held = coverage(mappings["ledger"], ontology)
    trips: Dict[str, List[RoundTrip]] = {"ledger": [], "promotion": []}
    for name, g in (ledger_examples if ledger_examples is not None else inputs.ledger_examples):
        family, held_count = ledger_triples(g, mappings["ledger"])
        trips["ledger"].append(round_trip(mappings["ledger"], name, family, g, held_count))
    name, g = inputs.promotion_example
    _, derived = promotion_triples(g)
    trips["promotion"].append(round_trip(mappings["promotion"], name, derived, g))
    return Result(mappings["ledger"], mappings["promotion"], vocabulary, outside, columns, missing, held, trips)


def logical_keys() -> Optional[Dict[URIRef, Tuple[str, ...]]]:
    """The persistence compiler's logical keys, read from its contract module where it is installed."""
    try:
        from persistence.contract import LOGICAL_KEYS  # noqa: PLC0415 - optional, read only
    except Exception:  # noqa: BLE001 - the comparison is skipped where the package is absent
        return None
    return {DAL[kind.value]: parts for kind, parts in LOGICAL_KEYS.items()}


def key_part_report(result: Result) -> List[str]:
    keys = logical_keys()
    held: Dict[URIRef, Set[str]] = defaultdict(set)
    for mapping in (result.ledger, result.promotion):
        for place in mapping.places.values():
            for _, resource, part in place.key_parts:
                held[resource].add(part)
    lines = []
    for resource in sorted(held, key=str):
        name = result.ledger.qname(resource)
        if keys is None:
            lines.append(f"{name}: holds {', '.join(sorted(held[resource]))} (the persistence package is not installed, so not compared)")
            continue
        named = set(keys.get(resource, ()))
        lines.append(f"{name}: holds {', '.join(sorted(held[resource]))}. Named by the logical keys and not held: "
                     f"{', '.join(sorted(named - held[resource])) or 'none'}. Held and not named: {', '.join(sorted(held[resource] - named)) or 'none'}")
    return lines


def places_markdown(result: Result) -> str:
    lines = ["<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->", "", "# The relational places, emitted from the two mappings", "",
             f"Generated by `spikes/{SPIKE}/mapping.py`. Do not edit. Each table's columns come from the term maps that read them, "
             "and its keys, key parts, derived columns and foreign keys from the place terms beside the mapping.", ""]
    for mapping in (result.ledger, result.promotion):
        lines += [f"## The {mapping.name} family", ""]
        for table in sorted(mapping.places):
            place = mapping.places[table]
            lines += [f"### `{table}`", "", f"- Primary key: {', '.join(place.primary_key)}."]
            for u in place.uniques:
                lines.append(f"- Unique: {', '.join(u)}.")
            for u in place.uniques_nulls_not_distinct:
                lines.append(f"- Unique, two nulls the same: {', '.join(u)}.")
            for fk in place.foreign_keys:
                lines.append(f"- Foreign key, {', '.join(fk.columns)}, to `{fk.table}` {', '.join(fk.ref_columns)}.")
            lines += ["", "| Column | SQL type | Null | Holds |", "|---|---|---|---|"]
            for name in sorted(place.columns, key=lambda c: (c not in place.primary_key, place.primary_key.index(c) if c in place.primary_key else 0, c)):
                col = place.columns[name]
                holds = [f"{mapping.qname(r).split(':')[-1]} {part}" for r, part in col.key_parts]
                holds += col.fields
                if col.derived:
                    holds.append(f"derived ({col.derived.rule})")
                sql = col.sql_type + (", at least 0" if col.datatype == XSD.nonNegativeInteger else "")
                lines.append(f"| `{name}` | {sql} | {'no' if col.not_null else 'yes'} | {', '.join(holds)} |")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def report(result: Result) -> List[str]:
    out = ["MSA-I10: two families in one mapping vocabulary", ""]
    for name in ("ledger", "promotion"):
        terms = sorted(result.ledger.qname(t) for t in result.vocabulary[name])
        out.append(f"{name}: {len(terms)} mapping terms, {len(result.outside[name])} outside R2RML and the place terms"
                   + (f": {', '.join(result.outside[name])}" if result.outside[name] else ""))
    only = {n: sorted(result.ledger.qname(t) for t in result.vocabulary[n] - result.vocabulary[o]) for n, o in (("ledger", "promotion"), ("promotion", "ledger"))}
    out.append(f"terms only the ledger uses: {', '.join(only['ledger']) or 'none'}")
    out.append(f"terms only the promotion uses: {', '.join(only['promotion']) or 'none'}")
    out.append("")
    for name, mapping in (("ledger", result.ledger), ("promotion", result.promotion)):
        n_cols = sum(len(p.columns) for p in mapping.places.values())
        out.append(f"{name} places: {len(mapping.places)} tables, {n_cols} columns, {len(result.columns[name])} column problems")
        out.extend(f"  {p}" for p in result.columns[name])
    out.append(f"ledger coverage: {len(result.missing)} missing, {len(result.held)} held for LG-Q58")
    out.extend(f"  missing: {m}" for m in result.missing)
    out.extend(f"  held: {h}" for h in result.held)
    out.append("")
    out.append("key parts against the persistence compiler's logical keys:")
    out.extend(f"  {line}" for line in key_part_report(result))
    out.append("")
    for name in ("ledger", "promotion"):
        for t in result.trips[name]:
            excluded = ", ".join(f"{n} {k}" for k, n in sorted(t.excluded.items())) or "none"
            rows = sum(t.rows.values())
            out.append(f"{name} {t.example}: {t.triples} triples, {rows} rows in {len(t.rows)} tables, "
                       f"{'round trip holds' if t.holds else 'ROUND TRIP FAILS'}, excluded {excluded}, held {t.held}, "
                       f"lexical changes {len(t.lexical)}")
            out.extend(f"  problem: {p}" for p in t.problems)
            out.extend(f"  missing: {m}" for m in t.missing)
            out.extend(f"  extra: {e}" for e in t.extra)
            out.extend(f"  lexical: {x}" for x in t.lexical)
    out.append("")
    out.append(f"falsifier (the two need different vocabularies): {'FIRED' if not result.one_vocabulary else 'did not fire'}")
    out.append(f"mapping holds (every column held, coverage, every round trip): {'yes' if result.mapping_holds else 'NO'}")
    return out


def main() -> int:
    inputs = read_inputs()
    result = run(inputs)
    (inputs.spike / "results").mkdir(exist_ok=True)
    (inputs.spike / "results" / "places.md").write_text(places_markdown(result), encoding="utf-8", newline="\n")
    print("\n".join(report(result)))
    return 0 if result.one_vocabulary and result.mapping_holds else 1


if __name__ == "__main__":
    sys.exit(main())
