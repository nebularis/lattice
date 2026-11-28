// SPDX-License-Identifier: MPL-2.0
// The construction editor's pure part (SVA-S1 part 4, SVA-Q57 (b)): a graph construction's constructed node, and the node an expansion makes for each member, which
// is the same statement stated beside an expansion statement on one result-target binding (srf:P22). Each function is one edit of the surface part, as the Surface
// README's section 6.16 gives it. The laws the editor keeps while it edits are srf:P11 (a node states one class and one identity, and writes each property once),
// srf:P12 (a value is read from an evidence binding of the same contract), srf:P13 (a key part is required evidence), srf:P23 (the member is spoken of only beside an
// expansion), srf:P24 (what an identity names) and srf:P25 (a value is read from a binding or from the member). The marks are the shapes' rules, and a mark never
// stops an edit, since an author reaches a good statement through breaches.

import { Graph, SRF, TYPE, XSD, iri, namedNode, typed, type Term } from "@lattice/authoring-domain";
import { fresh, isBoundEvidence, mark, objectsOf, validIri, type Evidence, type LawMark, type StatementContext } from "./statement";

export type Identity = "PerInstance" | "ByKey" | "MemberNode";
export const IDENTITIES: Record<Identity, string> = { PerInstance: SRF("PerInstance"), ByKey: SRF("ByKey"), MemberNode: SRF("MemberNode") };
const identityOf = (value: string | undefined): Identity | undefined => (Object.keys(IDENTITIES) as Identity[]).find((k) => IDENTITIES[k] === value);

/** One value a constructed node writes. A blank node is named by the key `value` gives it, which holds for the graph it was read from. */
export interface WriteRow {
  key: string;
  term: Term;
  property?: string;
  /** The evidence binding it is read from, and whether it states the member in its place. */
  binding?: string;
  member: boolean;
  /** How many times it states each part, for the marks. */
  properties: number;
  bindings: number;
  members: number;
}

export interface Construction {
  /** The node the result-target binding states. */
  node: string;
  /** Whether the statement is a node named by an IRI that is typed as a constructed node. */
  named: boolean;
  typedAsNode: boolean;
  classes: string[];
  identities: string[];
  keyBindings: string[];
  /** The key member and member name values as stated, for the marks. */
  keyMembers: Term[];
  memberNames: Term[];
  writes: WriteRow[];
  /** Whether an expansion statement stands on the same binding, which a node for each member is stated beside. */
  besideExpansion: boolean;
  class?: string;
  identity?: Identity;
  keyMember: boolean;
  memberName?: string;
}

const isTrue = (t: Term) => t.termType === "Literal" && t.value === "true" && t.datatype.value === XSD("boolean");

/** The construction the result-target binding states, or none where it states none. */
export function readConstruction(g: Graph, ctx: StatementContext): Construction | undefined {
  if (!ctx.result) return undefined;
  const stated = g.object(ctx.result, SRF("constructedAs"));
  if (!stated) return undefined;
  const node = stated.value;
  const writes = g.objects(stated, SRF("writes")).map((term): WriteRow => ({
    key: term.value, term,
    property: g.objects(term, SRF("writesProperty"))[0]?.value, binding: g.objects(term, SRF("fromBinding"))[0]?.value, member: g.objects(term, SRF("fromMember")).some(isTrue),
    properties: g.objects(term, SRF("writesProperty")).length, bindings: g.objects(term, SRF("fromBinding")).length, members: g.objects(term, SRF("fromMember")).length,
  })).sort((a, b) => (a.property ?? "").localeCompare(b.property ?? "") || a.key.localeCompare(b.key));
  const identities = g.objects(stated, SRF("nodeIdentity")).map((t) => t.value);
  const keyMembers = g.objects(stated, SRF("keyMember"));
  return {
    node, named: stated.termType === "NamedNode", typedAsNode: stated.termType === "NamedNode" && g.types(stated).includes(SRF("ConstructedNode")),
    classes: g.objects(stated, SRF("constructedClass")).map((t) => t.value), identities,
    keyBindings: g.objects(stated, SRF("keyBinding")).map((t) => t.value).sort(), keyMembers, memberNames: g.objects(stated, SRF("memberName")),
    writes, besideExpansion: g.objects(ctx.result, SRF("expandedAs")).length > 0,
    class: g.objects(stated, SRF("constructedClass"))[0]?.value, identity: identities.length === 1 ? identityOf(identities[0]) : undefined, keyMember: keyMembers.some(isTrue),
    memberName: g.objects(stated, SRF("memberName"))[0]?.value,
  };
}

/** The construction an edit may change, which is a node named by an IRI, the only node an edit can address. */
function editable(g: Graph, ctx: StatementContext): Construction | undefined {
  const c = readConstruction(g, ctx);
  return c?.named ? c : undefined;
}

// --- what each part may be -----------------------------------------------------------------------------------------------------------------

export interface ConstructionChoices {
  /** The identities offered. MemberNode only beside an expansion (srf:P23). */
  identities: Identity[];
  /** Required-evidence bindings that bind a property, the only key parts (srf:P13). Offered only for a key. */
  keys: Evidence[];
  /** Evidence bindings that bind a property, which a value may be read from (srf:P12). */
  from: Evidence[];
  /** Whether the member may be a key part, a name or a value, which only a node of an expansion that is keyed or a value allows (srf:P23, srf:P24). */
  member: { key: boolean; name: boolean; value: boolean };
}

export function constructionChoices(g: Graph, ctx: StatementContext): ConstructionChoices {
  const c = readConstruction(g, ctx);
  const besideExpansion = c?.besideExpansion === true;
  return {
    identities: besideExpansion ? ["PerInstance", "ByKey", "MemberNode"] : ["PerInstance", "ByKey"],
    keys: c?.identity === "ByKey" ? ctx.evidence.filter((e) => e.role === "required" && e.property !== undefined && !c.keyBindings.includes(e.iri)) : [],
    from: ctx.evidence.filter((e) => e.property !== undefined),
    member: { key: besideExpansion && c?.identity === "ByKey", name: besideExpansion && c?.identity !== "MemberNode", value: besideExpansion },
  };
}

// --- the edits -------------------------------------------------------------------------------------------------------------------------------

/**
 * States a construction on the result-target binding of a graph construction, which states none yet. The node is minted in the baseline's namespace, typed, and states
 * a node for each instance, the identity that merges nothing, since the contract never leaves an identity to silence. Its class and its values are left for the author.
 */
export function addConstruction(g: Graph, ctx: StatementContext): Graph {
  if (ctx.kind !== "construction" || !ctx.result || g.object(ctx.result, SRF("constructedAs")) || g.object(ctx.result, SRF("expandedAs"))) return g;
  return writeNode(g, ctx, "node");
}

/**
 * States a node for each member on the result-target binding of an expansion that states its expansion statement and no construction (srf:P22). It is a node for each
 * instance and member, which merges nothing.
 */
export function addMemberNode(g: Graph, ctx: StatementContext): Graph {
  if (ctx.kind !== "expansion" || !ctx.result || !g.object(ctx.result, SRF("expandedAs")) || g.object(ctx.result, SRF("constructedAs"))) return g;
  return writeNode(g, ctx, "member node");
}

function writeNode(g: Graph, ctx: StatementContext, what: string): Graph {
  const node = fresh(g, ctx, what);
  return g.edit((e) => {
    e.add(node, TYPE, iri(SRF("ConstructedNode")));
    e.add(node, SRF("nodeIdentity"), iri(SRF("PerInstance")));
    e.add(ctx.result!, SRF("constructedAs"), iri(node));
  });
}

/** Removes the construction, the node, the values it writes and the statement on the binding, which a node nothing states is not left behind (srf:P10). */
export function removeConstruction(g: Graph, ctx: StatementContext): Graph {
  const c = readConstruction(g, ctx);
  if (!c || !ctx.result) return g;
  return g.edit((e) => {
    const stated = objectsOf(e, ctx.result!, SRF("constructedAs"))[0];
    for (const w of objectsOf(e, stated, SRF("writes"))) e.remove(w);
    e.setAll(ctx.result!, SRF("constructedAs"), []);
    e.remove(stated);
  });
}

/** Sets the class the node is typed with, an absolute IRI, or removes it. A class the ontology does not declare is the author's, and the editor marks it undeclared. */
export function setConstructedClass(g: Graph, ctx: StatementContext, cls: string | undefined): Graph {
  const c = editable(g, ctx);
  if (!c || (cls !== undefined && !validIri(cls))) return g;
  if (c.classes.length === (cls ? 1 : 0) && c.classes[0] === cls) return g;
  return g.edit((e) => e.setAll(c.node, SRF("constructedClass"), cls ? [iri(cls)] : []));
}

/**
 * Sets the identity. What the new identity names is the only thing it can keep (srf:P24), so a node for each instance names no key part and no key member, and the
 * member itself names none of them and no member name. The member itself is offered only beside an expansion (srf:P23).
 */
export function setIdentity(g: Graph, ctx: StatementContext, identity: Identity): Graph {
  const c = editable(g, ctx);
  if (!c || (identity === "MemberNode" && !c.besideExpansion)) return g;
  if (c.identities.length === 1 && c.identities[0] === IDENTITIES[identity]) return g;
  return g.edit((e) => {
    e.setAll(c.node, SRF("nodeIdentity"), [iri(IDENTITIES[identity])]);
    if (identity !== "ByKey") {
      e.setAll(c.node, SRF("keyBinding"), []);
      e.setAll(c.node, SRF("keyMember"), []);
    }
    if (identity === "MemberNode") e.setAll(c.node, SRF("memberName"), []);
  });
}

/** Adds a part of the key, a required-evidence binding of the contract that binds a property (srf:P13), to a node that is by key (srf:P24). */
export function addKeyBinding(g: Graph, ctx: StatementContext, binding: string): Graph {
  const c = editable(g, ctx);
  if (!c || c.identity !== "ByKey" || c.keyBindings.includes(binding)) return g;
  if (!ctx.evidence.some((e) => e.iri === binding && e.role === "required" && e.property !== undefined)) return g;
  return g.edit((e) => e.add(c.node, SRF("keyBinding"), iri(binding)));
}

export function removeKeyBinding(g: Graph, ctx: StatementContext, binding: string): Graph {
  const c = editable(g, ctx);
  if (!c || !c.keyBindings.includes(binding)) return g;
  return g.edit((e) => e.store.removeQuad(g.quads(c.node, SRF("keyBinding"), binding)[0]));
}

/** Sets whether the member is a part of the key, which a keyed node of an expansion may state, true or not at all (srf:P23, srf:P24). */
export function setKeyMember(g: Graph, ctx: StatementContext, on: boolean): Graph {
  const c = editable(g, ctx);
  if (!c || !c.besideExpansion || c.identity !== "ByKey" || c.keyMember === on) return g;
  return g.edit((e) => e.setAll(c.node, SRF("keyMember"), on ? [typed("true", XSD("boolean"))] : []));
}

/** Sets the property of the members whose value names them, or none. Only a node of an expansion states one, and the member itself states none (srf:P23, srf:P24). */
export function setMemberName(g: Graph, ctx: StatementContext, property: string | undefined): Graph {
  const c = editable(g, ctx);
  if (!c || !c.besideExpansion || c.identity === "MemberNode" || (property !== undefined && !validIri(property))) return g;
  if (c.memberNames.length === (property ? 1 : 0) && c.memberNames[0]?.value === property) return g;
  return g.edit((e) => e.setAll(c.node, SRF("memberName"), property ? [namedNode(property)] : []));
}

/** Where a written value is read from, an evidence binding of the contract or the member. */
export type WriteFrom = { binding: string } | { member: true };

const writeTerm = (c: Construction, key: string) => c.writes.find((w) => w.key === key)?.term;

/** Whether `from` is a source this node may read a value from now (srf:P12, srf:P23, srf:P25). */
function readable(ctx: StatementContext, c: Construction, from: WriteFrom): boolean {
  if ("member" in from) return c.besideExpansion;
  return isBoundEvidence(ctx, from.binding);
}

/** Adds a value the node writes, a property each node writes once (srf:P11), read from an evidence binding or the member (srf:P12, srf:P25). */
export function addWrite(g: Graph, ctx: StatementContext, property: string, from: WriteFrom): Graph {
  const c = editable(g, ctx);
  if (!c || !c.named || !validIri(property) || c.writes.some((w) => w.property === property) || !readable(ctx, c, from)) return g;
  const node = fresh(g, ctx, `${property.slice(Math.max(property.lastIndexOf("#"), property.lastIndexOf("/")) + 1)} value`);
  return g.edit((e) => {
    e.add(c.node, SRF("writes"), iri(node));
    e.add(node, SRF("writesProperty"), iri(property));
    if ("member" in from) e.add(node, SRF("fromMember"), typed("true", XSD("boolean")));
    else e.add(node, SRF("fromBinding"), iri(from.binding));
  });
}

/** Sets the property a value is written as, refused where the node writes it already (srf:P11). */
export function setWriteProperty(g: Graph, ctx: StatementContext, key: string, property: string): Graph {
  const c = editable(g, ctx);
  const term = c && writeTerm(c, key);
  if (!c || !term || !validIri(property) || c.writes.some((w) => w.key !== key && w.property === property)) return g;
  if (g.objects(term, SRF("writesProperty")).length === 1 && g.value(term, SRF("writesProperty")) === property) return g;
  return g.edit((e) => e.setAll(term, SRF("writesProperty"), [namedNode(property)]));
}

/** Sets where a value is read from. Exactly one of the binding and the member is stated after it (srf:P25), and a value read from the member is a node of an expansion's alone (srf:P23). */
export function setWriteFrom(g: Graph, ctx: StatementContext, key: string, from: WriteFrom): Graph {
  const c = editable(g, ctx);
  const term = c && writeTerm(c, key);
  if (!c || !term || !readable(ctx, c, from)) return g;
  return g.edit((e) => {
    e.setAll(term, SRF("fromBinding"), "binding" in from ? [namedNode(from.binding)] : []);
    e.setAll(term, SRF("fromMember"), "member" in from ? [typed("true", XSD("boolean"))] : []);
  });
}

export function removeWrite(g: Graph, ctx: StatementContext, key: string): Graph {
  const c = editable(g, ctx);
  const term = c && writeTerm(c, key);
  if (!c || !term) return g;
  return g.edit((e) => e.remove(term));
}

// --- the marks -----------------------------------------------------------------------------------------------------------------------------

/** The bindings of the contract that state a construction, whatever their role, since the shapes read each of them. */
const stating = (g: Graph, ctx: StatementContext, predicate: string) => ctx.bindings.filter((b) => g.objects(b.iri, predicate).length > 0);

/**
 * The breaches of the laws a constructed node is held to, as the shapes of the Surface README state them. Each rule is the shape's: srf:P10 where the statement stands,
 * srf:P11 for the class, the identity and the values, srf:P12 for what a value is read from, srf:P13 for a key part, srf:P22 and srf:P23 for a node beside an expansion,
 * srf:P24 for what an identity names and srf:P25 for a value's source. The shapes that state what a node holds read a node typed as a constructed node, and the
 * shapes of a written value read each value a node writes, so a node that is not typed is marked for that and for its values alone.
 */
export function constructionMarks(g: Graph, ctx: StatementContext): LawMark[] {
  const out: LawMark[] = [];
  const results = ctx.bindings.filter((b) => b.role === "result");
  if (ctx.kinds.has("construction")) {
    if (!results.some((b) => g.objects(b.iri, SRF("constructedAs")).length > 0)) out.push(mark(10, "required", "node", "A graph construction projection states no constructed node on its result-target role binding."));
    if (results.some((b) => b.property === undefined)) out.push(mark(10, "link-property", "link", "The result-target role binding of a graph construction binds no property, so there is no link from an instance to the node."));
  }
  const done = new Set<string>();
  for (const link of stating(g, ctx, SRF("constructedAs"))) {
    const placed = link.role === "result" && (ctx.kinds.has("construction") || (ctx.kinds.has("expansion") && g.objects(link.iri, SRF("expandedAs")).length > 0));
    if (!placed) out.push(mark(ctx.kinds.has("expansion") ? 22 : 10, "placement", "node", "A role binding states a constructed node and is not the result-target role binding of a graph construction or of an expansion that states its expansion statement on the same binding."));
    for (const node of g.objects(link.iri, SRF("constructedAs"))) {
      const asNode = node.termType === "NamedNode" && g.types(node).includes(SRF("ConstructedNode"));
      if (!asNode) out.push(mark(10, "typed", "node", "A role binding states as its constructed node a term that is not a srf:ConstructedNode named by an IRI."));
      if (node.termType === "Literal") continue;
      const key = `${node.termType}:${node.value}`;
      // The writes of a node are marked once, and what reads the binding that states it is marked for each binding that does.
      out.push(...nodeMarks(g, ctx, node, !done.has(key), g.types(node).includes(SRF("ConstructedNode"))));
      done.add(key);
    }
  }
  return out;
}

function nodeMarks(g: Graph, ctx: StatementContext, node: Term, first: boolean, typedNode: boolean): LawMark[] {
  const out: LawMark[] = [];
  const get = (p: string) => g.objects(node, p);
  const classes = get(SRF("constructedClass"));
  const identities = get(SRF("nodeIdentity")).map((t) => t.value);
  const keyBindings = get(SRF("keyBinding")).map((t) => t.value);
  const keyMembers = get(SRF("keyMember"));
  const memberNames = get(SRF("memberName"));
  const writes = get(SRF("writes"));
  const writeRows = writes.map((term) => ({
    term, key: term.value,
    properties: g.objects(term, SRF("writesProperty")), bindings: g.objects(term, SRF("fromBinding")), members: g.objects(term, SRF("fromMember")),
  }));
  if (typedNode && first) {
    if (classes.length !== 1 || classes.some((t) => t.termType !== "NamedNode")) out.push(mark(11, "class", "class", "A constructed node states exactly one class."));
    if (identities.length !== 1 || !identityOf(identities[0])) out.push(mark(11, "identity", "identity", "A constructed node states exactly one identity, srf:PerInstance, srf:ByKey or, for a node of an expansion, srf:MemberNode."));
    if (keyMembers.length > 1 || keyMembers.some((t) => !isTrue(t))) out.push(mark(24, "key-member", "key", "A constructed node states at most one key member, and it is true."));
    if (memberNames.length > 1 || memberNames.some((t) => t.termType !== "NamedNode")) out.push(mark(24, "member-name", "name", "A constructed node states at most one member name, a property named by an IRI."));
    if (writes.length === 0) out.push(mark(11, "writes", "writes", "A constructed node writes at least one value."));
    // What an identity names (srf:P11, srf:P24). The one shape says both, so the marks do.
    if (identities.includes(IDENTITIES.ByKey) && keyBindings.length === 0 && keyMembers.length === 0) out.push(mark(24, "key-parts", "key", "A constructed node by key names no key binding and no key member."));
    if ((identities.includes(IDENTITIES.PerInstance) || identities.includes(IDENTITIES.MemberNode)) && (keyBindings.length > 0 || keyMembers.length > 0)) {
      out.push(mark(24, "key-forbidden", "key", "A constructed node for each instance, or the member itself, names a key binding or a key member."));
    }
    if (identities.includes(IDENTITIES.MemberNode) && (keyBindings.length > 0 || keyMembers.length > 0 || memberNames.length > 0)) {
      out.push(mark(24, "member-node", "identity", "A constructed node that is the member itself names a key binding, a key member or a member name, though it spells nothing."));
    }
    // The member is spoken of only beside an expansion statement on one binding (srf:P23).
    const speaksOfMember = keyMembers.length > 0 || memberNames.length > 0 || identities.includes(IDENTITIES.MemberNode) || writeRows.some((w) => w.members.length > 0);
    const beside = g.subjects(SRF("constructedAs"), node).some((b) => g.objects(b, SRF("expandedAs")).length > 0);
    if (speaksOfMember && !beside) out.push(mark(23, "member-placement", "node", "A constructed node states a key member, a member name or the member itself as its identity, or writes a value from the member, and is not stated beside an expansion statement on one binding."));
    // Each property written once, and each value read from evidence of the contract (srf:P11, srf:P12).
    for (const w of writeRows) {
      if (w.properties.some((p) => writeRows.some((o) => o.key !== w.key && o.properties.some((t) => t.value === p.value)))) {
        out.push(mark(11, "property-once", `write:${w.key}`, "A constructed node writes one property more than once."));
      }
      for (const b of w.bindings) {
        if (!isBoundEvidence(ctx, b.value)) out.push(mark(12, "evidence", `write:${w.key}`, "A value a constructed node writes is read from a term that is not a candidate-evidence or required-evidence role binding of the stating contract that binds a property."));
      }
    }
    for (const k of keyBindings) {
      if (!ctx.evidence.some((e) => e.iri === k && e.role === "required" && e.property !== undefined)) out.push(mark(13, "key-evidence", `key:${k}`, "A key binding of a constructed node is not a required-evidence role binding of the stating contract that binds a property."));
    }
  }
  // Each value a node writes is marked whether or not the node is typed, which the shapes of a value read as the object of a write.
  if (first) {
    for (const w of writeRows) {
      if (w.properties.length !== 1 || w.properties.some((t) => t.termType !== "NamedNode")) out.push(mark(12, "property", `write:${w.key}`, "A written value states exactly one property it is written as."));
      if (w.bindings.length > 1 || w.bindings.some((t) => t.termType !== "NamedNode")) out.push(mark(12, "binding", `write:${w.key}`, "A written value names at most one evidence role binding it is read from."));
      if (w.members.length > 1 || w.members.some((t) => !isTrue(t))) out.push(mark(25, "from-member", `write:${w.key}`, "A written value states at most one from member, and it is true."));
      if ((w.bindings.length === 0 && w.members.length === 0) || (w.bindings.length > 0 && w.members.length > 0)) out.push(mark(25, "source", `write:${w.key}`, "A written value states neither an evidence role binding nor the member it is read from, or states both. It states exactly one of them."));
    }
  }
  return out;
}
