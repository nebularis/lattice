// SPDX-License-Identifier: MPL-2.0
// What the construction, join and expansion editors share (SVA-S1 part 4, SVA-Q57 (b)). A projection states what it writes on its result-target role binding, with
// srf:constructedAs, srf:joinedAs or srf:expandedAs, and the Surface README says what each statement holds and which laws it is held to (srf:P10 to srf:P25). The
// editors are functions of the configuration in the way the expression editor's are. Each edit is a graph in and a graph out, so the editor makes it with one
// `model.edit` and undo works as for any edit. An edit that a law forbids, where the editor can know it, returns the graph it was given. Each editor also marks a breach
// of the laws its statement is held to, computed by the rules the shapes state, as the expression editor marks its typing. Nothing here evaluates or lowers a contract.

import { Graph, SRF, TYPE, XSD, iri, type GraphEditor, type Term } from "@lattice/authoring-domain";
import type { Issue } from "../rdf/report";
import { mint, nameOf } from "../rdf/editors";
import { bindingsOf, type Binding } from "./drawing";

/** A breach of a law, as the shape that states it would report it, and where the editor puts it. */
export interface LawMark {
  /** The law it breaches, such as `srf:P11`. */
  law: string;
  /** A short name for the rule, which the editor and a test can name it by. */
  code: string;
  message: string;
  /** The element of the statement it concerns, such as `node`, `class`, `identity`, `key`, `link`, `write:<key>`, `pair:<key>`, `source`, `path` or `from`. */
  part: string;
}

export const mark = (law: number, code: string, part: string, message: string): LawMark => ({ law: `srf:P${law}`, code, part, message });

export type StatementKind = "construction" | "join" | "expansion";

/** What a contract's `srf:projectionKind` says it is, which decides the statement the editor offers to add. */
const KIND_OF: Record<string, StatementKind | "derivation"> = {
  GraphConstructionProjection: "construction",
  JoinProjection: "join",
  ExpansionProjection: "expansion",
  DerivationProjection: "derivation",
};

export interface Evidence {
  iri: string;
  role: "required" | "candidate";
  property?: string;
  carrier?: string;
  datatype?: string;
}

export interface StatementContext {
  contract: string;
  name: string;
  /** The kind the contract says it is, and none where it states another or none. */
  kind: StatementKind | "derivation" | undefined;
  /** Every kind it says, which the shapes read, where it says more than one. */
  kinds: ReadonlySet<StatementKind | "derivation">;
  /** The contract's own carrier, and every carrier it states, which the shapes read each of. */
  carrier?: string;
  carriers: string[];
  /** The result-target role binding, which states the statement, and the property it binds. */
  result?: string;
  resultProperty?: string;
  bindings: Binding[];
  /** The contract's evidence bindings, required and candidate, whether or not they bind a property. */
  evidence: Evidence[];
  /** The baseline's namespace, where a node is minted, and the graph whose names a minted IRI must not repeat. */
  namespace: string;
  known?: Graph;
}

export function statementContext(g: Graph, contract: string, namespace: string, known?: Graph): StatementContext {
  const bindings = bindingsOf(g, contract);
  const result = bindings.find((b) => b.role === "result");
  const kinds = g.objects(contract, SRF("projectionKind")).map((t) => KIND_OF[t.value.slice(SRF("").length)]).filter((k): k is NonNullable<typeof k> => k !== undefined);
  const kind = KIND_OF[g.value(contract, SRF("projectionKind"))?.slice(SRF("").length) ?? ""];
  return {
    contract, name: nameOf(g, contract), kind, kinds: new Set(kinds), carrier: g.value(contract, SRF("carrier")), carriers: g.objects(contract, SRF("carrier")).map((t) => t.value), result: result?.iri, resultProperty: result?.property, bindings, namespace, known,
    evidence: bindings.filter((b): b is Binding & { role: "required" | "candidate" } => b.role === "required" || b.role === "candidate").map((b) => ({ iri: b.iri, role: b.role, property: b.property, carrier: b.carrier, datatype: b.datatype })),
  };
}

/** The evidence bindings of the contract that bind a property, which a value, a key part, a join side or an expansion reads. */
export const bound = (ctx: StatementContext): Evidence[] => ctx.evidence.filter((e) => e.property !== undefined);

export const evidenceById = (ctx: StatementContext, id: string): Evidence | undefined => ctx.evidence.find((e) => e.iri === id);

/** Whether `id` is a candidate-evidence or required-evidence role binding of the contract that binds a property, the test of srf:P12, P16 and P19. */
export const isBoundEvidence = (ctx: StatementContext, id: string): boolean => bound(ctx).some((e) => e.iri === id);

/** A term the editor writes as an IRI, which is absolute, has no space and none of the characters an IRI cannot hold. */
export const validIri = (text: string): boolean => /^[A-Za-z][A-Za-z0-9+.-]*:[^\s<>"{}|\\^`]+$/.test(text);

/** A fresh IRI in the baseline's namespace, readable, from the contract's name and what the node is for. */
export function fresh(g: Graph, ctx: StatementContext, what: string): string {
  const world = ctx.known ? g.merge(ctx.known) : g;
  return mint(world, ctx.namespace, `${ctx.name} ${what}`);
}

/**
 * A mint for an edit that names several nodes at once. Each name is fresh in the graph, in the baseline and among the names this mint has given, which the graph an
 * edit starts from does not yet hold.
 */
export function minter(g: Graph, ctx: StatementContext): (what: string) => string {
  let world = ctx.known ? g.merge(ctx.known) : g;
  return (what) => {
    const name = mint(world, ctx.namespace, `${ctx.name} ${what}`);
    world = world.edit((w) => w.add(name, TYPE, iri(SRF("ProjectionContract"))));
    return name;
  };
}

/** Removes every evidence binding of the contract that nothing reads, in one edit, which the author asks for once a contract is wired up. A contract with none is returned as it was. */
export function removeUnreadEvidence(g: Graph, contract: string): Graph {
  const unread = unreadEvidence(g, contract).map((i) => i.focus!);
  if (unread.length === 0) return g;
  return g.edit((e) => {
    for (const b of unread) e.remove(b);
  });
}

export const objectsOf = (e: GraphEditor, s: Term | string, p: string): Term[] => e.store.getObjects(typeof s === "string" ? iri(s) : s, iri(p), null);

/**
 * The evidence bindings of a contract that nothing reads: no expression, written value, key, join pair or expansion names them. The editors never
 * remove a binding when a statement stops reading it, so partly wired work is kept, and this marks what is left instead. It is information and
 * no law. Required evidence that nothing reads still excludes an instance that lacks the value, which narrows the contract, so the mark says so.
 */
export function unreadEvidence(g: Graph, contract: string): Issue[] {
  if (!g.types(contract).includes(SRF("ProjectionContract"))) return [];
  return bindingsOf(g, contract)
    .filter((b) => (b.role === "required" || b.role === "candidate") && g.quads(null, null, iri(b.iri)).every((q) => q.predicate.value === SRF("hasRoleBinding")))
    .map((b) => ({
      severity: "Info" as const,
      focus: b.iri,
      path: SRF("roleKind"),
      code: "unread-evidence",
      source: "studio" as const,
      message: b.role === "required"
        ? "No statement reads this binding. As required evidence it still excludes an instance that lacks the value."
        : "No statement reads this binding, so it has no effect.",
    }));
}

export const isTyped = (g: Graph, node: Term | string, type: string): boolean => g.types(node).includes(type);

export const xsdName = (datatype: string) => datatype.slice(XSD("").length);

/** The datatypes a join pair is offered to be compared as, the ones the Surface README's examples and the sample worlds use. */
export const JOIN_DATATYPES = ["string", "integer", "decimal", "boolean", "date", "dateTime", "anyURI"].map((n) => XSD(n));
