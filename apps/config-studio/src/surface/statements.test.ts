// SPDX-License-Identifier: MPL-2.0
// The construction, join and expansion editors' pure part (SVA-S1 part 4): each edit with the triples it writes, each law's mark, what is never offered and what a
// refused edit does, over the facility sample's four statements and over statements written here.

import { readFileSync } from "node:fs";
import { Graph, SRF, XSD, type Term } from "@lattice/authoring-domain";
import { describe, expect, it } from "vitest";
import {
  addConstruction, addKeyBinding, addMemberNode, addWrite, constructionChoices, constructionMarks, readConstruction, removeConstruction, removeKeyBinding, removeWrite, setConstructedClass, setIdentity,
  setKeyMember, setMemberName, setWriteFrom, setWriteProperty,
} from "./constructionEdit";
import { addExpansion, expansionChoices, expansionMarks, propertiesRead, readExpansion, removeExpansion, setExpandsFrom, useNamedSource } from "./expansionEdit";
import { addJoin, addPair, joinChoices, joinMarks, linksOf, matchesOf, readJoin, removeJoin, removePair, setCardinality, setPairDatatype, setPairSide, setSecondCarrier } from "./joinEdit";
import { replaceNamedSource } from "./pathmode";
import { removeUnreadEvidence, statementContext, unreadEvidence } from "./statement";
import { drawContract } from "./drawing";
import { ontologyOf, termsOf } from "./terms";

const sample = (n: string) => Graph.parse(readFileSync(new URL(`../../../../contracts/config-studio/samples/${n}`, import.meta.url), "utf-8"));
const surface = sample("facility-surface.ttl");
const baseline = sample("lending-baseline.ttl").merge(sample("facility-baseline.ttl"));
const EX = "https://example.org/lending#";
const at = (n: string) => `${EX}${n}`;
const ctxOf = (g: Graph, contract: string) => statementContext(g, at(contract), EX, baseline);
const codes = (marks: { code: string }[]) => marks.map((m) => m.code);
const has = (g: Graph, s: string, p: string, o?: string | Term) => g.quads(s, p, o ?? null).length > 0;
const count = (g: Graph, s: string, p: string) => g.objects(s, p).length;

const EXPOSURE = "borrower-exposure-projection";
const SCHEDULE = "drawdown-schedule-projection";
const BRANCH = "facility-branch-projection";
const REFINANCING = "facility-refinancing-projection";
const COVENANT = "facility-covenant-test-projection";

describe("the facility sample's four statements carry no mark", () => {
  it("a construction, a join, an expansion and a node for each member", () => {
    for (const c of [EXPOSURE, SCHEDULE, COVENANT]) expect(constructionMarks(surface, ctxOf(surface, c)), c).toEqual([]);
    expect(joinMarks(surface, ctxOf(surface, BRANCH))).toEqual([]);
    for (const c of [REFINANCING, COVENANT]) expect(expansionMarks(surface, ctxOf(surface, c)), c).toEqual([]);
    // A contract that states none of a kind has no mark of that kind either, apart from the statement it is missing.
    expect(joinMarks(surface, ctxOf(surface, EXPOSURE))).toEqual([]);
    expect(expansionMarks(surface, ctxOf(surface, BRANCH))).toEqual([]);
  });
});

describe("a graph construction", () => {
  const bare = removeConstruction(surface, ctxOf(surface, EXPOSURE));

  it("is removed with its node and the values it writes, and the contract is marked for stating none", () => {
    expect(has(bare, at("be-link"), SRF("constructedAs"))).toBe(false);
    expect(bare.quads(at("be-node"), null, null)).toEqual([]);
    // The blank node of the written value went with it, so nothing is left that nothing states.
    expect(bare.quads(null, SRF("writesProperty"), null)).toEqual(bare.quads(null, SRF("writesProperty"), null).filter((q) => q.subject.value !== undefined));
    expect(surface.quads(null, SRF("writesProperty"), null).length - bare.quads(null, SRF("writesProperty"), null).length).toBe(1);
    expect(codes(constructionMarks(bare, ctxOf(bare, EXPOSURE)))).toEqual(["required"]);
    expect(removeConstruction(bare, ctxOf(bare, EXPOSURE))).toBe(bare);
  });

  it("is added as a minted node that is typed and states a node for each instance, the identity that merges nothing", () => {
    const ctx = ctxOf(bare, EXPOSURE);
    const g = addConstruction(bare, ctx);
    const node = g.value(at("be-link"), SRF("constructedAs"))!;
    expect(node).toBe(at("BorrowerExposureNode"));
    expect(g.types(node)).toEqual([SRF("ConstructedNode")]);
    expect(g.value(node, SRF("nodeIdentity"))).toBe(SRF("PerInstance"));
    expect(g.quads(node, null, null)).toHaveLength(2);
    // The class and the values are the author's, and the contract is marked for them until they are stated.
    expect(codes(constructionMarks(g, ctxOf(g, EXPOSURE)))).toEqual(["class", "writes"]);
    // A second one is refused, and so is one for a contract of another kind or one that states no result binding.
    expect(addConstruction(g, ctxOf(g, EXPOSURE))).toBe(g);
    expect(addConstruction(surface, ctxOf(surface, BRANCH))).toBe(surface);
    expect(addConstruction(surface, ctxOf(surface, "facility-margin-projection"))).toBe(surface);
  });

  it("states the class as an IRI, marks one the ontology does not declare, and refuses a term that is no IRI", () => {
    const g0 = addConstruction(bare, ctxOf(bare, EXPOSURE));
    const picked = setConstructedClass(g0, ctxOf(g0, EXPOSURE), at("BorrowerExposure"));
    expect(picked.value(at("BorrowerExposureNode"), SRF("constructedClass"))).toBe(at("BorrowerExposure"));
    const typedIn = setConstructedClass(picked, ctxOf(picked, EXPOSURE), "https://example.org/other#Thing");
    expect(count(typedIn, at("BorrowerExposureNode"), SRF("constructedClass"))).toBe(1);
    expect(typedIn.value(at("BorrowerExposureNode"), SRF("constructedClass"))).toBe("https://example.org/other#Thing");
    const terms = termsOf(ontologyOf(baseline, []));
    expect(terms.declared("class", at("BorrowerExposure"))).toBe(true);
    expect(terms.declared("class", "https://example.org/other#Thing")).toBe(false);
    for (const bad of ["not an iri", "", "a b:c", "<x:y>"]) expect(setConstructedClass(picked, ctxOf(picked, EXPOSURE), bad)).toBe(picked);
    expect(setConstructedClass(picked, ctxOf(picked, EXPOSURE), at("BorrowerExposure"))).toBe(picked);
    expect(count(setConstructedClass(picked, ctxOf(picked, EXPOSURE), undefined), at("BorrowerExposureNode"), SRF("constructedClass"))).toBe(0);
  });

  it("is by key only with a required-evidence binding that binds a property for each part, and a node for each instance names none", () => {
    const ctx0 = ctxOf(surface, EXPOSURE);
    const byKey = readConstruction(surface, ctx0)!;
    expect(byKey.identity).toBe("ByKey");
    expect(byKey.keyBindings).toEqual([at("be-borrower")]);
    // Nothing is offered for a key while the node is for each instance, and a required binding is offered for one that is by key, beyond the parts it has.
    const perInstance = setIdentity(surface, ctx0, "PerInstance");
    expect(count(perInstance, at("be-node"), SRF("keyBinding"))).toBe(0);
    expect(perInstance.value(at("be-node"), SRF("nodeIdentity"))).toBe(SRF("PerInstance"));
    expect(constructionChoices(perInstance, ctxOf(perInstance, EXPOSURE)).keys).toEqual([]);
    expect(addKeyBinding(perInstance, ctxOf(perInstance, EXPOSURE), at("be-borrower"))).toBe(perInstance);
    // Back to a key, the node is marked for naming no part, and the only binding that can be one is the required evidence of the contract.
    const keyed = setIdentity(perInstance, ctxOf(perInstance, EXPOSURE), "ByKey");
    expect(codes(constructionMarks(keyed, ctxOf(keyed, EXPOSURE)))).toEqual(["key-parts"]);
    expect(constructionChoices(keyed, ctxOf(keyed, EXPOSURE)).keys.map((k) => k.iri)).toEqual([at("be-borrower")]);
    // The subject, the result and a binding of no property are never parts, and a candidate-evidence binding is not one (srf:P13).
    const withCandidate = keyed.merge(Graph.parse(`@prefix srf: <${SRF("")}> . @prefix ex: <${EX}> .
      ex:be-extra a srf:ProjectionRoleBinding ; srf:roleKind srf:CandidateEvidenceRole ; srf:bindsProperty ex:legalName .
      ex:be-unbound a srf:ProjectionRoleBinding ; srf:roleKind srf:RequiredEvidenceRole .
      ${at("borrower-exposure-projection").replace(EX, "ex:")} srf:hasRoleBinding ex:be-extra , ex:be-unbound .`));
    const ctx = ctxOf(withCandidate, EXPOSURE);
    expect(constructionChoices(withCandidate, ctx).keys.map((k) => k.iri)).toEqual([at("be-borrower")]);
    for (const refused of [at("be-extra"), at("be-unbound"), at("be-subject"), at("be-link"), at("fm-margin"), "https://example.org/nowhere#x"]) expect(addKeyBinding(withCandidate, ctx, refused), refused).toBe(withCandidate);
    const named = addKeyBinding(withCandidate, ctx, at("be-borrower"));
    expect(named.objects(at("be-node"), SRF("keyBinding")).map((t) => t.value)).toEqual([at("be-borrower")]);
    expect(constructionMarks(named, ctxOf(named, EXPOSURE))).toEqual([]);
    expect(removeKeyBinding(named, ctxOf(named, EXPOSURE), at("be-borrower")).objects(at("be-node"), SRF("keyBinding"))).toEqual([]);
  });

  it("marks a key part that is not required evidence, a node for each instance that names a key, and a node by key that names none", () => {
    const candidate = surface.edit((e) => e.setAll(at("be-borrower"), SRF("roleKind"), [{ termType: "NamedNode", value: SRF("CandidateEvidenceRole") } as never]));
    expect(codes(constructionMarks(candidate, ctxOf(candidate, EXPOSURE)))).toEqual(["key-evidence"]);
    const named = surface.edit((e) => e.add(at("be-node"), SRF("nodeIdentity"), at("be-subject")));
    expect(codes(constructionMarks(named, ctxOf(named, EXPOSURE)))).toContain("identity");
    const keyless = surface.edit((e) => e.setAll(at("be-node"), SRF("keyBinding"), []));
    expect(codes(constructionMarks(keyless, ctxOf(keyless, EXPOSURE)))).toEqual(["key-parts"]);
    const both = setIdentity(surface, ctxOf(surface, EXPOSURE), "PerInstance").edit((e) => e.add(at("be-node"), SRF("keyBinding"), at("be-borrower")));
    expect(codes(constructionMarks(both, ctxOf(both, EXPOSURE)))).toEqual(["key-forbidden"]);
  });

  it("writes each value once, read from an evidence binding of the contract, and refuses what the laws forbid", () => {
    const ctx = ctxOf(surface, SCHEDULE);
    const before = readConstruction(surface, ctx)!;
    expect(before.writes.map((w) => [w.property, w.binding])).toEqual([[at("scheduledAmount"), at("ds-amount")], [at("scheduleStart"), at("ds-date")]]);
    const choices = constructionChoices(surface, ctx);
    expect(choices.from.map((e) => e.iri)).toEqual([at("ds-amount"), at("ds-date")]);
    expect(choices.identities).toEqual(["PerInstance", "ByKey"]);
    expect(choices.member).toEqual({ key: false, name: false, value: false });
    // A value is added with a minted node, the property it is written as and the binding it is read from.
    const g = addWrite(surface, ctx, at("note"), { binding: at("ds-amount") });
    const written = readConstruction(g, ctxOf(g, SCHEDULE))!.writes.find((w) => w.property === at("note"))!;
    expect(written.binding).toBe(at("ds-amount"));
    expect(written.term.value.startsWith(EX)).toBe(true);
    expect(g.quads(written.term, null, null)).toHaveLength(2);
    expect(constructionMarks(g, ctxOf(g, SCHEDULE))).toEqual([]);
    // A property written already, a binding that is not evidence of the contract, the subject, the member of no expansion and a term that is no IRI are refused.
    for (const refused of [
      addWrite(surface, ctx, at("scheduledAmount"), { binding: at("ds-date") }),
      addWrite(surface, ctx, at("note"), { binding: at("fm-margin") }),
      addWrite(surface, ctx, at("note"), { binding: at("ds-subject") }),
      addWrite(surface, ctx, at("note"), { binding: at("ds-link") }),
      addWrite(surface, ctx, at("note"), { member: true }),
      addWrite(surface, ctx, "not an iri", { binding: at("ds-date") }),
    ]) expect(refused).toBe(surface);
    // A value changes its property and its source, and is removed.
    const key = written.key;
    const moved = setWriteProperty(g, ctxOf(g, SCHEDULE), key, at("noteOf"));
    expect(readConstruction(moved, ctxOf(moved, SCHEDULE))!.writes.map((w) => w.property)).toContain(at("noteOf"));
    expect(setWriteProperty(g, ctxOf(g, SCHEDULE), key, at("scheduledAmount"))).toBe(g);
    const read = setWriteFrom(g, ctxOf(g, SCHEDULE), key, { binding: at("ds-date") });
    expect(readConstruction(read, ctxOf(read, SCHEDULE))!.writes.find((w) => w.key === key)!.binding).toBe(at("ds-date"));
    expect(setWriteFrom(g, ctxOf(g, SCHEDULE), key, { member: true })).toBe(g);
    expect(removeWrite(g, ctxOf(g, SCHEDULE), key).quads(written.term, null, null)).toEqual([]);
    expect(readConstruction(removeWrite(g, ctxOf(g, SCHEDULE), key), ctxOf(g, SCHEDULE))!.writes).toHaveLength(2);
  });

  it("marks a value that is read from nothing or from both, from a term that is no evidence, or written twice", () => {
    const w = (g: Graph, ctx = ctxOf(g, SCHEDULE)) => codes(constructionMarks(g, ctx));
    const [first, second] = readConstruction(surface, ctxOf(surface, SCHEDULE))!.writes;
    const neither = surface.edit((e) => e.setAll(first.term, SRF("fromBinding"), []));
    expect(w(neither)).toEqual(["source"]);
    const both = surface.edit((e) => e.add(first.term, SRF("fromMember"), { termType: "Literal", value: "true", datatype: { value: XSD("boolean") } } as never));
    expect(w(both)).toContain("source");
    const stray = surface.edit((e) => e.setAll(first.term, SRF("fromBinding"), [{ termType: "NamedNode", value: at("ds-subject") } as never]));
    expect(w(stray)).toEqual(["evidence"]);
    const twice = surface.edit((e) => e.setAll(second.term, SRF("writesProperty"), [{ termType: "NamedNode", value: first.property! } as never]));
    expect(w(twice)).toEqual(["property-once", "property-once"]);
    const none = surface.edit((e) => e.setAll(first.term, SRF("writesProperty"), []));
    expect(w(none)).toEqual(["property"]);
    const empty = surface.edit((e) => e.setAll(at("ds-node"), SRF("writes"), []));
    expect(w(empty)).toEqual(["writes"]);
  });

  it("is marked where its result-target binding binds no link, and where it is stated by a contract of another kind", () => {
    const unlinked = surface.edit((e) => e.setAll(at("ds-link"), SRF("bindsProperty"), []));
    expect(codes(constructionMarks(unlinked, ctxOf(unlinked, SCHEDULE)))).toEqual(["link-property"]);
    const placed = surface.edit((e) => e.add(at("fb-link"), SRF("constructedAs"), at("ds-node")));
    // The node's values read bindings of another contract, which this one does not hold, so each is marked too.
    expect(codes(constructionMarks(placed, ctxOf(placed, BRANCH)))).toEqual(["placement", "evidence", "evidence"]);
  });
});

describe("a node for each member", () => {
  const ctx = ctxOf(surface, COVENANT);
  const plain = removeConstruction(surface, ctx);

  it("is read with its key that names the member, its class and the value it writes from the member", () => {
    const c = readConstruction(surface, ctx)!;
    expect(c).toMatchObject({ class: at("CovenantTest"), identity: "ByKey", keyMember: true, besideExpansion: true });
    expect(c.keyBindings).toEqual([at("ct-reference")]);
    expect(c.writes.map((w) => [w.property, w.member])).toEqual([[at("testedFacilityReference"), false], [at("testsCovenant"), true]]);
    expect(drawContract(surface, at(COVENANT), termsOf(ontologyOf(baseline, []))).kind).toBe("member");
  });

  it("is added beside the expansion statement on the one binding, as a node for each instance and member, and only there", () => {
    expect(readExpansion(plain, ctxOf(plain, COVENANT))!.hasNode).toBe(false);
    expect(drawContract(plain, at(COVENANT), termsOf(ontologyOf(baseline, []))).kind).toBe("expansion");
    const g = addMemberNode(plain, ctxOf(plain, COVENANT));
    const node = g.value(at("ct-link"), SRF("constructedAs"))!;
    expect(node).toBe(at("FacilityCovenantTestMemberNode"));
    expect(g.value(node, SRF("nodeIdentity"))).toBe(SRF("PerInstance"));
    expect(g.value(at("ct-link"), SRF("expandedAs"))).toBe(at("ct-expansion"));
    // An expansion without its statement, a contract that is not an expansion and a node already stated are refused.
    expect(addMemberNode(g, ctxOf(g, COVENANT))).toBe(g);
    expect(addMemberNode(surface, ctxOf(surface, EXPOSURE))).toBe(surface);
    const noStatement = plain.edit((e) => e.setAll(at("ct-link"), SRF("expandedAs"), []));
    expect(addMemberNode(noStatement, ctxOf(noStatement, COVENANT))).toBe(noStatement);
    // A plain construction is never offered the member.
    expect(constructionChoices(surface, ctxOf(surface, EXPOSURE)).identities).not.toContain("MemberNode");
    expect(setIdentity(surface, ctxOf(surface, EXPOSURE), "MemberNode")).toBe(surface);
  });

  it("is a node for each member with a stable name from a property of the member, a key part and a value of the member", () => {
    const g0 = addMemberNode(plain, ctxOf(plain, COVENANT));
    const c0 = ctxOf(g0, COVENANT);
    expect(constructionChoices(g0, c0).member).toEqual({ key: false, name: true, value: true });
    const named = setMemberName(g0, c0, at("covenantName"));
    expect(named.value(at("FacilityCovenantTestMemberNode"), SRF("memberName"))).toBe(at("covenantName"));
    expect(setMemberName(named, ctxOf(named, COVENANT), at("covenantName"))).toBe(named);
    expect(count(setMemberName(named, ctxOf(named, COVENANT), undefined), at("FacilityCovenantTestMemberNode"), SRF("memberName"))).toBe(0);
    expect(setMemberName(named, ctxOf(named, COVENANT), "not an iri")).toBe(named);
    // The key member is offered to a node by key alone, and is written as the boolean true.
    expect(setKeyMember(named, ctxOf(named, COVENANT), true)).toBe(named);
    const keyed = setIdentity(named, ctxOf(named, COVENANT), "ByKey");
    expect(constructionChoices(keyed, ctxOf(keyed, COVENANT)).member).toEqual({ key: true, name: true, value: true });
    expect(codes(constructionMarks(keyed, ctxOf(keyed, COVENANT)))).toEqual(["class", "writes", "key-parts"]);
    const withMember = setKeyMember(keyed, ctxOf(keyed, COVENANT), true);
    expect(withMember.quads(at("FacilityCovenantTestMemberNode"), SRF("keyMember"), null)[0].object.value).toBe("true");
    expect(withMember.quads(at("FacilityCovenantTestMemberNode"), SRF("keyMember"), null)[0].object).toMatchObject({ datatype: { value: XSD("boolean") } });
    // A value is read from the member, and from a binding in its place, never both (srf:P25).
    const written = addWrite(withMember, ctxOf(withMember, COVENANT), at("testsCovenant"), { member: true });
    const row = readConstruction(written, ctxOf(written, COVENANT))!.writes[0];
    expect(row).toMatchObject({ member: true, binding: undefined });
    const switched = setWriteFrom(written, ctxOf(written, COVENANT), row.key, { binding: at("ct-reference") });
    expect(readConstruction(switched, ctxOf(switched, COVENANT))!.writes[0]).toMatchObject({ member: false, binding: at("ct-reference") });
    expect(count(switched, row.term.value, SRF("fromMember"))).toBe(0);
    expect(constructionMarks(switched, ctxOf(switched, COVENANT)).map((m) => m.code)).not.toContain("source");
  });

  it("is the member itself only with no key part, no key member and no name, and choosing it takes them out", () => {
    const g = setIdentity(surface, ctx, "MemberNode");
    expect(g.value(at("ct-node"), SRF("nodeIdentity"))).toBe(SRF("MemberNode"));
    for (const p of ["keyBinding", "keyMember", "memberName"]) expect(count(g, at("ct-node"), SRF(p)), p).toBe(0);
    expect(constructionChoices(g, ctxOf(g, COVENANT)).member).toEqual({ key: false, name: false, value: true });
    expect(constructionChoices(g, ctxOf(g, COVENANT)).keys).toEqual([]);
    expect(setMemberName(g, ctxOf(g, COVENANT), at("covenantName"))).toBe(g);
    expect(setKeyMember(g, ctxOf(g, COVENANT), true)).toBe(g);
    expect(addKeyBinding(g, ctxOf(g, COVENANT), at("ct-reference"))).toBe(g);
    expect(constructionMarks(g, ctxOf(g, COVENANT))).toEqual([]);
    // The marks name what the member itself may not carry.
    const bad = g.edit((e) => e.add(at("ct-node"), SRF("memberName"), at("covenantName")));
    expect(codes(constructionMarks(bad, ctxOf(bad, COVENANT)))).toEqual(["member-node"]);
  });

  it("is marked where the member is spoken of by a node that is stated beside no expansion", () => {
    const stray = surface.edit((e) => e.add(at("be-node"), SRF("memberName"), at("covenantName")));
    expect(codes(constructionMarks(stray, ctxOf(stray, EXPOSURE)))).toEqual(["member-placement"]);
    const asMember = surface.edit((e) => e.add(at("ds-node"), SRF("keyMember"), { termType: "Literal", value: "true", datatype: { value: XSD("boolean") } } as never));
    expect(codes(constructionMarks(asMember, ctxOf(asMember, SCHEDULE)))).toContain("member-placement");
  });

  it("is removed with the construction and leaves the expansion", () => {
    expect(plain.quads(at("ct-node"), null, null)).toEqual([]);
    expect(has(plain, at("ct-link"), SRF("expandedAs"), at("ct-expansion"))).toBe(true);
    expect(expansionMarks(plain, ctxOf(plain, COVENANT))).toEqual([]);
  });
});

describe("a join", () => {
  const ctx = ctxOf(surface, BRANCH);

  it("is read with its pair, its second carrier and the defaults it leaves out, which the vocabulary gives", () => {
    const j = readJoin(surface, ctx)!;
    expect(j.pairs.map((p) => [p.left, p.right])).toEqual([[at("fb-code"), at("fb-match")]]);
    expect(j.secondCarrier).toBe(at("Branch"));
    expect(j.evidenceKind).toBe("required");
    expect([matchesOf(j), linksOf(j)]).toEqual([undefined, undefined]);
  });

  it("is added as a minted statement that states nothing, and removed with its pairs, its bindings staying and marked as read by nothing", () => {
    const bare = removeJoin(surface, ctx);
    expect(has(bare, at("fb-link"), SRF("joinedAs"))).toBe(false);
    for (const b of ["fb-code", "fb-match"]) expect(has(bare, at(BRANCH), SRF("hasRoleBinding"), at(b)), b).toBe(true);
    expect(unreadEvidence(bare, at(BRANCH)).map((i) => i.focus).sort()).toEqual([at("fb-code"), at("fb-match")]);
    expect(has(bare, at(BRANCH), SRF("hasRoleBinding"), at("fb-link"))).toBe(true);
    expect(codes(joinMarks(bare, ctxOf(bare, BRANCH)))).toEqual(["required"]);
    const added = addJoin(bare, ctxOf(bare, BRANCH));
    const node = added.value(at("fb-link"), SRF("joinedAs"))!;
    expect(node).toBe(at("FacilityBranchJoin"));
    expect(added.quads(node, null, null)).toHaveLength(1);
    expect(codes(joinMarks(added, ctxOf(added, BRANCH)))).toEqual(["pairs"]);
    expect(addJoin(added, ctxOf(added, BRANCH))).toBe(added);
    expect(addJoin(surface, ctxOf(surface, EXPOSURE))).toBe(surface);
    expect(removeJoin(bare, ctxOf(bare, BRANCH))).toBe(bare);
  });

  it("adds a composite key pair, a left binding on the first carrier and a right on the second, each reading a property, with the datatype the right states", () => {
    const choices = joinChoices(surface, ctx);
    expect(choices.left.map((e) => e.iri)).toEqual([at("fb-code")]);
    expect(choices.right.map((e) => e.iri)).toEqual([at("fb-match")]);
    expect(choices.kind).toBe("required");
    const g = addPair(surface, ctx, { left: { property: at("facilityReference") }, right: { property: at("branchCode") }, datatype: XSD("string") });
    const j = readJoin(g, ctxOf(g, BRANCH))!;
    expect(j.pairs).toHaveLength(2);
    const added = j.pairs.find((p) => p.left !== at("fb-code"))!;
    expect(added.left).toBe(at("FacilityBranchFacilityReference"));
    expect(added.right).toBe(at("FacilityBranchBranchCode"));
    // Each new binding is a required-evidence binding of the contract, as the statement's are, and the right one names the second carrier and the datatype.
    expect(g.value(added.left!, SRF("roleKind"))).toBe(SRF("RequiredEvidenceRole"));
    expect(g.value(added.left!, SRF("bindsProperty"))).toBe(at("facilityReference"));
    expect(g.objects(added.left!, SRF("bindsCarrier"))).toEqual([]);
    expect(g.value(added.right!, SRF("bindsCarrier"))).toBe(at("Branch"));
    expect(g.value(added.right!, SRF("bindsDatatype"))).toBe(XSD("string"));
    expect(has(g, at(BRANCH), SRF("hasRoleBinding"), added.left!)).toBe(true);
    expect(has(g, at(BRANCH), SRF("hasRoleBinding"), added.right!)).toBe(true);
    expect(joinMarks(g, ctxOf(g, BRANCH))).toEqual([]);
    // The facility sample's contracts read every evidence binding they state.
    expect(unreadEvidence(surface, at(BRANCH))).toEqual([]);
    // Removing the pair takes the pair alone. Its two bindings stay, so an author still wiring them up loses nothing, and each is marked as read by nothing.
    const back = removePair(g, ctxOf(g, BRANCH), added.key);
    expect(readJoin(back, ctxOf(back, BRANCH))!.pairs).toHaveLength(1);
    expect(has(back, at(BRANCH), SRF("hasRoleBinding"), added.left!)).toBe(true);
    expect(back.value(added.right!, SRF("bindsCarrier"))).toBe(at("Branch"));
    const unread = unreadEvidence(back, at(BRANCH));
    expect(unread.map((i) => i.focus).sort()).toEqual([added.left!, added.right!].sort());
    expect(unread.every((i) => i.severity === "Info" && i.code === "unread-evidence" && /excludes an instance that lacks the value/.test(i.message))).toBe(true);
    // A pair that reads them again clears the marks.
    const again = addPair(back, ctxOf(back, BRANCH), { left: { binding: added.left! }, right: { binding: added.right! } });
    expect(unreadEvidence(again, at(BRANCH))).toEqual([]);
    // Removing the unused bindings in one edit takes both and leaves the facility's join as it was.
    const tidy = removeUnreadEvidence(back, at(BRANCH));
    expect(tidy.toTurtle()).toBe(surface.toTurtle());
    expect(removeUnreadEvidence(surface, at(BRANCH))).toBe(surface);
  });

  it("keeps the binding a pair stood on when one of its sides is changed, and marks it as read by nothing", () => {
    const g = addPair(surface, ctx, { left: { property: at("facilityReference") }, right: { property: at("branchCode") } });
    const added = readJoin(g, ctxOf(g, BRANCH))!.pairs.find((p) => p.left !== at("fb-code"))!;
    const changed = setPairSide(g, ctxOf(g, BRANCH), added.key, "left", { property: at("bookingBranchCode") });
    expect(has(changed, at(BRANCH), SRF("hasRoleBinding"), added.left!)).toBe(true);
    expect(unreadEvidence(changed, at(BRANCH)).map((i) => i.focus)).toEqual([added.left!]);
  });

  it("says that a candidate-evidence binding read by nothing has no effect", () => {
    const g = surface.edit((e) => {
      e.add(at("fb-spare"), "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", SRF("ProjectionRoleBinding"));
      e.add(at("fb-spare"), SRF("roleKind"), SRF("CandidateEvidenceRole"));
      e.add(at("fb-spare"), SRF("bindsProperty"), at("facilityReference"));
      e.add(at(BRANCH), SRF("hasRoleBinding"), at("fb-spare"));
    });
    const [mark] = unreadEvidence(g, at(BRANCH));
    expect(mark.focus).toBe(at("fb-spare"));
    expect(mark.message).toMatch(/has no effect/);
  });

  it("offers a left side of the contract's own carrier and a right side of the second, of the statement's evidence kind, and refuses a side the laws forbid", () => {
    const g = surface.edit((e) => {
      e.add(at("fb-other"), "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", SRF("ProjectionRoleBinding"));
      e.add(at("fb-other"), SRF("roleKind"), SRF("CandidateEvidenceRole"));
      e.add(at("fb-other"), SRF("bindsProperty"), at("facilityReference"));
      e.add(at(BRANCH), SRF("hasRoleBinding"), at("fb-other"));
    });
    const c = ctxOf(g, BRANCH);
    // A candidate-evidence binding is not offered to a statement on required evidence (srf:P17), and a right binding is not a left one (srf:P16).
    expect(joinChoices(g, c).left.map((e) => e.iri)).toEqual([at("fb-code")]);
    expect(addPair(g, c, { left: { binding: at("fb-other") }, right: { binding: at("fb-match") } })).toBe(g);
    expect(addPair(g, c, { left: { binding: at("fb-match") }, right: { binding: at("fb-match") } })).toBe(g);
    expect(addPair(g, c, { left: { binding: at("fb-code") }, right: { binding: at("fb-code") } })).toBe(g);
    expect(addPair(g, c, { left: { binding: at("fb-subject") }, right: { binding: at("fb-match") } })).toBe(g);
    expect(addPair(g, c, { left: { binding: at("fb-link") }, right: { binding: at("fb-match") } })).toBe(g);
    // A new right side names the second carrier, which is not the contract's own and is the one the statement has.
    expect(addPair(g, c, { left: { property: at("facilityReference") }, right: { property: at("branchCode") }, carrier: at("Facility") })).toBe(g);
    expect(addPair(g, c, { left: { property: at("facilityReference") }, right: { property: at("branchCode") }, carrier: at("Lender") })).toBe(g);
    expect(addPair(g, c, { left: { property: "not an iri" }, right: { property: at("branchCode") } })).toBe(g);
    // The same pair of existing bindings is offered again, which a second pair may read.
    const again = addPair(g, c, { left: { binding: at("fb-code") }, right: { binding: at("fb-match") } });
    expect(readJoin(again, ctxOf(again, BRANCH))!.pairs).toHaveLength(2);
  });

  it("sets the datatype the left value is cast to on the right binding, and returns it to none", () => {
    const [pair] = readJoin(surface, ctx)!.pairs;
    const cast = setPairDatatype(surface, ctx, pair.key, XSD("string"));
    expect(cast.value(at("fb-match"), SRF("bindsDatatype"))).toBe(XSD("string"));
    expect(setPairDatatype(cast, ctxOf(cast, BRANCH), pair.key, XSD("string"))).toBe(cast);
    expect(count(setPairDatatype(cast, ctxOf(cast, BRANCH), pair.key, undefined), at("fb-match"), SRF("bindsDatatype"))).toBe(0);
    expect(setPairDatatype(surface, ctx, pair.key, "not an iri")).toBe(surface);
    // A left value that states a datatype with none to cast it to is marked, and the mark goes when the right states one.
    const left = surface.edit((e) => e.add(at("fb-code"), SRF("bindsDatatype"), XSD("integer")));
    expect(codes(joinMarks(left, ctxOf(left, BRANCH)))).toEqual(["datatype"]);
    const cured = setPairDatatype(left, ctxOf(left, BRANCH), pair.key, XSD("integer"));
    expect(joinMarks(cured, ctxOf(cured, BRANCH))).toEqual([]);
  });

  it("changes a side of a pair, and the binding it stood on stays, marked as read by nothing", () => {
    const [pair] = readJoin(surface, ctx)!.pairs;
    const g = setPairSide(surface, ctx, pair.key, "left", { property: at("facilityReference") });
    const [now] = readJoin(g, ctxOf(g, BRANCH))!.pairs;
    expect(now.left).toBe(at("FacilityBranchFacilityReference"));
    expect(has(g, at(BRANCH), SRF("hasRoleBinding"), at("fb-code"))).toBe(true);
    expect(unreadEvidence(g, at(BRANCH)).map((i) => i.focus)).toEqual([at("fb-code")]);
    // The only pair may take another second carrier, with its right side.
    const other = setPairSide(surface, ctx, pair.key, "right", { property: at("legalName") }, at("Lender"));
    expect(readJoin(other, ctxOf(other, BRANCH))!.secondCarrier).toBe(at("Lender"));
    expect(setPairSide(surface, ctx, pair.key, "right", { property: at("legalName") }, at("Facility"))).toBe(surface);
    expect(setPairSide(surface, ctx, pair.key, "left", { binding: at("fb-match") })).toBe(surface);
    expect(setPairSide(surface, ctx, "nowhere", "left", { property: at("facilityReference") })).toBe(surface);
  });

  it("names the second carrier on every right binding, which is never the contract's own", () => {
    const two = addPair(surface, ctx, { left: { property: at("facilityReference") }, right: { property: at("branchCode") } });
    const c2 = ctxOf(two, BRANCH);
    const g = setSecondCarrier(two, c2, at("Lender"));
    for (const p of readJoin(g, ctxOf(g, BRANCH))!.pairs) expect(g.value(p.right!, SRF("bindsCarrier"))).toBe(at("Lender"));
    expect(joinMarks(g, ctxOf(g, BRANCH))).toEqual([]);
    expect(setSecondCarrier(two, c2, at("Facility"))).toBe(two);
    expect(setSecondCarrier(two, c2, at("Branch"))).toBe(two);
    expect(setSecondCarrier(removeJoin(surface, ctx), ctxOf(removeJoin(surface, ctx), BRANCH), at("Lender")).toTurtle()).toBe(removeJoin(surface, ctx).toTurtle());
    // Two second carriers are marked, and so is a mix of required and candidate evidence.
    const split = two.edit((e) => e.setAll(readJoin(two, c2)!.pairs.find((p) => p.right !== at("fb-match"))!.right!, SRF("bindsCarrier"), [{ termType: "NamedNode", value: at("Lender") } as never]));
    expect(codes(joinMarks(split, ctxOf(split, BRANCH)))).toEqual(["second-carrier"]);
    const mixed = surface.edit((e) => e.setAll(at("fb-match"), SRF("roleKind"), [{ termType: "NamedNode", value: SRF("CandidateEvidenceRole") } as never]));
    expect(codes(joinMarks(mixed, ctxOf(mixed, BRANCH)))).toEqual(["evidence-kind"]);
  });

  it("returns each rule to its default, which removes its triple, and states what the default is", () => {
    const stated = setCardinality(setCardinality(surface, ctx, "matches", "AnyNumber"), ctx, "links", "AtMostOne");
    expect(stated.value(at("fb-join"), SRF("joinMatches"))).toBe(SRF("AnyNumber"));
    expect(stated.value(at("fb-join"), SRF("joinLinks"))).toBe(SRF("AtMostOne"));
    expect([matchesOf(readJoin(stated, ctxOf(stated, BRANCH))!), linksOf(readJoin(stated, ctxOf(stated, BRANCH))!)]).toEqual(["AnyNumber", "AtMostOne"]);
    expect(setCardinality(stated, ctxOf(stated, BRANCH), "matches", "AnyNumber")).toBe(stated);
    const matchesBack = setCardinality(stated, ctxOf(stated, BRANCH), "matches", "default");
    expect(count(matchesBack, at("fb-join"), SRF("joinMatches"))).toBe(0);
    expect(count(matchesBack, at("fb-join"), SRF("joinLinks"))).toBe(1);
    const both = setCardinality(matchesBack, ctxOf(matchesBack, BRANCH), "links", "default");
    expect(both.toTurtle()).toBe(surface.toTurtle());
    // Stating the default is a statement, and leaving it out says the same, so it is the author's to choose.
    const explicit = setCardinality(surface, ctx, "matches", "AtMostOne");
    expect(count(explicit, at("fb-join"), SRF("joinMatches"))).toBe(1);
    expect(setCardinality(surface, ctx, "matches", "default")).toBe(surface);
    expect(codes(joinMarks(explicit.edit((e) => e.add(at("fb-join"), SRF("joinLinks"), SRF("AtMostOne"))), ctx))).toEqual([]);
    const bad = surface.edit((e) => e.add(at("fb-join"), SRF("joinMatches"), SRF("Some")));
    expect(codes(joinMarks(bad, ctxOf(bad, BRANCH)))).toEqual(["matches"]);
  });

  it("is marked for no pair, a pair that names two bindings or one that is no evidence, and a left that names the second carrier", () => {
    const [pair] = readJoin(surface, ctx)!.pairs;
    expect(codes(joinMarks(surface.edit((e) => e.remove(pair.term)), ctx))).toEqual(["pairs"]);
    const noRight = surface.edit((e) => e.setAll(pair.term, SRF("joinRight"), []));
    expect(codes(joinMarks(noRight, ctxOf(noRight, BRANCH)))).toEqual(["right"]);
    const twoLeft = surface.edit((e) => e.add(pair.term, SRF("joinLeft"), at("fb-match")));
    expect(codes(joinMarks(twoLeft, ctxOf(twoLeft, BRANCH)))).toContain("left");
    const backwards = surface.edit((e) => {
      e.setAll(pair.term, SRF("joinLeft"), [{ termType: "NamedNode", value: at("fb-match") } as never]);
      e.setAll(pair.term, SRF("joinRight"), [{ termType: "NamedNode", value: at("fb-code") } as never]);
    });
    expect(codes(joinMarks(backwards, ctxOf(backwards, BRANCH)))).toEqual(["left-binding", "right-binding"]);
    const foreign = surface.edit((e) => e.setAll(pair.term, SRF("joinLeft"), [{ termType: "NamedNode", value: at("fm-margin") } as never]));
    // The binding that is not the contract's states a datatype, which the right binding states none to cast to.
    expect(codes(joinMarks(foreign, ctxOf(foreign, BRANCH)))).toEqual(["left-binding", "datatype"]);
    const unlinked = surface.edit((e) => e.setAll(at("fb-link"), SRF("bindsProperty"), []));
    expect(codes(joinMarks(unlinked, ctxOf(unlinked, BRANCH)))).toEqual(["link-property"]);
    const placed = surface.edit((e) => e.add(at("be-link"), SRF("joinedAs"), at("fb-join")));
    expect(codes(joinMarks(placed, ctxOf(placed, EXPOSURE)))).toEqual(["placement", "left-binding", "right-binding"]);
  });
});

describe("an expansion", () => {
  const ctx = ctxOf(surface, REFINANCING);

  it("is read with the evidence it expands from and the named source it states", () => {
    const x = readExpansion(surface, ctx)!;
    expect(x.from[0].value).toBe(at("fr-refinances"));
    expect(x).toMatchObject({ source: "TransitiveClosure", hasNode: false, paths: [] });
    expect(readExpansion(surface, ctxOf(surface, COVENANT))!.hasNode).toBe(true);
  });

  it("is added as a minted statement that expands from the contract's one evidence binding, and removed with its path", () => {
    const bare = removeExpansion(surface, ctx);
    expect(has(bare, at("fr-link"), SRF("expandedAs"))).toBe(false);
    expect(bare.quads(at("fr-expansion"), null, null)).toEqual([]);
    expect(codes(expansionMarks(bare, ctxOf(bare, REFINANCING)))).toEqual(["required"]);
    const g = addExpansion(bare, ctxOf(bare, REFINANCING));
    const node = g.value(at("fr-link"), SRF("expandedAs"))!;
    expect(node).toBe(at("FacilityRefinancingExpansion"));
    expect(g.value(node, SRF("expandsFrom"))).toBe(at("fr-refinances"));
    expect(codes(expansionMarks(g, ctxOf(g, REFINANCING)))).toEqual(["members"]);
    expect(addExpansion(g, ctxOf(g, REFINANCING))).toBe(g);
    expect(addExpansion(surface, ctxOf(surface, BRANCH))).toBe(surface);
    // Not while a node for each member is stated beside it, which no other kind of statement may be.
    expect(removeExpansion(surface, ctxOf(surface, COVENANT))).toBe(surface);
    // A contract with two evidence bindings to choose from leaves it to the author.
    const covenant = removeExpansion(removeConstruction(surface, ctxOf(surface, COVENANT)), ctxOf(removeConstruction(surface, ctxOf(surface, COVENANT)), COVENANT));
    const two = addExpansion(covenant, ctxOf(covenant, COVENANT));
    expect(count(two, at("FacilityCovenantTestExpansion"), SRF("expandsFrom"))).toBe(0);
  });

  it("states a named source or a path and never both, and a named source is replaced by the path it stands for", () => {
    const place = { kind: "members" as const, node: at("fr-expansion"), contract: at(REFINANCING), carrier: at("Facility"), label: "the members path" };
    const path = replaceNamedSource(surface, place);
    expect(count(path, at("fr-expansion"), SRF("expansionSource"))).toBe(0);
    expect(count(path, at("fr-expansion"), SRF("membersPath"))).toBe(1);
    expect(expansionMarks(path, ctxOf(path, REFINANCING))).toEqual([]);
    expect(propertiesRead(path, path.object(at("fr-expansion"), SRF("membersPath"))!)).toEqual([at("refinances")]);
    // Back to a name removes the path, and the other name replaces the first.
    const named = useNamedSource(path, ctxOf(path, REFINANCING), "ListMembers");
    expect(count(named, at("fr-expansion"), SRF("membersPath"))).toBe(0);
    expect(named.value(at("fr-expansion"), SRF("expansionSource"))).toBe(SRF("ListMembers"));
    expect(named.quads(null, "http://www.w3.org/ns/shacl#oneOrMorePath", null)).toEqual([]);
    expect(expansionMarks(named, ctxOf(named, REFINANCING))).toEqual([]);
    expect(useNamedSource(named, ctxOf(named, REFINANCING), "ListMembers")).toBe(named);
    expect(useNamedSource(surface, ctx, "TransitiveClosure")).toBe(surface);
    expect(useNamedSource(surface, ctxOf(surface, BRANCH), "ListMembers")).toBe(surface);
  });

  it("expands from the contract's own evidence that binds a property and is not the one it writes, and from one the path reads where it states a path", () => {
    const g = surface.edit((e) => {
      e.add(at("fr-other"), "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", SRF("ProjectionRoleBinding"));
      e.add(at("fr-other"), SRF("roleKind"), SRF("RequiredEvidenceRole"));
      e.add(at("fr-other"), SRF("bindsProperty"), at("hasDrawdown"));
      e.add(at("fr-second"), "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", SRF("ProjectionRoleBinding"));
      e.add(at("fr-second"), SRF("roleKind"), SRF("RequiredEvidenceRole"));
      e.add(at("fr-second"), SRF("bindsProperty"), at("legalName"));
      e.add(at("fr-second"), SRF("bindsCarrier"), at("Borrower"));
      e.add(at("fr-written"), "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", SRF("ProjectionRoleBinding"));
      e.add(at("fr-written"), SRF("roleKind"), SRF("RequiredEvidenceRole"));
      e.add(at("fr-written"), SRF("bindsProperty"), at("refinancesInChain"));
      e.add(at(REFINANCING), SRF("hasRoleBinding"), at("fr-other"));
      e.add(at(REFINANCING), SRF("hasRoleBinding"), at("fr-second"));
      e.add(at(REFINANCING), SRF("hasRoleBinding"), at("fr-written"));
    });
    const c = ctxOf(g, REFINANCING);
    // The binding that reads a second carrier and the one that reads the property the result writes are never offered (srf:P19, srf:P21).
    expect(expansionChoices(g, c).from.map((e) => e.iri)).toEqual([at("fr-other"), at("fr-refinances")]);
    expect(setExpandsFrom(g, c, at("fr-second"))).toBe(g);
    expect(setExpandsFrom(g, c, at("fr-written"))).toBe(g);
    expect(setExpandsFrom(g, c, at("fr-link"))).toBe(g);
    expect(setExpandsFrom(g, c, at("fr-refinances"))).toBe(g);
    const moved = setExpandsFrom(g, c, at("fr-other"));
    expect(moved.value(at("fr-expansion"), SRF("expandsFrom"))).toBe(at("fr-other"));
    expect(expansionMarks(moved, ctxOf(moved, REFINANCING))).toEqual([]);
    // Where a path is stated only the bindings whose property it reads are offered, and a name is the way to another property.
    const path = replaceNamedSource(g, { kind: "members", node: at("fr-expansion"), contract: at(REFINANCING), carrier: at("Facility"), label: "" });
    expect(expansionChoices(path, ctxOf(path, REFINANCING)).from.map((e) => e.iri)).toEqual([at("fr-refinances")]);
    expect(setExpandsFrom(path, ctxOf(path, REFINANCING), at("fr-other"))).toBe(path);
    const viaName = setExpandsFrom(useNamedSource(path, ctxOf(path, REFINANCING), "TransitiveClosure"), ctxOf(path, REFINANCING), at("fr-other"));
    expect(viaName.value(at("fr-expansion"), SRF("expandsFrom"))).toBe(at("fr-other"));
  });

  it("is marked for the evidence it expands from, how its members are stated, and members that read what the statement writes", () => {
    const e = (g: Graph) => codes(expansionMarks(g, ctxOf(g, REFINANCING)));
    expect(e(surface.edit((x) => x.setAll(at("fr-expansion"), SRF("expandsFrom"), [])))).toEqual(["from"]);
    expect(e(surface.edit((x) => x.setAll(at("fr-expansion"), SRF("expansionSource"), [])))).toEqual(["members"]);
    expect(e(surface.edit((x) => x.setAll(at("fr-expansion"), SRF("expansionSource"), [{ termType: "NamedNode", value: SRF("Other") } as never])))).toEqual(["source"]);
    const both = replaceNamedSource(surface, { kind: "members", node: at("fr-expansion"), contract: at(REFINANCING), carrier: at("Facility"), label: "" }).edit((x) => x.add(at("fr-expansion"), SRF("expansionSource"), SRF("ListMembers")));
    expect(e(both)).toEqual(["members"]);
    expect(e(surface.edit((x) => x.setAll(at("fr-expansion"), SRF("expandsFrom"), [{ termType: "NamedNode", value: at("fr-link") } as never])))).toEqual(["evidence", "path-writes"]);
    // A named source over the property the binding writes, and a path over it, feed on their own output (srf:P21).
    const feeds = surface.edit((x) => x.setAll(at("fr-link"), SRF("bindsProperty"), [{ termType: "NamedNode", value: at("refinances") } as never]));
    expect(e(feeds)).toEqual(["path-writes"]);
    const pathFeeds = replaceNamedSource(feeds, { kind: "members", node: at("fr-expansion"), contract: at(REFINANCING), carrier: at("Facility"), label: "" });
    expect(e(pathFeeds)).toEqual(["path-writes"]);
    // A path that does not read the evidence's property, and one that is a zero or one path.
    const other = surface.edit((x) => {
      x.setAll(at("fr-expansion"), SRF("expansionSource"), []);
      x.add(at("fr-expansion"), SRF("membersPath"), at("hasDrawdown"));
    });
    expect(e(other)).toEqual(["path-reads"]);
    const optional = surface.edit((x) => {
      x.setAll(at("fr-expansion"), SRF("expansionSource"), []);
      const b = { termType: "BlankNode", value: "z", id: "_:z" } as never;
      x.add(at("fr-expansion"), SRF("membersPath"), b);
      x.add(b, "http://www.w3.org/ns/shacl#zeroOrOnePath", at("refinances"));
    });
    expect(e(optional)).toContain("path-form");
    // The result binding binds no property, and the statement stands on another kind of contract.
    expect(e(surface.edit((x) => x.setAll(at("fr-link"), SRF("bindsProperty"), [])))).toEqual(["link-property"]);
    const placed = surface.edit((x) => x.add(at("fb-link"), SRF("expandedAs"), at("fr-expansion")));
    expect(codes(expansionMarks(placed, ctxOf(placed, BRANCH)))).toEqual(["placement", "evidence"]);
  });
});
