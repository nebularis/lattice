// SPDX-License-Identifier: MPL-2.0
// The contract builder's model over the library and assembly configurations (ADR-A138): the outline
// of a form, what an assembly of it may choose and set, and the writes that record a choice or a
// setting. A form's elements are ordered by wrd:rankKey and then wrd:objectId (Wording README §5.4),
// a variation slot's variants by wrd:objectId, since they carry no rank. An assembly is a
// cst:Assembly of the assembly configuration, its choices cst:choice and its settings cst:setting,
// each a wrd:VariableValue (contracts/config-studio/README.md).

import { CST, ELG, FND, LABEL, SKOS, TYPE, VOC, WRD, XSD, iri, literal, localName, typed, type Graph, type Term } from "@lattice/authoring-domain";
import { keyOf, mint } from "./editors";

export type InclusionMode = "Mandatory" | "Variation" | "Optional" | "Conditional";

export interface Admission {
  iri: string;
  name: string;
  /** The governing variables its conditions read. */
  reads: string[];
}

export interface OutlineNode {
  iri: string;
  objectId?: string;
  rank?: string;
  /** The element's label where it has one. */
  label?: string;
  /** Its text, the parts in order, a variable shown by its key in braces. */
  text: string;
  mode: InclusionMode;
  /** A variation slot, whose children are its variants. */
  slot: boolean;
  /** A variant of a slot. */
  variant: boolean;
  condition?: Admission;
  children: OutlineNode[];
}

export interface VariableInfo {
  iri: string;
  identity?: string;
  key: string;
  governing: boolean;
  multiValued: boolean;
  /** The scheme contract of a concept-valued variable. */
  contract?: string;
  /** The value space of a quantity-valued variable. */
  space?: string;
}

export interface FormOutline {
  iri: string;
  label: string;
  elements: OutlineNode[];
  variables: VariableInfo[];
}

const isA = (graph: Graph, node: Term | string, type: string) => graph.types(node).includes(type);

const naturally = new Intl.Collator("en", { numeric: true });

function byRank(graph: Graph) {
  return (a: Term, b: Term) => {
    const ra = graph.value(a, WRD("rankKey"));
    const rb = graph.value(b, WRD("rankKey"));
    if (ra !== undefined && rb !== undefined && ra !== rb) return ra < rb ? -1 : 1;
    if ((ra === undefined) !== (rb === undefined)) return ra === undefined ? 1 : -1;
    return naturally.compare(graph.value(a, WRD("objectId")) ?? "", graph.value(b, WRD("objectId")) ?? "") || a.value.localeCompare(b.value);
  };
}

export function isVariable(graph: Graph, node: Term | string): boolean {
  const types = graph.types(node);
  return types.includes(WRD("GoverningVariable")) || types.includes(WRD("EmbeddedVariable")) || types.includes(WRD("Variable"));
}

/** The forms of the library: every wrd:Wording that is not an assembled wording. */
export function formsOf(graph: Graph): string[] {
  return graph
    .ofType(WRD("Wording"))
    .filter((w) => !isA(graph, w, WRD("AssembledWording")))
    .map((w) => w.value)
    .sort((a, b) => naturally.compare(nameOfForm(graph, a), nameOfForm(graph, b)) || a.localeCompare(b));
}

export function nameOfForm(graph: Graph, form: string): string {
  return graph.value(form, LABEL) ?? graph.value(form, SKOS("prefLabel")) ?? localName(form).replace(/[-_]+/g, " ");
}

/** The variable a text part shows: its wrd:refersToVariable names the variable's identity. */
function variableByIdentity(graph: Graph, identity: string): string | undefined {
  return graph.subjects(FND("hasIdentity"), identity).find((s) => isVariable(graph, s))?.value;
}

function textOf(graph: Graph, element: string): string {
  const parts = graph.objects(element, WRD("hasTextPart")).sort((a, b) => Number(graph.value(a, WRD("partIndex")) ?? 0) - Number(graph.value(b, WRD("partIndex")) ?? 0));
  return parts
    .map((p) => {
      const ref = graph.value(p, WRD("refersToVariable"));
      if (ref) {
        const v = variableByIdentity(graph, ref) ?? ref;
        return `{${graph.value(v, WRD("variableKey")) ?? localName(v)}}`;
      }
      return graph.value(p, WRD("partText")) ?? graph.value(p, WRD("displayText")) ?? "";
    })
    .join("");
}

export function admissionOf(graph: Graph, element: string): Admission | undefined {
  const profile = graph.value(element, WRD("includedWhen"));
  if (!profile) return undefined;
  const reads = graph
    .objects(profile, ELG("hasCondition"))
    .map((c) => graph.value(c, WRD("readsVariable")))
    .filter((v): v is string => v !== undefined);
  return { iri: profile, name: graph.value(profile, LABEL) ?? localName(profile).replace(/[-_]+/g, " "), reads: [...new Set(reads)] };
}

function modeOf(graph: Graph, element: string): InclusionMode {
  const mode = graph.value(element, WRD("inclusionMode"));
  const name = mode ? localName(mode) : "Mandatory";
  return (["Mandatory", "Variation", "Optional", "Conditional"] as const).find((m) => m === name) ?? "Mandatory";
}

function variableInfo(graph: Graph, node: string): VariableInfo {
  return {
    iri: node,
    identity: graph.value(node, FND("hasIdentity")),
    key: graph.value(node, WRD("variableKey")) ?? localName(node),
    governing: isA(graph, node, WRD("GoverningVariable")),
    multiValued: graph.value(node, WRD("multiValued")) === "true",
    contract: graph.value(node, WRD("valueContract")),
    space: graph.value(node, WRD("valueSpace")),
  };
}

/** The outline of one form. `graph` holds the library and, for a condition's readings, the eligibility
 * configuration beside it. */
export function outline(graph: Graph, form: string): FormOutline {
  const rank = byRank(graph);
  const variables = new Map<string, VariableInfo>();
  const seen = new Set<string>();

  const build = (node: Term, variant: boolean): OutlineNode | undefined => {
    const iriOf = node.value;
    if (isVariable(graph, node)) {
      variables.set(iriOf, variableInfo(graph, iriOf));
      return undefined;
    }
    if (seen.has(iriOf)) return undefined;
    seen.add(iriOf);
    const slot = isA(graph, node, WRD("VariationSlot"));
    const comprised = graph.objects(node, WRD("directlyComprises"));
    const variants = graph.objects(node, WRD("hasVariant"));
    // A variant is also a part, so a reasoner's derived directlyComprises edge is not read twice.
    const isVariant = new Set(variants.map((v) => v.value));
    const direct = comprised.filter((c) => !isVariant.has(c.value));
    const children = [...direct.sort(rank), ...variants.sort(rank)].map((c) => build(c, isVariant.has(c.value))).filter((c): c is OutlineNode => c !== undefined);
    const element: OutlineNode = {
      iri: iriOf,
      objectId: graph.value(node, WRD("objectId")),
      rank: graph.value(node, WRD("rankKey")),
      label: graph.value(node, LABEL),
      text: textOf(graph, iriOf),
      mode: modeOf(graph, iriOf),
      slot,
      variant,
      condition: admissionOf(graph, iriOf),
      children,
    };
    // Variables the text shows or a condition reads belong to the form even when its tree omits them.
    for (const p of graph.objects(node, WRD("hasTextPart"))) {
      const ref = graph.value(p, WRD("refersToVariable"));
      const v = ref && variableByIdentity(graph, ref);
      if (v && !variables.has(v)) variables.set(v, variableInfo(graph, v));
    }
    for (const v of element.condition?.reads ?? []) if (!variables.has(v)) variables.set(v, variableInfo(graph, v));
    return element;
  };

  const roots = graph.objects(form, WRD("directlyComprises")).sort(rank);
  const elements = roots.map((r) => build(r, false)).filter((e): e is OutlineNode => e !== undefined);
  return { iri: form, label: nameOfForm(graph, form), elements, variables: [...variables.values()].sort((a, b) => a.key.localeCompare(b.key)) };
}

/** Every element of an outline, in reading order. */
export function flatten(nodes: OutlineNode[]): OutlineNode[] {
  return nodes.flatMap((n) => [n, ...flatten(n.children)]);
}

export interface Choice {
  iri: string;
  objectId?: string;
  title: string;
  kind: "optional" | "variant";
  /** The slot a variant belongs to. */
  slot?: string;
}

/** What the drafter may choose: each Optional element and each variant without an inclusion condition. */
export function choicesOf(form: FormOutline): Choice[] {
  const out: Choice[] = [];
  const walk = (nodes: OutlineNode[], slot?: OutlineNode) => {
    for (const n of nodes) {
      const title = n.label ?? (n.text.length > 70 ? n.text.slice(0, 67) + "..." : n.text);
      if (n.variant && !n.condition) out.push({ iri: n.iri, objectId: n.objectId, title, kind: "variant", slot: slot?.iri });
      else if (!n.variant && n.mode === "Optional") out.push({ iri: n.iri, objectId: n.objectId, title, kind: "optional" });
      walk(n.children, n.slot ? n : undefined);
    }
  };
  walk(form.elements);
  return out;
}

/** The variables an assembly sets: each governing variable a condition of the form reads, and each embedded
 * variable the text shows. */
export function settableOf(graph: Graph, form: FormOutline): VariableInfo[] {
  const all = flatten(form.elements);
  const read = new Set(all.flatMap((e) => e.condition?.reads ?? []));
  const shown = new Set<string>();
  for (const e of all) {
    for (const p of graph.objects(e.iri, WRD("hasTextPart"))) {
      const ref = graph.value(p, WRD("refersToVariable"));
      const v = ref && variableByIdentity(graph, ref);
      if (v) shown.add(v);
    }
  }
  return form.variables.filter((v) => (v.governing ? read.has(v.iri) : shown.has(v.iri)));
}

/** Concepts a concept-valued variable may take: those of the scheme its contract binds. */
export function conceptsFor(graph: Graph, variable: VariableInfo): { iri: string; label: string }[] {
  if (!variable.contract) return [];
  const schemes = graph.objects(variable.contract, VOC("boundScheme")).map((s) => s.value);
  return graph
    .subjects(SKOS("inScheme"))
    .filter((c) => schemes.includes(graph.value(c, SKOS("inScheme")) ?? ""))
    .map((c) => ({ iri: c.value, label: graph.value(c, SKOS("prefLabel")) ?? graph.value(c, LABEL) ?? localName(c.value) }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

// ---- Assemblies ------------------------------------------------------------------

export interface Setting {
  record: string;
  /** Resources, for wrd:value. */
  values: string[];
  /** Literals, for wrd:literalValue. */
  literals: string[];
}

export function assembliesOf(graph: Graph): string[] {
  return graph.ofType(CST("Assembly")).map((a) => a.value).sort((a, b) => nameOfAssembly(graph, a).localeCompare(nameOfAssembly(graph, b)) || a.localeCompare(b));
}

export function nameOfAssembly(graph: Graph, assembly: string): string {
  return graph.value(assembly, LABEL) ?? localName(assembly).replace(/[-_]+/g, " ");
}

export function choicesMade(graph: Graph, assembly: string): Set<string> {
  return new Set(graph.objects(assembly, CST("choice")).map((c) => c.value));
}

/** The assembly's settings by the variable they are for. */
export function settingsMade(graph: Graph, assembly: string): Map<string, Setting> {
  const out = new Map<string, Setting>();
  for (const record of graph.objects(assembly, CST("setting"))) {
    const variable = graph.value(record, WRD("forVariable"));
    if (!variable) continue;
    out.set(variable, {
      record: record.value,
      values: graph.objects(record, WRD("value")).map((v) => v.value),
      literals: graph.objects(record, WRD("literalValue")).map((v) => v.value),
    });
  }
  return out;
}

/** A new assembly. The `namespace` is the workspace's own, as for any new subject, and `world` is every graph, so that no IRI is minted twice. */
export function addAssembly(graph: Graph, world: Graph, namespace: string, name: string, form?: string): { graph: Graph; iri: string } {
  const node = mint(world, namespace, name);
  return {
    iri: node,
    graph: graph.edit((e) => {
      e.add(node, TYPE, iri(CST("Assembly")));
      e.add(node, LABEL, literal(name));
      if (form) e.add(node, CST("assembles"), iri(form));
    }),
  };
}

/** The form an assembly draws from. Choices and settings were for another form, so they are dropped. */
export function setForm(graph: Graph, assembly: string, form: string | undefined): Graph {
  return graph.edit((e) => {
    for (const record of graph.objects(assembly, CST("setting"))) e.remove(record);
    e.setAll(assembly, CST("choice"), []);
    e.set(assembly, CST("assembles"), form ? iri(form) : undefined);
  });
}

export function removeAssembly(graph: Graph, assembly: string): Graph {
  return graph.edit((e) => {
    for (const record of graph.objects(assembly, CST("setting"))) e.remove(record);
    e.remove(assembly);
  });
}

export function setLabel(graph: Graph, assembly: string, label: string): Graph {
  return graph.edit((e) => e.set(assembly, LABEL, label ? literal(label) : undefined));
}

export function toggleChoice(graph: Graph, assembly: string, element: string, on: boolean): Graph {
  const current = graph.objects(assembly, CST("choice")).filter((c) => c.value !== element);
  return graph.edit((e) => e.setAll(assembly, CST("choice"), on ? [...current, iri(element)] : current));
}

/** The datatype a variable's literal values are written with: a quantity-valued variable's are decimals. Else a plain string. */
export function datatypeOf(variable: VariableInfo): string | undefined {
  return variable.space ? XSD("decimal") : undefined;
}

export type Entry = { resources: string[] } | { literals: string[] };

/** Record the assembly's value for a variable, as one `wrd:VariableValue` holding every value (Wording README §5.12).
 * No values removes the record. */
export function writeSetting(graph: Graph, world: Graph, namespace: string, assembly: string, variable: VariableInfo, entry: Entry): Graph {
  const existing = settingsMade(graph, assembly).get(variable.iri)?.record;
  const resources = "resources" in entry ? entry.resources.filter(Boolean) : [];
  const literals = "literals" in entry ? entry.literals.map((l) => l.trim()).filter(Boolean) : [];
  if (resources.length + literals.length === 0) {
    return existing ? graph.edit((e) => e.remove(existing)) : graph;
  }
  const record = existing ?? mint(world, namespace, `${localName(assembly)} ${keyOf(variable.key)}`);
  const datatype = datatypeOf(variable);
  return graph.edit((e) => {
    if (!existing) {
      e.add(record, TYPE, iri(WRD("VariableValue")));
      e.add(record, WRD("forVariable"), iri(variable.iri));
      e.add(assembly, CST("setting"), iri(record));
    }
    e.setAll(record, WRD("value"), resources.map((r) => iri(r)));
    e.setAll(record, WRD("literalValue"), literals.map((l) => (datatype ? typed(l, datatype) : literal(l))));
  });
}
