// SPDX-License-Identifier: MPL-2.0
import { describe, expect, it } from "vitest";
import { Graph } from "@lattice/authoring-domain";
import { applyArtefacts, importDocument, mediaTypeOf } from "./odrl";

const P = "@prefix cst: <https://www.nebularis.org/neuro-semantic/lattice/config-studio#> .\n@prefix ex: <https://example.org/> .\n";
const art = (path: string, group: string, content: string) => ({ path, group, mediaType: "text/turtle", content });

describe("mediaTypeOf", () => {
  it("takes the media type from the extension", () => {
    expect(mediaTypeOf("a.jsonld")).toBe("application/ld+json");
    expect(mediaTypeOf("A.JSON")).toBe("application/ld+json");
    expect(mediaTypeOf("a.ttl")).toBe("text/turtle");
    expect(mediaTypeOf("a.nt")).toBe("application/n-triples");
    expect(mediaTypeOf("a.xml")).toBeUndefined();
  });
});

describe("importDocument", () => {
  it("sets the profile only on confirmation", () => {
    expect(importDocument("w", "{}", "text/turtle", false).toTurtle()).not.toContain("conformsTo");
    expect(importDocument("w", "{}", "text/turtle", true, "https://example.org/c").toTurtle()).toContain("http://www.w3.org/ns/odrl/2/");
  });
});

describe("applyArtefacts", () => {
  const proposal = `${P}ex:p1 a cst:Proposal ; cst:proposer "odrl" .\n`;
  it("adds each artefact to its configuration and leaves other groups unapplied", () => {
    const current = { vocabulary: Graph.parse(`${P}ex:old a ex:T .\n`) };
    const r = applyArtefacts(
      [art("review.ttl", "review", proposal), art("vocabulary.ttl", "vocabulary", `${P}ex:new a ex:T .\n`), art("baseline.ttl", "baseline", `${P}ex:r a ex:Role .\n`)],
      current,
    );
    expect(r.added).toBe(1);
    expect(r.edits.review!.has("https://example.org/p1")).toBe(true);
    expect(r.edits.vocabulary!.has("https://example.org/old")).toBe(true);
    expect(r.edits.vocabulary!.has("https://example.org/new")).toBe(true);
    expect(r.unapplied.map((a) => a.path)).toEqual(["baseline.ttl"]);
  });
  it("adds a proposal already in review only once", () => {
    const current = { review: Graph.parse(proposal) };
    expect(applyArtefacts([art("review.ttl", "review", proposal)], current).added).toBe(0);
  });
});
