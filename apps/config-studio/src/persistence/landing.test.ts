// SPDX-License-Identifier: MPL-2.0
// The persistence canvas's pure part, over the document the worker wrote for the facility sample (e2e/fixtures, which the worker's own
// test keeps equal to what the worker gives).

import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { choices, digest, drawing, fingerprint, freshness, localName, parseLanding, readCompiled, targetsOf, writeCompiled, type LandingPlaces, type RecordStore } from "./landing";

const text = readFileSync(new URL("../../e2e/fixtures/landing-places-facility.json", import.meta.url), "utf-8");
const doc = parseLanding(text);
const facility = doc.targets.find((t) => t.id === "Facility")!;

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
    const pinned: LandingPlaces = JSON.parse(text);
    pinned.targets.find((t) => t.id === "Facility")!.aggregate.references[2].mode = "Pinned";
    const p = drawing(pinned, "aggregate", "Facility");
    expect(p.edges.filter((e) => e.kind === "reference").map((e) => e.label)).toEqual(["arrangedBy · identity", "borrower · identity", "lender · pinned"]);
    expect(p.edges.find((e) => e.mode === "Pinned")!.dashed).toBe(true);
  });

  it("nests an owned node below an owned node", () => {
    const nested: LandingPlaces = JSON.parse(text);
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

  it("draws a place two targets share once, joined to each", () => {
    const shared: LandingPlaces = JSON.parse(text);
    // Both targets write the transaction claim to urn:g:txn, and the sample gives one profile to each. Give them one in common.
    for (const t of shared.targets) t.profiles.push("https://example.org/lending#Common");
    const d = drawing(shared, "profile", "https://example.org/lending#Common");
    expect(d.nodes.filter((n) => n.kind === "target")).toHaveLength(2);
    const claims = d.nodes.filter((n) => n.place?.kind === "transaction-claim");
    expect(claims).toHaveLength(1);
    expect(claims[0].targets).toEqual(["Borrower", "Facility"]);
    expect(d.edges.filter((e) => e.target === claims[0].id).map((e) => e.source).sort()).toEqual(["target:Borrower", "target:Facility"]);
    // A place only one writes is drawn once and for that one.
    expect(d.nodes.filter((n) => n.place?.kind === "patch-log-add")).toHaveLength(1);
    expect(d.nodes.filter((n) => n.kind === "place").length).toBeLessThan(doc.targets.reduce((n, t) => n + t.places.length, 0));
    expect(new Set(d.nodes.map((n) => n.id)).size).toBe(d.nodes.length);
  });

  it("draws the targets a scope node matches", () => {
    const d = drawing(doc, "scope", "https://example.org/lending#BorrowerEntity");
    expect(d.nodes.filter((n) => n.kind === "target").map((n) => n.label)).toEqual(["Borrower"]);
    expect(d.nodes.filter((n) => n.kind === "place")).toHaveLength(doc.targets.find((t) => t.id === "Borrower")!.places.length);
  });
});

describe("determinism", () => {
  it("draws the same from the same document, a repeat and a copy with its object keys in another order", () => {
    const stable = (v: unknown) => JSON.stringify(v, (_, x) => (x && typeof x === "object" && !Array.isArray(x) ? Object.fromEntries(Object.entries(x).sort(([a], [b]) => (a < b ? -1 : 1))) : x));
    const first = stable(drawing(doc, "aggregate", "Facility"));
    expect(stable(drawing(doc, "aggregate", "Facility"))).toBe(first);
    const reordered = parseLanding(JSON.stringify(JSON.parse(text), (_, v) => (v && typeof v === "object" && !Array.isArray(v) ? Object.fromEntries(Object.entries(v).reverse()) : v)));
    expect(stable(drawing(reordered, "aggregate", "Facility"))).toBe(first);
    expect(JSON.stringify(choices(reordered, "profile"))).toBe(JSON.stringify(choices(doc, "profile")));
  });
});

describe("the document", () => {
  it("is refused in plain words when it is not the worker's", () => {
    expect(() => parseLanding("not json")).toThrow("not JSON");
    expect(() => parseLanding("{}")).toThrow("Compile again");
    expect(() => parseLanding(JSON.stringify({ targets: [{ id: "x" }] }))).toThrow("Compile again");
  });

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
