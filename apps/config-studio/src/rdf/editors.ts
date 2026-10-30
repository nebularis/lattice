// SPDX-License-Identifier: MPL-2.0
// The node kinds a configuration holds, and how each kind's editor groups its fields. Fields come
// from the vocabulary (vocabulary.ts). A kind lists sections only where the vocabulary's grouping
// by rdfs:domain is not the one an author wants, as for the dimensions of a dal:DataAccessProfile.
// Any other dal: or srf: node gets one section of its type's own properties.

import { BHV, COMMENT, CST, DAL, ELG, FND, Graph, INS, LABEL, MORK, PREFIXES, QNT, SKOS, SRF, TYPE, VOC, WRD, XSD, compact, humanise, iri, literal, localName, sentence, type NamedNode, type Term, typed } from "@lattice/authoring-domain";
import type { Baseline } from "./baseline";
import type { Issue } from "./report";
import type { Field, Vocabulary } from "./vocabulary";

export type { ConfigPart as Part } from "./split";
import type { ConfigPart as Part } from "./split";

/** A section the vocabulary cannot derive, drawn by its own component. */
export type Special = "path" | "concepts" | "temporal" | "resolution" | "expansion" | "tests" | "ranges" | "line" | "profileTests";

export interface Section {
  title: string;
  /** Every property whose domain is one of these classes, by label. */
  classes?: string[];
  /** These properties first, in this order. */
  fields?: string[];
  special?: Special;
}

export interface Kind {
  type: string;
  part: Part;
  title: string;
  plural: string;
  /** Offered in the Add menu, in this order. */
  creatable: boolean;
  sections?: Section[];
  /** Left out of the part's list, since another node's editor manages it. */
  unlisted?: boolean;
}

const DIMENSIONS = [
  "AggregateBoundaryProfile",
  "ConcurrencyProfile",
  "OrderingProfile",
  "ReceiptProfile",
  "MetaTopologyProfile",
  "EpochProfile",
  "WriteDisciplineProfile",
  "PrivacyProfile",
].map(DAL);

const APPLIES_TO: Section = { title: "Applies to", fields: [DAL("appliesTo")] };

const CONTRACT: Section = {
  title: "Contract",
  fields: ["contractKey", "carrier", "targetNamespace", "surfaceProfile", "realisationMode", "populationBudget"].map(SRF),
};

export const KINDS: Kind[] = [
  // The contract builder's views draw these (ADR-A138). A form's elements are listed by their kinds, derived from the vocabulary.
  { type: CST("Assembly"), part: "assembly", title: "Assembly", plural: "Assemblies", creatable: false },
  {
    type: DAL("DataAccessProfile"),
    part: "persistence",
    title: "Data access profile",
    plural: "Data access profiles",
    creatable: true,
    sections: [
      APPLIES_TO,
      { title: "Aggregate boundary", classes: [DAL("AggregateBoundaryProfile")], fields: [DAL("strategy"), DAL("boundaryShape")] },
      { title: "Concurrency", classes: [DAL("ConcurrencyProfile")], fields: [DAL("concurrencyProfile"), DAL("minConcurrencyLevel")] },
      { title: "Ordering", classes: [DAL("OrderingProfile")], fields: [DAL("orderingGrain")] },
      { title: "Receipts", classes: [DAL("ReceiptProfile")], fields: [DAL("receiptModel")] },
      { title: "Meta topology", classes: [DAL("MetaTopologyProfile")], fields: [DAL("metaTopology"), DAL("metaShards")] },
      { title: "Epoch", classes: [DAL("EpochProfile")] },
      { title: "Write discipline", classes: [DAL("WriteDisciplineProfile")] },
      { title: "Privacy", classes: [DAL("PrivacyProfile")] },
    ],
  },
  { type: DAL("ClassScope"), part: "persistence", title: "Class scope", plural: "Class scopes", creatable: true },
  {
    type: DAL("GraphPatternScope"),
    part: "persistence",
    title: "Graph pattern scope",
    plural: "Graph pattern scopes",
    creatable: true,
    sections: [{ title: "Scope", classes: [DAL("GraphPatternScope")], fields: [DAL("graphPrefix"), DAL("coversClass")] }],
  },
  { type: DAL("NamespaceScope"), part: "persistence", title: "Namespace scope", plural: "Namespace scopes", creatable: true },
  {
    type: DAL("UniquenessConstraint"),
    part: "persistence",
    title: "Uniqueness constraint",
    plural: "Uniqueness constraints",
    creatable: true,
    sections: [
      APPLIES_TO,
      {
        title: "Key",
        classes: [DAL("UniquenessConstraint")],
        fields: [DAL("constraintId"), DAL("keyProperty"), DAL("scopeProperty"), DAL("normalizePipeline"), DAL("onViolation"), DAL("minEnforcementLevel")],
      },
    ],
  },
  {
    type: DAL("IdentityProfile"),
    part: "persistence",
    title: "Identity profile",
    plural: "Identity profiles",
    creatable: true,
    sections: [APPLIES_TO, { title: "Identity", classes: [DAL("IdentityProfile")], fields: [DAL("resourceRole"), DAL("identityStrategy")] }],
  },
  { type: DAL("ClaimScheme"), part: "persistence", title: "Claim scheme", plural: "Claim schemes", creatable: true },
  { type: DAL("DigestScheme"), part: "persistence", title: "Digest scheme", plural: "Digest schemes", creatable: true },
  {
    type: SRF("PromotionContract"),
    part: "surface",
    title: "Promotion contract",
    plural: "Promotion contracts",
    creatable: true,
    sections: [
      CONTRACT,
      { title: "Read path", special: "path" },
      { title: "Promotion", classes: [SRF("PromotionContract")], fields: [SRF("promotesTo"), SRF("sourceFidelity")] },
    ],
  },
  {
    type: SRF("IndexContract"),
    part: "surface",
    title: "Index contract",
    plural: "Index contracts",
    creatable: true,
    sections: [
      CONTRACT,
      { title: "Read path", special: "path" },
      {
        title: "Index",
        classes: [SRF("IndexContract")],
        fields: [SRF("valuePopulation"), SRF("indexForm"), SRF("namingPolicy"), SRF("closureBasis")],
      },
    ],
  },
  { type: SRF("SurfaceProfile"), part: "surface", title: "Surface profile", plural: "Surface profiles", creatable: true },
  { type: SRF("ContractBoundPopulation"), part: "surface", title: "Scheme-bound population", plural: "Scheme-bound populations", creatable: true },
  { type: SRF("EnumeratedPopulation"), part: "surface", title: "Enumerated population", plural: "Enumerated populations", creatable: true },
  { type: SRF("ClassExtentPopulation"), part: "surface", title: "Class extent population", plural: "Class extent populations", creatable: true },

  {
    type: VOC("ConceptScheme"),
    part: "vocabulary",
    title: "Concept scheme",
    plural: "Concept schemes",
    creatable: true,
    sections: [
      { title: "Scheme", fields: [SKOS("prefLabel"), FND("hasGovernanceState"), FND("hasIdentity")] },
      { title: "Concepts", special: "concepts" },
    ],
  },
  {
    type: VOC("SchemeContract"),
    part: "vocabulary",
    title: "Scheme contract",
    plural: "Scheme contracts",
    creatable: true,
    sections: [
      { title: "Contract", classes: [VOC("SchemeContract")], fields: [VOC("constrainsProperty"), VOC("boundScheme"), VOC("requiresGovernanceState"), FND("hasGovernanceState"), FND("hasIdentity")] },
      { title: "How it resolves", special: "resolution" },
    ],
  },
  {
    type: VOC("SchemeBinding"),
    part: "vocabulary",
    title: "Scheme binding",
    plural: "Scheme bindings",
    creatable: true,
    sections: [
      { title: "Binding", classes: [VOC("SchemeBinding")], fields: [VOC("forContract"), VOC("bindsScheme"), VOC("bindingScope")] },
      { title: "Valid", special: "temporal" },
    ],
  },
  { type: VOC("BindingScope"), part: "vocabulary", title: "Binding scope", plural: "Binding scopes", creatable: true, sections: [{ title: "Scope", fields: [SKOS("prefLabel")] }] },
  {
    type: SKOS("Concept"),
    part: "vocabulary",
    title: "Concept",
    plural: "Concepts",
    creatable: false,
    unlisted: true,
    sections: [{ title: "Concept", fields: [SKOS("prefLabel"), SKOS("inScheme"), SKOS("broader"), SKOS("definition"), SKOS("notation")] }],
  },

  { type: QNT("ValueSpace"), part: "quantification", title: "Value space", plural: "Value spaces", creatable: true, sections: [{ title: "Space", classes: [QNT("ValueSpace")], fields: [QNT("spaceKey"), QNT("orderKind"), QNT("densityKind"), QNT("unitContract")] }] },
  { type: QNT("DerivedValueSpace"), part: "quantification", title: "Derived value space", plural: "Derived value spaces", creatable: true },
  { type: QNT("UnitContract"), part: "quantification", title: "Unit contract", plural: "Unit contracts", creatable: true },
  { type: QNT("UnitFamily"), part: "quantification", title: "Unit family", plural: "Unit families", creatable: true },
  { type: QNT("Unit"), part: "quantification", title: "Unit", plural: "Units", creatable: true },
  { type: QNT("RangeSet"), part: "quantification", title: "Range set", plural: "Range sets", creatable: true, sections: [{ title: "Range set", fields: [QNT("onSpace")] }, { title: "Ranges", special: "ranges" }] },
  { type: QNT("Range"), part: "quantification", title: "Range", plural: "Ranges", creatable: false, sections: [{ title: "Range", classes: [QNT("Range")], fields: [QNT("onSpace"), QNT("lowerBound"), QNT("upperBound"), QNT("hasBound")] }, { title: "On the number line", special: "line" }] },
  { type: QNT("Bound"), part: "quantification", title: "Bound", plural: "Bounds", creatable: false, sections: [{ title: "Bound", classes: [QNT("Bound")], fields: [QNT("onSpace"), QNT("boundValue"), QNT("boundSense"), QNT("boundClosure")] }] },
  { type: QNT("Quantity"), part: "quantification", title: "Quantity", plural: "Quantities", creatable: true, sections: [{ title: "Quantity", classes: [QNT("Quantity")], fields: [QNT("onSpace"), QNT("numericValue"), QNT("inUnit")] }] },
  { type: QNT("Conversion"), part: "quantification", title: "Conversion", plural: "Conversions", creatable: true },
  { type: QNT("OperationCapability"), part: "quantification", title: "Operation capability", plural: "Operation capabilities", creatable: true },

  {
    type: ELG("Condition"),
    part: "eligibility",
    title: "Concept condition",
    plural: "Conditions",
    creatable: true,
    sections: [
      { title: "Condition", fields: [ELG("conditionKey"), ELG("matchStrategy"), ELG("wildcardSemantics"), ELG("constrainedByContract"), ELG("requiredConcept"), ELG("excludedConcept"), ELG("negated")] },
      { title: "Decision by concept", special: "expansion" },
      { title: "Tests", special: "tests" },
    ],
  },
  {
    type: ELG("IntervalCondition"),
    part: "eligibility",
    title: "Interval condition",
    plural: "Conditions",
    creatable: true,
    sections: [
      { title: "Condition", fields: [ELG("conditionKey"), ELG("matchStrategy"), ELG("wildcardSemantics"), ELG("requiredRangeSet"), ELG("negated")] },
      { title: "Required values", special: "ranges" },
      { title: "Tests", special: "tests" },
    ],
  },
  {
    type: ELG("AdmissionProfile"),
    part: "eligibility",
    title: "Admission profile",
    plural: "Admission profiles",
    creatable: true,
    sections: [{ title: "Profile", classes: [ELG("AdmissionProfile")], fields: [ELG("hasCondition"), ELG("compositionOperation")] }, { title: "Tests", special: "profileTests" }],
  },
  { type: ELG("EvidenceBinding"), part: "eligibility", title: "Evidence binding", plural: "Evidence bindings", creatable: true },
  {
    type: ELG("Question"),
    part: "eligibility",
    title: "Question",
    plural: "Questions",
    creatable: false,
    sections: [{ title: "Question", fields: [ELG("forCondition"), ELG("candidateConcept"), ELG("candidateRangeSet"), CST("expectedDecision")] }],
  },
];

/** Kinds the studio never lists: path steps belong to their contract's read path, and a template is a marker beside the node's own kind. */
const MANAGED = new Set([SRF("PathStep"), INS("Template")]);
const PATH_PROPERTIES = new Set([SRF("readProperty"), SRF("hasPathStep")]);
/** Bound meaning's properties, shown and never written: the builder writes stated meaning only, and binding is the instantiator's (ADR-A138 decision 2). */
const BOUND_PROPERTIES = new Set([INS("boundIn"), INS("boundFrom"), INS("impliedBy")]);
const BOUND_REASON = "Bound meaning. Instantiating an assembled wording writes it, never the builder, so it is shown here and not edited.";

const KIND_BY_TYPE = new Map(KINDS.map((k) => [k.type, k]));

const OWN_NAMESPACE: Record<Part, string> = { library: WRD(""), assembly: CST(""), meaning: INS(""), review: CST(""), mapping: MORK(""), persistence: DAL(""), surface: SRF(""), vocabulary: VOC(""), quantification: QNT(""), eligibility: ELG("") };

export function kindOf(graph: Graph, node: Term | string, part: Part): Kind | undefined {
  const types = graph.types(node);
  for (const t of types) {
    const kind = KIND_BY_TYPE.get(t);
    if (kind) return kind;
  }
  // A regime state is Behaviour's, and stated meaning holds it beside the regime that owns it.
  const own = types.find((t) => (t.startsWith(OWN_NAMESPACE[part]) || (part === "meaning" && t === BHV("State"))) && !MANAGED.has(t));
  return own ? { type: own, part, title: sentence(humanise(localName(own))), plural: sentence(humanise(localName(own))) + "s", creatable: false } : undefined;
}

export interface Item {
  iri: string;
  kind: Kind;
  name: string;
  detail: string;
}

/** Every node of the configuration an author edits, grouped by kind in KINDS order. */
export function items(graph: Graph, part: Part, baseline: Baseline, vocab: Vocabulary): Item[] {
  const out: Item[] = [];
  const seen = new Set<string>();
  for (const q of graph.quads(null, TYPE)) {
    if (q.subject.termType !== "NamedNode" || seen.has(q.subject.value)) continue;
    const kind = kindOf(graph, q.subject, part);
    // A node of another part's kind, such as the range set of a test's candidate, belongs to the
    // node that made it and is reached from there.
    if (!kind || kind.unlisted || kind.part !== part) continue;
    seen.add(q.subject.value);
    out.push({ iri: q.subject.value, kind, name: nameOf(graph, q.subject.value), detail: detailOf(graph, q.subject.value, kind, baseline, vocab) });
  }
  const order = (k: Kind) => {
    const i = KINDS.indexOf(KIND_BY_TYPE.get(k.type)!);
    return i < 0 ? KINDS.length : i;
  };
  return out.sort((a, b) => order(a.kind) - order(b.kind) || a.kind.type.localeCompare(b.kind.type) || a.name.localeCompare(b.name));
}

export function nameOf(graph: Graph, node: string): string {
  return (
    graph.value(node, LABEL) ??
    graph.value(node, SKOS("prefLabel")) ??
    graph.value(node, ELG("conditionKey")) ??
    graph.value(node, QNT("spaceKey")) ??
    graph.value(node, SRF("contractKey")) ??
    graph.value(node, DAL("constraintId")) ??
    graph.value(node, WRD("variableKey")) ??
    graph.value(node, WRD("objectId")) ??
    sentence(humanise(localName(node)))
  );
}

function detailOf(graph: Graph, node: string, kind: Kind, baseline: Baseline, vocab: Vocabulary): string {
  const label = (t?: string) => (t ? (baseline.classes.get(t)?.label ?? baseline.properties.get(t)?.label ?? vocab.label(t)) : "");
  const carrier = graph.value(node, SRF("carrier"));
  if (carrier) return `carrier ${label(carrier)}`;
  const target = graph.value(node, DAL("targetClass"));
  if (target) return `class ${label(target)}`;
  const scope = graph.value(node, DAL("appliesTo"));
  if (scope) return `applies to ${scopeLabel(graph, scope, baseline)}`;
  return kind.title;
}

export function scopeLabel(graph: Graph, scope: string, baseline: Baseline): string {
  const target = graph.value(scope, DAL("targetClass"));
  if (target) return baseline.classes.get(target)?.label ?? humanise(localName(target));
  return nameOf(graph, scope);
}

export interface ResolvedSection {
  title: string;
  special?: Special;
  fields: Field[];
}

/** The sections and fields of a node's editor. */
export function sectionsFor(kind: Kind, vocab: Vocabulary): ResolvedSection[] {
  const placed = new Set<string>();
  const resolve = (section: Section): ResolvedSection => {
    const ordered = [
      ...(section.fields ?? []).map((p) => [p, kind.type] as const),
      ...(section.classes ?? []).flatMap((c) => vocab.propertiesOf(c).map((p) => [p, c] as const)),
    ];
    const fields: Field[] = [];
    for (const [p, c] of ordered) {
      if (placed.has(p) || PATH_PROPERTIES.has(p)) continue;
      placed.add(p);
      const field = vocab.field(p, c);
      fields.push(BOUND_PROPERTIES.has(p) ? { ...field, readOnly: BOUND_REASON } : field);
    }
    return { title: section.title, special: section.special, fields };
  };
  if (kind.sections) return kind.sections.map(resolve);
  const sections = [];
  if (kind.part === "persistence" && vocab.ancestors(kind.type).some((c) => DIMENSIONS.includes(c) || c === DAL("IdentityProfile"))) {
    sections.push(resolve(APPLIES_TO));
  }
  sections.push(resolve({ title: "Properties", classes: [kind.type] }));
  return sections;
}

/** A fresh IRI in the baseline's namespace, from a name the author typed. */
export function mint(graph: Graph, namespace: string, name: string): string {
  const stem =
    name
      .replace(/[^\p{L}\p{N}]+(.)?/gu, (_, c?: string) => (c ? c.toUpperCase() : ""))
      .replace(/^\p{Ll}/u, (c) => c.toUpperCase()) || "Node";
  let candidate = namespace + stem;
  for (let i = 2; graph.has(candidate); i++) candidate = `${namespace}${stem}${i}`;
  return candidate;
}

export function keyOf(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[^\p{L}\p{N}]+/gu, "-")
    .replace(/^-|-$/g, "");
}

export interface Created {
  graph: Graph;
  iri: string;
}

/** Create a node of a kind. With a class, a scope or contract is made for it, the shortest way to a
 * working configuration. Defaults are never written: an unset dimension resolves as the
 * compiler's baseline default. */
export function create(graph: Graph, kind: Kind, name: string, namespace: string, forClass?: string): Created {
  const node = mint(graph, namespace, name);
  let next = graph.edit((e) => {
    e.add(node, TYPE, iri(kind.type));
    if (kind.type === DAL("ClassScope") && forClass) e.add(node, DAL("targetClass"), iri(forClass));
    if (kind.type === DAL("UniquenessConstraint")) e.add(node, DAL("constraintId"), literal(keyOf(name)));
    if (kind.part === "surface" && kind.type.endsWith("Contract")) {
      e.add(node, SRF("contractKey"), literal(keyOf(name)));
      if (forClass) e.add(node, SRF("carrier"), iri(forClass));
      e.add(node, SRF("targetNamespace"), typed(namespace.replace(/[#/]?$/, "/generated#"), XSD("anyURI")));
      const profile = graph.ofType(SRF("SurfaceProfile"))[0];
      if (profile) e.add(node, SRF("surfaceProfile"), profile);
    }
    if (kind.type === VOC("ConceptScheme") || kind.type === VOC("BindingScope")) e.add(node, SKOS("prefLabel"), literal(name, "en"));
    if (kind.type === VOC("ConceptScheme") || kind.type === VOC("SchemeContract")) e.add(node, FND("hasGovernanceState"), iri(FND("Active")));
    if (kind.type === QNT("ValueSpace")) e.add(node, QNT("spaceKey"), literal(keyOf(name)));
    if (kind.type === ELG("Condition") || kind.type === ELG("IntervalCondition")) {
      e.add(node, ELG("conditionKey"), literal(keyOf(name)));
      e.add(node, ELG("wildcardSemantics"), iri(ELG("NoWildcard")));
      if (kind.type === ELG("IntervalCondition")) e.add(node, ELG("matchStrategy"), iri(ELG("IntervalContainment")));
    }
  });
  if (forClass && kind.type !== DAL("ClassScope") && kind.part === "persistence") {
    const scope = classScopeFor(next, forClass, namespace);
    next = scope.graph.edit((e) => e.set(node, DAL("appliesTo"), iri(scope.iri)));
  }
  return { graph: next, iri: node };
}

/** The class scope that targets exactly this class, made when there is none. */
export function classScopeFor(graph: Graph, classIri: string, namespace: string): Created {
  const existing = graph.ofType(DAL("ClassScope")).find((s) => graph.value(s, DAL("targetClass")) === classIri);
  if (existing) return { graph, iri: existing.value };
  return create(graph, KIND_BY_TYPE.get(DAL("ClassScope"))!, `${localName(classIri)} class`, namespace, classIri);
}

/** References a SHACL run cannot see: a term a baseline picker names that the baseline does not
 * declare, and a reference to a node declared nowhere. Terms of a well-known or LATTICE namespace are
 * the vocabulary's, never the baseline's. An undeclared reference is a warning, and a persistent
 * identity is never one, since an identity is a name that nothing need describe, as in the
 * repository's own examples. */
export function checkReferences(graph: Graph, baseline: Baseline, vocab: Vocabulary, world: Graph = graph): Issue[] {
  const issues: Issue[] = [];
  const known = (t: string) => baseline.declares(t) || vocab.graph.has(t) || world.has(t) || Object.values(PREFIXES).some((base) => t.startsWith(base));
  for (const q of graph.quads()) {
    if (q.subject.termType !== "NamedNode" || q.object.termType !== "NamedNode") continue;
    const field = vocab.field(q.predicate.value);
    const members = field.kind === "propertyList" ? ((graph.list(q.object) ?? []).filter((t) => t.termType === "NamedNode") as NamedNode[]) : [q.object as NamedNode];
    for (const m of members) {
      if (known(m.value) || graph.has(m.value) || mintedBy(world, q.subject.value, q.predicate.value, m.value)) continue;
      const name = compact(m.value, { ...graph.prefixes });
      if (field.kind === "class" || field.kind === "property" || field.kind === "propertyList") {
        issues.push({ severity: "Warning", message: `${name} is not declared in the baseline.`, focus: q.subject.value, path: q.predicate.value, source: "studio" });
      } else if (field.kind === "reference" && field.range !== FND("PersistentIdentity")) {
        issues.push({ severity: "Warning", message: `Refers to ${name}, which is declared nowhere.`, focus: q.subject.value, path: q.predicate.value, source: "studio" });
      }
    }
  }
  return issues;
}

/** A promotion onto a property in its contract's own target namespace mints that property when it compiles, so the
 * baseline need not declare it. Outside that namespace the property is the consuming layer's, and must be. */
function mintedBy(graph: Graph, contract: string, predicate: string, value: string): boolean {
  const namespace = graph.value(contract, SRF("targetNamespace"));
  return predicate === SRF("promotesTo") && namespace !== undefined && value.startsWith(namespace);
}

export function describe(vocab: Vocabulary, type: string): string {
  return vocab.graph.value(type, COMMENT) ?? "";
}

/** The baseline class a persistence node is about: its scope's target class. */
export function classOf(graph: Graph, node: string): string | undefined {
  const direct = graph.value(node, DAL("targetClass"));
  if (direct) return direct;
  const scope = graph.value(node, DAL("appliesTo"));
  return scope ? graph.value(scope, DAL("targetClass")) : undefined;
}

/** Whether a finding is about a node: its focus is the node, one of the node's path steps, or, for a
 * compiler finding, the class the node configures. */
export function concerns(graph: Graph, node: string, issue: Issue): boolean {
  const focus = issue.focus;
  if (!focus) return false;
  if (focus === node) return true;
  if (graph.objects(node, SRF("hasPathStep")).some((s) => s.value === focus)) return true;
  return !graph.has(focus) && (graph.value(node, SRF("carrier")) === focus || classOf(graph, node) === focus);
}

/** The node a finding should open: its focus when the configuration declares it, otherwise the first
 * node it concerns. */
export function nodeFor(graph: Graph, issue: Issue): string | undefined {
  if (issue.focus && graph.has(issue.focus) && graph.types(issue.focus).length) return issue.focus;
  const owner = graph.subjects(SRF("hasPathStep"), issue.focus).find((s) => s.termType === "NamedNode");
  if (owner) return owner.value;
  return graph.ofType(DAL("DataAccessProfile")).concat(graph.quads(null, TYPE).map((q) => q.subject as NamedNode)).find((n) => concerns(graph, n.value, issue))?.value;
}
