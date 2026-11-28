// SPDX-License-Identifier: MPL-2.0
// The join editor's pure part (SVA-S1 part 4, SVA-Q57 (b)): a join projection's statement of what relates an instance to an instance of a second carrier, as the Surface
// README's section 6.17 gives it. A pair is an equality of two evidence role bindings, one that reads the contract's own carrier and one that reads the second, the
// right one stating the datatype the left value is cast to. A composite key is several pairs. The laws the editor keeps while it edits are srf:P16 (a left binding names
// no carrier but the contract's own, a right binding names the second carrier, the same in every pair) and srf:P17 (every binding of the statement is of one evidence
// kind). The marks are the shapes' rules for srf:P14 to srf:P17. A rule that is left out means what the vocabulary says, so returning it to its default removes its triple.

import { Graph, SRF, TYPE, iri, localName, type GraphEditor, type Term } from "@lattice/authoring-domain";
import { fresh, mark, minter, referencedBy, validIri, type Evidence, type LawMark, type StatementContext } from "./statement";

export type Cardinality = "AtMostOne" | "AnyNumber";
export const CARDINALITIES: Record<Cardinality, string> = { AtMostOne: SRF("AtMostOne"), AnyNumber: SRF("AnyNumber") };
export const WORDS: Record<Cardinality, string> = { AtMostOne: "at most one", AnyNumber: "any number" };
/** What leaving a count out means, as the vocabulary states it (srf:P15). */
export const DEFAULTS: Record<"matches" | "links", Cardinality> = { matches: "AtMostOne", links: "AnyNumber" };
const PREDICATE = { matches: "joinMatches", links: "joinLinks" } as const;

export interface JoinPair {
  key: string;
  term: Term;
  left?: string;
  right?: string;
  /** How many times it states each side, for the marks. */
  lefts: number;
  rights: number;
}

export interface Join {
  node: string;
  named: boolean;
  typedAsJoin: boolean;
  pairs: JoinPair[];
  /** The counts as stated, which are none where the vocabulary's default applies. */
  matches: Term[];
  links: Term[];
  /** The second carrier the right bindings name, and the kind of evidence the statement's bindings are, where they agree. */
  secondCarrier?: string;
  evidenceKind?: "required" | "candidate";
}

const cardinalityOf = (t: Term | undefined): Cardinality | undefined => (Object.keys(CARDINALITIES) as Cardinality[]).find((k) => CARDINALITIES[k] === t?.value);

export const matchesOf = (j: Join): Cardinality | undefined => cardinalityOf(j.matches[0]);
export const linksOf = (j: Join): Cardinality | undefined => cardinalityOf(j.links[0]);

/** The join the result-target binding states, or none where it states none. */
export function readJoin(g: Graph, ctx: StatementContext): Join | undefined {
  if (!ctx.result) return undefined;
  const stated = g.object(ctx.result, SRF("joinedAs"));
  if (!stated) return undefined;
  const pairs = g.objects(stated, SRF("joinsOn")).map((term): JoinPair => ({
    key: term.value, term, left: g.objects(term, SRF("joinLeft"))[0]?.value, right: g.objects(term, SRF("joinRight"))[0]?.value,
    lefts: g.objects(term, SRF("joinLeft")).length, rights: g.objects(term, SRF("joinRight")).length,
  })).sort((a, b) => a.key.localeCompare(b.key));
  const rights = pairs.flatMap((p) => (p.right ? [ctx.evidence.find((e) => e.iri === p.right)] : [])).filter((e): e is Evidence => e !== undefined);
  const roles = new Set(pairs.flatMap((p) => [p.left, p.right]).flatMap((b) => ctx.evidence.filter((e) => e.iri === b).map((e) => e.role)));
  return {
    node: stated.value, named: stated.termType === "NamedNode", typedAsJoin: stated.termType === "NamedNode" && g.types(stated).includes(SRF("JoinStatement")), pairs,
    matches: g.objects(stated, SRF("joinMatches")), links: g.objects(stated, SRF("joinLinks")),
    secondCarrier: rights.find((e) => e.carrier !== undefined)?.carrier,
    evidenceKind: roles.size === 1 ? [...roles][0] : undefined,
  };
}

function editable(g: Graph, ctx: StatementContext): Join | undefined {
  const j = readJoin(g, ctx);
  return j?.named ? j : undefined;
}

// --- what each part may be -----------------------------------------------------------------------------------------------------------------

export interface JoinChoices {
  /** The bindings a left side may be: evidence of the contract that binds a property and names no other carrier, of the statement's kind (srf:P16, srf:P17). */
  left: Evidence[];
  /** The bindings a right side may be: evidence that binds a property and names the second carrier, of the statement's kind. */
  right: Evidence[];
  /** The kind a new binding takes, which is the statement's where it has one and else required evidence. */
  kind: "required" | "candidate";
}

export function joinChoices(g: Graph, ctx: StatementContext): JoinChoices {
  const j = readJoin(g, ctx);
  const kind = j?.evidenceKind ?? "required";
  const own = ctx.carrier;
  const sameKind = (e: Evidence) => e.property !== undefined && (j?.evidenceKind === undefined || e.role === j.evidenceKind);
  return {
    kind,
    left: ctx.evidence.filter((e) => sameKind(e) && (e.carrier === undefined || e.carrier === own)),
    right: ctx.evidence.filter((e) => sameKind(e) && e.carrier !== undefined && e.carrier !== own && (j?.secondCarrier === undefined || e.carrier === j.secondCarrier)),
  };
}

// --- the edits -------------------------------------------------------------------------------------------------------------------------------

/** States a join on the result-target binding of a join projection, which states none yet. The node is minted and states no pair and no count, which mean the defaults. */
export function addJoin(g: Graph, ctx: StatementContext): Graph {
  if (ctx.kind !== "join" || !ctx.result || g.object(ctx.result, SRF("joinedAs"))) return g;
  const node = fresh(g, ctx, "join");
  return g.edit((e) => {
    e.add(node, TYPE, iri(SRF("JoinStatement")));
    e.add(ctx.result!, SRF("joinedAs"), iri(node));
  });
}

/** Removes the statement and its pairs, and the bindings only they referred to, as removing each pair does. */
export function removeJoin(g: Graph, ctx: StatementContext): Graph {
  const j = editable(g, ctx);
  if (!j) return g;
  let next = g;
  for (const p of j.pairs) next = removePair(next, ctx, p.key);
  return next.edit((e) => {
    e.setAll(ctx.result!, SRF("joinedAs"), []);
    e.remove(j.node);
  });
}

/** Sets how many instances one value may name, or how many links one instance may have. `default` states nothing, which means what the vocabulary says. */
export function setCardinality(g: Graph, ctx: StatementContext, which: "matches" | "links", value: Cardinality | "default"): Graph {
  const j = editable(g, ctx);
  if (!j) return g;
  const stated = (which === "matches" ? j.matches : j.links).map((t) => t.value);
  const want = value === "default" ? [] : [CARDINALITIES[value]];
  if (stated.length === want.length && stated.every((v, i) => v === want[i])) return g;
  return g.edit((e) => e.setAll(j.node, SRF(PREDICATE[which]), want.map((v) => iri(v))));
}

/** Names the second carrier on every right binding of the statement, the same in every pair (srf:P16). A carrier that is the contract's own is refused. */
export function setSecondCarrier(g: Graph, ctx: StatementContext, carrier: string): Graph {
  const j = editable(g, ctx);
  if (!j || !validIri(carrier) || carrier === ctx.carrier) return g;
  const rights = [...new Set(j.pairs.flatMap((p) => (p.right ? [p.right] : [])))].filter((b) => ctx.evidence.some((e) => e.iri === b));
  if (rights.length === 0 || rights.every((b) => g.objects(b, SRF("bindsCarrier")).length === 1 && g.value(b, SRF("bindsCarrier")) === carrier)) return g;
  return g.edit((e) => {
    for (const b of rights) e.setAll(b, SRF("bindsCarrier"), [iri(carrier)]);
  });
}

/** A side of a pair, an evidence binding of the contract that stands now, or a property a new binding reads. */
export type Side = { binding: string } | { property: string };

/** Writes a role binding of the contract that reads `property`, of the evidence kind, naming a carrier where it reads the second. */
function newBinding(e: GraphEditor, ctx: StatementContext, name: string, property: string, kind: "required" | "candidate", carrier?: string): string {
  e.add(name, TYPE, iri(SRF("ProjectionRoleBinding")));
  e.add(name, SRF("roleKind"), iri(SRF(kind === "required" ? "RequiredEvidenceRole" : "CandidateEvidenceRole")));
  e.add(name, SRF("bindsProperty"), iri(property));
  if (carrier) e.add(name, SRF("bindsCarrier"), iri(carrier));
  e.add(ctx.contract, SRF("hasRoleBinding"), iri(name));
  return name;
}

/** Whether a side may stand as the left or the right of a pair now (srf:P16, srf:P17). */
function sideAllowed(g: Graph, ctx: StatementContext, j: Join, side: "left" | "right", pick: Side, carrier: string | undefined): boolean {
  const choices = joinChoices(g, ctx);
  if ("binding" in pick) return (side === "left" ? choices.left : choices.right).some((e) => e.iri === pick.binding);
  if (!validIri(pick.property)) return false;
  return side === "left" || (carrier !== undefined && validIri(carrier) && carrier !== ctx.carrier && (j.secondCarrier === undefined || j.secondCarrier === carrier));
}

/**
 * Adds a pair to the statement, which a composite key is several of. The left side is evidence that reads the contract's own carrier and the right side evidence that reads
 * the second, and a property picked for a side is read by a new binding of the statement's evidence kind. `carrier` is the second carrier a new right binding names, and
 * `datatype` the datatype the left value is cast to, stated on the right binding (srf:P17). A side the laws forbid is refused.
 */
export function addPair(g: Graph, ctx: StatementContext, spec: { left: Side; right: Side; carrier?: string; datatype?: string }): Graph {
  const j = editable(g, ctx);
  const carrier = spec.carrier ?? j?.secondCarrier;
  if (!j || !sideAllowed(g, ctx, j, "left", spec.left, undefined) || !sideAllowed(g, ctx, j, "right", spec.right, carrier)) return g;
  if (spec.datatype !== undefined && !validIri(spec.datatype)) return g;
  const kind = joinChoices(g, ctx).kind;
  const name = minter(g, ctx);
  return g.edit((editor) => {
    const left = "binding" in spec.left ? spec.left.binding : newBinding(editor, ctx, name(localName(spec.left.property)), spec.left.property, kind);
    const right = "binding" in spec.right ? spec.right.binding : newBinding(editor, ctx, name(localName(spec.right.property)), spec.right.property, kind, carrier);
    const pair = name("key");
    editor.add(pair, SRF("joinLeft"), iri(left));
    editor.add(pair, SRF("joinRight"), iri(right));
    editor.add(j.node, SRF("joinsOn"), iri(pair));
    if (spec.datatype) editor.setAll(right, SRF("bindsDatatype"), [iri(spec.datatype)]);
  });
}

/** Replaces one side of a pair, and the binding it stood on goes where nothing else refers to it. */
export function setPairSide(g: Graph, ctx: StatementContext, key: string, which: "left" | "right", pick: Side, carrier?: string): Graph {
  const j = editable(g, ctx);
  const pair = j?.pairs.find((p) => p.key === key);
  const wasOnly = which === "right" && j !== undefined && j.pairs.length === 1;
  const second = carrier ?? j?.secondCarrier;
  if (!j || !pair) return g;
  // A single pair may change the second carrier with its right side, which is the only binding that names it.
  const view: Join = wasOnly ? { ...j, secondCarrier: undefined } : j;
  if (!sideAllowed(g, ctx, view, which, pick, wasOnly ? carrier ?? j.secondCarrier : second)) return g;
  const kind = joinChoices(g, ctx).kind;
  const old = which === "left" ? pair.left : pair.right;
  const name = minter(g, ctx);
  return g.edit((editor) => {
    const next = "binding" in pick ? pick.binding : newBinding(editor, ctx, name(localName(pick.property)), pick.property, kind, which === "right" ? (wasOnly ? carrier ?? j.secondCarrier : second) : undefined);
    editor.setAll(pair.term, SRF(which === "left" ? "joinLeft" : "joinRight"), [iri(next)]);
    if (old && old !== next && referencedBy(editor, old, ctx.contract) === 0) editor.remove(old);
  });
}

/** Sets the datatype the left value is cast to, which the right binding of the pair states, or states none (srf:P17). */
export function setPairDatatype(g: Graph, ctx: StatementContext, key: string, datatype: string | undefined): Graph {
  const j = editable(g, ctx);
  const pair = j?.pairs.find((p) => p.key === key);
  if (!j || !pair?.right || !ctx.evidence.some((e) => e.iri === pair.right) || (datatype !== undefined && !validIri(datatype))) return g;
  const stated = g.objects(pair.right, SRF("bindsDatatype")).map((t) => t.value);
  if (stated.length === (datatype ? 1 : 0) && stated[0] === datatype) return g;
  return g.edit((e) => e.setAll(pair.right!, SRF("bindsDatatype"), datatype ? [iri(datatype)] : []));
}

/** Removes a pair and each of its bindings that nothing else refers to, so a pair added by the editor leaves nothing behind when it goes. */
export function removePair(g: Graph, ctx: StatementContext, key: string): Graph {
  const j = editable(g, ctx);
  const pair = j?.pairs.find((p) => p.key === key);
  if (!j || !pair) return g;
  return g.edit((e) => {
    e.remove(pair.term);
    for (const b of [pair.left, pair.right]) {
      if (b && ctx.evidence.some((x) => x.iri === b) && referencedBy(e, b, ctx.contract) === 0) e.remove(b);
    }
  });
}

// --- the marks -----------------------------------------------------------------------------------------------------------------------------

/** The role kind a binding states, as its IRI. */
const roleOf = (g: Graph, binding: string) => g.value(binding, SRF("roleKind"));

/**
 * The breaches of the laws a join is held to, as the shapes of the Surface README state them. srf:P14 is where the statement stands, srf:P15 what it states of its pairs
 * and counts, srf:P16 which bindings a pair names and which carrier, and srf:P17 the evidence kind and the datatype. Each binding of the contract that states a join is
 * read, as the shapes read it, and what a statement holds is read where it is typed as a join statement. A pair is read wherever a statement names it.
 */
export function joinMarks(g: Graph, ctx: StatementContext): LawMark[] {
  const out: LawMark[] = [];
  const results = ctx.bindings.filter((b) => b.role === "result");
  if (ctx.kinds.has("join")) {
    if (!results.some((b) => g.objects(b.iri, SRF("joinedAs")).length > 0)) out.push(mark(14, "required", "node", "A join projection states no join statement on its result-target role binding."));
    if (results.some((b) => b.property === undefined)) out.push(mark(14, "link-property", "link", "The result-target role binding of a join binds no property, so there is no link from an instance to the instance it names."));
  }
  const bound = (b: string) => ctx.evidence.some((e) => e.iri === b && e.property !== undefined);
  // A binding may state more than one carrier, and the shapes read each.
  const carriersOf = (b: string) => g.objects(b, SRF("bindsCarrier")).map((t) => t.value);
  const done = new Set<string>();
  for (const link of ctx.bindings.filter((b) => g.objects(b.iri, SRF("joinedAs")).length > 0)) {
    if (!(link.role === "result" && ctx.kinds.has("join"))) out.push(mark(14, "placement", "node", "A role binding states a join statement and is not the result-target role binding of a join."));
    for (const node of g.objects(link.iri, SRF("joinedAs"))) {
      const asJoin = node.termType === "NamedNode" && g.types(node).includes(SRF("JoinStatement"));
      if (!asJoin) out.push(mark(14, "typed", "node", "A role binding states as its join statement a term that is not a srf:JoinStatement named by an IRI."));
      if (node.termType === "Literal" || done.has(`${node.termType}:${node.value}`)) continue;
      done.add(`${node.termType}:${node.value}`);
      const pairs = g.objects(node, SRF("joinsOn"));
      if (g.types(node).includes(SRF("JoinStatement"))) {
        const matches = g.objects(node, SRF("joinMatches"));
        const links = g.objects(node, SRF("joinLinks"));
        if (pairs.length === 0) out.push(mark(15, "pairs", "pairs", "A join statement states at least one pair of bindings that must be equal."));
        if (matches.length > 1 || matches.some((t) => !cardinalityOf(t))) out.push(mark(15, "matches", "matches", "A join statement states at most one match count, srf:AtMostOne or srf:AnyNumber."));
        if (links.length > 1 || links.some((t) => !cardinalityOf(t))) out.push(mark(15, "links", "links", "A join statement states at most one link count, srf:AtMostOne or srf:AnyNumber."));
        if (ctx.carriers.length > 0) {
          for (const p of pairs) {
            for (const l of g.objects(p, SRF("joinLeft"))) {
              if (!bound(l.value) || ctx.carriers.some((own) => carriersOf(l.value).some((other) => other !== own))) out.push(mark(16, "left-binding", `pair:${p.value}`, "The left binding of a join pair is not a candidate-evidence or required-evidence role binding of the stating contract that binds a property, or it names a carrier other than the contract's own."));
            }
            for (const r of g.objects(p, SRF("joinRight"))) {
              const others = carriersOf(r.value);
              if (!bound(r.value) || others.length === 0 || ctx.carriers.some((own) => others.some((other) => other === own))) out.push(mark(16, "right-binding", `pair:${p.value}`, "The right binding of a join pair is not a candidate-evidence or required-evidence role binding of the stating contract that binds a property, or it names no carrier other than the contract's own."));
            }
          }
        }
        const carriers = new Set(pairs.flatMap((p) => g.objects(p, SRF("joinRight"))).flatMap((r) => carriersOf(r.value)));
        if (carriers.size > 1) out.push(mark(16, "second-carrier", "carrier", "The right bindings of a join statement name more than one second carrier."));
        const roles = new Set(pairs.flatMap((p) => [...g.objects(p, SRF("joinLeft")), ...g.objects(p, SRF("joinRight"))]).flatMap((b) => (roleOf(g, b.value) ? [roleOf(g, b.value)!] : [])));
        if (roles.size > 1) out.push(mark(17, "evidence-kind", "kind", "The bindings of a join statement are not all candidate evidence or all required evidence, so the join is on a mix."));
      }
      // A pair is read wherever a statement names it, typed or not.
      for (const p of pairs) {
        if (g.objects(p, SRF("joinLeft")).length !== 1 || g.objects(p, SRF("joinLeft")).some((t) => t.termType !== "NamedNode")) out.push(mark(15, "left", `pair:${p.value}`, "A join pair names exactly one left role binding."));
        if (g.objects(p, SRF("joinRight")).length !== 1 || g.objects(p, SRF("joinRight")).some((t) => t.termType !== "NamedNode")) out.push(mark(15, "right", `pair:${p.value}`, "A join pair names exactly one right role binding."));
        for (const l of g.objects(p, SRF("joinLeft"))) {
          for (const r of g.objects(p, SRF("joinRight"))) {
            if (g.objects(l, SRF("bindsDatatype")).length > 0 && g.objects(r, SRF("bindsDatatype")).length === 0) {
              out.push(mark(17, "datatype", `pair:${p.value}`, "The left binding of a join pair states a datatype and the right binding states none to cast it to."));
            }
          }
        }
      }
    }
  }
  return out;
}
