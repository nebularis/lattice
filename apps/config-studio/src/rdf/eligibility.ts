// SPDX-License-Identifier: MPL-2.0
// Eligibility tests are the layer's own elg:Question nodes: a question names its condition and a
// candidate, and the studio adds the decision the author expects (cst:expectedDecision) and the
// resolution instant and scopes to decide it under (cst:resolutionTime, cst:resolutionScope). The
// worker decides each with the condition's compiled query.

import { Graph, iri, typed, type Term } from "./graph";
import { CST, ELG, QNT, SKOS, TYPE, XSD } from "./ns";
import { mint } from "./editors";
import { pointRangeSet, removeRange } from "./quantity";
import type { Decision } from "./report";

export interface Question {
  iri: string;
  candidate?: string;
  expected?: Decision;
  at?: string;
  scopes: string[];
}

export function questionsFor(graph: Graph, condition: string): Question[] {
  return graph
    .subjects(ELG("forCondition"), condition)
    .filter((q) => graph.types(q).includes(ELG("Question")))
    .map((q) => {
      const expected = graph.value(q, CST("expectedDecision"));
      return {
        iri: q.value,
        candidate: graph.value(q, ELG("candidateConcept")) ?? graph.value(q, ELG("candidateRangeSet")),
        expected: expected ? (expected.slice(expected.lastIndexOf("#") + 1) as Decision) : undefined,
        at: graph.value(q, CST("resolutionTime")),
        scopes: graph.objects(q, CST("resolutionScope")).map((t) => t.value),
      };
    })
    .sort((a, b) => a.iri.localeCompare(b.iri));
}

export type Candidate = { concept: string } | { value: number; space: string };

export function addQuestion(graph: Graph, namespace: string, condition: string, name: string, candidate: Candidate, expected?: Decision): { graph: Graph; iri: string } {
  const question = mint(graph, namespace, `${name} question`);
  let next = graph;
  let candidateTerm: Term;
  let predicate: string;
  if ("concept" in candidate) {
    candidateTerm = iri(candidate.concept);
    predicate = ELG("candidateConcept");
  } else {
    const made = pointRangeSet(graph, namespace, name, candidate.space, candidate.value);
    next = made.graph;
    candidateTerm = iri(made.iri);
    predicate = ELG("candidateRangeSet");
  }
  next = next.edit((e) => {
    e.add(question, TYPE, iri(ELG("Question")));
    e.add(question, ELG("forCondition"), iri(condition));
    e.add(question, predicate, candidateTerm);
    if (expected) e.add(question, CST("expectedDecision"), iri(ELG(expected)));
  });
  return { graph: next, iri: question };
}

export function setExpected(graph: Graph, question: string, expected?: Decision): Graph {
  return graph.edit((e) => e.set(question, CST("expectedDecision"), expected ? iri(ELG(expected)) : undefined));
}

export function setContext(graph: Graph, node: string, at: string | undefined, scopes: string[]): Graph {
  return graph.edit((e) => {
    e.set(node, CST("resolutionTime"), at ? typed(at, XSD("dateTime")) : undefined);
    e.setAll(node, CST("resolutionScope"), scopes.map((s) => iri(s)));
  });
}

/** A question, and the range set of its candidate when no other node uses it. */
export function removeQuestion(graph: Graph, question: string): Graph {
  const set = graph.value(question, ELG("candidateRangeSet"));
  let next = graph.edit((e) => e.remove(question));
  if (set && next.subjects(null, set).length === 0) {
    for (const range of next.objects(set, QNT("hasRange"))) next = removeRange(next, range.value);
    next = next.edit((e) => e.remove(set));
  }
  return next;
}

export interface ConceptNode {
  iri: string;
  label: string;
  children: ConceptNode[];
}

/** The members of a set of concepts as a forest, by skos:broader among themselves. */
export function conceptForest(world: Graph, members: string[]): ConceptNode[] {
  const inSet = new Set(members);
  const label = (c: string) => world.value(c, SKOS("prefLabel")) ?? c.slice(Math.max(c.lastIndexOf("#"), c.lastIndexOf("/")) + 1);
  const node = (c: string, seen: Set<string>): ConceptNode => ({
    iri: c,
    label: label(c),
    children: members
      .filter((m) => !seen.has(m) && world.objects(m, SKOS("broader")).some((b) => b.value === c))
      .map((m) => node(m, new Set([...seen, m])))
      .sort((a, b) => a.label.localeCompare(b.label)),
  });
  return members
    .filter((m) => !world.objects(m, SKOS("broader")).some((b) => inSet.has(b.value)))
    .map((m) => node(m, new Set([m])))
    .sort((a, b) => a.label.localeCompare(b.label));
}

export function conceptsOf(world: Graph, scheme: string): string[] {
  return world.subjects(SKOS("inScheme"), scheme).map((c) => c.value);
}
