// SPDX-License-Identifier: MPL-2.0
// The persistence canvas's pure part, over the facility sample's compiled profile (e2e/fixtures, which the worker's own test keeps equal to
// what the compiler gives for the sample).

import { readFileSync } from "node:fs";
import { DataFactory, Writer } from "n3";
import { DAL, Graph, TYPE, namedNode } from "@lattice/authoring-domain";
import { describe, expect, it } from "vitest";
import {
  artefactPath, choices, digest, drawing, fingerprint, freshness, landingOf, localName, readCompiled, readLanding, targetsOf, writeCompiled,
  type LandingPlaces, type RecordStore,
} from "./landing";

const fixture = (name: string) => readFileSync(new URL(`../../e2e/fixtures/${name}`, import.meta.url), "utf-8");
const text = fixture("compiled-profile-facility.ttl");

/** What the canvas reads of a compiled profile, which is always a document and never "predates" for the sample. */
function read(turtle: string): LandingPlaces {
  const reading = readLanding(turtle);
  if (reading.state !== "ready") throw new Error("predates");
  return reading.doc;
}

const doc = read(text);
const facility = doc.targets.find((t) => t.id === "Facility")!;
const borrower = doc.targets.find((t) => t.id === "Borrower")!;
const copy = (): LandingPlaces => structuredClone(doc);
const graph = () => Graph.parse(text);

/** The compiled profile with the triples `drop` names left out and the ones `swap` rewrites. */
function changed(drop: (s: string, p: string, o: string) => boolean, swap: (s: string, p: string, o: string) => string | undefined = () => undefined): string {
  const g = graph();
  const quads = g.quads().filter((q) => !drop(q.subject.value, q.predicate.value, q.object.value));
  const rewritten = quads.map((q) => {
    const o = swap(q.subject.value, q.predicate.value, q.object.value);
    return o === undefined ? q : DataFactory.quad(q.subject, q.predicate, namedNode(o), q.graph);
  });
  return Graph.of(rewritten, g.prefixes).toTurtle();
}

describe("reading the compiled profile", () => {
  it("gives a target for each compiled profile, with its deployment, the profiles that won and the scope nodes that matched", () => {
    expect(doc.targets.map((t) => [t.id, t.class, t.deployment])).toEqual([
      ["Borrower", "https://example.org/lending#Borrower", null],
      ["Facility", "https://example.org/lending#Facility", null],
    ]);
    expect(facility.profiles).toEqual([
      "https://example.org/lending#FacilityBoundaryProfile", "https://example.org/lending#FacilityConcurrencyProfile",
      "https://example.org/lending#FacilityEpoch", "https://example.org/lending#FacilityReceiptProfile",
    ]);
    expect(facility.scopes).toEqual(["https://example.org/lending#FacilityClass"]);
    expect(facility.matchedScopes).toEqual(["https://example.org/lending#FacilityClass"]);
    expect(borrower.matchedScopes).toEqual(["https://example.org/lending#BorrowerEntity"]);
    expect(facility.aggregate.strategy).toBe("CompositePropertyBoundary");
    expect(borrower.aggregate.strategy).toBe("NamedGraphBoundary");
  });

  it("gives each target the places its write accesses land in, the graph as the profile states it", () => {
    const graphs = (t: typeof facility) => t.places.map((p) => [p.kind, p.graph]);
    expect(graphs(facility)).toEqual([
      ["data-graph", "urn:g:facilities"],
      ["version-row", "urn:g:meta/6"],
      ["receipt", "urn:g:txlog/{month}"],
      ["transaction-claim", "urn:g:txn"],
      ["patch-log-add", "{newRev}/add"],
      ["patch-log-del", "{newRev}/del"],
      ["key-claim", "urn:g:keys"],
    ]);
    expect(graphs(borrower)).toEqual([
      ["data-graph", "urn:g:borrower/{root}"],
      ["version-row", "urn:g:meta/52"],
      ["receipt", "urn:g:txlog/{month}"],
      ["transaction-claim", "urn:g:txn"],
      ["key-claim", "urn:g:keys"],
    ]);
  });

  it("names a place's operations as the ones that write it, never one that only reads", () => {
    const kind = (k: string) => facility.places.find((p) => p.kind === k)!;
    expect(kind("patch-log-add").operations).toEqual(["cas-replace", "create-if-absent", "replace-whole"]);
    expect(kind("patch-log-del").operations).toEqual(["cas-replace", "replace-whole", "tombstone-delete"]);
    expect(kind("key-claim").operations).toEqual(["key-claim-retire:facility-reference-per-branch", "key-claim-write:facility-reference-per-branch"]);
    const writers = new Set(facility.places.flatMap((p) => p.operations));
    for (const read of ["gap-scan-audit", "fork-detection-audit", "payload-check", "revision-multi-txn-audit", "txn-multi-revision-audit", "key-claim-duplicate-audit:facility-reference-per-branch"]) {
      expect(writers.has(read)).toBe(false);
    }
    // Each place also names the templates of those operations.
    const byName = new Map(facility.operations.map((o) => [o.operation, o.templateId]));
    for (const p of facility.places) expect(p.from).toEqual([...new Set(p.operations.map((n) => byName.get(n)!))].sort());
    expect(kind("patch-log-add").from).toContain("cas-replace-composite-property-delta-patch-log-dataset-guard");
  });

  it("labels a key claim with the constraint it serves, and no other place", () => {
    expect(facility.places.find((p) => p.kind === "key-claim")!.label).toBe("Key claim, FacilityReferencePerBranch");
    expect(borrower.places.find((p) => p.kind === "key-claim")!.label).toBe("Key claim, BorrowerTaxIdentifierUnique");
    expect(facility.places.find((p) => p.kind === "receipt")!.label).toBe("Receipt of each write");
  });

  it("lists every operation, the reads too, with its template and kind", () => {
    expect(facility.operations).toHaveLength(12);
    expect(facility.operations.find((o) => o.operation === "gap-scan-audit")).toMatchObject({ kind: "Audit", path: "Facility/gap-scan-audit.rq" });
    expect(facility.operations.find((o) => o.operation === "cas-replace")).toMatchObject({ kind: "DeltaReplace", templateId: "cas-replace-composite-property-delta-patch-log-dataset-guard" });
    expect(facility.operations.map((o) => o.operation)).toEqual([...facility.operations.map((o) => o.operation)].sort());
  });

  it("decides a place's kind from what the access and its place state, and from nothing in a name or a template", () => {
    // The data graph is the new version's triples where the operation's kind is AppendVersion.
    const versions = read(changed(() => false, (_s, p, o) => (p === DAL("operationKind") && o === DAL("Create") ? DAL("AppendVersion") : undefined)));
    expect(versions.targets.find((t) => t.id === "Facility")!.places.filter((p) => p.graph === "urn:g:facilities").map((p) => [p.kind, p.operations])).toEqual([
      ["data-graph", ["cas-replace", "replace-whole", "tombstone-delete"]],
      ["version", ["create-if-absent"]],
    ]);
    // The keys graph holds a merge record where the access's resource kind says so.
    const merged = read(changed(() => false, (s, p, o) => (s.includes("key-claim-write-facility-reference-per-branch#") && p === DAL("resourceKind") && o === DAL("KeyClaim") ? DAL("MergeRecord") : undefined)));
    expect(merged.targets.find((t) => t.id === "Facility")!.places.filter((p) => p.graph === "urn:g:keys").map((p) => [p.kind, p.operations])).toEqual([
      ["key-claim", ["key-claim-retire:facility-reference-per-branch"]],
      ["merge-record", ["key-claim-write:facility-reference-per-branch"]],
    ]);
    // A patch log's direction decides add or del, and a write that states none is refused.
    const flipped = read(changed(() => false, (_s, p, o) => (p === DAL("patchDirection") ? (o === DAL("Added") ? DAL("Removed") : DAL("Added")) : undefined)));
    expect(flipped.targets.find((t) => t.id === "Facility")!.places.find((p) => p.kind === "patch-log-add")!.operations).toEqual(["cas-replace", "replace-whole", "tombstone-delete"]);
    expect(() => readLanding(changed((_s, p) => p === DAL("patchDirection")))).toThrow("states no direction");
  });

  it("states the place of a role that needs nothing else from the role alone", () => {
    const kinds = new Map(facility.places.map((p) => [p.graph, p.kind]));
    expect(kinds.get("urn:g:meta/6")).toBe("version-row");
    expect(kinds.get("urn:g:txn")).toBe("transaction-claim");
    expect(kinds.get("urn:g:txlog/{month}")).toBe("receipt");
  });

  it("gives the aggregate the profile's edges give, each owned edge nested as its shape nests and a reference with its mode", () => {
    const a = facility.aggregate;
    expect(a.rootShape).toBe("https://example.org/lending#FacilityShape");
    expect(a.owned.map((e) => [e.property, e.class, e.shape])).toEqual([["https://example.org/lending#hasDrawdown", "https://example.org/lending#Drawdown", "https://example.org/lending#DrawdownShape"]]);
    expect(a.references.map((e) => [e.property.split("#")[1], e.ownership, e.mode])).toEqual([["arrangedBy", "Reference", "ByIdentity"], ["borrower", "Reference", "ByIdentity"], ["lender", "Reference", "ByIdentity"]]);
    // A family with no boundary shape has a root and no edges.
    expect(borrower.aggregate).toMatchObject({ rootShape: null, owned: [], references: [] });
  });

  it("reads a pinned edge as pinned, and nests an owned edge of an owned edge", () => {
    const pinned = read(changed(() => false, (s, p, o) => (s.endsWith("Facility/compiled/profile#edge-03") && p === DAL("referenceMode") && o === DAL("ByIdentity") ? DAL("Pinned") : undefined)));
    expect(pinned.targets.find((t) => t.id === "Facility")!.aggregate.references.map((r) => r.mode)).toEqual(["ByIdentity", "ByIdentity", "Pinned"]);
    const g = graph();
    const edge = "https://example.org/lending/Facility/compiled/profile#edge-09";
    const extra = g.edit((e) => {
      e.add(edge, TYPE, DAL("ReferenceEdge"));
      e.add(edge, DAL("edgeSource"), "https://example.org/lending#DrawdownShape");
      e.add(edge, DAL("edgePredicate"), "https://example.org/lending#hasFee");
      e.add(edge, DAL("edgeOwnership"), DAL("Owned"));
      e.add(edge, DAL("edgeTargetClass"), "https://example.org/lending#Fee");
      e.add(edge, DAL("edgeTargetShape"), "https://example.org/lending#FeeShape");
      const node = g.subjects(DAL("forTarget"), "https://example.org/lending#Facility")[0];
      e.add(node, DAL("referenceEdge"), edge);
    });
    const nested = landingOf(extra);
    if (nested.state !== "ready") throw new Error("predates");
    const drawdown = nested.doc.targets.find((t) => t.id === "Facility")!.aggregate.owned[0];
    expect(drawdown.owned.map((e) => e.property)).toEqual(["https://example.org/lending#hasFee"]);
  });

  it("names a target in a deployment by its class and its deployment", () => {
    const g = graph();
    const node = g.subjects(DAL("forTarget"), "https://example.org/lending#Facility")[0];
    const reading = landingOf(g.edit((e) => e.add(node, DAL("forDeployment"), "https://example.org/lending#Lakehouse")));
    if (reading.state !== "ready") throw new Error("predates");
    const deployed = reading.doc;
    const t = deployed.targets.find((x) => x.class.endsWith("#Facility"))!;
    expect(t.id).toBe("Facility.Lakehouse");
    expect(t.deployment).toBe("https://example.org/lending#Lakehouse");
    expect(t.operations[0].path.startsWith("Facility.Lakehouse/")).toBe(true);
  });
});

describe("an operation's path", () => {
  const paths = fixture("compiled-profile-facility.paths.txt").trim().split("\n");

  it("is a path the facility sample's job holds, for every operation of both targets", () => {
    for (const t of doc.targets) for (const o of t.operations) expect(paths, `${t.id} ${o.operation}`).toContain(o.path);
  });

  it("is each path of the job but the compiled profile itself", () => {
    const all = doc.targets.flatMap((t) => t.operations.map((o) => o.path)).sort();
    expect(all).toEqual(paths.filter((p) => p !== "compiled-profile.ttl").sort());
  });

  it("writes a colon and a slash of an operation's name as an underscore", () => {
    expect(artefactPath("Facility", "key-claim-write:facility-reference-per-branch")).toBe("Facility/key-claim-write_facility-reference-per-branch.rq");
    expect(artefactPath("Facility.Lakehouse", "a/b")).toBe("Facility.Lakehouse/a_b.rq");
  });
});

describe("a profile compiled before it stated where data lands", () => {
  const old = changed((_s, p, o) => p === DAL("landsIn") || (p === TYPE && o === DAL("GraphPlace")));

  it("predates the landing places where it has targets and no place", () => {
    expect(readLanding(old)).toEqual({ state: "predates" });
    expect(Graph.parse(old).subjects(TYPE, DAL("CompiledProfile"))).toHaveLength(2);
  });

  it("has nothing to say of a graph with no target, which is not an old one", () => {
    expect(readLanding("@prefix ex: <https://example.org/> . ex:a ex:b ex:c .")).toEqual({ state: "ready", doc: { targets: [] } });
  });

  it("is refused in plain words where it is not Turtle", () => {
    expect(() => readLanding("this is { not turtle")).toThrow("Compile again");
  });
});

describe("the picker lists only what the compile job holds", () => {
  it("lists the targets, the profiles that won and the scope nodes that match", () => {
    expect(choices(doc, "aggregate").map((c) => c.label)).toEqual(["Borrower", "Facility"]);
    expect(choices(doc, "profile").map((c) => c.label)).toEqual([
      "BorrowerAccessProfile", "BorrowerEpoch", "BorrowerIdentity", "BorrowerPrivacy", "FacilityBoundaryProfile", "FacilityConcurrencyProfile", "FacilityEpoch", "FacilityReceiptProfile",
    ]);
    expect(choices(doc, "scope").map((c) => c.label)).toEqual(["BorrowerEntity", "FacilityClass"]);
  });

  it("lists nothing for a document with no target", () => {
    for (const lens of ["aggregate", "profile", "scope"] as const) expect(choices({ targets: [] }, lens)).toEqual([]);
  });

  it("draws the targets a choice of each lens names", () => {
    expect(targetsOf(doc, "aggregate", "Facility").map((t) => t.id)).toEqual(["Facility"]);
    expect(targetsOf(doc, "profile", "https://example.org/lending#FacilityEpoch").map((t) => t.id)).toEqual(["Facility"]);
    expect(targetsOf(doc, "scope", "https://example.org/lending#BorrowerEntity").map((t) => t.id)).toEqual(["Borrower"]);
    expect(targetsOf(doc, "scope", "https://example.org/lending#Nothing")).toEqual([]);
  });
});

describe("the aggregate lens", () => {
  const d = drawing(doc, "aggregate", "Facility");
  const node = (id: string) => d.nodes.find((n) => n.id === id)!;

  it("draws the root, what it owns and what it references, with its places", () => {
    expect(d.nodes.filter((n) => n.kind === "root").map((n) => n.label)).toEqual(["Facility"]);
    expect(d.nodes.filter((n) => n.kind === "owned").map((n) => n.label)).toEqual(["Drawdown"]);
    expect(d.nodes.filter((n) => n.kind === "reference").map((n) => n.label).sort()).toEqual(["Borrower", "Branch", "Lender"]);
    expect(d.nodes.filter((n) => n.kind === "place").map((n) => n.place!.kind).sort()).toEqual(facility.places.map((p) => p.kind).sort());
    expect(d.nodes.some((n) => n.kind === "target")).toBe(false);
  });

  it("joins every place to the root, solid, with the graph or its rule on the node", () => {
    const lands = d.edges.filter((e) => e.kind === "lands");
    expect(lands).toHaveLength(facility.places.length);
    expect(lands.every((e) => e.source === "root:Facility" && !e.dashed)).toBe(true);
    const add = d.nodes.find((n) => n.place?.kind === "patch-log-add")!;
    expect(add.sub).toBe("{newRev}/add");
    expect(add.label).toBe("Patch log, the triples added");
    expect(d.nodes.find((n) => n.place?.kind === "data-graph")!.sub).toBe("urn:g:facilities");
  });

  it("draws a referenced edge dashed with its mode and an owned edge solid", () => {
    const refs = d.edges.filter((e) => e.kind === "reference");
    expect(refs).toHaveLength(3);
    expect(refs.every((e) => e.dashed && e.label!.endsWith("identity") && e.mode === "ByIdentity")).toBe(true);
    const owned = d.edges.filter((e) => e.kind === "owned");
    expect(owned.map((e) => [e.label, e.dashed])).toEqual([["hasDrawdown", false]]);
    expect(node("ref:Facility::https://example.org/lending#lender").edge?.mode).toBe("ByIdentity");
  });

  it("keeps the boundary left of the root and the places right of it", () => {
    expect(d.nodes.filter((n) => n.kind === "owned" || n.kind === "reference").every((n) => n.rank < 0)).toBe(true);
    expect(d.nodes.filter((n) => n.kind === "place").every((n) => n.rank > 0)).toBe(true);
    expect(node("root:Facility").rank).toBe(0);
  });

  it("draws a family with no boundary shape as a root and its places", () => {
    const named = drawing(doc, "aggregate", "Borrower");
    expect(named.nodes.filter((n) => n.kind === "owned" || n.kind === "reference")).toEqual([]);
    expect(named.nodes.filter((n) => n.kind === "place").map((n) => n.place!.kind).sort()).toEqual(["data-graph", "key-claim", "receipt", "transaction-claim", "version-row"]);
    expect(named.nodes.some((n) => n.place?.kind === "patch-log-add")).toBe(false);
  });

  it("marks a pinned reference as pinned", () => {
    const pinned = copy();
    pinned.targets.find((t) => t.id === "Facility")!.aggregate.references[2].mode = "Pinned";
    const p = drawing(pinned, "aggregate", "Facility");
    expect(p.edges.filter((e) => e.kind === "reference").map((e) => e.label)).toEqual(["arrangedBy · identity", "borrower · identity", "lender · pinned"]);
    expect(p.edges.find((e) => e.mode === "Pinned")!.dashed).toBe(true);
  });

  it("nests an owned node below an owned node", () => {
    const nested = copy();
    const drawdown = nested.targets.find((t) => t.id === "Facility")!.aggregate.owned[0];
    drawdown.owned.push({ property: "https://example.org/lending#hasFee", inverse: false, class: "https://example.org/lending#Fee", shape: null, owned: [], references: [] });
    const n = drawing(nested, "aggregate", "Facility");
    const fee = n.nodes.find((x) => x.label === "Fee")!;
    expect(fee.rank).toBe(-2);
    expect(n.edges.find((e) => e.target === fee.id)!.source).toBe(n.nodes.find((x) => x.label === "Drawdown")!.id);
  });
});

describe("the profile and scope node lenses", () => {
  it("draws every target of a profile as a compact node, with no boundary", () => {
    const d = drawing(doc, "profile", "https://example.org/lending#FacilityEpoch");
    expect(d.nodes.filter((n) => n.kind === "target").map((n) => n.id)).toEqual(["target:Facility"]);
    expect(d.nodes.some((n) => n.kind === "owned" || n.kind === "reference" || n.kind === "root")).toBe(false);
  });

  it("draws a place two targets share once, joined to each, though the profile mints its IRI for each target", () => {
    // Each target has its own node for the transaction claim's graph, and the places are merged by role and graph, never by IRI.
    const claims = graph().subjects(TYPE, DAL("GraphPlace")).filter((s) => graph().value(s, DAL("inGraph")) === "urn:g:txn");
    expect(claims).toHaveLength(2);
    expect(new Set(claims.map((c) => c.value)).size).toBe(2);
    const shared = copy();
    // The sample gives each target its own profiles. Give them one in common.
    for (const t of shared.targets) t.profiles.push("https://example.org/lending#Common");
    const d = drawing(shared, "profile", "https://example.org/lending#Common");
    expect(d.nodes.filter((n) => n.kind === "target")).toHaveLength(2);
    const txn = d.nodes.filter((n) => n.place?.kind === "transaction-claim");
    expect(txn).toHaveLength(1);
    expect(txn[0].targets).toEqual(["Borrower", "Facility"]);
    expect(d.edges.filter((e) => e.target === txn[0].id).map((e) => e.source).sort()).toEqual(["target:Borrower", "target:Facility"]);
    // The receipt and the keys graph are shared as well, and a place only one writes is drawn once and for that one.
    expect(d.nodes.filter((n) => n.place?.kind === "receipt")).toHaveLength(1);
    expect(d.nodes.filter((n) => n.place?.kind === "patch-log-add")).toHaveLength(1);
    expect(d.nodes.filter((n) => n.place?.kind === "patch-log-add")[0].targets).toEqual(["Facility"]);
    expect(d.nodes.filter((n) => n.kind === "place").length).toBeLessThan(shared.targets.reduce((n, t) => n + t.places.length, 0));
    expect(new Set(d.nodes.map((n) => n.id)).size).toBe(d.nodes.length);
  });

  it("draws the targets a scope node matches", () => {
    const d = drawing(doc, "scope", "https://example.org/lending#BorrowerEntity");
    expect(d.nodes.filter((n) => n.kind === "target").map((n) => n.label)).toEqual(["Borrower"]);
    expect(d.nodes.filter((n) => n.kind === "place")).toHaveLength(borrower.places.length);
  });
});

describe("determinism", () => {
  /** The compiled profile as N-Triples lines, which are Turtle, in the order a seeded shuffle gives. */
  function shuffled(seed: number): string {
    const lines = new Writer({ format: "N-Triples" }).quadsToString(graph().quads()).split("\n").filter(Boolean);
    let state = seed;
    const next = () => ((state = (Math.imul(state, 1664525) + 1013904223) >>> 0) / 4294967296);
    for (let i = lines.length - 1; i > 0; i--) {
      const j = Math.floor(next() * (i + 1));
      [lines[i], lines[j]] = [lines[j], lines[i]];
    }
    return lines.join("\n");
  }

  it("draws the same from the same profile, a repeat and a copy with its triples in another order", () => {
    const first = JSON.stringify(drawing(doc, "aggregate", "Facility"));
    expect(JSON.stringify(drawing(doc, "aggregate", "Facility"))).toBe(first);
    expect(JSON.stringify(read(text))).toBe(JSON.stringify(doc));
    for (const seed of [1, 2, 3]) {
      const other = read(shuffled(seed));
      expect(JSON.stringify(other)).toBe(JSON.stringify(doc));
      expect(JSON.stringify(drawing(other, "aggregate", "Facility"))).toBe(first);
      for (const lens of ["profile", "scope"] as const) expect(JSON.stringify(choices(other, lens))).toBe(JSON.stringify(choices(doc, lens)));
    }
  });
});

describe("the document", () => {
  it("names an IRI by its last part", () => {
    expect(localName("https://example.org/lending#Facility")).toBe("Facility");
    expect(localName("urn:x/y/z")).toBe("z");
    expect(localName("plain")).toBe("plain");
  });
});

describe("whether the picture is out of date", () => {
  const store = (): RecordStore & { data: Record<string, string> } => {
    const data: Record<string, string> = {};
    return { data, getItem: (k) => data[k] ?? null, setItem: (k, v) => void (data[k] = v) };
  };

  it("is current where the compilation read what the editor holds, and out of date after an edit or a new baseline", () => {
    const sent = fingerprint("dal:a dal:b dal:c .", "3");
    expect(freshness(sent, fingerprint("dal:a dal:b dal:c .", "3"))).toBe("current");
    expect(freshness(sent, fingerprint("dal:a dal:b dal:d .", "3"))).toBe("out-of-date");
    expect(freshness(sent, fingerprint("dal:a dal:b dal:c .", "4"))).toBe("out-of-date");
  });

  it("is unknown for a compilation this browser did not start", () => {
    expect(freshness(undefined, fingerprint("x", "1"))).toBe("unknown");
  });

  it("tells two texts apart and the same text alike", () => {
    expect(digest("abc")).toBe(digest("abc"));
    expect(digest("abc")).not.toBe(digest("abd"));
    expect(digest("")).toBe(digest(""));
  });

  it("keeps what a workspace sent by job, in memory when the store refuses", () => {
    const s = store();
    writeCompiled("ws-1", "job-a", "f1", s);
    writeCompiled("ws-1", "job-b", "f2", s);
    expect(readCompiled("ws-1", s)).toEqual({ "job-a": "f1", "job-b": "f2" });
    expect(readCompiled("ws-2", s)).toEqual({});
    const refusing: RecordStore = { getItem: () => { throw new Error("blocked"); }, setItem: () => { throw new Error("blocked"); } };
    writeCompiled("ws-3", "job-c", "f3", refusing);
    expect(readCompiled("ws-3", refusing)).toEqual({ "job-c": "f3" });
  });
});
