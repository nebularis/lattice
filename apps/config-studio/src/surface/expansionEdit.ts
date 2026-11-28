// SPDX-License-Identifier: MPL-2.0
// The expansion editor's pure part (SVA-S1 part 4, SVA-Q57 (b)): an expansion projection's statement of the members it restates, as the Surface README's section 6.18
// gives it. The statement names the evidence binding it expands from and states its members as a named source or a SHACL members path, never both (srf:P20). The path
// itself is built in path mode (part 2), and a named source is replaced by the path it stands for with part 3's action. The laws the editor keeps while it edits are
// srf:P19 (the evidence is the contract's own, binds a property and names no other carrier), srf:P20 (a path reads that property) and srf:P21 (the members never read the
// property the result-target binding writes). The marks are the shapes' rules for srf:P18 to srf:P21.

import { Graph, RDF, SH, SRF, TYPE, iri, type Term } from "@lattice/authoring-domain";
import { fresh, mark, type Evidence, type LawMark, type StatementContext } from "./statement";

export type Source = "ListMembers" | "TransitiveClosure";
export const SOURCES: Record<Source, string> = { ListMembers: SRF("ListMembers"), TransitiveClosure: SRF("TransitiveClosure") };
export const SOURCE_WORDS: Record<Source, string> = { ListMembers: "the members of an RDF list", TransitiveClosure: "everything it reaches by one or more steps" };
const sourceOf = (value: string | undefined): Source | undefined => (Object.keys(SOURCES) as Source[]).find((k) => SOURCES[k] === value);

export interface Expansion {
  node: string;
  named: boolean;
  typedAsExpansion: boolean;
  /** What the statement states, each as many times as it does, for the marks. */
  from: Term[];
  sources: Term[];
  paths: Term[];
  source?: Source;
  /** Whether a construction stands on the same binding, a node for each member. */
  hasNode: boolean;
}

export function readExpansion(g: Graph, ctx: StatementContext): Expansion | undefined {
  if (!ctx.result) return undefined;
  const stated = g.object(ctx.result, SRF("expandedAs"));
  if (!stated) return undefined;
  const sources = g.objects(stated, SRF("expansionSource"));
  return {
    node: stated.value, named: stated.termType === "NamedNode", typedAsExpansion: stated.termType === "NamedNode" && g.types(stated).includes(SRF("ExpansionStatement")),
    from: g.objects(stated, SRF("expandsFrom")), sources, paths: g.objects(stated, SRF("membersPath")),
    source: sources.length === 1 ? sourceOf(sources[0].value) : undefined, hasNode: g.objects(ctx.result, SRF("constructedAs")).length > 0,
  };
}

function editable(g: Graph, ctx: StatementContext): Expansion | undefined {
  const x = readExpansion(g, ctx);
  return x?.named ? x : undefined;
}

// --- reading a members path as the shapes read it -----------------------------------------------------------------------------------------

const STEP = [SH("inversePath"), SH("zeroOrMorePath"), SH("oneOrMorePath")];

/** The items of the list headed by `head`, read as the shapes read it, `rdf:rest` zero or more times and then `rdf:first`. A malformed list gives the items it has. */
function itemsOf(g: Graph, head: Term): Term[] {
  const out: Term[] = [];
  const seen = new Set<string>();
  let node: Term | undefined = head;
  while (node && node.termType === "BlankNode" && !seen.has(node.id)) {
    seen.add(node.id);
    const first = g.object(node, RDF("first"));
    if (first) out.push(first);
    node = g.object(node, RDF("rest"));
  }
  return out;
}

/** The nodes a members path reaches by the path of the shapes, `(inversePath | zeroOrMorePath | oneOrMorePath | alternativePath/rest*\/first | rest*\/first)*`, the root included. */
export function pathNodes(g: Graph, root: Term): Term[] {
  const seen = new Map<string, Term>();
  const walk = (n: Term) => {
    const key = `${n.termType}:${n.value}`;
    if (seen.has(key)) return;
    seen.set(key, n);
    for (const p of STEP) for (const o of g.objects(n, p)) walk(o);
    for (const a of g.objects(n, SH("alternativePath"))) for (const o of itemsOf(g, a)) walk(o);
    for (const o of itemsOf(g, n)) walk(o);
  };
  walk(root);
  return [...seen.values()];
}

/** The properties a members path reads, the named nodes it reaches. */
export const propertiesRead = (g: Graph, root: Term): string[] => pathNodes(g, root).filter((n) => n.termType === "NamedNode").map((n) => n.value);

/** Whether a node of a members path is in a form the shapes refuse, as `srf:ExpansionPathShape` states it. */
function badForm(g: Graph, n: Term): boolean {
  if (n.termType === "Literal") return true;
  if (n.termType !== "BlankNode") return false;
  const has = (p: string) => g.objects(n, p).length > 0;
  const forms = [SH("inversePath"), SH("zeroOrMorePath"), SH("oneOrMorePath"), SH("alternativePath"), RDF("first")].filter(has).length;
  const alternatives = g.objects(n, SH("alternativePath")).some((a) => itemsOf(g, a).length < 2);
  const sequence = has(RDF("first")) && !(g.objects(n, RDF("rest")).some((r) => g.objects(r, RDF("first")).length > 0));
  return has(SH("zeroOrOnePath")) || forms !== 1 || alternatives || sequence;
}

// --- what each part may be -----------------------------------------------------------------------------------------------------------------

export interface ExpansionChoices {
  /**
   * The bindings the statement may expand from (srf:P19): evidence of the contract that binds a property and names no other carrier, that is not the property the
   * result-target binding writes (srf:P21), and, where a members path is stated, one the path reads (srf:P20). A path is changed to another property by a named source.
   */
  from: Evidence[];
}

export function expansionChoices(g: Graph, ctx: StatementContext): ExpansionChoices {
  const x = readExpansion(g, ctx);
  const path = x?.paths.length === 1 ? x.paths[0] : undefined;
  const read = path ? new Set(propertiesRead(g, path)) : undefined;
  return {
    from: ctx.evidence.filter((e) => e.property !== undefined && (e.carrier === undefined || e.carrier === ctx.carrier) && e.property !== ctx.resultProperty && (read === undefined || read.has(e.property!))),
  };
}

// --- the edits -------------------------------------------------------------------------------------------------------------------------------

/**
 * States an expansion on the result-target binding of an expansion projection, which states none yet. The node is minted, and expands from the contract's one evidence
 * binding where it has one to choose. Its members are left for the author, a named source or a path.
 */
export function addExpansion(g: Graph, ctx: StatementContext): Graph {
  if (ctx.kind !== "expansion" || !ctx.result || g.object(ctx.result, SRF("expandedAs"))) return g;
  const node = fresh(g, ctx, "expansion");
  const only = expansionChoices(g, ctx).from;
  return g.edit((e) => {
    e.add(node, TYPE, iri(SRF("ExpansionStatement")));
    if (only.length === 1) e.add(node, SRF("expandsFrom"), iri(only[0].iri));
    e.add(ctx.result!, SRF("expandedAs"), iri(node));
  });
}

/** Removes the statement and its members path. It is not offered while a node for each member is stated beside it, which no other kind of statement may be (srf:P22). */
export function removeExpansion(g: Graph, ctx: StatementContext): Graph {
  const x = editable(g, ctx);
  if (!x || x.hasNode) return g;
  return g.edit((e) => {
    e.setAll(x.node, SRF("membersPath"), []);
    e.setAll(ctx.result!, SRF("expandedAs"), []);
    e.remove(x.node);
  });
}

/** Sets the evidence binding the members are reached by, one the choices offer (srf:P19, srf:P20, srf:P21). */
export function setExpandsFrom(g: Graph, ctx: StatementContext, binding: string): Graph {
  const x = editable(g, ctx);
  if (!x || !expansionChoices(g, ctx).from.some((e) => e.iri === binding)) return g;
  if (x.from.length === 1 && x.from[0].value === binding) return g;
  return g.edit((e) => e.setAll(x.node, SRF("expandsFrom"), [iri(binding)]));
}

/** States a named source and no members path, which the statement states one of and never both (srf:P20). */
export function useNamedSource(g: Graph, ctx: StatementContext, source: Source): Graph {
  const x = editable(g, ctx);
  if (!x) return g;
  const from = x.from.length === 1 ? ctx.evidence.find((e) => e.iri === x.from[0].value) : undefined;
  if (from?.property !== undefined && from.property === ctx.resultProperty) return g;
  if (x.sources.length === 1 && x.sources[0].value === SOURCES[source] && x.paths.length === 0) return g;
  return g.edit((e) => {
    e.setAll(x.node, SRF("membersPath"), []);
    e.setAll(x.node, SRF("expansionSource"), [iri(SOURCES[source])]);
  });
}

// --- the marks -----------------------------------------------------------------------------------------------------------------------------

/**
 * The breaches of the laws an expansion is held to, as the shapes of the Surface README state them. srf:P18 is where the statement stands, srf:P19 the evidence it
 * expands from, srf:P20 how its members are stated and srf:P21 that the members never read the property the statement's own binding writes. Each binding of the
 * contract that states an expansion is read, as the shapes read it, and what a statement holds is read where it is typed as an expansion statement.
 */
export function expansionMarks(g: Graph, ctx: StatementContext): LawMark[] {
  const out: LawMark[] = [];
  const results = ctx.bindings.filter((b) => b.role === "result");
  if (ctx.kinds.has("expansion")) {
    if (!results.some((b) => g.objects(b.iri, SRF("expandedAs")).length > 0)) out.push(mark(18, "required", "node", "An expansion projection states no expansion statement on its result-target role binding."));
    if (results.some((b) => b.property === undefined)) out.push(mark(18, "link-property", "link", "The result-target role binding of an expansion binds no property, so there is no property to write each member as."));
  }
  const evidence = (b: string) => ctx.evidence.find((e) => e.iri === b);
  for (const link of ctx.bindings.filter((b) => g.objects(b.iri, SRF("expandedAs")).length > 0)) {
    if (!(link.role === "result" && ctx.kinds.has("expansion"))) out.push(mark(18, "placement", "node", "A role binding states an expansion statement and is not the result-target role binding of an expansion."));
    for (const node of g.objects(link.iri, SRF("expandedAs"))) {
      const asStatement = node.termType === "NamedNode" && g.types(node).includes(SRF("ExpansionStatement"));
      if (!asStatement) out.push(mark(18, "typed", "node", "A role binding states as its expansion statement a term that is not a srf:ExpansionStatement named by an IRI."));
      if (!g.types(node).includes(SRF("ExpansionStatement"))) continue;
      const from = g.objects(node, SRF("expandsFrom"));
      const sources = g.objects(node, SRF("expansionSource"));
      const paths = g.objects(node, SRF("membersPath"));
      if (from.length !== 1 || from.some((t) => t.termType !== "NamedNode")) out.push(mark(19, "from", "from", "An expansion statement names exactly one binding to expand from."));
      if (sources.length > 1 || sources.some((t) => !sourceOf(t.value))) out.push(mark(20, "source", "source", "An expansion statement states at most one named source, srf:ListMembers or srf:TransitiveClosure."));
      if (paths.length > 1) out.push(mark(20, "path", "path", "An expansion statement states at most one members path."));
      if ((sources.length === 0 && paths.length === 0) || (sources.length > 0 && paths.length > 0)) out.push(mark(20, "members", "source", "An expansion statement states neither a named source nor a members path, or states both. It states exactly one of them."));
      if (ctx.carriers.length > 0) {
        for (const f of from) {
          const b = evidence(f.value);
          if (!b || b.property === undefined || ctx.carriers.some((own) => g.objects(f, SRF("bindsCarrier")).some((other) => other.value !== own))) {
            out.push(mark(19, "evidence", "from", "The binding an expansion statement expands from is not a candidate-evidence or required-evidence role binding of the stating contract that binds a property, or it names a carrier other than the contract's own."));
          }
        }
      }
      const fromProperties = from.flatMap((f) => g.objects(f, SRF("bindsProperty")).map((t) => t.value));
      const written = link.property;
      for (const root of paths) {
        const read = propertiesRead(g, root);
        if (pathNodes(g, root).some((n) => badForm(g, n))) out.push(mark(20, "path-form", "path", "A members path is not a SHACL property path of the forms an expansion states, a property, a sequence or an alternative of at least two paths, an inverse, zero or more or one or more."));
        for (const property of fromProperties) {
          if (!read.includes(property)) out.push(mark(20, "path-reads", "path", "A members path does not read the property of the binding the expansion statement expands from."));
        }
        if (written !== undefined && read.includes(written)) out.push(mark(21, "path-writes", "path", "An expansion statement's members read the property the result-target role binding that states it binds, so the expansion would feed on its own output."));
      }
      if (sources.length > 0 && written !== undefined && fromProperties.includes(written)) {
        out.push(mark(21, "path-writes", "source", "An expansion statement's members read the property the result-target role binding that states it binds, so the expansion would feed on its own output."));
      }
    }
  }
  return out;
}
