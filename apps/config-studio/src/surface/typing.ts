// SPDX-License-Identifier: MPL-2.0
// The datatype each node of an expression has, and where what the contract states disagrees with it (SVA-S1 part 3, SVA-Q59 (b)). The rules are the
// Surface README's (section 6.15, laws srf:P7 and srf:P8), restated here so that the editor shows them as the author edits and before any shape runs.
// The shapes check each node against the datatypes its direct operands state, so this does too. The datatype an operand has is the one it states, or
// where it states none the one its own operands give, so that a tree that is only partly stated still shows what it would be. The rules, each with the
// shape that states it:
//
// - Numeric means xsd:integer, xsd:decimal, xsd:float or xsd:double (srf:ProjectionOperandNumericShape).
// - A sum, difference or product has the wider of its operands' datatypes under XPath promotion, integer then decimal then float then double
//   (srf:ProjectionArithmeticDatatypeShape). A quotient has that too and at least xsd:decimal (srf:ProjectionQuotientDatatypeShape).
// - A rounding has the datatype of its operand (srf:ProjectionRoundingDatatypeShape).
// - A choice has the datatype of both its branches, which must agree with each other and with the datatype the choice states
//   (srf:ProjectionBranchDatatypeShape). Its compared operands are numeric where the comparison is by order, and otherwise are of one datatype or both
//   numeric (srf:ProjectionOrderingOperandsShape, srf:ProjectionComparedOperandsShape).
// - A typed literal has the datatype it states, which is the datatype of its value as written (srf:ProjectionLiteralDatatypeShape).
// - Each node states a datatype, and each operand states one (srf:ProjectionOperandTypedShape).
// - The result-target binding states the datatype of the expression (srf:ProjectionResultTargetDatatypeShape).
//
// A placeholder, an operand that is not an evidence binding of the contract (srf:P7) and a part with no value are marked too. Nothing here
// edits or evaluates an expression.

import { XSD } from "@lattice/authoring-domain";
import { datatypeName, type ExprNode } from "./expression";

export const NUMERIC = [XSD("integer"), XSD("decimal"), XSD("float"), XSD("double")] as const;

/** 1 for xsd:integer to 4 for xsd:double, and 0 for any datatype that is not numeric. */
const rank = (datatype: string | undefined): number => (datatype === undefined ? 0 : NUMERIC.indexOf(datatype as (typeof NUMERIC)[number]) + 1);

export const isNumeric = (datatype: string | undefined): boolean => rank(datatype) > 0;

/** The wider of two numeric datatypes under promotion, and at least `floor`. Undefined where either is not numeric. */
export function promote(a: string | undefined, b: string | undefined, floor: (typeof NUMERIC)[number] = NUMERIC[0]): string | undefined {
  if (!isNumeric(a) || !isNumeric(b)) return undefined;
  return NUMERIC[Math.max(rank(a), rank(b), rank(floor)) - 1];
}

export type MarkCode =
  | "missing"
  | "untyped"
  | "not-numeric"
  | "disagrees"
  | "branches"
  | "compared"
  | "literal"
  | "foreign"
  | "result"
  | "no-scale"
  | "no-comparison";

export interface Mark {
  code: MarkCode;
  message: string;
  /** Where the datatype the rules give is one an author may state, the datatype that agrees. */
  fix?: string;
}

export interface TypedNode {
  node: ExprNode;
  /** What the node is to its parent, such as the left operand. The expression's own node has none. */
  role?: string;
  /** The datatype the node has, the one it states and else the one its operands give. */
  datatype?: string;
  /** The datatype the rules give from the operands the node states, where they give one. */
  expected?: string;
  marks: Mark[];
  children: TypedNode[];
}

export interface TypingContext {
  /** Whether a result-target binding states the expression, and the datatype it states. */
  result?: { datatype?: string };
}

const ORDERING = new Set(["<", "≤", "≥", ">"]);

/** The parts of a node that are expressions or evidence, with what each is to the node. */
export function childrenOf(n: ExprNode): { role: string; node: ExprNode }[] {
  switch (n.kind) {
    case "binary":
      return [{ role: "left operand", node: n.left }, { role: "right operand", node: n.right }];
    case "round":
      return [{ role: "rounded operand", node: n.operand }];
    case "choice":
      return [{ role: "compared left", node: n.left }, { role: "compared right", node: n.right }, { role: "if true", node: n.whenTrue }, { role: "if false", node: n.whenFalse }];
    default:
      return [];
  }
}

const mark = (code: MarkCode, message: string, fix?: string): Mark => ({ code, message, fix });

const KIND_WORD: Record<string, string> = { "+": "sum", "−": "difference", "×": "product", "÷": "quotient" };

/** The words for what a node is, for a message and a label. */
export function kindWord(n: ExprNode): string {
  switch (n.kind) {
    case "binary":
      return KIND_WORD[n.op];
    case "round":
      return "rounding";
    case "choice":
      return "choice";
    case "literal":
      return "typed literal";
    case "operand":
      return "evidence";
    case "missing":
      return "missing";
  }
}

/** Types the tree, giving each node the datatype it has and the marks the rules put on it. */
export function typeTree(root: ExprNode, context: TypingContext = {}): TypedNode {
  const type = (n: ExprNode, role?: string): TypedNode => {
    const kids = childrenOf(n).map((c) => type(c.node, c.role));
    const out: TypedNode = { node: n, role, marks: [], children: kids };
    const stated = n.kind === "operand" ? n.datatype : n.kind === "missing" ? undefined : n.kind === "literal" ? n.statedDatatype : n.datatype;
    const at = (i: number) => kids[i];
    // The datatype of an operand is what it is typed as, which a placeholder has none of.
    const operandNumeric = (kid: TypedNode, what: string) => {
      if (kid.datatype !== undefined && !isNumeric(kid.datatype)) kid.marks.push(mark("not-numeric", `${what} is ${datatypeName(kid.datatype)}, which is not numeric`));
    };
    const disagrees = (expected: string | undefined, why: string) => {
      if (expected !== undefined && stated !== undefined && stated !== expected) out.marks.push(mark("disagrees", `states ${datatypeName(stated)}, ${why} ${datatypeName(expected)}`, isNumeric(expected) ? expected : undefined));
      else if (stated === undefined) out.marks.push(mark("untyped", expected === undefined ? "states no datatype" : `states no datatype, ${why} ${datatypeName(expected)}`, expected !== undefined && isNumeric(expected) ? expected : undefined));
    };
    switch (n.kind) {
      case "operand": {
        if (n.foreign) out.marks.push(mark("foreign", "is not an evidence binding of this contract, which an operand has to be"));
        if (stated === undefined) out.marks.push(mark("untyped", "states no datatype"));
        out.datatype = stated;
        break;
      }
      case "missing":
        out.marks.push(mark("missing", `${n.part} is missing`));
        break;
      case "literal": {
        if (n.value === undefined) out.marks.push(mark("missing", "the value is missing"));
        // A literal with no datatype is a string.
        const own = n.value === undefined ? undefined : (n.valueDatatype ?? XSD("string"));
        if (stated !== undefined && own !== undefined && stated !== own) out.marks.push(mark("literal", `the value is ${datatypeName(own)}, and the node states ${datatypeName(stated)}`, isNumeric(own) ? own : undefined));
        else if (stated === undefined) out.marks.push(mark("untyped", own === undefined ? "states no datatype" : `states no datatype, the value is ${datatypeName(own)}`, own !== undefined && isNumeric(own) ? own : undefined));
        out.expected = own;
        out.datatype = stated ?? own;
        break;
      }
      case "binary": {
        const [left, right] = [at(0), at(1)];
        operandNumeric(left, "the left operand");
        operandNumeric(right, "the right operand");
        out.expected = promote(left.datatype, right.datatype, n.op === "÷" ? NUMERIC[1] : NUMERIC[0]);
        disagrees(out.expected, "the operands give");
        out.datatype = stated ?? out.expected;
        break;
      }
      case "round": {
        const operand = at(0);
        operandNumeric(operand, "the rounded operand");
        out.expected = operand.datatype;
        if (n.scale === undefined) out.marks.push(mark("no-scale", "the scale is missing"));
        disagrees(out.expected, "its operand is");
        out.datatype = stated ?? out.expected;
        break;
      }
      case "choice": {
        const [left, right, whenTrue, whenFalse] = kids;
        if (n.comparison === undefined) out.marks.push(mark("no-comparison", "the comparison is missing"));
        if (n.comparison !== undefined && ORDERING.has(n.comparison)) {
          operandNumeric(left, "the left compared operand, which is compared by order,");
          operandNumeric(right, "the right compared operand, which is compared by order,");
        }
        if (left.datatype !== undefined && right.datatype !== undefined && left.datatype !== right.datatype && !(isNumeric(left.datatype) && isNumeric(right.datatype))) {
          out.marks.push(mark("compared", `compares ${datatypeName(left.datatype)} with ${datatypeName(right.datatype)}, which are not both numeric`));
        }
        const [a, b] = [whenTrue.datatype, whenFalse.datatype];
        out.expected = a !== undefined && b !== undefined ? (a === b ? a : undefined) : (a ?? b);
        if (a !== undefined && b !== undefined && a !== b) out.marks.push(mark("branches", `the branches disagree, ${datatypeName(a)} and ${datatypeName(b)}`));
        else disagrees(out.expected, "the branches give");
        out.datatype = stated ?? out.expected;
        break;
      }
    }
    return out;
  };
  const typed = type(root);
  // The result-target binding states the datatype of the expression, and the expression's own stated one is what it is compared with.
  if (context.result && typed.node.kind !== "missing" && typed.node.kind !== "operand") {
    const own = typed.node.kind === "literal" ? typed.node.statedDatatype : typed.node.datatype;
    if (own !== undefined && context.result.datatype !== own) {
      typed.marks.push(mark("result", context.result.datatype === undefined ? "the result binding states no datatype" : `the result binding states ${datatypeName(context.result.datatype)}`));
    }
  }
  return typed;
}

/** Every mark of the tree, with the node it is on, for a count and for tests. */
export function marksOf(t: TypedNode): { node: ExprNode; mark: Mark }[] {
  return [...t.marks.map((m) => ({ node: t.node, mark: m })), ...t.children.flatMap(marksOf)];
}
