# SPDX-License-Identifier: MPL-2.0
# NB: This module has been produced using GenAI

"""
Reference binder for one instrument (CCS C8, ADR-A104 and its 2026-10-06 addenda).

Bound meaning is generated, never stored with the instance (D4). Given a graph holding a form's
stated meaning and one instance (its assembled wording, values and parties), ``bind`` generates the
instrument's bound meaning:

- each stated term the wording includes is bound once for each group of sections whose words and
  values resolve alike (D5), recording the fewest sections covering the group (``ins:boundWithin``)
- words are resolved through the definitions applying in each section (D12, D13), and placeholders
  through their variable or value word (C8-Q1, Instrument README §18)
- a stated node holding no word or placeholder is shared. One that does is generated anew, with the
  path from the slot down to the value. Blank nodes under a generated node are always copied
- generated nodes are named deterministically from the instrument's namespace and the stated node

It reports, never guesses: an unresolved word, a variable with no value, a cycle of words or
variables (with every hop and the clause stating it), and an overlap of definitions (law I16).

It does not evaluate, cache, or share across instruments (C12, C13, C16b).

Usage::

    python tools/instrument_binder.py ontology/instrument/examples/facility-parameters.ttl \\
        https://example.org/lattice/instrument/facility-parameters/halden-v1
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF
from rdflib.term import Node

LATTICE = "https://www.nebularis.org/neuro-semantic/lattice/"
INS = Namespace(LATTICE + "instrument#")
WRD = Namespace(LATTICE + "wording#")
FND = Namespace(LATTICE + "foundation#")
PTY = Namespace(LATTICE + "party#")
ELG = Namespace(LATTICE + "eligibility#")
QNT = Namespace(LATTICE + "quantification#")

PARTY_SLOTS = {INS.obligor, INS.obligee, INS.holder, INS.counterparty}
RELATION_LINKS = {INS.excepts, INS.arisesOnBreachOf, INS.arisesOnExerciseOf, INS.forPurposeOf}
CONCEPT_SLOTS = {ELG.requiredConcept, ELG.excludedConcept}
CONDITION_SLOTS = {INS.condition, INS.scope, INS.maintains, INS.deems, INS.when, INS.resolutionFilter}
STATED_ONLY = {INS.Regime, INS.Sectioning}
# Edges the word search never follows: they lead to other terms' relations, or back to ownership.
NOT_FOLLOWED = {RDF.type, INS.arisesUnder, INS.boundFrom, INS.defines, INS.qualifies} | RELATION_LINKS
# Nodes the copier never descends into: they are named things, shared by every instrument.
SHARED_KINDS = {PTY.Role, INS.LegalRelation, INS.Obligation, INS.Power, INS.Permission, INS.Exclusion,
                INS.Prohibition, INS.ContinuingObligation, INS.Term, WRD.Element, WRD.Text, QNT.ValueSpace,
                QNT.Unit, QNT.CalendarUnit, QNT.ContextValue, PTY.RoleOccupancy, PTY.ParticipationGroup}

WHOLE = None  # the whole instrument, as a section


@dataclass
class Report:
    kind: str       # "unresolved-word", "no-value", "cycle", "overlap"
    message: str
    section: Optional[Node] = None
    hops: List[str] = field(default_factory=list)


def _local(node: Node) -> str:
    text = str(node)
    return text.rsplit("/", 1)[-1].rsplit("#", 1)[-1]


class Binder:
    def __init__(self, graph: Graph, instrument: URIRef) -> None:
        self.g = graph
        self.instrument = instrument
        self.ns = str(instrument).rsplit("/", 1)[0] + "/"
        self.inst_local = _local(instrument)
        self.out = Graph()
        self.reports: List[Report] = []
        wording = graph.value(instrument, INS.expressedIn)
        self.wording = wording
        self.included = set(graph.objects(wording, WRD.includes))
        self.parent: Dict[Node, Node] = {c: p for p, c in graph.subject_objects(WRD.directlyComprises)}
        self.stated_terms = sorted(
            (t for t in graph.subjects(INS.expressedIn, None)
             if (t, RDF.type, INS.Template) in graph and (t, RDF.type, INS.Term) in graph
             and graph.value(t, INS.expressedIn) in self.included), key=str)
        self.definitions = [d for d in graph.subjects(RDF.type, INS.Definition)
                            if (d, RDF.type, INS.Template) in graph
                            and graph.value(d, INS.arisesUnder) in self.stated_terms]
        self.words = {graph.value(d, INS.defines) for d in self.definitions}
        self.sections = self._sections()
        self._values: Dict[Node, List[Node]] = {}
        self._copies: Dict[Tuple[Node, object], Node] = {}
        self._bound: Dict[Node, Dict[object, Node]] = {}     # stated node → group key → bound node
        self._groups: Dict[Node, List[Tuple[object, Optional[frozenset]]]] = {}

    # ---- sections ------------------------------------------------------------------------------

    def _element(self, identity: Node) -> Optional[Node]:
        elements = [e for e in self.g.subjects(FND.hasIdentity, identity)]
        included = [e for e in elements if e in self.included]
        return (included or elements or [None])[0]

    def _ancestors(self, element: Node) -> List[Node]:
        chain = []
        while element in self.parent:
            element = self.parent[element]
            chain.append(element)
        return chain

    def _sections(self) -> List[Node]:
        declared = set()
        for term in self.stated_terms:
            for node in self.g.subjects(INS.arisesUnder, term):
                if (node, RDF.type, INS.Sectioning) in self.g:
                    declared |= set(self.g.objects(node, INS.section))
        self.declared = bool(declared)
        if not declared:  # D7: a part a term's words scope to is a section by being named
            for term in self.stated_terms:
                declared |= set(self.g.objects(term, INS.appliesWithin)) | set(self.g.objects(term, INS.notWithin))
        return sorted(declared, key=str)

    def _at_or_below(self, section: Node, part: Node) -> bool:
        element, above = self._element(section), self._element(part)
        return element is not None and above is not None and (element == above or above in self._ancestors(element))

    def _term_sections(self, term: Node) -> Optional[Set[Node]]:
        within = set(self.g.objects(term, INS.appliesWithin))
        without = set(self.g.objects(term, INS.notWithin))
        if within or without:
            candidates = [s for s in self.sections if not within or any(self._at_or_below(s, a) for a in within)]
            return {s for s in candidates if not any(self._at_or_below(s, x) for x in without)}
        if self.declared:
            clause = self.g.value(term, INS.expressedIn)
            for ancestor in self._ancestors(clause):
                identity = self.g.value(ancestor, FND.hasIdentity)
                if identity in self.sections:
                    return {identity}
        return WHOLE

    def _applies_at(self, term: Node, section: Optional[Node]) -> bool:
        sections = self._term_sections(term)
        if sections is WHOLE or section is WHOLE:
            return True
        return any(self._at_or_below(section, s) for s in sections)

    def _cover(self, sections: Iterable[Node]) -> frozenset:
        sections = set(sections)
        return frozenset(s for s in sections if not any(t != s and self._at_or_below(s, t) for t in sections))

    # ---- values and words ----------------------------------------------------------------------

    def _clause_of(self, definition: Node) -> str:
        return _local(self.g.value(self.g.value(definition, INS.arisesUnder), INS.expressedIn))

    def _variable_value(self, identity: Node, seen: Tuple[Node, ...] = ()) -> Optional[Node]:
        records = [v for v in self.g.objects(self.wording, WRD.hasValue)
                   if (self.g.value(v, WRD.forVariable), FND.hasIdentity, identity) in self.g]
        if len(records) > 1:
            self.reports.append(Report("no-value", f"two values for versions of {_local(identity)}: ambiguous"))
            return None
        if records:
            return records[0]
        for variable in self.g.subjects(FND.hasIdentity, identity):
            source = self.g.value(variable, WRD.populatedFrom)
            if source is None:
                continue
            next_identity = self.g.value(source, FND.hasIdentity)
            if next_identity in seen + (identity,):
                hops = [_local(i) for i in seen + (identity, next_identity)]
                self.reports.append(Report("cycle", "variable cycle: " + " → ".join(hops), hops=hops))
                return None
            return self._variable_value(next_identity, seen + (identity,))
        return None

    def _placeholder(self, placeholder: Node, section: Optional[Node], stack: Tuple[Node, ...]) -> List[Node]:
        source = self.g.value(placeholder, INS.valueFrom)
        if source in self.words:
            return self._word(source, section, stack)
        if source in self._values:
            return self._values[source]
        record = self._variable_value(source)
        default = [o for o in self.g.objects(placeholder, QNT.numericValue)]
        if record is None and not default:
            self.reports.append(Report("no-value", f"no value for the variable {_local(source)}", section))
            self._values[source] = []
            return []
        literals = list(self.g.objects(record, WRD.literalValue)) if record is not None else default
        objects = list(self.g.objects(record, WRD.value)) if record is not None else []
        if literals:
            node = BNode()
            for p, o in self.g.predicate_objects(placeholder):
                if p not in (INS.valueFrom, QNT.numericValue):
                    self.out.add((node, p, o))
            self.out.add((node, QNT.numericValue, literals[0]))
            values = [node]
        else:
            values = []
            for value in objects:
                if isinstance(value, BNode):  # a value node, such as an amount: merged with the placeholder
                    node = BNode()
                    for p, o in list(self.g.predicate_objects(placeholder)) + list(self.g.predicate_objects(value)):
                        if p != INS.valueFrom:
                            self.out.add((node, p, o))
                    values.append(node)
                else:
                    values.append(value)
        self._values[source] = values
        return values

    def _word(self, word: Node, section: Optional[Node], stack: Tuple[Node, ...] = ()) -> List[Node]:
        if word in stack:
            loop = list(stack[stack.index(word):]) + [word]
            hops = []
            for w in loop[:-1]:
                definition = next(d for d in self.definitions if self.g.value(d, INS.defines) == w)
                hops.append(f"{_local(w)} (defined in {self._clause_of(definition)})")
            hops.append(_local(word))
            where = f" within {_local(section)}" if section is not None else ""
            self.reports.append(Report("cycle", f"word cycle{where}: " + " → ".join(hops) +
                                       ". Nothing in the loop can have a value", section, hops))
            return []
        applying = [d for d in self.definitions if self.g.value(d, INS.defines) == word
                    and self._applies_at(self.g.value(d, INS.arisesUnder), section)
                    and not any(self.g.value(o, INS.defines) == word and (o, INS.prevailsOver, d) in self.g
                                and self._applies_at(self.g.value(o, INS.arisesUnder), section) for o in self.definitions)]
        if not applying:
            where = f" within {_local(section)}" if section is not None else ""
            self.reports.append(Report("unresolved-word", f"no definition of {_local(word)} applies{where}", section))
            return []
        if len(applying) > 1:
            where = _local(section) if section is not None else "the whole instrument"
            self.reports.append(Report("overlap", f"{', '.join(sorted(_local(d) for d in applying))} all define "
                                                  f"{_local(word)} within {where}: combined by union (law I16)", section))
        meaning: List[Node] = []
        for definition in applying:
            for m in self._means(definition, section, stack + (word,)):
                if m not in meaning:
                    meaning.append(m)
        return meaning

    def _means(self, definition: Node, section: Optional[Node], stack: Tuple[Node, ...] = ()) -> List[Node]:
        means = sorted(self.g.objects(definition, INS.means), key=str)
        roles = [m for m in means if (m, RDF.type, PTY.Role) in self.g and self.g.value(m, INS.valueFrom) is None]
        if len(roles) > 1:  # several roles: the group the instance names for them
            group = self._group(set(roles), self.g.value(definition, INS.actingRule))
            if group is not None:
                return [group]
        result: List[Node] = []
        for m in means:
            if self.g.value(m, INS.valueFrom) is not None:
                result += self._placeholder(m, section, stack)
            elif (m, RDF.type, PTY.Role) in self.g:
                result += self._role(m, section, stack)
            else:
                result.append(m)
        return result

    def _group(self, roles: Set[Node], rule: Optional[Node]) -> Optional[Node]:
        for group in sorted(self.g.subjects(RDF.type, PTY.ParticipationGroup), key=str):
            members = {self.g.value(self.g.value(m, PTY.memberOccupancy), PTY.inRole)
                       for m in self.g.objects(group, PTY.hasParticipant)}
            if members == roles and (rule is None or (group, PTY.hasCompositionRule, rule) in self.g):
                return group
        return None

    def _role(self, role: Node, section: Optional[Node], stack: Tuple[Node, ...] = ()) -> List[Node]:
        if role in self.words:
            return self._word(role, section, stack)
        occupancies = sorted(self.g.subjects(PTY.inRole, role), key=str)
        parties = set(self.g.objects(self.instrument, INS.party))
        named = [o for o in occupancies if o in parties]
        return named or occupancies

    # ---- signatures and groups -----------------------------------------------------------------

    def _words_used(self, term: Node) -> List[Node]:
        found, seen = set(), set()
        frontier = [n for n in self.g.subjects(INS.arisesUnder, term)]
        while frontier:
            node = frontier.pop()
            if node in seen:
                continue
            seen.add(node)
            for p, o in self.g.predicate_objects(node):
                if p in NOT_FOLLOWED:
                    continue
                if o in self.words:
                    found.add(o)
                elif p == INS.valueFrom:
                    continue
                elif isinstance(o, (BNode, URIRef)) and not self._shared(o):
                    frontier.append(o)
        return sorted(found, key=str)

    def _shared(self, node: Node) -> bool:
        return any((node, RDF.type, k) in self.g for k in SHARED_KINDS)

    def _key(self, nodes: List[Node]) -> frozenset:
        return frozenset(nodes)

    def _signature(self, term: Node, words: List[Node], section: Optional[Node]) -> tuple:
        return tuple((w, self._key(self._word(w, section))) for w in words)

    def _plan(self, term: Node) -> List[Tuple[object, Optional[frozenset]]]:
        sections = self._term_sections(term)
        words = self._words_used(term)
        if sections is WHOLE:
            if not self.sections or not words:
                return [("whole", WHOLE)]
            candidates = self.sections
        else:
            candidates = sorted(sections, key=str)
            if not candidates:
                return []
        quiet = len(self.reports)
        groups: Dict[tuple, List[Node]] = {}
        for s in candidates:
            groups.setdefault(self._signature(term, words, s), []).append(s)
        del self.reports[quiet:]  # reported once, when the term is bound
        if sections is WHOLE and len(groups) == 1:
            return [("whole", WHOLE)]
        return [(self._cover(members), self._cover(members)) for members in groups.values()]

    # ---- generation ----------------------------------------------------------------------------

    def _name(self, stated: Node, key: object, split: bool) -> URIRef:
        name = self.ns + _local(stated)
        if split and key != "whole":
            name += "-in-" + "-".join(sorted(_local(s).removesuffix("-identity") for s in key))
        return URIRef(name)

    def _section_of(self, key: object) -> Optional[Node]:
        return WHOLE if key == "whole" else sorted(key, key=str)[0]

    def _needs_copy(self, node: Node, seen: Optional[set] = None) -> bool:
        seen = seen if seen is not None else set()
        if node in seen or not isinstance(node, (BNode, URIRef)) or self._shared(node):
            return False
        seen.add(node)
        for p, o in self.g.predicate_objects(node):
            if p == RDF.type:
                continue
            if p == INS.valueFrom:
                return True
            if (p in CONCEPT_SLOTS or p in CONDITION_SLOTS) and o in self.words:
                return True
            if self._needs_copy(o, seen):
                return True
        return False

    def _copy(self, node: Node, key: object, section: Optional[Node]) -> List[Node]:
        if self.g.value(node, INS.valueFrom) is not None:
            return self._placeholder(node, section, ())
        if isinstance(node, URIRef) and not self._needs_copy(node):
            return [node]
        if (node, key) in self._copies:
            return [self._copies[(node, key)]]
        copy = BNode() if isinstance(node, BNode) else URIRef(f"{node}-{self.inst_local}" if key == "whole" else
                                                              f"{node}-{self.inst_local}-" + "-".join(
                                                                  sorted(_local(s).removesuffix("-identity") for s in key)))
        if isinstance(node, URIRef):
            copy = URIRef(self.ns + _local(copy))
        self._copies[(node, key)] = copy
        for p, o in self.g.predicate_objects(node):
            if p == ELG.conditionKey:
                self.out.add((copy, p, Literal(f"{o}-{self.inst_local}")))
            elif (p in CONCEPT_SLOTS or p in CONDITION_SLOTS) and o in self.words:
                for value in self._word(o, section):
                    self.out.add((copy, p, value))
            elif p == RDF.type or isinstance(o, Literal):
                self.out.add((copy, p, o))
            else:
                for value in self._copy(o, key, section):
                    self.out.add((copy, p, value))
        return [copy]

    def _bound_of(self, stated: Node, key: object) -> List[Node]:
        copies = self._bound.get(stated, {})
        if key in copies:
            return [copies[key]]
        if len(copies) == 1:
            return list(copies.values())
        if key != "whole":  # a copy whose sections cover these
            return [b for k, b in copies.items() if k != "whole" and any(
                self._at_or_below(s, t) for s in key for t in k)]
        return list(copies.values())

    def bind(self) -> Graph:
        for term in self.stated_terms:
            self._groups[term] = self._plan(term)
        for term in self.stated_terms:  # bound nodes first, so links between them resolve
            groups = self._groups[term]
            split = len(groups) > 1
            for key, _ in groups:
                self._bound.setdefault(term, {})[key] = self._name(term, key, split)
                for node in self.g.subjects(INS.arisesUnder, term):
                    if not any((node, RDF.type, k) in self.g for k in STATED_ONLY):
                        self._bound.setdefault(node, {})[key] = self._name(node, key, split)
        for term in self.stated_terms:
            for key, cover in self._groups[term]:
                self._bind_term(term, key, cover)
        return self.out

    def _bind_term(self, term: Node, key: object, cover: Optional[frozenset]) -> None:
        section = self._section_of(key)
        bound_term = self._bound[term][key]
        self.out.add((bound_term, RDF.type, INS.Term))
        self.out.add((bound_term, INS.boundIn, self.instrument))
        self.out.add((bound_term, INS.boundFrom, term))
        if cover:
            for s in cover:
                self.out.add((bound_term, INS.boundWithin, s))
        for node in sorted(self.g.subjects(INS.arisesUnder, term), key=str):
            if any((node, RDF.type, k) in self.g for k in STATED_ONLY):
                continue
            bound = self._bound[node][key]
            self.out.add((bound, INS.boundFrom, node))
            self.out.add((bound, INS.arisesUnder, bound_term))
            for p, o in self.g.predicate_objects(node):
                if p == INS.arisesUnder or (p == RDF.type and o == INS.Template):
                    continue
                for value in self._convert(p, o, key, section):
                    self.out.add((bound, p, value))

    def _convert(self, p: Node, o: Node, key: object, section: Optional[Node]) -> List[Node]:
        if p == RDF.type or isinstance(o, Literal) or p in (INS.defines, INS.actingRule, INS.activity):
            return [o]
        if p in PARTY_SLOTS:
            return self._role(o, section) if (o, RDF.type, PTY.Role) in self.g else [o]
        if p == INS.means:
            return self._means_one(o, section)
        if p in RELATION_LINKS:
            return self._bound_of(o, key)
        if p == INS.qualifies:
            return sorted(self._bound.get(o, {}).values(), key=str) or [o]
        if p in CONDITION_SLOTS and o in self.words:
            return self._word(o, section)
        return self._copy(o, key, section)

    def _means_one(self, meaning: Node, section: Optional[Node]) -> List[Node]:
        definition = next(d for d in self.g.subjects(INS.means, meaning))
        roles = [m for m in self.g.objects(definition, INS.means)
                 if (m, RDF.type, PTY.Role) in self.g and self.g.value(m, INS.valueFrom) is None]
        if len(roles) > 1:
            group = self._group(set(roles), self.g.value(definition, INS.actingRule))
            if group is not None:
                return [group] if meaning == sorted(roles, key=str)[0] else []
        if self.g.value(meaning, INS.valueFrom) is not None:
            return self._placeholder(meaning, section, ())
        if (meaning, RDF.type, PTY.Role) in self.g:
            return self._role(meaning, section)
        return [meaning]


def bind(graph: Graph, instrument: URIRef) -> Tuple[Graph, List[Report]]:
    """Generate one instrument's bound meaning from its form and instance. Returns the generated
    graph and the binder's reports."""
    binder = Binder(graph, instrument)
    out = binder.bind()
    seen, reports = set(), []
    for r in binder.reports:
        if r.message not in seen:
            seen.add(r.message)
            reports.append(r)
    return out, reports


def main(argv: Optional[List[str]] = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print(__doc__)
        return 2
    graph = Graph().parse(args[0])
    out, reports = bind(graph, URIRef(args[1]))
    print(out.serialize(format="turtle"))
    for r in reports:
        print(f"# {r.kind}: {r.message}", file=sys.stderr)
    return 1 if any(r.kind == "cycle" for r in reports) else 0


if __name__ == "__main__":
    raise SystemExit(main())
