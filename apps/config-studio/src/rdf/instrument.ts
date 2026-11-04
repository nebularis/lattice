// SPDX-License-Identifier: MPL-2.0
// The contract builder's instrument view over stated meaning (ADR-A138 decisions 6 and 7): the regimes the meaning
// configuration states, read as state machines with a deterministic layout, the relations each state gates, and the
// request for a dry run of a stated term (contracts/config-studio/README.md, "Dry run"). A regime is stated once and
// shared by every instrument on the form (Instrument README, section 11). Nothing here is bound meaning, which only
// instantiation produces.

import { BHV, CST, ELG, Graph, INS, QNT, RDFS, SKOS, TYPE, VOC, XSD, iri, localName, typed } from "@lattice/authoring-domain";
import type { Lexicon } from "./meaning";
import { relationsOf, say } from "./meaning";

// ---- Regimes ------------------------------------------------------------------------------

export interface RegimeState {
  iri: string;
  /** The state kind's label, or the state's own name when it has no kind. */
  label: string;
  initial: boolean;
  /** Column, by distance from the initial state, and row within the column. */
  column: number;
  row: number;
  /** Relations gated by the state, in plain words. */
  gates: { iri: string; text: string }[];
}

export interface RegimeTransition {
  iri: string;
  from: string;
  to: string;
  trigger?: string;
  /** The trigger's kind and the relation it names, in plain words. */
  label: string;
}

export interface Regime {
  iri: string;
  label: string;
  term?: string;
  states: RegimeState[];
  transitions: RegimeTransition[];
  columns: number;
  rows: number;
}

const TRIGGER_KINDS: [string, string][] = [
  ["OnExercise", "Exercise"],
  ["OnBreach", "Breach"],
  ["OnExpiry", "Expiry"],
  ["OnCondition", "Condition"],
  ["OnAct", "Act"],
  ["OnEntry", "Entry"],
];

/** A trigger in plain words, "Exercise of Licensor can Terminate Licensee", "Expiry after 90 day". */
export function triggerLabel(meaning: Graph, lex: Lexicon, trigger: string): string {
  const types = meaning.types(trigger);
  const kind = TRIGGER_KINDS.find(([name]) => types.includes(INS(name)));
  const head = kind?.[1] ?? "Trigger";
  const relationNode = meaning.value(trigger, INS("ofPower")) ?? meaning.value(trigger, INS("ofObligation"));
  if (relationNode) {
    const relation = relationsOf(meaning, lex).find((r) => r.iri === relationNode);
    return `${head} of ${relation ? say(relation, lex) : lex.label(relationNode)}`;
  }
  const condition = meaning.value(trigger, INS("condition"));
  if (condition) return `${head} of ${lex.label(condition)}`;
  const after = meaning.object(trigger, INS("after"));
  if (after) {
    const number = meaning.value(after, QNT("numericValue"));
    const unit = meaning.value(after, QNT("inUnit"));
    return `${head} after ${[number, unit ? lex.label(unit) : ""].filter(Boolean).join(" ")}`.trim();
  }
  return head;
}

/** Every regime of the meaning configuration, with the layout of its states: columns by distance from the initial state
 * (longest forward path, and a state the initial one does not reach follows the last column), rows by label and then IRI, so the same graph always
 * draws the same diagram. */
export function regimesOf(meaning: Graph, lex: Lexicon): Regime[] {
  return meaning
    .ofType(INS("Regime"))
    .map((r) => r.value)
    .sort()
    .map((regime) => {
      const stateIris = meaning.subjects(BHV("inStateSpace"), regime).map((s) => s.value).sort();
      const initial = meaning.value(regime, BHV("initialState"));
      if (initial && !stateIris.includes(initial)) stateIris.push(initial);
      const transitions = stateIris
        .flatMap((from) => meaning.subjects(BHV("fromState"), from).map((t) => t.value))
        .sort()
        .map((t): RegimeTransition => {
          const trigger = meaning.value(t, BHV("hasTrigger"));
          return { iri: t, from: meaning.value(t, BHV("fromState"))!, to: meaning.value(t, BHV("toState")) ?? "", trigger, label: trigger ? triggerLabel(meaning, lex, trigger) : "" };
        });
      const stateLabel = (s: string) => {
        const kind = meaning.value(s, INS("stateKind"));
        return kind ? lex.label(kind) : lex.label(s);
      };
      // A state sits after every state that reaches it by a forward transition. A transition back to a state still being
      // explored (found by depth first search from the initial state) is left out, so the rest is acyclic.
      const layer = new Map<string, number>();
      const forward: RegimeTransition[] = [];
      if (initial) {
        const onPath = new Set<string>();
        const reached = new Set<string>();
        const visit = (s: string) => {
          reached.add(s);
          onPath.add(s);
          for (const t of transitions) {
            if (t.from !== s || !stateIris.includes(t.to)) continue;
            if (!onPath.has(t.to)) forward.push(t);
            if (!reached.has(t.to)) visit(t.to);
          }
          onPath.delete(s);
        };
        visit(initial);
        for (const s of reached) layer.set(s, 0);
        for (let grew = true; grew; ) {
          grew = false;
          for (const t of forward) {
            if (layer.get(t.to)! < layer.get(t.from)! + 1) {
              layer.set(t.to, layer.get(t.from)! + 1);
              grew = true;
            }
          }
        }
      }
      const farthest = Math.max(-1, ...layer.values());
      const column = (s: string) => layer.get(s) ?? farthest + 1;
      const ordered = [...stateIris].sort((a, b) => column(a) - column(b) || stateLabel(a).localeCompare(stateLabel(b)) || a.localeCompare(b));
      const used = new Map<number, number>();
      const relations = relationsOf(meaning, lex);
      const states = ordered.map((s): RegimeState => {
        const c = column(s);
        const row = used.get(c) ?? 0;
        used.set(c, row + 1);
        const gates = meaning
          .subjects(INS("appliesInState"), s)
          .filter((g) => meaning.types(g).includes(INS("Template")))
          .map((g) => g.value)
          .sort()
          .map((g) => {
            const relation = relations.find((r) => r.iri === g);
            return { iri: g, text: relation ? say(relation, lex) : lex.label(g) };
          });
        return { iri: s, label: stateLabel(s), initial: s === initial, column: c, row, gates };
      });
      return {
        iri: regime,
        label: lex.label(regime),
        term: meaning.value(regime, INS("arisesUnder")),
        states,
        transitions,
        columns: Math.max(0, ...states.map((s) => s.column + 1)),
        rows: Math.max(0, ...used.values()),
      };
    });
}

/** The regime a node belongs to, whether it is the regime, one of its states, a transition or a trigger. */
export function regimeOfNode(regimes: Regime[], node: string): Regime | undefined {
  return regimes.find((r) => r.iri === node || r.states.some((s) => s.iri === node) || r.transitions.some((t) => t.iri === node || t.trigger === node));
}

// ---- Dry run ------------------------------------------------------------------------------------

/** The kind of sample a condition takes: a number for an interval condition, concepts for any other. */
export function isIntervalCondition(world: Graph, condition: string): boolean {
  return world.types(condition).includes(ELG("IntervalCondition")) || world.value(condition, ELG("matchStrategy")) === ELG("IntervalContainment");
}

/** The concepts a concept condition may be given: the members of the schemes its contract binds and those of the concepts it requires or excludes. */
export function conceptsForCondition(world: Graph, condition: string): { iri: string; label: string }[] {
  const schemes = new Set<string>();
  for (const contract of world.objects(condition, ELG("constrainedByContract"))) for (const s of world.objects(contract, VOC("boundScheme"))) schemes.add(s.value);
  for (const p of [ELG("requiredConcept"), ELG("excludedConcept")]) for (const c of world.objects(condition, p)) for (const s of world.objects(c, SKOS("inScheme"))) schemes.add(s.value);
  const found = new Map<string, string>();
  for (const c of world.subjects(SKOS("inScheme"))) {
    if (c.termType !== "NamedNode") continue;
    if (world.objects(c, SKOS("inScheme")).some((s) => schemes.has(s.value))) found.set(c.value, world.value(c, SKOS("prefLabel")) ?? world.value(c, RDFS("label")) ?? localName(c.value));
  }
  return [...found].map(([i, label]) => ({ iri: i, label })).sort((a, b) => a.label.localeCompare(b.label) || a.iri.localeCompare(b.iri));
}

export interface Sample {
  condition: string;
  /** A number, as typed, for an interval condition. */
  number?: string;
  concepts?: string[];
}

export const DRY_RUN = "urn:lattice:studio:dryrun:1";

/** The `cst:DryRun` request: the term and one fact per number or concept given. It is a scratch graph for the job's input, never put into a part. */
export function dryRunGraph(term: string, samples: Sample[]): Graph {
  return Graph.empty().edit((e) => {
    e.add(DRY_RUN, TYPE, iri(CST("DryRun")));
    e.add(DRY_RUN, CST("term"), iri(term));
    let n = 0;
    const fact = (condition: string) => {
      const node = `${DRY_RUN}:fact:${++n}`;
      e.add(DRY_RUN, CST("fact"), iri(node));
      e.add(node, CST("forCondition"), iri(condition));
      return node;
    };
    for (const s of samples) {
      if (s.number !== undefined && s.number.trim() !== "" && Number.isFinite(Number(s.number))) e.add(fact(s.condition), CST("number"), typed(String(Number(s.number)), XSD("decimal")));
      for (const c of s.concepts ?? []) e.add(fact(s.condition), CST("concept"), iri(c));
    }
  });
}
