// SPDX-License-Identifier: MPL-2.0
// A derivation's expression, read from the configuration as the author stated it (SVA-Q59). `readExpression` gives the tree of what the
// contract states, with a placeholder wherever a part is missing, and `infix` writes the tree as one line of text with the brackets its
// precedence needs. The tree is the seam of the expression editor, which draws it as nodes in a later part. Nothing here evaluates an
// expression or lowers it. A missing operand, an unknown kind or a cycle is a placeholder and never an error.

import { Graph, SRF, XSD, localName, namedNode, type Term } from "@lattice/authoring-domain";

export type ExprNode =
  /** An evidence role binding of the contract, named by the property it binds. */
  | { kind: "operand"; iri: string; label: string }
  | { kind: "binary"; iri: string; op: Operator; left: ExprNode; right: ExprNode; datatype?: string }
  | { kind: "round"; iri: string; operand: ExprNode; scale?: number; datatype?: string }
  | { kind: "literal"; iri: string; value?: string; datatype?: string }
  | { kind: "choice"; iri: string; comparison?: string; left: ExprNode; right: ExprNode; whenTrue: ExprNode; whenFalse: ExprNode; datatype?: string }
  /** A part the contract does not state yet, or states in a way that cannot be read as an expression. `part` says which. */
  | { kind: "missing"; part: string };

/** What the text writes where a part is missing. */
export const PLACEHOLDER = "…";

type Operator = "+" | "−" | "×" | "÷";

const BINARY: Record<string, Operator> = {
  [SRF("SumExpression")]: "+",
  [SRF("DifferenceExpression")]: "−",
  [SRF("ProductExpression")]: "×",
  [SRF("QuotientExpression")]: "÷",
};

const COMPARISON: Record<string, string> = {
  [SRF("LessThan")]: "<",
  [SRF("LessThanOrEqual")]: "≤",
  [SRF("EqualTo")]: "=",
  [SRF("NotEqualTo")]: "≠",
  [SRF("GreaterThanOrEqual")]: "≥",
  [SRF("GreaterThan")]: ">",
};

/** The binding's own name, the label of the property it binds, or its local name where it binds none. */
export type Namer = (iri: string) => string;

/** Every node an expression is made of, the root first, so that a finding on any of them is drawn on the expression. */
export function expressionNodes(g: Graph, root: string | undefined): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  const visit = (n: Term | undefined) => {
    if (!n || seen.has(n.value)) return;
    seen.add(n.value);
    if (!g.types(n).some((t) => t === SRF("ProjectionExpression") || t in BINARY || [SRF("RoundingExpression"), SRF("TypedLiteralExpression"), SRF("ChoiceExpression")].includes(t))) return;
    out.push(n.value);
    for (const p of ["leftOperand", "rightOperand", "roundedOperand", "comparedLeft", "comparedRight", "whenTrue", "whenFalse"]) visit(g.object(n, SRF(p)));
  };
  visit(root === undefined ? undefined : namedNode(root));
  return out;
}

/** The expression stated at `root`, which is the node `srf:derivedAs` names. `name` gives an operand's text. */
export function readExpression(g: Graph, root: string | undefined, name: Namer): ExprNode {
  const seen = new Set<string>();
  const read = (node: Term | undefined, part: string): ExprNode => {
    if (!node) return { kind: "missing", part };
    const iri = node.value;
    const types = g.types(node);
    // An evidence binding of the contract is an operand, named by the property it binds.
    if (types.includes(SRF("ProjectionRoleBinding"))) {
      const bound = g.value(node, SRF("bindsProperty"));
      return bound ? { kind: "operand", iri, label: name(bound) } : { kind: "missing", part: `the property of ${localName(iri)}` };
    }
    if (seen.has(iri)) return { kind: "missing", part: `${localName(iri)}, which states itself` };
    seen.add(iri);
    const datatype = g.value(node, SRF("resultDatatype"));
    const done = <T extends ExprNode>(n: T): T => (seen.delete(iri), n);
    const arithmetic = types.find((t) => t in BINARY);
    if (arithmetic) {
      return done({ kind: "binary", iri, op: BINARY[arithmetic], left: read(g.object(node, SRF("leftOperand")), "the left operand"), right: read(g.object(node, SRF("rightOperand")), "the right operand"), datatype });
    }
    if (types.includes(SRF("RoundingExpression"))) {
      const scale = g.value(node, SRF("roundingScale"));
      return done({ kind: "round", iri, operand: read(g.object(node, SRF("roundedOperand")), "the rounded operand"), scale: scale === undefined || Number.isNaN(Number(scale)) ? undefined : Number(scale), datatype });
    }
    if (types.includes(SRF("TypedLiteralExpression"))) {
      const value = g.object(node, SRF("typedValue"));
      return done({ kind: "literal", iri, value: value?.value, datatype: datatype ?? (value && "datatype" in value ? value.datatype.value : undefined) });
    }
    if (types.includes(SRF("ChoiceExpression"))) {
      const op = g.value(node, SRF("comparisonOperator"));
      return done({
        kind: "choice", iri, comparison: op === undefined ? undefined : (COMPARISON[op] ?? localName(op)), datatype,
        left: read(g.object(node, SRF("comparedLeft")), "the left compared operand"), right: read(g.object(node, SRF("comparedRight")), "the right compared operand"),
        whenTrue: read(g.object(node, SRF("whenTrue")), "the true branch"), whenFalse: read(g.object(node, SRF("whenFalse")), "the false branch"),
      });
    }
    // A node that is no expression the vocabulary knows, such as an expression with no kind yet.
    return done({ kind: "missing", part: `the kind of ${localName(iri)}` });
  };
  return read(root === undefined ? undefined : namedNode(root), "the expression");
}

/** Binding strength, so that a sum inside a product is bracketed and a product inside a sum is not. */
const STRENGTH = { choice: 0, sum: 1, product: 2, atom: 3 } as const;

function strength(n: ExprNode): number {
  if (n.kind === "choice") return STRENGTH.choice;
  if (n.kind === "binary") return n.op === "+" || n.op === "−" ? STRENGTH.sum : STRENGTH.product;
  return STRENGTH.atom;
}

/**
 * The tree as one line of infix text. A bracket is written where the operand binds less tightly than its operator, and on the right of
 * a difference or a quotient where it binds as tightly, since a − (b − c) is not a − b − c. A rounding is written as a call, a choice as
 * `a < b ? x : y`, and a part that is missing as the placeholder.
 */
export function infix(n: ExprNode): string {
  switch (n.kind) {
    case "operand":
      return n.label;
    case "literal":
      return n.value === undefined ? PLACEHOLDER : n.value;
    case "missing":
      return PLACEHOLDER;
    case "round":
      return `round(${infix(n.operand)}, ${n.scale === undefined ? PLACEHOLDER : n.scale})`;
    case "binary": {
      const own = strength(n);
      const hard = n.op === "−" || n.op === "÷";
      const side = (child: ExprNode, right: boolean) => {
        const text = infix(child);
        const s = strength(child);
        return s < own || (right && hard && s === own) ? `(${text})` : text;
      };
      return `${side(n.left, false)} ${n.op} ${side(n.right, true)}`;
    }
    case "choice": {
      // Every part of a choice is bracketed where it is a choice itself, so that nesting reads without precedence rules.
      const part = (child: ExprNode) => (child.kind === "choice" ? `(${infix(child)})` : infix(child));
      return `${part(n.left)} ${n.comparison ?? PLACEHOLDER} ${part(n.right)} ? ${part(n.whenTrue)} : ${part(n.whenFalse)}`;
    }
  }
}

/** The datatype the line says the expression gives, the expression's own and else the one the result binding states. */
export function datatypeOf(n: ExprNode, stated?: string): string | undefined {
  const own = "datatype" in n ? n.datatype : undefined;
  return own ?? stated;
}

export const datatypeName = (iri: string | undefined): string => (iri === undefined ? PLACEHOLDER : iri.startsWith(XSD("")) ? iri.slice(XSD("").length) : localName(iri));

/** The line that sits on a derivation's result edge, for example `round(commitment × margin, 2) : decimal`. */
export function expressionLine(n: ExprNode, stated?: string): string {
  return `${infix(n)} : ${datatypeName(datatypeOf(n, stated))}`;
}

/** The number of parts of the tree the contract does not state, which a finding about the expression often says too. */
export function gaps(n: ExprNode): number {
  switch (n.kind) {
    case "missing":
      return 1;
    case "binary":
      return gaps(n.left) + gaps(n.right);
    case "round":
      return gaps(n.operand) + (n.scale === undefined ? 1 : 0);
    case "choice":
      return gaps(n.left) + gaps(n.right) + gaps(n.whenTrue) + gaps(n.whenFalse) + (n.comparison === undefined ? 1 : 0);
    case "literal":
      return n.value === undefined ? 1 : 0;
    case "operand":
      return 0;
  }
}
