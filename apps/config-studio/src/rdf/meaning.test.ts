// SPDX-License-Identifier: MPL-2.0
// The contract builder's model of stated meaning and its review (rdf/meaning.ts), against the builder sample
// (`mise run build:config-studio-assets`) and the vocabulary the studio serves.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { CST, ELG, Graph, INS, QNT, XSD, literal } from "@lattice/authoring-domain";
import { DECISIONS, activitiesOf, addRole, decide, isWaiting, lexiconOf, mergeProposals, proposalsOf, propose, readsOf, relationKinds, relationsOf, rolesOf, say, termsFor, termsOf } from "./meaning";
import { split } from "./split";
import { Vocabulary } from "./vocabulary";

const assets = process.env.LATTICE_STUDIO_ASSETS ?? join(import.meta.dirname, "../../../../.build/config-studio");
const vocab = Vocabulary.parse(readFileSync(join(assets, "vocabulary.ttl"), "utf-8"));
const parts = split(Graph.parse(readFileSync(join(assets, "samples/builder.ttl"), "utf-8")));
const world = Object.values(parts).reduce((g, p) => g.merge(p), Graph.empty());
const lex = lexiconOf(world, vocab);

const F = "https://example.org/lattice/wording/facility-form/";
const M = "https://example.org/lattice/studio/meaning/";
const R = "https://example.org/lattice/studio/roles/";
const NS = "https://example.org/lattice/studio/";
const AT = "2026-10-28T12:00:00Z";

const kind = (name: string) => lex.kinds.get(INS(name))!;
const quadsOf = (g: Graph) => g.quads().map((q) => `${q.subject.value} ${q.predicate.value} ${q.object.termType}:${q.object.value}`).sort();
const entry = () => ({
  clause: F + "cl-12-1",
  name: "12.1",
  kind: kind("Obligation"),
  role: R + "Borrower",
  counter: R + "Lender",
  activity: activitiesOf(world, vocab, lex).find((a) => a.label === "Report")!.iri,
});

describe("what the vocabulary declares", () => {
  it("offers the relation kinds, with Prohibition and Power among them, and the verb each reads with", () => {
    const kinds = relationKinds(vocab);
    expect(kinds.map((k) => k.label)).toEqual(expect.arrayContaining(["Obligation", "Prohibition", "Permission", "Power"]));
    expect(kinds.find((k) => k.label === "Prohibition")).toMatchObject({ verb: "must not", obligation: true });
    expect(kinds.find((k) => k.label === "Power")).toMatchObject({ verb: "can", obligation: false });
  });

  it("offers the roles the workspace holds and the concepts of the activity scheme", () => {
    expect(rolesOf(world, lex).map((r) => r.label)).toEqual(["Agent", "Borrower", "Lender"]);
    expect(activitiesOf(world, vocab, lex).map((a) => a.label)).toEqual(expect.arrayContaining(["Pay", "Report", "Provide service"]));
  });

  it("writes a role into the baseline, minted once", () => {
    const made = addRole(parts.baseline, world, NS, "Guarantor");
    expect(made.graph.types(made.iri)).toEqual(expect.arrayContaining([expect.stringContaining("party#Role")]));
    expect(made.graph.value(made.iri, "http://www.w3.org/2000/01/rdf-schema#label")).toBe("Guarantor");
    expect(addRole(made.graph, world.merge(made.graph), NS, "Guarantor").iri).not.toBe(made.iri);
  });
});

describe("a clause's stated meaning in plain words", () => {
  it("reads the term a clause expresses and the relations under it, with roles shown as roles", () => {
    const terms = termsFor(parts.meaning, F + "cl-5-1");
    expect(terms).toEqual([M + "term-5-1"]);
    const relations = relationsOf(parts.meaning, lex, terms[0]);
    expect(relations.map((r) => say(r, lex))).toEqual(["Borrower must Pay Lender"]);
    expect(relationsOf(parts.meaning, lex).map((r) => say(r, lex)).sort()).toEqual(["Agent must Provide service Lender", "Borrower must Pay Lender"]);
  });

  it("says a power with its holder and counterparty, and a prohibition as must not", () => {
    const g = Graph.parse(`
      @prefix ins: <${INS("")}> . @prefix r: <${R}> . @prefix ex: <https://example.org/x/> .
      ex:t a ins:Term .
      ex:acc a ins:Power ; ins:arisesUnder ex:t ; ins:holder r:Lender ; ins:counterparty r:Borrower .
      ex:neg a ins:Prohibition ; ins:arisesUnder ex:t ; ins:obligor r:Borrower ; ins:obligee r:Lender .`);
    expect(relationsOf(g, lex, "https://example.org/x/t").map((r) => say(r, lex))).toEqual(["Lender can Borrower", "Borrower must not Lender"]);
  });

  it("reports that a clause has none, and that a proposal waits", () => {
    expect(termsFor(parts.meaning, F + "cl-12-1")).toEqual([]);
    expect(termsFor(parts.meaning, F + "cl-5-3")).toEqual([]);
    const waiting = proposalsOf(parts.review).filter(isWaiting);
    expect(waiting.map((p) => [p.span, p.proposer])).toEqual([[F + "cl-5-3", "sentence-forms"]]);
    expect(waiting[0].payload?.ofType(INS("Term")).map((t) => t.value)).toEqual([M + "term-5-3"]);
    expect(relationsOf(waiting[0].payload!, lex).map((r) => say(r, lex))).toEqual(["Borrower must Report Lender"]);
  });
});

describe("a manual proposal", () => {
  const written = propose(parts.meaning, parts.review, world, NS, entry(), lex, AT);

  it("is a confirmed proposal in the review part, as the contract says", () => {
    const p = written.proposal;
    const r = written.review;
    expect(r.types(p)).toEqual([CST("Proposal")]);
    expect(r.value(p, CST("span"))).toBe(F + "cl-12-1");
    expect(r.value(p, CST("proposer"))).toBe("manual");
    expect(r.value(p, CST("proposedAt"))).toBe(AT);
    expect(r.value(p, CST("decidedAt"))).toBe(AT);
    expect(r.value(p, CST("decision"))).toBe(CST("Confirm"));
    expect(r.objects(p, CST("proposes")).length).toBe(2);
    expect(r.objects(p, CST("proposes")).every((o) => written.meaning.has(o))).toBe(true);
    expect(r.quads(p, CST("proposedAt"))[0].object).toMatchObject({ datatype: { value: XSD("dateTime") } });
  });

  it("writes the same triples into the meaning part, creating the stated term the clause lacked", () => {
    const [term] = termsFor(written.meaning, F + "cl-12-1");
    expect(term).toBeDefined();
    expect(written.meaning.types(term)).toEqual(expect.arrayContaining([INS("Term"), INS("Template")]));
    const [relation] = relationsOf(written.meaning, lex, term);
    expect(say(relation, lex)).toBe("Borrower must Report Lender");
    expect(written.meaning.types(relation.iri)).toEqual(expect.arrayContaining([INS("Obligation"), INS("Template")]));
    // Nothing else changed: the sample's own meaning is intact.
    expect(termsOf(written.meaning)).toHaveLength(termsOf(parts.meaning).length + 1);
  });

  it("carries a payload that parses back to the triples it wrote", () => {
    const payload = Graph.parse(written.review.value(written.proposal, CST("payload"))!);
    const added = quadsOf(written.meaning).filter((q) => !quadsOf(parts.meaning).includes(q));
    expect(quadsOf(payload)).toEqual(added);
  });

  it("states only the relation when the clause already has a term, and mints each IRI once", () => {
    const again = propose(written.meaning, written.review, world.merge(written.meaning).merge(written.review), NS, { ...entry(), kind: kind("Prohibition") }, lex, AT);
    expect(termsFor(again.meaning, F + "cl-12-1")).toHaveLength(1);
    expect(again.review.objects(again.proposal, CST("proposes"))).toHaveLength(1);
    expect(again.proposal).not.toBe(written.proposal);
    const payload = Graph.parse(again.review.value(again.proposal, CST("payload"))!);
    expect(payload.ofType(INS("Term"))).toHaveLength(0);
    expect(relationsOf(payload, lex).map((r) => say(r, lex))).toEqual(["Borrower must not Report Lender"]);
  });

  it("uses a holder and a counterparty for a power", () => {
    const power = propose(parts.meaning, parts.review, world, NS, { ...entry(), kind: kind("Power") }, lex, AT);
    const [term] = termsFor(power.meaning, F + "cl-12-1");
    const [relation] = relationsOf(power.meaning, lex, term);
    expect(power.meaning.value(relation.iri, INS("holder"))).toBe(R + "Borrower");
    expect(power.meaning.value(relation.iri, INS("counterparty"))).toBe(R + "Lender");
  });
});

describe("the four decisions", () => {
  const waiting = proposalsOf(parts.review).find(isWaiting)!;

  it("lists them as ADR-A42 does", () => {
    expect(DECISIONS).toEqual(["Confirm", "Retarget", "Decline", "Defer"]);
  });

  it("confirm writes the payload into the meaning part and records the decision and time", () => {
    const out = decide(parts.meaning, parts.review, waiting.iri, "Confirm", AT);
    expect(termsFor(out.meaning, F + "cl-5-3")).toEqual([M + "term-5-3"]);
    expect(relationsOf(out.meaning, lex, M + "term-5-3").map((r) => say(r, lex))).toEqual(["Borrower must Report Lender"]);
    expect(out.review.value(waiting.iri, CST("decision"))).toBe(CST("Confirm"));
    expect(out.review.value(waiting.iri, CST("decidedAt"))).toBe(AT);
    expect(proposalsOf(out.review).filter(isWaiting)).toHaveLength(0);
    // The payload is kept with the proposal.
    expect(out.review.value(waiting.iri, CST("payload"))).toBe(parts.review.value(waiting.iri, CST("payload")));
  });

  it("retarget records the decision and writes the payload, to be corrected there", () => {
    const out = decide(parts.meaning, parts.review, waiting.iri, "Retarget", AT);
    expect(relationsOf(out.meaning, lex, M + "term-5-3").map((r) => say(r, lex))).toEqual(["Borrower must Report Lender"]);
    expect(out.review.value(waiting.iri, CST("decision"))).toBe(CST("Retarget"));
    expect(out.review.value(waiting.iri, CST("decidedAt"))).toBe(AT);
    expect(proposalsOf(out.review).filter(isWaiting)).toHaveLength(0);
  });

  it("retarget writes templates given as corrected", () => {
    const fixed = Graph.parse(waiting.payload!.toTurtle().replace("Report", "Pay"));
    const out = decide(parts.meaning, parts.review, waiting.iri, "Retarget", AT, fixed);
    expect(termsFor(out.meaning, F + "cl-5-3")).toEqual([M + "term-5-3"]);
    expect(out.review.value(waiting.iri, CST("decision"))).toBe(CST("Retarget"));
  });

  it.each(["Decline", "Defer"] as const)("%s records the decision only", (decision) => {
    const out = decide(parts.meaning, parts.review, waiting.iri, decision, AT);
    expect(out.meaning).toBe(parts.meaning);
    expect(out.review.value(waiting.iri, CST("decision"))).toBe(CST(decision));
    expect(out.review.value(waiting.iri, CST("decidedAt"))).toBe(AT);
    expect(termsFor(out.meaning, F + "cl-5-3")).toEqual([]);
  });

  it("refuses to confirm a proposal whose payload cannot be read", () => {
    const broken = parts.review.edit((e) => e.set(waiting.iri, CST("payload"), literal("not turtle {")));
    expect(proposalsOf(broken).find((p) => p.iri === waiting.iri)?.problem).toMatch(/cannot be read/);
    expect(() => decide(parts.meaning, broken, waiting.iri, "Confirm", AT)).toThrow();
  });
});

describe("what a term reads", () => {
  const g = Graph.parse(`
    @prefix ins: <${INS("")}> . @prefix ins-voc: <https://www.nebularis.org/neuro-semantic/lattice/instrument/vocab#> .
    @prefix pty: <https://www.nebularis.org/neuro-semantic/lattice/party#> .
    @prefix elg: <${ELG("")}> . @prefix qnt: <${QNT("")}> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix wrd: <https://www.nebularis.org/neuro-semantic/lattice/wording#> . @prefix ex: <https://example.org/x/> .
    ex:clause a wrd:Text .
    ex:t a ins:Term ; ins:expressedIn ex:clause .
    ex:ob a ins:Obligation ; ins:arisesUnder ex:t ; ins:obligor ex:b ; ins:obligee ex:l ; ins:activity ins-voc:Pay .
    ex:b a pty:Role ; rdfs:label "Borrower" . ex:l a pty:Role ; rdfs:label "Lender" . ex:other a pty:Role .
    ex:q a ins:Qualifier ; ins:arisesUnder ex:t ; ins:qualifies ex:ob ; ins:limit ex:cond .
    ex:cond a elg:IntervalCondition ; elg:onRange ex:rs .
    ex:rs a qnt:RangeSet ; qnt:hasRange ex:r1 .
    ex:r1 a qnt:Range .
    ex:unrelated a ins:Term ; ins:expressedIn ex:clause .
    ex:ob2 a ins:Obligation ; ins:arisesUnder ex:unrelated ; ins:obligor ex:other .`);
  const reads = readsOf(g, vocab, lexiconOf(g, vocab), "https://example.org/x/t");

  it("lists the roles, concepts, ranges and conditions its templates and qualifiers reach", () => {
    expect(reads.roles.map((r) => r.label)).toEqual(["Borrower", "Lender"]);
    expect(reads.concepts.map((c) => c.label)).toEqual(["Pay"]);
    expect(reads.conditions.map((c) => c.iri)).toEqual(["https://example.org/x/cond"]);
    // A condition reaches the ranges it names, and a range ends the path.
    expect(reads.ranges.map((r) => r.iri)).toEqual(["https://example.org/x/rs"]);
  });

  it("leaves out what only another term reaches, and never reaches into the wording", () => {
    expect(reads.roles.map((r) => r.iri)).not.toContain("https://example.org/x/other");
  });

  it("reads nothing for a term with no relation", () => {
    expect(readsOf(parts.meaning, vocab, lex, M + "term-5-3")).toEqual({ roles: [], concepts: [], ranges: [], conditions: [] });
  });
});

describe("merging a propose job's proposals", () => {
  const review = parts.review;
  const incoming = Graph.parse(`
    @prefix cst: <https://www.nebularis.org/neuro-semantic/lattice/config-studio#> .
    <urn:job:1:proposal/1> a cst:Proposal ; cst:span <${F}cl-12-1> ; cst:proposer "sentence-forms" ; cst:evidence "may operate" ; cst:proposerVersion "v1" ; cst:payload "" .
  `);

  it("adds a new proposal once, with its evidence and version, and leaves the existing ones as they were", () => {
    const once = mergeProposals(review, incoming);
    expect(once.added).toBe(1);
    expect(proposalsOf(once.review).find((p) => p.iri === "urn:job:1:proposal/1")).toMatchObject({ evidence: "may operate", proposerVersion: "v1" });
    for (const p of proposalsOf(review)) expect({ ...proposalsOf(once.review).find((q) => q.iri === p.iri), payload: 0 }).toEqual({ ...p, payload: 0 });
    const twice = mergeProposals(once.review, incoming);
    expect(twice.added).toBe(0);
    expect(quadsOf(twice.review)).toEqual(quadsOf(once.review));
  });
});
