// SPDX-License-Identifier: MPL-2.0
// The expression editor's pure part (SVA-S1 part 3): the tree read from the configuration, the typing of each node under the Surface README's rules,
// and each edit with the triples it writes, over the facility sample's derivation and over expressions written here.

import { readFileSync } from "node:fs";
import { Graph, SRF, XSD } from "@lattice/authoring-domain";
import { describe, expect, it } from "vitest";
import { drawContract } from "./drawing";
import {
  COMPARISONS, addExpression, changeKind, contextOf, kindOfNode, operandChoices, removeAt, setComparison, setLiteral, setOperand, setResultDatatype, setScale, statedBy, validLexical, wouldCycle,
} from "./expressionEdit";
import { infix } from "./expression";
import { childrenOf, isNumeric, marksOf, promote, typeTree, type TypedNode } from "./typing";
import { ontologyOf, termsOf } from "./terms";

const sample = (n: string) => Graph.parse(readFileSync(new URL(`../../../../contracts/config-studio/samples/${n}`, import.meta.url), "utf-8"));
const surface = sample("facility-surface.ttl");
const baseline = sample("lending-baseline.ttl").merge(sample("facility-baseline.ttl"));
const terms = termsOf(ontologyOf(baseline, []));
const EX = "https://example.org/lending#";
const at = (n: string) => `${EX}${n}`;
const label = (iri: string) => terms.label(iri);
const decimal = XSD("decimal");
const integer = XSD("integer");

/** The facility derivation's own context. */
const facility = contextOf(surface, at("facility-margin-projection"), EX, baseline);
const slot = (parent: string, predicate: string) => ({ parent: at(parent), predicate: SRF(predicate) });

/** A derivation of its own, written here, with evidence of each datatype and no expression, so each test states what it types. */
const PREFIXES = `@prefix srf: <${SRF("")}> . @prefix ex: <${EX}> . @prefix xsd: <${XSD("")}> .`;
const evidence = `
  ex:subject a srf:ProjectionRoleBinding ; srf:roleKind srf:EvaluationSubjectRole .
  ex:i a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsProperty ex:drawnAmount ; srf:bindsDatatype xsd:integer .
  ex:d a srf:ProjectionRoleBinding ; srf:roleKind srf:CandidateEvidenceRole ; srf:bindsProperty ex:commitment ; srf:bindsDatatype xsd:decimal .
  ex:f a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsProperty ex:margin ; srf:bindsDatatype xsd:float .
  ex:s a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsProperty ex:facilityReference ; srf:bindsDatatype xsd:string .
  ex:dependency a srf:ProjectionRoleBinding ; srf:roleKind srf:TransformDependencyRole ; srf:bindsProperty ex:lender ; srf:bindsDatatype xsd:decimal .
  ex:unbound a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsDatatype xsd:decimal .
  ex:result a srf:ProjectionRoleBinding ; srf:roleKind srf:ResultTargetRole ; srf:bindsProperty ex:out ; srf:bindsDatatype xsd:decimal ; srf:derivedAs ex:e .
  ex:other a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsProperty ex:elsewhere ; srf:bindsDatatype xsd:decimal .
  ex:contract a srf:ProjectionContract ; srf:projectionKind srf:DerivationProjection ; srf:carrier ex:Facility ; srf:contractKey "own" ;
    srf:hasRoleBinding ex:subject , ex:i , ex:d , ex:f , ex:s , ex:dependency , ex:unbound , ex:result .`;
const own = (body: string) => Graph.parse(`${PREFIXES} ${evidence} ${body}`);
const ownContext = (g: Graph) => contextOf(g, at("contract"), EX);
const typed = (body: string, bindingDatatype?: string) => {
  const g = own(body);
  // The result binding states what the expression does unless the case says otherwise, so a case marks only what it is about.
  const ctx = { ...ownContext(g), bindingDatatype: bindingDatatype ?? g.value(at("e"), SRF("resultDatatype")) };
  return statedBy(g, ctx, label);
};
const marks = (t: TypedNode) => marksOf(t).map((m) => `${m.mark.code}`);
const codes = (body: string) => marks(typed(body).typed);

describe("the tree of the facility derivation", () => {
  const stated = statedBy(surface, facility, label);

  it("reads the product of the two evidence bindings, each an operand with its datatype, and types it with no mark", () => {
    expect(stated.root).toBe(at("fm-expression"));
    expect(stated.expression).toMatchObject({ kind: "binary", op: "×", datatype: decimal, slot: { parent: at("fm-target"), predicate: SRF("derivedAs") } });
    const kids = childrenOf(stated.expression);
    expect(kids.map((k) => [k.role, k.node.kind, k.node.kind === "operand" ? k.node.label : undefined])).toEqual([["left operand", "operand", "commitment"], ["right operand", "operand", "margin"]]);
    expect(kids.map((k) => (k.node.slot as { predicate: string }).predicate)).toEqual([SRF("leftOperand"), SRF("rightOperand")]);
    expect(stated.typed.datatype).toBe(decimal);
    expect(stated.typed.children.map((c) => c.datatype)).toEqual([decimal, decimal]);
    expect(marksOf(stated.typed)).toEqual([]);
    expect(stated.line).toBe("commitment × margin : decimal");
  });

  it("is the same expression the infix line and the tree draw, which both come from one reading", () => {
    // The leaves of the tree, in order, are the operands the line writes, in order.
    const leaves = (t: TypedNode): string[] => (t.children.length ? t.children.flatMap(leaves) : [t.node.kind === "operand" ? t.node.label : t.node.kind === "literal" ? (t.node.value ?? "…") : "…"]);
    const words = (line: string) => line.split(/[\s(),?:<≤=≠≥>+−×÷]+/).filter((w) => w && w !== "round" && !/^-?\d+$/.test(w) || /^-?\d+\.\d+$/.test(w));
    expect(leaves(stated.typed)).toEqual(["commitment", "margin"]);
    expect(words(infix(stated.expression))).toEqual(leaves(stated.typed));
    // The drawing's result edge writes the line the editor writes.
    expect(drawContract(surface, at("facility-margin-projection"), terms).targets[0].edge.label).toBe(stated.line);
  });

  it("is read from the configuration, so an edit shows in both at once", () => {
    const quotient = changeKind(surface, at("fm-expression"), "quotient");
    const again = statedBy(quotient, facility, label);
    expect(again.line).toBe("commitment ÷ margin : decimal");
    expect(again.typed.node.kind === "binary" && again.typed.node.op).toBe("÷");
    expect(drawContract(quotient, at("facility-margin-projection"), terms).targets[0].edge.label).toBe(again.line);
  });
});

describe("a nested expression three levels deep", () => {
  const body = `
    ex:e a srf:ChoiceExpression ; srf:resultDatatype xsd:decimal ; srf:comparisonOperator srf:LessThan ; srf:comparedLeft ex:d ; srf:comparedRight ex:i ;
      srf:whenTrue ex:r ; srf:whenFalse ex:d .
    ex:r a srf:RoundingExpression ; srf:resultDatatype xsd:decimal ; srf:roundingScale -2 ; srf:roundedOperand ex:sum .
    ex:sum a srf:SumExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:p ; srf:rightOperand ex:c .
    ex:p a srf:ProductExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:d ; srf:rightOperand ex:i .
    ex:c a srf:TypedLiteralExpression ; srf:resultDatatype xsd:decimal ; srf:typedValue "1.5"^^xsd:decimal .`;
  const stated = typed(body);

  it("is one node for each expression node with its operands as children, down the levels", () => {
    const outline = (t: TypedNode, depth = 0): string[] => [`${"  ".repeat(depth)}${t.role ? `${t.role}: ` : ""}${t.node.kind}${t.node.kind === "binary" ? ` ${t.node.op}` : ""}`, ...t.children.flatMap((c) => outline(c, depth + 1))];
    expect(outline(stated.typed)).toEqual([
      "choice",
      "  compared left: operand",
      "  compared right: operand",
      "  if true: round",
      "    rounded operand: binary +",
      "      left operand: binary ×",
      "        left operand: operand",
      "        right operand: operand",
      "      right operand: literal",
      "  if false: operand",
    ]);
    // Each node states the datatype it has.
    expect(stated.typed.children[2].children[0].children[0].datatype).toBe(decimal);
    expect(stated.typed.children[2].children[0].datatype).toBe(decimal);
    expect(marks(stated.typed)).toEqual([]);
  });

  it("writes the line with its brackets and the tree draws the same leaves", () => {
    expect(stated.line).toBe("commitment < drawn amount ? round(commitment × drawn amount + 1.5, -2) : commitment : decimal");
  });
});

describe("the datatype of each kind, under the rules the shapes state", () => {
  const sum = (a: string, b: string, stateds = "xsd:decimal") => `ex:e a srf:SumExpression ; srf:resultDatatype ${stateds} ; srf:leftOperand ex:${a} ; srf:rightOperand ex:${b} .`;

  it("promotes the wider of the operands, integer then decimal then float then double", () => {
    expect(promote(integer, integer)).toBe(integer);
    expect(promote(integer, decimal)).toBe(decimal);
    expect(promote(decimal, XSD("float"))).toBe(XSD("float"));
    expect(promote(XSD("float"), XSD("double"))).toBe(XSD("double"));
    expect(promote(integer, XSD("string"))).toBeUndefined();
    expect(typed(sum("i", "d")).typed).toMatchObject({ datatype: decimal, expected: decimal, marks: [] });
    expect(typed(sum("d", "f", "xsd:float")).typed).toMatchObject({ datatype: XSD("float"), expected: XSD("float"), marks: [] });
    expect(typed(sum("i", "i", "xsd:integer"), integer).typed).toMatchObject({ expected: integer, marks: [] });
  });

  it("gives a quotient of two integers the datatype decimal, and a quotient of a float is a float", () => {
    expect(typed(`ex:e a srf:QuotientExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:i ; srf:rightOperand ex:i .`).typed).toMatchObject({ expected: decimal, datatype: decimal, marks: [] });
    expect(typed(`ex:e a srf:QuotientExpression ; srf:resultDatatype xsd:integer ; srf:leftOperand ex:i ; srf:rightOperand ex:i .`).typed.marks).toEqual([{ code: "disagrees", message: "states integer, the operands give decimal", fix: decimal }]);
    expect(typed(`ex:e a srf:QuotientExpression ; srf:resultDatatype xsd:float ; srf:leftOperand ex:i ; srf:rightOperand ex:f .`).typed).toMatchObject({ expected: XSD("float"), marks: [] });
    // The other three arithmetic kinds keep integer.
    for (const kind of ["Sum", "Difference", "Product"]) {
      expect(typed(`ex:e a srf:${kind}Expression ; srf:resultDatatype xsd:integer ; srf:leftOperand ex:i ; srf:rightOperand ex:i .`).typed).toMatchObject({ expected: integer, marks: [] });
    }
  });

  it("gives a rounding the datatype of its operand, and marks a stated datatype that is another", () => {
    expect(typed(`ex:e a srf:RoundingExpression ; srf:resultDatatype xsd:decimal ; srf:roundingScale 2 ; srf:roundedOperand ex:d .`).typed).toMatchObject({ expected: decimal, marks: [] });
    expect(typed(`ex:e a srf:RoundingExpression ; srf:resultDatatype xsd:integer ; srf:roundingScale 2 ; srf:roundedOperand ex:d .`).typed.marks.map((m) => m.message)).toEqual(["states integer, its operand is decimal"]);
    // A negative scale is a scale.
    expect(codes(`ex:e a srf:RoundingExpression ; srf:resultDatatype xsd:decimal ; srf:roundingScale -2 ; srf:roundedOperand ex:d .`)).toEqual([]);
    expect(codes(`ex:e a srf:RoundingExpression ; srf:resultDatatype xsd:decimal ; srf:roundedOperand ex:d .`)).toEqual(["no-scale"]);
  });

  it("gives a choice the datatype of both its branches, and marks branches that disagree", () => {
    const choice = (whenTrue: string, whenFalse: string, stated = "xsd:decimal", operator = "srf:LessThan") =>
      `ex:e a srf:ChoiceExpression ; srf:resultDatatype ${stated} ; srf:comparisonOperator ${operator} ; srf:comparedLeft ex:d ; srf:comparedRight ex:i ; srf:whenTrue ex:${whenTrue} ; srf:whenFalse ex:${whenFalse} .`;
    expect(typed(choice("d", "d")).typed).toMatchObject({ expected: decimal, datatype: decimal, marks: [] });
    // A choice does not promote. A decimal and an integer branch disagree, and the choice states neither as the other.
    expect(typed(choice("d", "i")).typed.marks.map((m) => [m.code, m.message])).toEqual([["branches", "the branches disagree, decimal and integer"]]);
    expect(typed(choice("d", "d", "xsd:integer")).typed.marks).toEqual([{ code: "disagrees", message: "states integer, the branches give decimal", fix: decimal }]);
    expect(typed(choice("i", "i", "xsd:integer")).typed).toMatchObject({ expected: integer, marks: [] });
  });

  it("compares by order only numeric operands, and by equality operands of one datatype or both numeric", () => {
    const choice = (operator: string, left: string, right: string) =>
      `ex:e a srf:ChoiceExpression ; srf:resultDatatype xsd:decimal ; srf:comparisonOperator ${operator} ; srf:comparedLeft ex:${left} ; srf:comparedRight ex:${right} ; srf:whenTrue ex:d ; srf:whenFalse ex:d .`;
    expect(codes(choice("srf:LessThan", "d", "i"))).toEqual([]);
    expect(codes(choice("srf:LessThan", "d", "s"))).toEqual(["compared", "not-numeric"]);
    expect(codes(choice("srf:EqualTo", "s", "s"))).toEqual([]);
    expect(codes(choice("srf:EqualTo", "s", "d"))).toEqual(["compared"]);
    expect(codes(choice("srf:EqualTo", "d", "f"))).toEqual([]);
    expect(codes(`ex:e a srf:ChoiceExpression ; srf:resultDatatype xsd:decimal ; srf:comparedLeft ex:d ; srf:comparedRight ex:i ; srf:whenTrue ex:d ; srf:whenFalse ex:d .`)).toEqual(["no-comparison"]);
  });

  it("gives a typed literal the datatype it states, which is the datatype of its value", () => {
    const literal = (stated: string, value: string) => `ex:e a srf:TypedLiteralExpression ; srf:resultDatatype ${stated} ; srf:typedValue ${value} .`;
    expect(typed(literal("xsd:decimal", '"1.5"^^xsd:decimal')).typed).toMatchObject({ datatype: decimal, expected: decimal, marks: [] });
    expect(typed(literal("xsd:integer", '"1.5"^^xsd:decimal')).typed.marks.map((m) => [m.code, m.message])).toEqual([["literal", "the value is decimal, and the node states integer"]]);
    // A plain literal is a string.
    expect(codes(literal("xsd:decimal", '"1.5"'))).toEqual(["literal"]);
    expect(codes(`ex:e a srf:TypedLiteralExpression ; srf:resultDatatype xsd:decimal .`)).toEqual(["missing"]);
  });

  it("marks an operand that is not numeric, one that states no datatype, one that is missing and one that is not evidence of the contract", () => {
    expect(typed(sum("s", "d")).typed.children.map((c) => c.marks.map((m) => m.message))).toEqual([["the left operand is string, which is not numeric"], []]);
    const noType = own(`ex:untyped a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole ; srf:bindsProperty ex:x . ex:contract srf:hasRoleBinding ex:untyped . ex:e a srf:SumExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:untyped ; srf:rightOperand ex:d .`);
    expect(marks(statedBy(noType, ownContext(noType), label).typed)).toEqual(["untyped"]);
    expect(codes(`ex:e a srf:SumExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:d .`)).toEqual(["missing"]);
    // A binding of another contract is read as an operand and marked, as is the subject.
    expect(codes(sum("other", "d"))).toEqual(["foreign"]);
    // The subject binds no property, so it is read as a placeholder.
    expect(codes(sum("subject", "d"))).toEqual(["missing"]);
    // An operand that is a placeholder gives its parent no datatype to disagree with.
    expect(typed(`ex:e a srf:SumExpression ; srf:resultDatatype xsd:integer ; srf:leftOperand ex:d .`).typed.marks).toEqual([]);
  });

  it("marks a node that states no datatype, with the one the operands give", () => {
    const t = typed(`ex:e a srf:ProductExpression ; srf:leftOperand ex:d ; srf:rightOperand ex:i .`);
    expect(t.typed.marks).toEqual([{ code: "untyped", message: "states no datatype, the operands give decimal", fix: decimal }]);
    expect(t.typed.datatype).toBe(decimal);
  });

  it("marks a result-target binding that states another datatype than the expression", () => {
    expect(typed(sum("d", "d"), XSD("integer")).typed.marks.map((m) => m.message)).toEqual(["the result binding states integer"]);
    expect(typed(sum("d", "d"), decimal).typed.marks).toEqual([]);
  });

  it("names the numeric datatypes", () => {
    expect([integer, decimal, XSD("float"), XSD("double")].every(isNumeric)).toBe(true);
    expect([XSD("string"), XSD("int"), undefined].some(isNumeric)).toBe(false);
  });
});

describe("an edit writes the triples the Surface README gives for the kind", () => {
  it("changes the product to a quotient, keeping both operands and the node", () => {
    const g = changeKind(surface, at("fm-expression"), "quotient");
    expect(g.types(at("fm-expression"))).toEqual([SRF("QuotientExpression")]);
    expect(g.value(at("fm-expression"), SRF("leftOperand"))).toBe(at("fm-commitment"));
    expect(g.value(at("fm-expression"), SRF("rightOperand"))).toBe(at("fm-margin"));
    expect(g.value(at("fm-expression"), SRF("resultDatatype"))).toBe(decimal);
    expect(g.value(at("fm-target"), SRF("derivedAs"))).toBe(at("fm-expression"));
  });

  it("moves the operands by position and leaves a placeholder for each the new kind has and the old did not", () => {
    const round = changeKind(surface, at("fm-expression"), "round");
    expect(round.types(at("fm-expression"))).toEqual([SRF("RoundingExpression")]);
    expect(round.value(at("fm-expression"), SRF("roundedOperand"))).toBe(at("fm-commitment"));
    expect(round.value(at("fm-expression"), SRF("rightOperand"))).toBeUndefined();
    expect(round.value(at("fm-expression"), SRF("roundingScale"))).toBeUndefined();
    // The binding the dropped operand was stays in the contract.
    expect(round.has(at("fm-margin"))).toBe(true);
    expect(statedBy(round, facility, label).line).toBe("round(commitment, …) : decimal");
    const choice = changeKind(surface, at("fm-expression"), "choice");
    expect(choice.value(at("fm-expression"), SRF("comparedLeft"))).toBe(at("fm-commitment"));
    expect(choice.value(at("fm-expression"), SRF("comparedRight"))).toBe(at("fm-margin"));
    expect(statedBy(choice, facility, label).line).toBe("commitment … margin ? … : … : decimal");
    const literal = changeKind(surface, at("fm-expression"), "literal");
    expect(literal.types(at("fm-expression"))).toEqual([SRF("TypedLiteralExpression")]);
    expect(literal.objects(at("fm-expression"), SRF("leftOperand"))).toEqual([]);
    expect(statedBy(literal, facility, label).line).toBe("… : decimal");
  });

  it("takes a kind's own parts with it and drops a nested expression only a dropped operand stated", () => {
    const base = own(`ex:e a srf:SumExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:d ; srf:rightOperand ex:n . ex:n a srf:RoundingExpression ; srf:resultDatatype xsd:decimal ; srf:roundingScale 2 ; srf:roundedOperand ex:i .`);
    const round = changeKind(base, at("e"), "round");
    expect(round.value(at("e"), SRF("roundedOperand"))).toBe(at("d"));
    // The nested rounding was the right operand, which a rounding has no place for, so it is gone from the graph and no finding says it is reached from nowhere.
    expect(round.has(at("n"))).toBe(false);
    const sum = changeKind(round, at("e"), "sum");
    expect(sum.value(at("e"), SRF("leftOperand"))).toBe(at("d"));
    expect(sum.value(at("e"), SRF("roundingScale"))).toBeUndefined();
    // Setting the same kind is no edit.
    expect(changeKind(base, at("e"), "sum")).toBe(base);
    expect(kindOfNode(sum, at("e"))?.id).toBe("sum");
  });

  it("sets an operand to an evidence binding of the contract", () => {
    const g = setOperand(surface, facility, slot("fm-expression", "leftOperand"), { kind: "evidence", iri: at("fm-margin") });
    expect(g.value(at("fm-expression"), SRF("leftOperand"))).toBe(at("fm-margin"));
    expect(g.objects(at("fm-expression"), SRF("leftOperand"))).toHaveLength(1);
  });

  it("offers an operand the contract's evidence and nothing else (srf:P7)", () => {
    const g = own(`ex:e a srf:SumExpression ; srf:resultDatatype xsd:decimal .`);
    const ctx = ownContext(g);
    const choices = operandChoices(g, ctx, { parent: at("e"), predicate: SRF("leftOperand") });
    // The subject, the result, the dependency, a binding that binds no property and another contract's binding are not offered.
    expect(choices.evidence.map((x) => x.iri)).toEqual([at("d"), at("f"), at("i"), at("s")]);
    for (const not of ["subject", "result", "dependency", "unbound", "other"]) {
      const refused = setOperand(g, ctx, { parent: at("e"), predicate: SRF("leftOperand") }, { kind: "evidence", iri: at(not) });
      expect(refused).toBe(g);
    }
    expect(setOperand(g, ctx, { parent: at("e"), predicate: SRF("leftOperand") }, { kind: "evidence", iri: at("d") }).value(at("e"), SRF("leftOperand"))).toBe(at("d"));
    // The facility's own: its commitment and its margin, and not its subject or its target.
    expect(facility.evidence.map((x) => x.iri).sort()).toEqual([at("fm-commitment"), at("fm-margin")]);
    // The expression's own slot takes no binding.
    expect(operandChoices(surface, facility, { parent: at("fm-target"), predicate: SRF("derivedAs") }).evidence).toEqual([]);
    expect(setOperand(surface, facility, { parent: at("fm-target"), predicate: SRF("derivedAs") }, { kind: "evidence", iri: at("fm-margin") })).toBe(surface);
    // No part of a node takes a predicate it does not have.
    expect(setOperand(surface, facility, { parent: at("fm-expression"), predicate: SRF("roundedOperand") }, { kind: "evidence", iri: at("fm-margin") })).toBe(surface);
  });

  it("sets an operand to a typed literal, with its value and datatype", () => {
    const g = setOperand(surface, facility, slot("fm-expression", "rightOperand"), { kind: "literal", value: "1.5", datatype: decimal });
    const node = g.value(at("fm-expression"), SRF("rightOperand"))!;
    expect(node.startsWith(EX)).toBe(true);
    expect(node).toBe(`${EX}FacilityMarginConstant`);
    expect(g.types(node)).toEqual([SRF("TypedLiteralExpression")]);
    expect(g.value(node, SRF("resultDatatype"))).toBe(decimal);
    const value = g.object(node, SRF("typedValue"))!;
    expect(value.value).toBe("1.5");
    expect("datatype" in value && value.datatype.value).toBe(decimal);
    // The binding it replaced stays in the contract, and the line reads the literal.
    expect(g.has(at("fm-margin"))).toBe(true);
    expect(statedBy(g, facility, label).line).toBe("commitment × 1.5 : decimal");
    // A value not written as its datatype, and a datatype that is not numeric, are refused.
    expect(setOperand(surface, facility, slot("fm-expression", "rightOperand"), { kind: "literal", value: "1.5", datatype: integer })).toBe(surface);
    expect(setOperand(surface, facility, slot("fm-expression", "rightOperand"), { kind: "literal", value: "x", datatype: XSD("string") })).toBe(surface);
    expect(validLexical("-2", integer) && validLexical(".5", decimal) && validLexical("1e3", XSD("double")) && validLexical("INF", XSD("float"))).toBe(true);
    expect(validLexical("1e3", decimal) || validLexical("", integer) || validLexical("1.", integer)).toBe(false);
  });

  it("sets an operand to a new nested expression, named in the baseline's namespace and stating no operand", () => {
    const g = setOperand(surface, facility, slot("fm-expression", "leftOperand"), { kind: "new", expression: "sum" });
    const node = g.value(at("fm-expression"), SRF("leftOperand"))!;
    expect(node).toBe(`${EX}FacilityMarginExpression`);
    expect(g.types(node)).toEqual([SRF("SumExpression")]);
    expect(g.value(node, SRF("resultDatatype"))).toBe(decimal);
    expect(g.objects(node, SRF("leftOperand"))).toEqual([]);
    expect(statedBy(g, facility, label).line).toBe("(… + …) × margin : decimal");
    // A second one is not named as the first, and neither repeats a name the baseline holds.
    const twice = setOperand(g, facility, slot("fm-expression", "rightOperand"), { kind: "new", expression: "product" });
    expect(twice.value(at("fm-expression"), SRF("rightOperand"))).toBe(`${EX}FacilityMarginExpression2`);
    const clash = setOperand(surface, { ...facility, name: "Facility" }, slot("fm-expression", "leftOperand"), { kind: "new", expression: "sum" });
    expect(clash.value(at("fm-expression"), SRF("leftOperand"))).toBe(`${EX}FacilityExpression`);
    const taken = setOperand(surface, { ...facility, name: "drawn", known: baseline.merge(Graph.parse(`@prefix ex: <${EX}> . ex:DrawnExpression a ex:Thing .`)) }, slot("fm-expression", "leftOperand"), { kind: "new", expression: "sum" });
    expect(taken.value(at("fm-expression"), SRF("leftOperand"))).toBe(`${EX}DrawnExpression2`);
  });

  it("removes a node, which leaves a placeholder, and the nested expressions only it stated", () => {
    const nested = setOperand(setOperand(surface, facility, slot("fm-expression", "leftOperand"), { kind: "new", expression: "sum" }), facility, { parent: `${EX}FacilityMarginExpression`, predicate: SRF("leftOperand") }, { kind: "new", expression: "round" });
    expect(nested.has(`${EX}FacilityMarginExpression2`)).toBe(true);
    const gone = removeAt(nested, facility, slot("fm-expression", "leftOperand"));
    expect(gone.objects(at("fm-expression"), SRF("leftOperand"))).toEqual([]);
    expect(gone.has(`${EX}FacilityMarginExpression`)).toBe(false);
    expect(gone.has(`${EX}FacilityMarginExpression2`)).toBe(false);
    expect(statedBy(gone, facility, label).line).toBe("… × margin : decimal");
    // An evidence binding is let go and stays in the contract, and the expression itself can be removed.
    const bare = removeAt(surface, facility, { parent: at("fm-target"), predicate: SRF("derivedAs") });
    expect(bare.object(at("fm-target"), SRF("derivedAs"))).toBeUndefined();
    expect(bare.has(at("fm-expression"))).toBe(false);
    expect(bare.has(at("fm-commitment"))).toBe(true);
    expect(statedBy(bare, facility, label).root).toBeUndefined();
    // Removing what is not there is no edit.
    expect(removeAt(bare, facility, { parent: at("fm-target"), predicate: SRF("derivedAs") })).toBe(bare);
  });

  it("states an expression where the binding states none, with every operand missing", () => {
    const bare = removeAt(surface, facility, { parent: at("fm-target"), predicate: SRF("derivedAs") });
    const g = addExpression(bare, facility, "round");
    const node = g.value(at("fm-target"), SRF("derivedAs"))!;
    expect(node).toBe(`${EX}FacilityMarginExpression`);
    expect(g.types(node)).toEqual([SRF("RoundingExpression")]);
    expect(g.value(node, SRF("resultDatatype"))).toBe(decimal);
    expect(statedBy(g, facility, label).line).toBe("round(…, …) : decimal");
    // It states one only where there is none, and only through a result-target binding.
    expect(addExpression(g, facility, "sum")).toBe(g);
    expect(addExpression(bare, { ...facility, binding: undefined }, "sum")).toBe(bare);
  });

  it("builds a rounding of a sum of the two evidence bindings, as the README's example states it", () => {
    const ctx = facility;
    let g = removeAt(surface, ctx, { parent: at("fm-target"), predicate: SRF("derivedAs") });
    g = addExpression(g, ctx, "round");
    const round = g.value(at("fm-target"), SRF("derivedAs"))!;
    g = setOperand(g, ctx, { parent: round, predicate: SRF("roundedOperand") }, { kind: "new", expression: "sum" });
    const sum = g.value(round, SRF("roundedOperand"))!;
    g = setOperand(g, ctx, { parent: sum, predicate: SRF("leftOperand") }, { kind: "evidence", iri: at("fm-commitment") });
    g = setOperand(g, ctx, { parent: sum, predicate: SRF("rightOperand") }, { kind: "evidence", iri: at("fm-margin") });
    g = setScale(g, round, 2);
    const stated = statedBy(g, ctx, label);
    expect(stated.line).toBe("round(commitment + margin, 2) : decimal");
    expect(marksOf(stated.typed)).toEqual([]);
  });

  it("sets a rounding's scale, which may be negative, as an integer", () => {
    const g = changeKind(surface, at("fm-expression"), "round");
    const two = setScale(g, at("fm-expression"), 2);
    expect(two.object(at("fm-expression"), SRF("roundingScale"))).toMatchObject({ value: "2", datatype: { value: integer } });
    const negative = setScale(two, at("fm-expression"), -2);
    expect(negative.objects(at("fm-expression"), SRF("roundingScale"))).toHaveLength(1);
    expect(negative.value(at("fm-expression"), SRF("roundingScale"))).toBe("-2");
    expect(statedBy(negative, facility, label).line).toBe("round(commitment, -2) : decimal");
    // Only a rounding has one, and a scale is whole.
    expect(setScale(surface, at("fm-expression"), 2)).toBe(surface);
    expect(setScale(g, at("fm-expression"), 1.5)).toBe(g);
  });

  it("sets a choice's comparison to one of the six", () => {
    const g = changeKind(surface, at("fm-expression"), "choice");
    expect(COMPARISONS.map((c) => c.symbol)).toEqual(["<", "≤", "=", "≠", "≥", ">"]);
    for (const { symbol, iri } of COMPARISONS) {
      const set = setComparison(g, at("fm-expression"), symbol);
      expect(set.value(at("fm-expression"), SRF("comparisonOperator"))).toBe(iri);
      expect(set.objects(at("fm-expression"), SRF("comparisonOperator"))).toHaveLength(1);
    }
    expect(statedBy(setComparison(g, at("fm-expression"), "≥"), facility, label).line).toBe("commitment ≥ margin ? … : … : decimal");
    expect(setComparison(g, at("fm-expression"), "~")).toBe(g);
    expect(setComparison(surface, at("fm-expression"), "<")).toBe(surface);
  });

  it("sets a node's result datatype from the four numeric ones", () => {
    for (const dt of [integer, decimal, XSD("float"), XSD("double")]) {
      expect(setResultDatatype(surface, at("fm-expression"), dt).value(at("fm-expression"), SRF("resultDatatype"))).toBe(dt);
    }
    expect(setResultDatatype(surface, at("fm-expression"), XSD("string"))).toBe(surface);
    // The result datatype of a quotient of two integers that the author states as integer is marked, and the mark offers the one that agrees.
    const g = setResultDatatype(changeKind(surface, at("fm-expression"), "quotient"), at("fm-expression"), integer);
    const t = statedBy(g, facility, label).typed;
    expect(t.marks.map((m) => [m.code, m.message, m.fix])).toEqual([["disagrees", "states integer, the operands give decimal", decimal], ["result", "the result binding states decimal", undefined]]);
  });

  it("sets a typed literal's value and datatype together, and a literal's result datatype is the datatype of its value", () => {
    const g = setOperand(surface, facility, slot("fm-expression", "rightOperand"), { kind: "literal", value: "2", datatype: integer });
    const node = g.value(at("fm-expression"), SRF("rightOperand"))!;
    const asDecimal = setResultDatatype(g, node, decimal);
    expect(asDecimal.value(node, SRF("resultDatatype"))).toBe(decimal);
    expect(asDecimal.object(node, SRF("typedValue"))).toMatchObject({ value: "2", datatype: { value: decimal } });
    expect(marksOf(statedBy(asDecimal, facility, label).typed)).toEqual([]);
    const edited = setLiteral(asDecimal, node, "2.25", decimal);
    expect(edited.value(node, SRF("typedValue"))).toBe("2.25");
    expect(setLiteral(edited, node, "2.25", integer)).toBe(edited);
    expect(setResultDatatype(edited, node, integer)).toBe(edited);
    expect(setLiteral(surface, at("fm-expression"), "2", integer)).toBe(surface);
  });
});

describe("no cycle (srf:P9)", () => {
  const base = own(`
    ex:e a srf:SumExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:a ; srf:rightOperand ex:b .
    ex:a a srf:ProductExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:d ; srf:rightOperand ex:c .
    ex:c a srf:RoundingExpression ; srf:resultDatatype xsd:decimal ; srf:roundingScale 2 ; srf:roundedOperand ex:d .
    ex:b a srf:RoundingExpression ; srf:resultDatatype xsd:decimal ; srf:roundingScale 2 ; srf:roundedOperand ex:d .`);
  const ctx = ownContext(base);

  it("never offers the node itself or one of its ancestors as an operand", () => {
    const choices = (parent: string, predicate: string) => operandChoices(base, ctx, { parent: at(parent), predicate: SRF(predicate) }).expressions.sort();
    // c sits under a under e. Its slot may take b, which reaches neither, and not e, a or c.
    expect(choices("c", "roundedOperand")).toEqual([at("b")]);
    // a may take b and c, which sit below or beside it, and not e or a.
    expect(choices("a", "rightOperand")).toEqual([at("b"), at("c")]);
    // The root has no ancestor, and may take every other node but not itself.
    expect(choices("e", "leftOperand")).toEqual([at("a"), at("b"), at("c")]);
    expect(wouldCycle(base, at("c"), at("e"))).toBe(true);
    expect(wouldCycle(base, at("c"), at("a"))).toBe(true);
    expect(wouldCycle(base, at("c"), at("c"))).toBe(true);
    expect(wouldCycle(base, at("c"), at("b"))).toBe(false);
  });

  it("refuses to set an operand to the node itself or an ancestor, and leaves the graph as it was", () => {
    const refuse = (parent: string, predicate: string, target: string) => setOperand(base, ctx, { parent: at(parent), predicate: SRF(predicate) }, { kind: "existing", iri: at(target) });
    expect(refuse("c", "roundedOperand", "c")).toBe(base);
    expect(refuse("c", "roundedOperand", "a")).toBe(base);
    expect(refuse("c", "roundedOperand", "e")).toBe(base);
    expect(refuse("a", "leftOperand", "e")).toBe(base);
    // A node of another contract, or a node that is no expression of this tree, is no operand.
    expect(refuse("c", "roundedOperand", "other")).toBe(base);
    expect(refuse("c", "roundedOperand", "nowhere")).toBe(base);
  });

  it("lets a node that causes no cycle be an operand where another expression stands, and drops nothing another node still states", () => {
    const g = setOperand(base, ctx, { parent: at("c"), predicate: SRF("roundedOperand") }, { kind: "existing", iri: at("b") });
    expect(g.value(at("c"), SRF("roundedOperand"))).toBe(at("b"));
    // The tree states b twice now, and drawing it does not loop.
    const t = statedBy(g, ctx, label);
    expect(marksOf(t.typed).map((m) => m.mark.code)).toEqual([]);
    expect(g.has(at("b"))).toBe(true);
    // Removing one place b stands leaves b, which the other still states.
    expect(removeAt(g, ctx, { parent: at("e"), predicate: SRF("rightOperand") }).has(at("b"))).toBe(true);
    expect(removeAt(removeAt(g, ctx, { parent: at("e"), predicate: SRF("rightOperand") }), ctx, { parent: at("c"), predicate: SRF("roundedOperand") }).has(at("b"))).toBe(false);
  });

  it("reads a cycle that was authored elsewhere as a placeholder and never fails", () => {
    const looped = own(`ex:e a srf:SumExpression ; srf:resultDatatype xsd:decimal ; srf:leftOperand ex:e ; srf:rightOperand ex:d .`);
    const t = statedBy(looped, ownContext(looped), label);
    expect(t.line).toBe("… + commitment : decimal");
    expect(t.typed.children[0].marks.map((m) => m.message)).toEqual(["e, which states itself is missing"]);
  });
});

describe("the editor never parses text", () => {
  it("has no function that takes the line, so an edit is always one of the structured ones", async () => {
    const edits = await import("./expressionEdit");
    expect(Object.keys(edits).filter((k) => /parse/i.test(k))).toEqual([]);
  });
});

it("types the facility derivation and each expression of the sample's contracts without a mark", () => {
  const every = [...surface.ofType(SRF("ProjectionContract"))].map((c) => contextOf(surface, c.value, EX, baseline)).filter((c) => c.binding && surface.object(c.binding, SRF("derivedAs")));
  expect(every.map((c) => c.contract)).toEqual([at("facility-margin-projection")]);
  for (const c of every) expect(marksOf(statedBy(surface, c, label).typed)).toEqual([]);
  expect(typeTree({ kind: "missing", part: "the expression" }).marks.map((m) => m.code)).toEqual(["missing"]);
});
