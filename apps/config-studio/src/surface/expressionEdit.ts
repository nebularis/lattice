// SPDX-License-Identifier: MPL-2.0
// The pure part of the expression editor (SVA-S1 part 3, SVA-Q57 (b), SVA-Q59). Each function here is one edit of the surface part, a graph in and a
// graph out, so the editor makes each by one `model.edit` and undo works as for any edit. An edit that is refused, because it would break a law the
// editor keeps, returns the graph it was given and so adds nothing to the undo history. Nothing here parses text. An expression is stated as the
// Surface README gives it (section 6.15): a node typed as its kind, named by an IRI minted in the baseline's namespace, stating its result datatype
// and its operands. The laws the editor keeps while it edits are srf:P6 (an expression is stated by the result-target binding of a derivation, and
// every node is reached from it, so a node dropped from the tree is dropped from the graph), srf:P7 (an operand is an expression or an evidence
// binding of the same contract that binds a property) and srf:P9 (no cycle). srf:P8, typing, is shown by `typing.ts` and left to the author.

import { DataFactory } from "n3";
import { Graph, SRF, TYPE, XSD, iri, namedNode, typed, type GraphEditor, type Term } from "@lattice/authoring-domain";
import { mint, nameOf } from "../rdf/editors";
import { bindingsOf } from "./drawing";
import { COMPARISON, datatypeName, expressionLine, expressionNodes, readExpression, type ExprNode } from "./expression";
import { NUMERIC, typeTree, type TypedNode } from "./typing";

export type KindId = "sum" | "difference" | "product" | "quotient" | "round" | "choice" | "literal";

export interface KindInfo {
  id: KindId;
  /** The class the node is typed with. */
  type: string;
  /** The words the editor calls it by. */
  word: string;
  /** The properties its operands are stated with, in order. A rounding's scale, a choice's comparison and a literal's value are not operands. */
  operands: string[];
}

const { quad } = DataFactory;
const L = SRF("leftOperand");
const R = SRF("rightOperand");

export const KINDS: KindInfo[] = [
  { id: "sum", type: SRF("SumExpression"), word: "Sum", operands: [L, R] },
  { id: "difference", type: SRF("DifferenceExpression"), word: "Difference", operands: [L, R] },
  { id: "product", type: SRF("ProductExpression"), word: "Product", operands: [L, R] },
  { id: "quotient", type: SRF("QuotientExpression"), word: "Quotient", operands: [L, R] },
  { id: "round", type: SRF("RoundingExpression"), word: "Rounding", operands: [SRF("roundedOperand")] },
  { id: "choice", type: SRF("ChoiceExpression"), word: "Choice", operands: [SRF("comparedLeft"), SRF("comparedRight"), SRF("whenTrue"), SRF("whenFalse")] },
  { id: "literal", type: SRF("TypedLiteralExpression"), word: "Typed literal", operands: [] },
];

const kindInfo = (id: KindId): KindInfo => KINDS.find((k) => k.id === id)!;
const ALL_OPERANDS = [...new Set(KINDS.flatMap((k) => k.operands))];

/** The kind a node of the graph is, or none where it is no expression the vocabulary knows. */
export function kindOfNode(g: Graph, node: string): KindInfo | undefined {
  const types = g.types(node);
  return KINDS.find((k) => types.includes(k.type));
}

/** The six comparison operators, by the symbol the line writes and the individual the vocabulary names. */
export const COMPARISONS: { symbol: string; iri: string }[] = Object.entries(COMPARISON).map(([iri, symbol]) => ({ symbol, iri }));

/** What an operand may be, the contract's evidence bindings, as the editor offers them. */
export interface Evidence {
  iri: string;
  /** The property it binds. */
  property: string;
  role: "required" | "candidate";
  datatype?: string;
}

export interface ExprContext {
  contract: string;
  /** The contract's result-target binding, which states the expression with srf:derivedAs. Where it has none the contract cannot state one. */
  binding?: string;
  /** The datatype the result-target binding states. */
  bindingDatatype?: string;
  /** The evidence bindings of the contract that bind a property, the only bindings an operand may be (srf:P7). The subject, the result and the others are never offered. */
  evidence: Evidence[];
  /** The baseline's namespace, where a new node is minted, and the graph whose names it must not repeat. */
  namespace: string;
  known?: Graph;
  /** What the new nodes are named after. */
  name: string;
}

/** What an editor needs to know of a derivation. `known` is the baseline, which a minted IRI must not repeat. */
export function contextOf(g: Graph, contract: string, namespace: string, known?: Graph): ExprContext {
  const bindings = bindingsOf(g, contract);
  const result = bindings.find((b) => b.role === "result");
  return {
    contract, binding: result?.iri, bindingDatatype: result?.datatype, namespace, known, name: nameOf(g, contract),
    evidence: bindings.filter((b): b is typeof b & { role: "required" | "candidate"; property: string } => (b.role === "required" || b.role === "candidate") && b.property !== undefined).map((b) => ({ iri: b.iri, property: b.property, role: b.role, datatype: b.datatype })),
  };
}

/** The tree a contract states, read, typed and written as a line. */
export interface Stated {
  /** The node `srf:derivedAs` names, where the result-target binding states one. */
  root?: string;
  expression: ExprNode;
  typed: TypedNode;
  /** The infix line with its datatype, as the canvas draws it on the result edge. */
  line: string;
}

export function statedBy(g: Graph, ctx: ExprContext, label: (iri: string) => string): Stated {
  const root = ctx.binding ? g.value(ctx.binding, SRF("derivedAs")) : undefined;
  const expression = readExpression(g, root, label, { evidence: new Set(ctx.evidence.map((e) => e.iri)), binding: ctx.binding });
  return { root, expression, typed: typeTree(expression, root === undefined ? {} : { result: { datatype: ctx.bindingDatatype } }), line: expressionLine(expression, ctx.bindingDatatype) };
}

// --- minting and pruning ---------------------------------------------------------------------------------------------------------------------

/** A fresh IRI in the baseline's namespace, readable, from the contract's name and what the node is for. Neither the surface part nor the baseline holds it. */
function fresh(g: Graph, ctx: ExprContext, what: string): string {
  const world = ctx.known ? g.merge(ctx.known) : g;
  return mint(world, ctx.namespace, `${ctx.name} ${what}`);
}

const store = (e: GraphEditor) => e.store;
const objectsOf = (e: GraphEditor, s: Term | string, p: string): Term[] => store(e).getObjects(typeof s === "string" ? namedNode(s) : s, namedNode(p), null);
const isExpression = (e: GraphEditor, node: Term): boolean => store(e).getObjects(node, namedNode(TYPE), null).some((t) => KINDS.some((k) => k.type === t.value));

/**
 * Drops an expression node nothing refers to any more, and so each expression only it referred to (srf:P6). An evidence binding belongs to the
 * contract and stays, and so does an expression something else still refers to.
 */
function prune(e: GraphEditor, node: Term): void {
  if (node.termType !== "NamedNode" || !isExpression(e, node) || store(e).countQuads(null, null, node, null) > 0) return;
  const operands = ALL_OPERANDS.flatMap((p) => objectsOf(e, node, p));
  e.remove(node);
  for (const o of operands) prune(e, o);
}

/** The expression nodes `from` reaches through operands, itself included. */
function reaches(g: Graph, from: string): Set<string> {
  const seen = new Set<string>();
  const walk = (n: string) => {
    if (seen.has(n)) return;
    seen.add(n);
    for (const p of ALL_OPERANDS) for (const o of g.objects(n, p)) walk(o.value);
  };
  walk(from);
  return seen;
}

/** Whether `target` as an operand of `parent` would make an expression an operand of itself (srf:P9), which it does where `target` is `parent` or reaches it. */
export function wouldCycle(g: Graph, parent: string, target: string): boolean {
  return reaches(g, target).has(parent);
}

// --- what each part may be -----------------------------------------------------------------------------------------------------------------

export interface OperandChoices {
  /** The evidence bindings of the contract. Never the subject, the result or a binding of another contract (srf:P7). */
  evidence: Evidence[];
  /** Expressions already in the tree that could stand here without a cycle (srf:P9). None where the slot is the expression's own. */
  expressions: string[];
}

/** Where a slot is: the expression's own, which the result-target binding states, or an operand of a node. */
const isRoot = (ctx: ExprContext, slot: { parent: string; predicate: string }) => ctx.binding !== undefined && slot.parent === ctx.binding && slot.predicate === SRF("derivedAs");

function slotAllowed(g: Graph, ctx: ExprContext, slot: { parent: string; predicate: string }): boolean {
  if (isRoot(ctx, slot)) return g.has(slot.parent);
  const kind = kindOfNode(g, slot.parent);
  return kind !== undefined && kind.operands.includes(slot.predicate);
}

export function operandChoices(g: Graph, ctx: ExprContext, slot: { parent: string; predicate: string }): OperandChoices {
  if (!slotAllowed(g, ctx, slot)) return { evidence: [], expressions: [] };
  const root = ctx.binding ? g.value(ctx.binding, SRF("derivedAs")) : undefined;
  const inTree = expressionNodes(g, root);
  return {
    evidence: isRoot(ctx, slot) ? [] : ctx.evidence,
    expressions: isRoot(ctx, slot) ? [] : inTree.filter((n) => !wouldCycle(g, slot.parent, n)),
  };
}

// --- values ----------------------------------------------------------------------------------------------------------------------------------

const LEXICAL: Record<string, RegExp> = {
  [XSD("integer")]: /^[+-]?\d+$/,
  [XSD("decimal")]: /^[+-]?(\d+(\.\d*)?|\.\d+)$/,
  [XSD("float")]: /^([+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?|[+-]?INF|NaN)$/,
  [XSD("double")]: /^([+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?|[+-]?INF|NaN)$/,
};

/** Whether `value` is written as a literal of `datatype`, for the four numeric datatypes. */
export const validLexical = (value: string, datatype: string): boolean => LEXICAL[datatype]?.test(value) ?? false;

export const isNumericDatatype = (datatype: string): boolean => (NUMERIC as readonly string[]).includes(datatype);

// --- the edits -------------------------------------------------------------------------------------------------------------------------------

/** What an operand is set to. */
export type OperandTo =
  | { kind: "evidence"; iri: string }
  | { kind: "literal"; value: string; datatype: string }
  | { kind: "new"; expression: Exclude<KindId, "literal"> }
  | { kind: "existing"; iri: string }
  | { kind: "missing" };

const DEFAULT_DATATYPE = XSD("decimal");

function writeNew(e: GraphEditor, node: string, kind: KindInfo, datatype = DEFAULT_DATATYPE): void {
  e.add(node, TYPE, iri(kind.type));
  e.add(node, SRF("resultDatatype"), iri(datatype));
}

/**
 * States an expression of `kind` on the result-target binding, which states none yet. The node is minted and states xsd:decimal, the datatype
 * the README's own example gives, and every operand is left missing for the author to set. A typed literal is no expression of its own here.
 */
export function addExpression(g: Graph, ctx: ExprContext, kind: Exclude<KindId, "literal">): Graph {
  if (!ctx.binding || g.object(ctx.binding, SRF("derivedAs"))) return g;
  return setOperand(g, ctx, { parent: ctx.binding, predicate: SRF("derivedAs") }, { kind: "new", expression: kind });
}

/**
 * Sets what an operand is, at `slot`. The slot's old value goes, and a nested expression only it stated goes with it. An evidence binding of another
 * contract, the subject, the result or one that binds no property is refused (srf:P7), and so is an existing expression that is or reaches the node
 * (srf:P9). A literal whose value is not written as its datatype is refused.
 */
export function setOperand(g: Graph, ctx: ExprContext, slot: { parent: string; predicate: string }, to: OperandTo): Graph {
  if (!slotAllowed(g, ctx, slot)) return g;
  const root = isRoot(ctx, slot);
  let value: Term | undefined;
  let create: ((e: GraphEditor) => void) | undefined;
  switch (to.kind) {
    case "missing":
      break;
    case "evidence":
      if (root || !ctx.evidence.some((x) => x.iri === to.iri)) return g;
      value = namedNode(to.iri);
      break;
    case "existing": {
      // The node must be one the tree states, and never the node itself or one that reaches it.
      const treeRoot = ctx.binding ? g.value(ctx.binding, SRF("derivedAs")) : undefined;
      if (root || !expressionNodes(g, treeRoot).includes(to.iri) || wouldCycle(g, slot.parent, to.iri)) return g;
      value = namedNode(to.iri);
      break;
    }
    case "new": {
      const node = fresh(g, ctx, "expression");
      value = namedNode(node);
      create = (e) => writeNew(e, node, kindInfo(to.expression));
      break;
    }
    case "literal": {
      if (root || !isNumericDatatype(to.datatype) || !validLexical(to.value, to.datatype)) return g;
      const node = fresh(g, ctx, "constant");
      value = namedNode(node);
      create = (e) => {
        writeNew(e, node, kindInfo("literal"), to.datatype);
        e.add(node, SRF("typedValue"), typed(to.value, to.datatype));
      };
      break;
    }
  }
  const current = g.objects(slot.parent, slot.predicate);
  if (current.length === (value ? 1 : 0) && current[0]?.value === value?.value && !create) return g;
  return g.edit((e) => {
    const old = objectsOf(e, slot.parent, slot.predicate);
    create?.(e);
    e.setAll(slot.parent, slot.predicate, value ? [value] : []);
    for (const o of old) if (o.value !== value?.value) prune(e, o);
  });
}

/** Removes the node at `slot`, which leaves a placeholder. A nested expression goes with the nodes only it stated, and an evidence binding is only let go. */
export const removeAt = (g: Graph, ctx: ExprContext, slot: { parent: string; predicate: string }): Graph => setOperand(g, ctx, slot, { kind: "missing" });

/**
 * Changes the kind of an expression node. Its IRI, its result datatype and its place stay. Its operands move by position, the first operand of the old
 * kind to the first of the new, so a sum's two operands become a product's, a rounding's operand a sum's left operand and a choice's compared operands
 * a sum's. Each operand with no place in the new kind goes, with the nested expression only it stated, and each place the old kind had no operand for
 * is left missing. A rounding's scale, a choice's comparison and a literal's value belong to their kind and go with it.
 */
export function changeKind(g: Graph, node: string, kind: KindId): Graph {
  const from = kindOfNode(g, node);
  const to = kindInfo(kind);
  if (!from || from.id === kind) return g;
  return g.edit((e) => {
    const kept = from.operands.map((p) => objectsOf(e, node, p)[0]);
    for (const p of ALL_OPERANDS) e.setAll(node, p, []);
    e.store.removeQuad(quad(namedNode(node), namedNode(TYPE), namedNode(from.type)));
    e.add(node, TYPE, iri(to.type));
    if (from.id === "round") e.setAll(node, SRF("roundingScale"), []);
    if (from.id === "choice") e.setAll(node, SRF("comparisonOperator"), []);
    if (from.id === "literal") e.setAll(node, SRF("typedValue"), []);
    kept.forEach((operand, i) => {
      if (!operand) return;
      if (to.operands[i]) e.add(node, to.operands[i], operand);
      else prune(e, operand);
    });
  });
}

/** Sets a rounding's scale, an integer that may be negative. */
export function setScale(g: Graph, node: string, scale: number): Graph {
  if (kindOfNode(g, node)?.id !== "round" || !Number.isInteger(scale)) return g;
  return g.edit((e) => e.set(node, SRF("roundingScale"), typed(String(scale), XSD("integer"))));
}

/** Sets a choice's comparison to one of the six the vocabulary names, by its symbol or its IRI. */
export function setComparison(g: Graph, node: string, operator: string): Graph {
  const found = COMPARISONS.find((c) => c.symbol === operator || c.iri === operator);
  if (kindOfNode(g, node)?.id !== "choice" || !found) return g;
  return g.edit((e) => e.set(node, SRF("comparisonOperator"), namedNode(found.iri)));
}

/**
 * Sets the datatype a node states, one of the four numeric ones. For a typed literal it is the datatype of its value too, since a literal's value is
 * of the datatype the node states, and the value is refused where it is not written as that datatype.
 */
export function setResultDatatype(g: Graph, node: string, datatype: string): Graph {
  const kind = kindOfNode(g, node);
  if (!kind || !isNumericDatatype(datatype)) return g;
  if (kind.id === "literal") {
    const value = g.value(node, SRF("typedValue"));
    return value === undefined ? g.edit((e) => e.set(node, SRF("resultDatatype"), iri(datatype))) : setLiteral(g, node, value, datatype);
  }
  return g.edit((e) => e.set(node, SRF("resultDatatype"), iri(datatype)));
}

/** Sets a typed literal's value and datatype together, as a literal of that datatype that the node states too. Refused where the value is not written as it. */
export function setLiteral(g: Graph, node: string, value: string, datatype: string): Graph {
  if (kindOfNode(g, node)?.id !== "literal" || !isNumericDatatype(datatype) || !validLexical(value, datatype)) return g;
  return g.edit((e) => {
    e.set(node, SRF("typedValue"), typed(value, datatype));
    e.set(node, SRF("resultDatatype"), iri(datatype));
  });
}

export { datatypeName };
