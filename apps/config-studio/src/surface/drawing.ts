// SPDX-License-Identifier: MPL-2.0
// What the surface canvas draws of a contract (SVA-Q59), as nodes and edges and nothing the browser draws them with. One grammar serves every kind,
// left to right, the carrier class first, then what is read from it, then what is written. It is drawn from the configuration as authored
// (SVA-Q58 (a)), so an edit shows at once, and it never computes what a contract lowers to. The targets a contract writes are shared nodes on the
// right that contracts writing the same term meet at, and each is read from the ontology the workspace holds (SVA-Q62). A finding is placed on
// the element that claims its focus node and path (findings.ts).

import { Graph, RDF, SRF, localName, type Term } from "@lattice/authoring-domain";
import { readPath, type Step } from "../rdf/path";
import { nameOf } from "../rdf/editors";
import { datatypeName, expressionLine, expressionNodes, readExpression } from "./expression";
import { membersPath, sourceHops, type Hop } from "./paths";
import { readTarget, type TargetInfo, type Terms } from "./terms";

export type ContractKind = "promotion" | "index" | "derivation" | "construction" | "join" | "expansion" | "member";

/** A statement the element makes about a node of the configuration, by the paths of that node it shows. A claim with no path is the element's general claim. */
export interface Claim {
  focus: string;
  paths?: string[];
}

export type NodeKind = "carrier" | "contract" | "class" | "evidence" | "statement" | "entries" | "target" | "scheme";

export interface DrawNode {
  id: string;
  kind: NodeKind;
  /** The small line above the title. */
  tag: string;
  title: string;
  /** Rows under the title. */
  lines: string[];
  rank: number;
  /** The contract the node belongs to. A target is shared by the contracts that write it and has none. */
  contract?: string;
  /** The node of the configuration a click opens in the form. */
  select?: string;
  /** For a target, the term and what the ontology says of it. */
  target?: TargetInfo;
  /** For a scheme box, the contract it is the lowered scheme of. */
  scheme?: string;
  /** Where path mode starts from this element, where it holds a path or a property (SVA-Q60). */
  place?: PathPlace;
  claims: Claim[];
}

/**
 * A place in the drawing that holds a path or a property, which path mode builds by clicking (SVA-Q60). A read path hangs off a promotion or an
 * index, a binding's property is one property, and a members path is the statement of an expansion.
 */
export interface PathPlace {
  kind: "read" | "binding" | "members";
  /** The promotion or index of a read path, the binding of a property and the expansion statement of a members path. */
  node: string;
  /** The contract the place is in, and the class the path starts from, which is the contract's carrier, or the second carrier of a binding that names one. */
  contract: string;
  carrier?: string;
  /** What the author sees it called. */
  label: string;
}

export type EdgeKind = "read" | "hop" | "write" | "key" | "lowered";

export interface DrawEdge {
  id: string;
  source: string;
  target: string;
  kind: EdgeKind;
  label?: string;
  title: string;
  /** Candidate evidence and the like are drawn dashed, required evidence solid. */
  dashed: boolean;
  /** An inverse hop is marked. */
  inverse?: boolean;
  closure?: "+" | "*" | "?";
  contract?: string;
  /** On the edge that writes a derivation's value, where its expression is edited (SVA-Q57 (b)). `binding` is the result-target binding that states, or would state, `srf:derivedAs`. */
  expression?: { contract: string; binding?: string };
  claims: Claim[];
}

interface TargetRef {
  kind: "property" | "class";
  iri: string;
  /** The datatype the contract states for it. */
  stated?: string;
  /** The node the shared target node is joined from, by a new edge. */
  from: string;
  edge: { label?: string; title: string; claims?: Claim[]; dashed?: boolean; expression?: { contract: string; binding?: string } };
  /** An edge already drawn to the end of the contract, which is pointed at the shared node in place of a new edge. */
  retarget?: string;
}

export interface ContractDrawing {
  contract: string;
  name: string;
  kind: ContractKind;
  nodes: DrawNode[];
  edges: DrawEdge[];
  targets: TargetRef[];
  /** The last rank before the targets. */
  depth: number;
  /** The target the lowered scheme sits beside, which is the term the contract writes first. */
  primary?: string;
  /** The classes the contract reads from, the carrier and where a join names one, its second carrier. */
  carriers: string[];
}

export const CONTRACT_TYPES = [SRF("PromotionContract"), SRF("IndexContract"), SRF("ProjectionContract")];

export interface ContractRow {
  iri: string;
  name: string;
  kind: "promotion" | "index" | "projection";
}

const ORDER = { promotion: 0, index: 1, projection: 2 };

/** The contracts of the surface part, promotions first, then indexes and projections, each group by name. */
export function contractsOf(g: Graph): ContractRow[] {
  const rows: ContractRow[] = [];
  for (const [type, kind] of [[SRF("PromotionContract"), "promotion"], [SRF("IndexContract"), "index"], [SRF("ProjectionContract"), "projection"]] as const) {
    for (const n of g.ofType(type)) rows.push({ iri: n.value, name: nameOf(g, n.value), kind });
  }
  return rows.sort((a, b) => ORDER[a.kind] - ORDER[b.kind] || a.name.localeCompare(b.name) || a.iri.localeCompare(b.iri));
}

/** The contract a node of the surface part belongs to, as the node it is or a node the contract holds, for a click in the list to draw its contract. */
export function contractOf(g: Graph, node: string, contracts: readonly ContractRow[]): string | undefined {
  if (contracts.some((c) => c.iri === node)) return node;
  for (const c of contracts) {
    const d = drawContract(g, c.iri, LABELS);
    // The edge that writes a derivation's value is made from its target, so the result binding and the expression nodes are claimed there.
    const claimed = (claims: readonly Claim[] | undefined) => claims?.some((k) => k.focus === node) === true;
    if (d.nodes.some((n) => claimed(n.claims)) || d.edges.some((e) => claimed(e.claims)) || d.targets.some((t) => claimed(t.edge.claims))) return c.iri;
  }
  return undefined;
}

const LABELS: Terms = {
  label: (iri) => localName(iri),
  range: () => undefined,
  domain: () => undefined,
  isClass: () => false,
  declared: () => false,
  rangesOf: () => [],
};

/** The classes a contract reads from, its carrier and the second carrier a binding names. */
function carriersOf(g: Graph, contract: string): string[] {
  const own = g.value(contract, SRF("carrier"));
  const others = sorted(g.objects(contract, SRF("hasRoleBinding"))).map((b) => g.value(b, SRF("bindsCarrier"))).filter((c): c is string => c !== undefined && c !== own);
  return [...(own ? [own] : []), ...new Set(others)];
}

const words = (iri: string) => localName(iri).replace(/([a-z0-9])([A-Z])/g, "$1 $2").toLowerCase();
const sorted = (terms: readonly Term[]) => terms.map((t) => t.value).sort();

export interface Binding {
  iri: string;
  role: "subject" | "required" | "candidate" | "dependency" | "closure" | "result" | "unknown";
  property?: string;
  carrier?: string;
  datatype?: string;
}

const ROLES: Record<string, Binding["role"]> = {
  EvaluationSubjectRole: "subject",
  RequiredEvidenceRole: "required",
  CandidateEvidenceRole: "candidate",
  TransformDependencyRole: "dependency",
  ClosureBasisRole: "closure",
  ResultTargetRole: "result",
};

export function bindingsOf(g: Graph, contract: string): Binding[] {
  return sorted(g.objects(contract, SRF("hasRoleBinding"))).map((iri) => ({
    iri,
    role: ROLES[localName(g.value(iri, SRF("roleKind")) ?? "")] ?? "unknown",
    property: g.value(iri, SRF("bindsProperty")),
    carrier: g.value(iri, SRF("bindsCarrier")),
    datatype: g.value(iri, SRF("bindsDatatype")),
  }));
}

const ROLE_WORDS: Record<Binding["role"], string> = {
  subject: "subject", required: "required evidence", candidate: "candidate evidence", dependency: "dependency", closure: "closure basis", result: "result", unknown: "binding without a role",
};

/** Cardinality rules as the sentence a reader says them in. */
const CARDINALITY: Record<string, string> = { AtMostOne: "at most one", AnyNumber: "any number" };

function projectionShape(g: Graph, contract: string, result?: Binding): ContractKind {
  const has = (p: string) => result !== undefined && g.value(result.iri, SRF(p)) !== undefined;
  if (has("expandedAs") && has("constructedAs")) return "member";
  if (has("expandedAs")) return "expansion";
  if (has("joinedAs")) return "join";
  if (has("constructedAs")) return "construction";
  if (has("derivedAs")) return "derivation";
  // A contract that states nothing yet is drawn as the kind it says it is.
  switch (localName(g.value(contract, SRF("projectionKind")) ?? "")) {
    case "JoinProjection":
      return "join";
    case "ExpansionProjection":
      return "expansion";
    case "GraphConstructionProjection":
      return "construction";
    default:
      return "derivation";
  }
}

/** The drawing of one contract, with its targets still to be joined to the shared nodes on the right. */
export function drawContract(g: Graph, contract: string, terms: Terms): ContractDrawing {
  const name = nameOf(g, contract);
  const type = g.types(contract);
  const draw = type.includes(SRF("PromotionContract")) ? promotion : type.includes(SRF("IndexContract")) ? index : projection;
  return draw(g, contract, name, terms);
}

// --- the shared parts ---------------------------------------------------------------------------------------------------------------

function carrierNode(g: Graph, contract: string, name: string, terms: Terms, tag: string, reads?: PathPlace["kind"]): DrawNode {
  const carrier = g.value(contract, SRF("carrier"));
  return {
    id: `${contract}|carrier`, kind: "carrier", tag, title: carrier ? terms.label(carrier) : "…", lines: [name], rank: 0, contract, select: contract,
    place: reads ? { kind: reads, node: contract, contract, carrier, label: "the read path" } : undefined,
    claims: [{ focus: contract }, ...(carrier ? [{ focus: carrier }] : [])],
  };
}

/** The class a hop reaches, by the ontology's range of a forward hop and domain of an inverse one. A datatype is the value the path ends in. */
function reached(step: { property: string; inverse: boolean }, terms: Terms): string {
  const end = step.inverse ? terms.domain(step.property) : terms.range(step.property);
  return end === undefined ? "value" : terms.label(end);
}

const hopLabel = (terms: Terms, h: { property: string; inverse?: boolean; closure?: string; alternatives?: string[] }) =>
  `${h.inverse ? "← " : ""}${[h.property, ...(h.alternatives ?? [])].map((p) => terms.label(p)).join(" | ")}${h.closure ? ` ${h.closure}` : ""}`;

const closureWords: Record<string, string> = { "+": "one or more times", "*": "zero or more times", "?": "zero or one time" };

function hopTitle(terms: Terms, from: string, h: Hop | Step, to: string): string {
  const closure = "closure" in h && h.closure ? `, ${closureWords[h.closure]}` : "";
  return h.inverse ? `${to} is read inversely through ${terms.label(h.property)} from ${from}${closure}` : `${terms.label(h.property)} from ${from} to ${to}${closure}`;
}

/** The claims of a read path. A single property is the contract's own statement, and each hop of the steps is the node that states it. */
function stepClaims(g: Graph, contract: string, index: number): Claim[] {
  const steps = g.objects(contract, SRF("hasPathStep")).sort((a, b) => Number(g.value(a, SRF("stepIndex")) ?? 0) - Number(g.value(b, SRF("stepIndex")) ?? 0));
  const claim = [{ focus: contract, paths: [SRF("readProperty"), SRF("hasPathStep")] }];
  return steps[index] ? [{ focus: steps[index].value, paths: [SRF("stepIndex"), SRF("stepProperty"), SRF("stepDirection")] }, ...claim] : claim;
}

/** The read path as hops from the carrier through a class for each. The last hop ends at `end`, the node the contract writes. */
function readHopsOf(g: Graph, contract: string, terms: Terms, steps: Step[], end: { id: string; carrierLabel: string; endLabel: string }, hopNodes: DrawNode[], edges: DrawEdge[]): void {
  let from = `${contract}|carrier`;
  let fromLabel = end.carrierLabel;
  steps.forEach((step, i) => {
    const last = i === steps.length - 1;
    const toLabel = last ? end.endLabel : reached(step, terms);
    const to = last ? end.id : `${contract}|hop|${i}`;
    if (!last) {
      hopNodes.push({ id: to, kind: "class", tag: "Reached", title: toLabel, lines: [], rank: i + 1, contract, select: contract, claims: [] });
    }
    edges.push({
      id: `${contract}|e|hop|${i}`, source: from, target: to, kind: "hop", label: hopLabel(terms, step), title: hopTitle(terms, fromLabel, step, toLabel),
      dashed: false, inverse: step.inverse, contract, claims: stepClaims(g, contract, i),
    });
    from = to;
    fromLabel = toLabel;
  });
}

// --- a promotion and an index --------------------------------------------------------------------------------------------------------

function promotion(g: Graph, contract: string, name: string, terms: Terms): ContractDrawing {
  const steps = readPath(g, contract);
  const to = g.value(contract, SRF("promotesTo"));
  const carrier = carrierNode(g, contract, name, terms, "Promotion", "read");
  const nodes: DrawNode[] = [carrier];
  const edges: DrawEdge[] = [];
  const end = `${contract}|promoted`;
  if (steps.length === 0) {
    // No read path yet, so the carrier is drawn with the one dashed edge to what it restates.
    edges.push({ id: `${contract}|e|hop|0`, source: carrier.id, target: end, kind: "hop", label: "no read path", title: `${name} states no read path yet`, dashed: true, contract, claims: [{ focus: contract, paths: [SRF("readProperty"), SRF("hasPathStep")] }] });
  } else {
    readHopsOf(g, contract, terms, steps, { id: end, carrierLabel: carrier.title, endLabel: to ? terms.label(to) : "…" }, nodes, edges);
  }
  // The last edge carries what is promoted, so a finding on promotesTo is drawn there, and the shared target node ends it.
  const last = edges[edges.length - 1];
  last.claims = [...last.claims, { focus: contract, paths: [SRF("promotesTo")] }];
  return { contract, name, kind: "promotion", nodes, edges, targets: [{ kind: "property", iri: to ?? "", from: carrier.id, edge: { title: "" }, retarget: last.id }], depth: Math.max(0, steps.length - 1), primary: to, carriers: carriersOf(g, contract) };
}

function index(g: Graph, contract: string, name: string, terms: Terms): ContractDrawing {
  const steps = readPath(g, contract);
  const carrier = carrierNode(g, contract, name, terms, "Index", "read");
  const nodes: DrawNode[] = [carrier];
  const edges: DrawEdge[] = [];
  const population = g.value(contract, SRF("valuePopulation"));
  const forms = sorted(g.objects(contract, SRF("indexForm"))).map(words);
  const basis = g.value(contract, SRF("closureBasis"));
  const populationLine = (() => {
    if (!population) return "population: not stated";
    const types = g.types(population).map(localName);
    if (types.includes("ContractBoundPopulation")) {
      const scheme = g.value(population, SRF("fromSchemeContract"));
      return `population: the members of the scheme ${scheme ? terms.label(scheme) : "…"} resolves to`;
    }
    if (types.includes("EnumeratedPopulation")) return "population: the values listed";
    if (types.includes("ClassExtentPopulation")) return "population: the instances of a class";
    return `population: ${words(population)}`;
  })();
  const entries: DrawNode = {
    id: `${contract}|entries`, kind: "entries", tag: "Entries", title: "Index entries", rank: steps.length, contract, select: contract,
    lines: [forms.length ? `forms: ${forms.join(", ")}` : "forms: none stated", ...(basis ? [`closure over ${terms.label(basis)}`] : []), populationLine],
    claims: [
      { focus: contract, paths: [SRF("valuePopulation"), SRF("indexForm"), SRF("namingPolicy"), SRF("closureBasis"), SRF("closureScope")] },
      ...(population ? [{ focus: population }] : []),
    ],
  };
  nodes.push(entries);
  if (steps.length === 0) {
    edges.push({ id: `${contract}|e|none`, source: carrier.id, target: entries.id, kind: "hop", label: "no read path", title: `${name} states no read path yet`, dashed: true, contract, claims: [{ focus: contract, paths: [SRF("readProperty"), SRF("hasPathStep")] }] });
  } else {
    readHopsOf(g, contract, terms, steps, { id: entries.id, carrierLabel: carrier.title, endLabel: entries.title }, nodes, edges);
  }
  return { contract, name, kind: "index", nodes, edges, targets: [], depth: steps.length, carriers: carriersOf(g, contract) };
}

// --- a projection ----------------------------------------------------------------------------------------------------------------------

function projection(g: Graph, contract: string, name: string, terms: Terms): ContractDrawing {
  const bindings = bindingsOf(g, contract);
  const result = bindings.find((b) => b.role === "result");
  const kind = projectionShape(g, contract, result);
  const carrier = carrierNode(g, contract, name, terms, KIND_TAG[kind]);
  const nodes: DrawNode[] = [carrier];
  const edges: DrawEdge[] = [];
  const targets: TargetRef[] = [];

  const statementOf = (p: string) => (result ? g.value(result.iri, SRF(p)) : undefined);
  const expansion = statementOf("expandedAs");
  const expandsFrom = expansion ? g.value(expansion, SRF("expandsFrom")) : undefined;
  const second = bindings.find((b) => b.carrier !== undefined && b.carrier !== g.value(contract, SRF("carrier")));

  // The second carrier of a join, a box of its own beside the first.
  let carrier2: DrawNode | undefined;
  if (second?.carrier) {
    carrier2 = {
      id: `${contract}|carrier2`, kind: "carrier", tag: "Second carrier", title: terms.label(second.carrier), lines: [], rank: 0, contract, select: second.iri,
      claims: bindings.filter((b) => b.carrier === second.carrier).map((b) => ({ focus: b.iri, paths: [SRF("bindsCarrier")] })),
    };
    nodes.push(carrier2);
  }

  // Each evidence binding is an edge from its carrier to the property it reads, solid where it is required and dashed where it is not.
  // The binding an expansion expands from is the first hop of its members path instead, drawn with the same dash.
  const evidence = bindings.filter((b) => b.role === "required" || b.role === "candidate" || b.role === "dependency" || b.role === "closure");
  const evidenceNode = new Map<string, string>();
  for (const b of evidence) {
    if (b.iri === expandsFrom) continue;
    const id = `${contract}|ev|${b.iri}`;
    evidenceNode.set(b.iri, id);
    const own = b.carrier !== undefined && carrier2 !== undefined && b.carrier === second?.carrier;
    const label = b.property ? terms.label(b.property) : "…";
    nodes.push({
      id, kind: "evidence", tag: ROLE_WORDS[b.role], title: label, lines: b.datatype ? [`: ${datatypeName(b.datatype)}`] : [], rank: 1, contract, select: b.iri,
      place: { kind: "binding", node: b.iri, contract, carrier: own ? second?.carrier : g.value(contract, SRF("carrier")), label: `the property of ${ROLE_WORDS[b.role]}` },
      claims: [{ focus: b.iri, paths: [SRF("bindsProperty"), SRF("bindsDatatype"), SRF("bindsCarrier")] }],
    });
    edges.push({
      id: `${contract}|e|read|${b.iri}`, source: own ? carrier2!.id : carrier.id, target: id, kind: "read", dashed: b.role !== "required",
      title: `${own ? carrier2!.title : carrier.title} reads ${label} as ${ROLE_WORDS[b.role]}`, contract, claims: [{ focus: b.iri, paths: [SRF("roleKind")] }],
    });
  }

  const linkProperty = result?.property;
  const linkLabel = linkProperty ? terms.label(linkProperty) : "…";
  const resultClaims: Claim[] = result ? [{ focus: result.iri, paths: [SRF("bindsProperty"), SRF("bindsDatatype"), SRF("roleKind"), SRF("derivedAs"), SRF("constructedAs"), SRF("joinedAs"), SRF("expandedAs")] }] : [{ focus: contract, paths: [SRF("hasRoleBinding")] }];
  let depth = evidence.length || carrier2 ? 1 : 0;

  if (kind === "derivation") {
    // The expression, as one line on the edge that writes the derived property.
    const root = statementOf("derivedAs");
    const text = readExpression(g, root, (iri) => terms.label(iri));
    const claims = [...resultClaims, ...expressionNodes(g, root).map((e) => ({ focus: e }))];
    const line = expressionLine(text, result?.datatype);
    targets.push({ kind: "property", iri: linkProperty ?? "", stated: result?.datatype, from: carrier.id, edge: { label: line, title: `${carrier.title} is written ${linkLabel} as ${line}`, claims, expression: { contract, binding: result?.iri } } });
    return { contract, name, kind, nodes, edges, targets, depth, primary: linkProperty, carriers: carriersOf(g, contract) };
  }

  // The members path of an expansion, step by step to the member class. Its first hop is the evidence the statement expands from.
  let memberNode: string | undefined;
  if (expansion) {
    const binding = bindings.find((b) => b.iri === expandsFrom);
    const source = g.value(expansion, SRF("expansionSource"));
    const states = g.object(expansion, SRF("membersPath"));
    const hops: Hop[] | undefined = states ? (membersPath(g, expansion) ?? undefined) : binding?.property ? sourceHops(source, binding.property) : undefined;
    const claims: Claim[] = [{ focus: expansion, paths: [SRF("expandsFrom"), SRF("expansionSource"), SRF("membersPath")] }, ...(binding ? [{ focus: binding.iri, paths: [SRF("bindsProperty"), SRF("roleKind")] }] : [])];
    const dashed = binding?.role !== "required";
    const membersPlace: PathPlace = { kind: "members", node: expansion, contract, carrier: g.value(contract, SRF("carrier")), label: "the members path" };
    let from = carrier.id;
    let fromLabel = carrier.title;
    const path = hops ?? (binding?.property ? [{ property: binding.property, inverse: false } as Hop] : []);
    if (path.length === 0) {
      memberNode = `${contract}|member`;
      nodes.push({ id: memberNode, kind: "class", tag: "Members", title: "…", lines: [], rank: 1, contract, select: expansion, place: membersPlace, claims: [] });
      edges.push({ id: `${contract}|e|hop|0`, source: from, target: memberNode, kind: "hop", label: "no members path", title: `${name} states no members path`, dashed: true, contract, claims });
    }
    path.forEach((hop, i) => {
      const last = i === path.length - 1;
      const next = path[i + 1];
      const toLabel = last ? memberClass(terms, hop) : next?.property === RDF("rest") || hop.property === RDF("rest") ? "list" : reached(hop, terms);
      const to = last ? `${contract}|member` : `${contract}|hop|${i}`;
      nodes.push({ id: to, kind: "class", tag: last ? "Members" : "Reached", title: toLabel, lines: [], rank: i + 1, contract, select: expansion, place: last ? membersPlace : undefined, claims: [] });
      edges.push({
        id: `${contract}|e|hop|${i}`, source: from, target: to, kind: "hop", label: hopLabel(terms, hop), title: hopTitle(terms, fromLabel, hop, toLabel), dashed,
        inverse: hop.inverse, closure: hop.closure, contract, claims: i === 0 ? claims : [],
      });
      from = to;
      fromLabel = toLabel;
      if (last) memberNode = to;
    });
    depth = Math.max(depth, path.length);
  }


  // A constructed node, with the class it is typed with, its identity and each value it writes.
  const constructed = statementOf("constructedAs");
  let statement: DrawNode | undefined;
  if (constructed) {
    const cls = g.value(constructed, SRF("constructedClass"));
    const identity = g.value(constructed, SRF("nodeIdentity"));
    const keys = sorted(g.objects(constructed, SRF("keyBinding")));
    const byKey = (iri: string) => {
      const b = bindings.find((x) => x.iri === iri);
      return b?.property ? terms.label(b.property) : localName(iri);
    };
    const keyParts = [...keys.map(byKey), ...(g.value(constructed, SRF("keyMember")) === "true" ? ["the member"] : [])];
    const identityLine = (() => {
      switch (localName(identity ?? "")) {
        case "PerInstance":
          return expansion ? "identity: for each instance and member" : "identity: for each instance";
        case "ByKey":
          return `identity: by key${keyParts.length ? ` (${keyParts.join(", ")})` : ""}`;
        case "MemberNode":
          return "identity: the member itself";
        default:
          return "identity: not stated";
      }
    })();
    const memberName = g.value(constructed, SRF("memberName"));
    const writes = g.objects(constructed, SRF("writes")).map((w) => {
      const property = g.value(w, SRF("writesProperty"));
      const from = g.value(w, SRF("fromBinding"));
      return { node: w, property, from, member: g.value(w, SRF("fromMember")) === "true" };
    }).sort((a, b) => (a.property ?? "").localeCompare(b.property ?? ""));
    const writeLine = (w: (typeof writes)[number]) => `${w.property ? terms.label(w.property) : "…"} ← ${w.member ? "the member" : w.from ? byKey(w.from) : "…"}`;
    statement = {
      id: `${contract}|stmt`, kind: "statement", tag: expansion ? "Node for each member" : "Constructs", title: cls ? terms.label(cls) : "…",
      lines: [identityLine, ...(memberName ? [`name: ${terms.label(memberName)}`] : []), ...writes.map(writeLine)],
      rank: Math.max(2, depth + 1), contract, select: constructed,
      claims: [{ focus: constructed, paths: [SRF("constructedClass"), SRF("nodeIdentity"), SRF("keyBinding"), SRF("keyMember"), SRF("memberName"), SRF("writes")] }],
    };
    nodes.push(statement);
    edges.push({
      id: `${contract}|e|result`, source: memberNode ?? carrier.id, target: statement.id, kind: "write", label: memberNode ? "for each member" : linkLabel,
      title: memberNode ? `${statement.title} is made for each member and linked by ${linkLabel}` : `${carrier.title} is linked by ${linkLabel} to a ${statement.title}`, dashed: false, contract, claims: resultClaims,
    });
    // Each value is joined to the binding it is written from, and a key to the bindings it names.
    for (const w of writes) {
      const claim: Claim[] = [{ focus: w.node.value }];
      if (w.member && memberNode) {
        edges.push({ id: `${contract}|e|write|${w.node.value}`, source: memberNode, target: statement.id, kind: "write", label: w.property ? terms.label(w.property) : "…", title: `${w.property ? terms.label(w.property) : "…"} is written from the member`, dashed: false, contract, claims: claim });
      } else if (w.from && evidenceNode.has(w.from)) {
        edges.push({ id: `${contract}|e|write|${w.node.value}`, source: evidenceNode.get(w.from)!, target: statement.id, kind: "write", label: w.property ? terms.label(w.property) : "…", title: `${w.property ? terms.label(w.property) : "…"} is written from ${byKey(w.from)}`, dashed: false, contract, claims: claim });
      }
    }
    for (const k of keys) {
      if (evidenceNode.has(k)) edges.push({ id: `${contract}|e|key|${k}`, source: evidenceNode.get(k)!, target: statement.id, kind: "key", label: "key", title: `${byKey(k)} is a part of the key`, dashed: true, contract, claims: [{ focus: constructed, paths: [SRF("keyBinding")] }] });
    }
    depth = Math.max(depth, statement.rank);
    const written = (property: string | undefined, datatype: string | undefined, label: string, title: string) => property && targets.push({ kind: "property", iri: property, stated: datatype, from: statement!.id, edge: { label, title } });
    if (cls) targets.push({ kind: "class", iri: cls, from: statement.id, edge: { label: "is a", title: `${statement.title} is typed ${terms.label(cls)}` } });
    if (linkProperty) targets.push({ kind: "property", iri: linkProperty, stated: result?.datatype, from: statement.id, edge: { label: "linked by", title: `${carrier.title} is linked to it by ${linkLabel}` } });
    for (const w of writes) {
      const binding = bindings.find((b) => b.iri === w.from);
      written(w.property, binding?.datatype, "writes", `${w.property ? terms.label(w.property) : "…"} is written on the ${statement.title}`);
    }
    return { contract, name, kind, nodes, edges, targets, depth, primary: linkProperty, carriers: carriersOf(g, contract) };
  }

  if (kind === "join") {
    const join = statementOf("joinedAs");
    const matches = join ? g.value(join, SRF("joinMatches")) : undefined;
    const links = join ? g.value(join, SRF("joinLinks")) : undefined;
    const rule = (v: string | undefined, fallback: string) => (v ? (CARDINALITY[localName(v)] ?? words(v)) : `${fallback} (default)`);
    const pairs = join ? g.objects(join, SRF("joinsOn")) : [];
    const stmt: DrawNode = {
      id: `${contract}|stmt`, kind: "statement", tag: "Join", title: second?.carrier ? terms.label(second.carrier) : "…", rank: 2, contract, select: join ?? contract,
      lines: [`one value finds: ${rule(matches, "at most one")}`, `one instance links: ${rule(links, "any number")}`],
      claims: join ? [{ focus: join, paths: [SRF("joinMatches"), SRF("joinLinks"), SRF("joinsOn")] }] : [],
    };
    nodes.push(stmt);
    edges.push({
      id: `${contract}|e|result`, source: carrier.id, target: stmt.id, kind: "write", label: linkLabel, title: `${carrier.title} is linked by ${linkLabel} to the ${stmt.title} its key finds`, dashed: false, contract, claims: resultClaims,
    });
    for (const pair of pairs) {
      const left = g.value(pair, SRF("joinLeft"));
      const right = g.value(pair, SRF("joinRight"));
      const lb = bindings.find((b) => b.iri === left);
      const rb = bindings.find((b) => b.iri === right);
      const datatype = lb?.datatype ?? rb?.datatype;
      const from = left ? evidenceNode.get(left) : undefined;
      const to = right ? evidenceNode.get(right) : undefined;
      if (!from || !to) continue;
      edges.push({
        id: `${contract}|e|key|${pair.value}`, source: from, target: to, kind: "key", label: `=${datatype ? ` : ${datatypeName(datatype)}` : ""}`,
        title: `${lb?.property ? terms.label(lb.property) : "…"} equals ${rb?.property ? terms.label(rb.property) : "…"}${datatype ? `, compared as ${datatypeName(datatype)}` : ", with no datatype stated"}`, dashed: false, contract, claims: [{ focus: pair.value }],
      });
    }
    if (linkProperty) targets.push({ kind: "property", iri: linkProperty, stated: result?.datatype, from: stmt.id, edge: { label: "writes", title: `${carrier.title} is linked to the ${stmt.title} by ${linkLabel}` } });
    return { contract, name, kind, nodes, edges, targets, depth: 2, primary: linkProperty, carriers: carriersOf(g, contract) };
  }

  // An expansion that writes statements on the instance, or a construction or a derivation with nothing stated yet.
  const from = memberNode ?? carrier.id;
  if (linkProperty) {
    targets.push({ kind: "property", iri: linkProperty, stated: result?.datatype, from, edge: { label: memberNode ? "written as" : linkLabel, title: `${carrier.title} is written ${linkLabel}`, claims: resultClaims } });
  } else {
    targets.push({ kind: "property", iri: "", from, edge: { label: "…", title: `${name} states no result property yet`, claims: resultClaims, dashed: true } });
  }
  return { contract, name, kind, nodes, edges, targets, depth, primary: linkProperty, carriers: carriersOf(g, contract) };
}

const KIND_TAG: Record<ContractKind, string> = {
  promotion: "Promotion", index: "Index", derivation: "Derivation", construction: "Construction", join: "Join", expansion: "Expansion", member: "Node for each member",
};

/** The class the members of an expansion are, by the ontology's range of the last hop, and else just the members. */
function memberClass(terms: Terms, last: Hop): string {
  const end = last.property === RDF("first") ? "value" : reached(last, terms);
  return end === "value" ? "member" : end;
}

// --- the whole drawing -------------------------------------------------------------------------------------------------------------------

export interface SchemeBox {
  /** The contract the scheme was lowered from. */
  contract: string;
  title: string;
  lines: string[];
  /** Where the box stands: no compilation, a compilation without the scheme, a scheme, and whether what it was compiled from has changed since. */
  state: "none" | "absent" | "ready";
  stale: boolean;
}

export interface Drawing {
  nodes: DrawNode[];
  edges: DrawEdge[];
  contracts: ContractDrawing[];
  /** The rank of the targets. */
  targetRank: number;
}

export const targetId = (kind: "property" | "class", iri: string) => `target|${kind}|${iri}`;

export interface DrawOptions {
  /** Draws every contract but `expand` as an overview, its carriers, itself and its targets, with no hops, bindings, statements or scheme box. */
  overview?: boolean;
  /** The contract an overview draws in full, in place. */
  expand?: string;
}

/**
 * The drawing of `contracts`, which share the nodes on the right where they write the same term. Each target is read from the ontology, and the
 * lowered scheme of each projection stands beside the targets, joined to the term the contract writes first. As an overview each contract is a
 * node between the classes it reads from and the terms it writes, and the contract `expand` names is drawn in full among them.
 */
export function drawContracts(g: Graph, contracts: readonly string[], terms: Terms, schemes: (contract: string) => SchemeBox | undefined = () => undefined, options: DrawOptions = {}): Drawing {
  const drawn = [...contracts].map((c) => drawContract(g, c, terms));
  const full = (d: ContractDrawing) => !options.overview || d.contract === options.expand;
  const targetRank = options.overview ? Math.max(2, ...drawn.filter(full).map((d) => d.depth + 1)) : Math.max(1, ...drawn.map((d) => d.depth + 1));
  const nodes: DrawNode[] = [];
  const edges: DrawEdge[] = [];
  const shared = new Map<string, { kind: "property" | "class"; iri: string; stated: Set<string> }>();
  const missing: DrawNode[] = [];
  const carriers = new Map<string, string>();
  const join = (d: ContractDrawing, targets: readonly TargetRef[]) => {
    for (const t of targets) {
      const id = t.iri === "" ? `${d.contract}|missing` : targetId(t.kind, t.iri);
      if (t.iri === "") {
        missing.push({ id, kind: "target", tag: "Property", title: "…", lines: ["not stated yet"], rank: targetRank, contract: d.contract, claims: [] });
      } else {
        const known = shared.get(id) ?? { kind: t.kind, iri: t.iri, stated: new Set<string>() };
        if (t.stated) known.stated.add(t.stated);
        shared.set(id, known);
      }
      // The edge that writes it. A promotion's last hop already is that edge, so it is pointed at the shared node.
      const hop = t.retarget ? edges.find((e) => e.id === t.retarget) : undefined;
      if (hop) hop.target = id;
      else edges.push({ id: `${d.contract}|e|target|${t.from}|${id}`, source: t.from, target: id, kind: "write", label: t.edge.label, title: t.edge.title, dashed: t.edge.dashed ?? false, contract: d.contract, expression: t.edge.expression, claims: t.edge.claims ?? [] });
    }
  };
  for (const d of drawn.filter(full)) {
    nodes.push(...d.nodes);
    edges.push(...d.edges);
    if (d.carriers[0]) carriers.set(d.carriers[0], `${d.contract}|carrier`);
    join(d, d.targets);
  }
  for (const d of drawn.filter((x) => !full(x))) {
    const id = `${d.contract}|overview`;
    nodes.push({ id, kind: "contract", tag: KIND_TAG[d.kind], title: d.name, lines: [], rank: 1, contract: d.contract, select: d.contract, claims: [{ focus: d.contract }] });
    d.carriers.forEach((c, i) => {
      let from = carriers.get(c);
      if (!from) {
        from = `carrier|${c}`;
        carriers.set(c, from);
        nodes.push({ id: from, kind: "carrier", tag: "Carrier", title: terms.label(c), lines: [], rank: 0, claims: [{ focus: c }] });
      }
      edges.push({
        id: `${d.contract}|e|ov|carrier|${c}`, source: from, target: id, kind: "read", dashed: i > 0, label: i > 0 ? "second carrier" : undefined,
        title: `${d.name} reads from ${terms.label(c)}`, contract: d.contract, claims: [],
      });
    });
    const seen = new Set<string>();
    const writes: TargetRef[] = [];
    for (const t of d.targets) {
      if (t.iri === "" || seen.has(targetId(t.kind, t.iri))) continue;
      seen.add(targetId(t.kind, t.iri));
      writes.push({ kind: t.kind, iri: t.iri, stated: t.stated, from: id, edge: { title: `${d.name} writes ${terms.label(t.iri)}` } });
    }
    join(d, writes);
  }
  const live = [...nodes];
  for (const [id, t] of shared) {
    const info = readTarget(terms, t.kind, t.iri, [...t.stated]);
    live.push({
      id, kind: "target", tag: t.kind === "class" ? "Class" : "Property", title: info.label,
      lines: targetLines(info), rank: targetRank, target: info, claims: [],
    });
  }
  live.push(...missing);
  // The lowered scheme of each projection, beside the targets.
  for (const d of drawn.filter(full)) {
    const box = d.kind !== "promotion" && d.kind !== "index" ? schemes(d.contract) : undefined;
    if (!box) continue;
    const id = `${d.contract}|scheme`;
    live.push({ id, kind: "scheme", tag: "Lowered scheme", title: box.title, lines: box.lines, rank: targetRank + 1, contract: d.contract, scheme: d.contract, claims: [] });
    const primary = d.primary ? targetId(d.targets.find((t) => t.iri === d.primary)?.kind ?? "property", d.primary) : d.targets[0]?.iri === "" ? `${d.contract}|missing` : undefined;
    if (primary) edges.push({ id: `${d.contract}|e|lowered`, source: primary, target: id, kind: "lowered", label: "lowered to", title: `${d.name} is lowered to ${box.title}`, dashed: true, contract: d.contract, claims: [] });
  }
  return { nodes: live, edges, contracts: drawn, targetRank };
}

/** What a target node says of the term: its range or class, and where the ontology does not declare it or disagrees with the contract. */
export function targetLines(t: TargetInfo): string[] {
  const out: string[] = [];
  if (!t.declared) out.push(`not declared in the ontology`);
  else if (t.kind === "property") out.push(t.ranges.length ? `range ${t.ranges.join(", ")}` : "declared, no range");
  else out.push("a class of the ontology");
  if (t.disagrees) out.push(`the contract states ${t.stated.join(", ")}`);
  return out;
}
