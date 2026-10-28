// SPDX-License-Identifier: MPL-2.0
// The contract builder's model over stated meaning and its review (ADR-A138, ADR-A42): the stated term a
// clause expresses and the relations under it read in plain words, a manual entry as a proposal its author
// confirms at once, the four decisions on a proposal, and what a term reads, derived by walking its graph.
// Stated meaning is the meaning configuration (`ins:`), proposals the review configuration (`cst:`), and a
// proposal carries what it proposes as Turtle in `cst:payload` (contracts/config-studio/README.md).

import { CST, ELG, Graph, INS, INS_VOC, LABEL, PTY, QNT, RDFS, SKOS, TYPE, VOC, WRD, XSD, iri, literal, localName, namedNode, typed, type Term } from "@lattice/authoring-domain";
import { mint } from "./editors";
import type { Vocabulary } from "./vocabulary";

// ---- What the vocabulary declares ---------------------------------------------------------

export interface RelationKind {
  iri: string;
  label: string;
  /** The word between the roles in plain speech, "must" for an obligation. */
  verb: string;
  /** An obligation or a kind of one, whose roles are the obligor and the obligees. Other kinds have a holder and counterparties. */
  obligation: boolean;
}

const VERBS: [string, string][] = [
  ["Prohibition", "must not"],
  ["Obligation", "must"],
  ["Permission", "may"],
  ["Exclusion", "need not"],
  ["Power", "can"],
];

/** Every class the vocabulary declares a subclass of `ins:LegalRelation`, however deep. */
export function relationKinds(vocab: Vocabulary): RelationKind[] {
  const found: string[] = [];
  const queue = [INS("LegalRelation")];
  for (let i = 0; i < queue.length; i++) {
    for (const sub of vocab.graph.subjects(RDFS("subClassOf"), queue[i])) {
      if (sub.termType !== "NamedNode" || found.includes(sub.value)) continue;
      found.push(sub.value);
      queue.push(sub.value);
    }
  }
  return found
    .map((kind): RelationKind => {
      const ancestors = vocab.ancestors(kind);
      const verb = VERBS.find(([name]) => ancestors.includes(INS(name)))?.[1] ?? vocab.label(kind).toLowerCase();
      return { iri: kind, label: vocab.label(kind), verb, obligation: ancestors.includes(INS("Obligation")) };
    })
    .sort((a, b) => a.label.localeCompare(b.label));
}

export interface Lexicon {
  kinds: Map<string, RelationKind>;
  /** A node's name in plain words: its label, or its preferred label, or its local name. */
  label: (node: string) => string;
}

/** `world` is every graph of the workspace, and the vocabulary is the ontology's. */
export function lexiconOf(world: Graph, vocab: Vocabulary): Lexicon {
  const kinds = new Map(relationKinds(vocab).map((k) => [k.iri, k]));
  const label = (node: string) =>
    world.value(node, LABEL) ?? world.value(node, SKOS("prefLabel")) ?? vocab.graph.value(node, SKOS("prefLabel")) ?? vocab.graph.value(node, LABEL) ?? localName(node).replace(/[-_]+/g, " ");
  return { kinds, label };
}

export interface Named {
  iri: string;
  label: string;
}

/** The roles the workspace holds, `pty:Role` individuals. */
export function rolesOf(world: Graph, lex: Lexicon): Named[] {
  return world
    .ofType(PTY("Role"))
    .map((r) => ({ iri: r.value, label: lex.label(r.value) }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

/** The concepts of the scheme bound to `ins-voc:ActivityContract`, from the vocabulary and from the workspace's own. */
export function activitiesOf(world: Graph, vocab: Vocabulary, lex: Lexicon): Named[] {
  const schemes = new Set(vocab.graph.objects(INS_VOC("ActivityContract"), VOC("boundScheme")).map((s) => s.value));
  const out = new Map<string, Named>();
  for (const graph of [vocab.graph, world]) {
    for (const concept of graph.subjects(SKOS("inScheme"))) {
      if (concept.termType === "NamedNode" && schemes.has(graph.value(concept, SKOS("inScheme")) ?? "")) out.set(concept.value, { iri: concept.value, label: lex.label(concept.value) });
    }
  }
  return [...out.values()].sort((a, b) => a.label.localeCompare(b.label));
}

/** A role, written into the baseline since it is no part of the meaning configuration. `world` is every graph, so that no IRI is minted twice. */
export function addRole(baseline: Graph, world: Graph, namespace: string, label: string): { graph: Graph; iri: string } {
  const node = mint(world, namespace, label);
  return { iri: node, graph: baseline.edit((e) => { e.add(node, TYPE, iri(PTY("Role"))); e.add(node, LABEL, literal(label)); }) };
}

// ---- Reading stated meaning ---------------------------------------------------------------

export interface Relation {
  iri: string;
  kind: RelationKind;
  /** The obligor, or the holder. */
  roles: string[];
  /** The obligees, or the counterparties. */
  counters: string[];
  activity?: string;
}

/** Every stated term of the graph. */
export function termsOf(meaning: Graph): string[] {
  return meaning.ofType(INS("Term")).map((t) => t.value).sort();
}

/** The stated terms expressed in a clause. */
export function termsFor(meaning: Graph, clause: string): string[] {
  return meaning
    .subjects(INS("expressedIn"), clause)
    .filter((t) => t.termType === "NamedNode" && meaning.types(t).includes(INS("Term")))
    .map((t) => t.value)
    .sort();
}

/** The relations that arise under a term, or under any when none is named. */
export function relationsOf(graph: Graph, lex: Lexicon, term?: string): Relation[] {
  const out: Relation[] = [];
  for (const s of graph.subjects(INS("arisesUnder"), term)) {
    if (s.termType !== "NamedNode") continue;
    const kind = graph.types(s).map((t) => lex.kinds.get(t)).find((k) => k !== undefined);
    if (!kind) continue;
    const values = (...properties: string[]) => properties.flatMap((p) => graph.objects(s, p).map((o) => o.value));
    out.push({
      iri: s.value,
      kind,
      roles: values(INS("obligor"), INS("holder")),
      counters: values(INS("obligee"), INS("counterparty")),
      activity: graph.value(s, INS("activity")),
    });
  }
  return out.sort((a, b) => a.iri.localeCompare(b.iri));
}

/** A relation in plain words, with its roles shown as roles: "Borrower must Pay Lender". */
export function say(relation: Relation, lex: Lexicon): string {
  const names = (iris: string[]) => iris.map(lex.label).join(" and ");
  return [names(relation.roles), relation.kind.verb, relation.activity ? lex.label(relation.activity) : "", names(relation.counters)].filter(Boolean).join(" ");
}

// ---- Proposals ----------------------------------------------------------------------------

export type Decision = "Confirm" | "Retarget" | "Decline" | "Defer";
export const DECISIONS: Decision[] = ["Confirm", "Retarget", "Decline", "Defer"];

export interface Proposal {
  iri: string;
  /** The clause it reads. */
  span?: string;
  proposer: string;
  proposedAt?: string;
  decision?: Decision;
  decidedAt?: string;
  proposes: string[];
  /** What it proposes, parsed. Absent when the Turtle is missing or cannot be read. */
  payload?: Graph;
  problem?: string;
}

export function readProposal(review: Graph, node: string): Proposal {
  const text = review.value(node, CST("payload"));
  let payload: Graph | undefined;
  let problem: string | undefined;
  if (text === undefined) problem = "The proposal carries no payload.";
  else {
    try {
      payload = Graph.parse(text);
    } catch (error) {
      problem = `The payload cannot be read: ${error instanceof Error ? error.message : String(error)}`;
    }
  }
  const decision = review.value(node, CST("decision"));
  return {
    iri: node,
    span: review.value(node, CST("span")),
    proposer: review.value(node, CST("proposer")) ?? "unknown",
    proposedAt: review.value(node, CST("proposedAt")),
    decision: decision ? (localName(decision) as Decision) : undefined,
    decidedAt: review.value(node, CST("decidedAt")),
    proposes: review.objects(node, CST("proposes")).map((o) => o.value),
    payload,
    problem,
  };
}

/** Every proposal, the oldest first. */
export function proposalsOf(review: Graph): Proposal[] {
  return review
    .ofType(CST("Proposal"))
    .map((p) => readProposal(review, p.value))
    .sort((a, b) => (a.proposedAt ?? "").localeCompare(b.proposedAt ?? "") || a.iri.localeCompare(b.iri));
}

export const isWaiting = (p: Proposal) => p.decision === undefined;


export interface Entry {
  clause: string;
  /** The clause's name, for the IRIs minted. */
  name: string;
  kind: RelationKind;
  role: string;
  counter: string;
  activity: string;
}

export interface Written {
  meaning: Graph;
  review: Graph;
  proposal: string;
}

const dateTime = (at: string) => typed(at, XSD("dateTime"));

/** Manual entry: a proposal its author confirms at once. It states the relation, and the stated term when the clause has none,
 * in the proposal's payload and in the meaning configuration. `world` is every graph, so that no IRI is minted twice, and `at` is the time. */
export function propose(meaning: Graph, review: Graph, world: Graph, namespace: string, entry: Entry, lex: Lexicon, at: string): Written {
  const existing = termsFor(meaning, entry.clause)[0];
  const term = existing ?? mint(world, namespace, `Term ${entry.name}`);
  const relation = mint(world, namespace, `${entry.kind.label} ${lex.label(entry.activity)} ${entry.name}`);
  const proposal = mint(world, namespace, `Proposal ${entry.name}`);
  const [roleProperty, counterProperty] = entry.kind.obligation ? [INS("obligor"), INS("obligee")] : [INS("holder"), INS("counterparty")];
  const templates = Graph.empty().edit((e) => {
    if (!existing) {
      e.add(term, TYPE, iri(INS("Term")));
      e.add(term, TYPE, iri(INS("Template")));
      e.add(term, INS("expressedIn"), iri(entry.clause));
    }
    e.add(relation, TYPE, iri(entry.kind.iri));
    e.add(relation, TYPE, iri(INS("Template")));
    e.add(relation, INS("arisesUnder"), iri(term));
    e.add(relation, roleProperty, iri(entry.role));
    e.add(relation, counterProperty, iri(entry.counter));
    e.add(relation, INS("activity"), iri(entry.activity));
  });
  const proposed = existing ? [relation] : [term, relation];
  return {
    proposal,
    meaning: meaning.merge(templates),
    review: review.edit((e) => {
      e.add(proposal, TYPE, iri(CST("Proposal")));
      e.add(proposal, CST("span"), iri(entry.clause));
      for (const t of proposed) e.add(proposal, CST("proposes"), iri(t));
      e.add(proposal, CST("proposer"), literal("manual"));
      e.add(proposal, CST("proposedAt"), dateTime(at));
      e.add(proposal, CST("decidedAt"), dateTime(at));
      e.add(proposal, CST("decision"), iri(CST("Confirm")));
      e.add(proposal, CST("payload"), literal(templates.toTurtle()));
    }),
  };
}

/** Record a decision and its time. Confirm writes the payload into the meaning configuration. Retarget writes the
 * templates as `corrected` where they are given, else the payload, to be corrected there with the forms, so meaning never
 * holds a template no decision admitted (CS-B49). Decline and Defer write no meaning. */
export function decide(meaning: Graph, review: Graph, proposal: string, decision: Decision, at: string, corrected?: Graph): { meaning: Graph; review: Graph } {
  let written = meaning;
  if (decision === "Confirm") {
    const payload = readProposal(review, proposal).payload;
    if (!payload) throw new Error("The proposal has no payload to confirm.");
    written = meaning.merge(payload);
  } else if (decision === "Retarget") {
    const templates = corrected ?? readProposal(review, proposal).payload;
    if (!templates) throw new Error("The proposal has no payload to retarget.");
    written = meaning.merge(templates);
  }
  return {
    meaning: written,
    review: review.edit((e) => {
      e.set(proposal, CST("decision"), iri(CST(decision)));
      e.set(proposal, CST("decidedAt"), dateTime(at));
    }),
  };
}


// ---- What a term reads ------------------------------------------------------------------

export interface Reads {
  roles: Named[];
  concepts: Named[];
  ranges: Named[];
  conditions: Named[];
}

const NOT_FOLLOWED = new Set([TYPE, INS("expressedIn"), INS("arisesUnder"), INS("qualifies")]);

/** The roles, concepts, ranges and eligibility conditions the templates under a term and their qualifiers reach, by walking
 * `world` from them. Nothing is stored: the walk is the answer (ADR-A138 decision 6). A role, concept or range ends a path, a
 * condition does not, since it reaches its own ranges and concepts. */
export function readsOf(world: Graph, vocab: Vocabulary, lex: Lexicon, term: string): Reads {
  const templates = new Set<string>([term]);
  for (let grew = true; grew; ) {
    grew = false;
    for (const p of [INS("arisesUnder"), INS("qualifies")]) {
      for (const s of world.subjects(p)) {
        if (s.termType === "NamedNode" && !templates.has(s.value) && world.objects(s, p).some((o) => templates.has(o.value))) {
          templates.add(s.value);
          grew = true;
        }
      }
    }
  }
  const kinds = (node: Term) => [...world.types(node), ...vocab.graph.types(node)].flatMap((t) => vocab.ancestors(t));
  const found: Record<keyof Reads, Set<string>> = { roles: new Set(), concepts: new Set(), ranges: new Set(), conditions: new Set() };
  const start = [...templates].map((t) => namedNode(t));
  const seen = new Set<string>([...templates].map((t) => `NamedNode:${t}`));
  const queue: Term[] = [...start];
  for (let i = 0; i < queue.length; i++) {
    const node = queue[i];
    const own = i >= start.length ? kinds(node) : [];
    if (own.includes(PTY("Role"))) found.roles.add(node.value);
    else if (own.includes(SKOS("Concept"))) found.concepts.add(node.value);
    else if (own.includes(QNT("Range")) || own.includes(QNT("RangeSet"))) found.ranges.add(node.value);
    else if (own.some((k) => k.startsWith(WRD("")))) continue;
    else {
      if (own.includes(ELG("Condition"))) found.conditions.add(node.value);
      for (const q of world.quads(node)) {
        const key = `${q.object.termType}:${q.object.value}`;
        if (NOT_FOLLOWED.has(q.predicate.value) || q.object.termType === "Literal" || seen.has(key)) continue;
        seen.add(key);
        queue.push(q.object);
      }
    }
  }
  const named = (set: Set<string>) =>
    [...set].map((n) => ({ iri: n, label: lex.label(n) })).sort((a, b) => a.label.localeCompare(b.label) || a.iri.localeCompare(b.iri));
  return { roles: named(found.roles), concepts: named(found.concepts), ranges: named(found.ranges), conditions: named(found.conditions) };
}
