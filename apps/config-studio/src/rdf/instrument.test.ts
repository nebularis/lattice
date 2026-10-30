// SPDX-License-Identifier: MPL-2.0
// The instrument view's model (rdf/instrument.ts): a regime read as a state machine, laid out the same way every time, and the
// request for a dry run. The regime is the one of Instrument's licence-notice example, and the conditions are the builder sample's.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { CST, Graph, XSD } from "@lattice/authoring-domain";
import { DRY_RUN, conceptsForCondition, dryRunGraph, isIntervalCondition, regimeOfNode, regimesOf } from "./instrument";
import { lexiconOf } from "./meaning";
import { split } from "./split";
import { Vocabulary } from "./vocabulary";

const assets = process.env.LATTICE_STUDIO_ASSETS ?? join(import.meta.dirname, "../../../../.build/config-studio");
const vocab = Vocabulary.parse(readFileSync(join(assets, "vocabulary.ttl"), "utf-8"));
const notice = Graph.parse(readFileSync(join(import.meta.dirname, "../../../../ontology/instrument/examples/licence-notice.ttl"), "utf-8"));
const T = "https://example.org/lattice/instrument/licence-notice/form/";
const parts = split(Graph.parse(readFileSync(join(assets, "samples/builder.ttl"), "utf-8")));
const world = Object.values(parts).reduce((g, p) => g.merge(p), Graph.empty());
const F = "https://example.org/lattice/wording/facility-form/";

describe("a regime as a state machine", () => {
  const lex = lexiconOf(notice, vocab);
  const [regime] = regimesOf(notice, lex);

  it("finds the regime, its term and its states by the label of their kind, with the initial one marked", () => {
    expect(regimesOf(notice, lex)).toHaveLength(1);
    expect(regime.iri).toBe(T + "notice-regime");
    expect(regime.term).toBe(T + "term-11-1");
    expect(regime.states.map((s) => [s.label, s.initial])).toEqual([
      ["In force", true],
      ["Notice period", false],
      ["Terminated", false],
    ]);
  });

  it("lays states out in columns by distance from the initial state, one row each, the same on every read", () => {
    expect(regime.states.map((s) => [s.column, s.row])).toEqual([[0, 0], [1, 0], [2, 0]]);
    expect(regime.columns).toBe(3);
    expect(regime.rows).toBe(1);
    expect(regimesOf(notice, lexiconOf(notice, vocab))).toEqual(regimesOf(notice, lex));
  });

  it("reads each transition with its trigger's kind and the relation the trigger names", () => {
    const label = (t: string) => regime.transitions.find((x) => x.iri === T + t)!;
    expect(regime.transitions).toHaveLength(4);
    expect(label("give-notice")).toMatchObject({ from: T + "in-force", to: T + "notice-period", label: "Exercise of Licensor can Terminate Licensee" });
    expect(label("notice-runs-out")).toMatchObject({ from: T + "notice-period", to: T + "terminated", label: "Expiry after 90 day" });
    expect(label("terminate-during-notice").label).toBe("Exercise of Licensor can Terminate Licensee");
  });

  it("lists the relation a state gates under that state, and no other", () => {
    const gates = (s: string) => regime.states.find((x) => x.iri === T + s)!.gates.map((g) => g.iri);
    expect(gates("notice-period")).toEqual([expect.stringContaining("sublicensing-excluded")]);
    expect(gates("in-force")).toEqual([]);
    expect(gates("terminated")).toEqual([]);
  });

  it("puts a state the initial one cannot reach after the last column", () => {
    const extra = notice.merge(
      Graph.parse(`@prefix bhv: <https://www.nebularis.org/neuro-semantic/lattice/behaviour#> . @prefix ins: <https://www.nebularis.org/neuro-semantic/lattice/instrument#> .
        <${T}orphan> a bhv:State ; bhv:inStateSpace <${T}notice-regime> ; ins:stateKind ins:Unknown .`),
    );
    const orphan = regimesOf(extra, lexiconOf(extra, vocab))[0].states.find((s) => s.iri === T + "orphan")!;
    expect(orphan.column).toBe(3);
  });

  it("tells which regime a state, a transition or a trigger belongs to", () => {
    const regimes = [regime];
    for (const node of [regime.iri, T + "in-force", T + "give-notice", T + "give-notice-on-notice-given"]) expect(regimeOfNode(regimes, node)).toBe(regime);
    expect(regimeOfNode(regimes, T + "term-11-1")).toBeUndefined();
  });
});

describe("a dry run request", () => {
  it("knows a condition by its kind and offers a concept condition the concepts of its scheme", () => {
    expect(isIntervalCondition(world, F + "when-syndicated-more-than-one-lender")).toBe(true);
    const eligibility = Graph.parse(readFileSync(join(assets, "samples/lending-eligibility.ttl"), "utf-8"));
    const sector = "https://example.org/lattice/eligibility/eligible-sector";
    expect(isIntervalCondition(eligibility, sector)).toBe(false);
    expect(conceptsForCondition(eligibility, sector).map((c) => c.label)).toEqual(expect.arrayContaining(["Manufacturing", "Retail", "Textiles"]));
  });

  it("builds a cst:DryRun with a fact for each number and each concept, and none for a condition left empty", () => {
    const term = F + "term";
    const graph = dryRunGraph(term, [
      { condition: "urn:c:1", number: "3" },
      { condition: "urn:c:2", concepts: ["urn:k:a", "urn:k:b"] },
      { condition: "urn:c:3", number: "" },
      { condition: "urn:c:4", concepts: [] },
    ]);
    expect(graph.value(DRY_RUN, CST("term"))).toBe(term);
    const facts = graph.objects(DRY_RUN, CST("fact")).map((f) => ({
      condition: graph.value(f, CST("forCondition")),
      number: graph.value(f, CST("number")),
      concept: graph.value(f, CST("concept")),
    }));
    expect(facts).toHaveLength(3);
    expect(facts).toEqual(expect.arrayContaining([{ condition: "urn:c:1", number: "3", concept: undefined }, { condition: "urn:c:2", number: undefined, concept: "urn:k:a" }, { condition: "urn:c:2", number: undefined, concept: "urn:k:b" }]));
    expect(graph.object(graph.objects(DRY_RUN, CST("fact")).find((f) => graph.value(f, CST("number")))!, CST("number"))).toMatchObject({ datatype: { value: XSD("decimal") } });
  });
});
