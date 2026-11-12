// @vitest-environment jsdom
// SPDX-License-Identifier: MPL-2.0
import { describe, expect, it } from "vitest";
import { buildCatalogLookup, isWebLocation, normalisePath, parseCatalog } from "./catalog";

const NS = 'xmlns="urn:oasis:names:tc:entity:xmlns:xml:catalog"';
const catalog = (body: string, attributes = "") => `<?xml version="1.0"?><catalog ${NS} prefer="public" ${attributes}>${body}</catalog>`;

describe("normalisePath", () => {
  it("resolves dot segments and keeps a climb above the root", () => {
    expect(normalisePath("a/./b/../c.ttl")).toBe("a/c.ttl");
    expect(normalisePath("./a//b")).toBe("a/b");
    expect(normalisePath("../x/y")).toBe("../x/y");
    expect(normalisePath("a\\b\\c")).toBe("a/b/c");
  });
  it("tells a location with a scheme from a path", () => {
    expect(isWebLocation("https://www.w3.org/ns/prov-o")).toBe(true);
    expect(isWebLocation("a/b.ttl")).toBe(false);
  });
});

describe("parseCatalog", () => {
  it("reads uri entries relative to the catalog's own directory", () => {
    const parsed = parseCatalog(catalog('<uri name="https://example.org/a" uri="a/a.ttl"/><uri name="https://example.org/b" uri="../b.ttl"/>'), "ont/spec/catalog-v001.xml");
    expect(parsed.error).toBeUndefined();
    expect(parsed.entries).toEqual([
      { name: "https://example.org/a", target: "ont/spec/a/a.ttl" },
      { name: "https://example.org/b", target: "ont/b.ttl" },
    ]);
  });

  it("applies xml:base on the root and on a group, and ignores other elements", () => {
    const text = catalog(
      `<system systemId="x" uri="ignored.ttl"/>
       <group xml:base="sub/"><uri name="https://example.org/g" uri="g.ttl"/>
         <group xml:base="deeper/"><uri name="https://example.org/h" uri="h.ttl"/></group>
       </group>
       <uri name="https://example.org/r" uri="r.ttl"/>`,
      'xml:base="root/"',
    );
    const parsed = parseCatalog(text, "catalog-v001.xml");
    expect(parsed.entries).toEqual([
      { name: "https://example.org/g", target: "root/sub/g.ttl" },
      { name: "https://example.org/h", target: "root/sub/deeper/h.ttl" },
      { name: "https://example.org/r", target: "root/r.ttl" },
    ]);
  });

  it("decodes percent escapes and leaves a web location as written", () => {
    const parsed = parseCatalog(catalog('<uri name="https://example.org/s" uri="my%20file.ttl"/><uri name="http://www.w3.org/ns/prov-o-20130430" uri="https://www.w3.org/ns/prov-o-20130430"/>'), "catalog-v001.xml");
    expect(parsed.entries.map((e) => e.target)).toEqual(["my file.ttl", "https://www.w3.org/ns/prov-o-20130430"]);
  });

  it("reads nextCatalog targets as paths relative to the dropped root", () => {
    const parsed = parseCatalog(catalog('<nextCatalog catalog="../../catalog-v001.xml"/>'), "foundation/spec/catalog-v001.xml");
    expect(parsed.nextCatalogs).toEqual(["catalog-v001.xml"]);
  });

  it("reports text that is not a catalog", () => {
    expect(parseCatalog("<catalog", "c.xml").error).toBeDefined();
    expect(parseCatalog("<other/>", "c.xml").error).toBeDefined();
  });
});

describe("buildCatalogLookup", () => {
  const files = (record: Record<string, string>) => new Map(Object.entries(record));

  it("follows a nextCatalog chain and lets the first catalog win a duplicate IRI", () => {
    const result = buildCatalogLookup(
      files({
        "a/spec/catalog-v001.xml": catalog('<uri name="https://example.org/x" uri="x.ttl"/><nextCatalog catalog="../../catalog-v001.xml"/>'),
        "catalog-v001.xml": catalog('<uri name="https://example.org/x" uri="other.ttl"/><uri name="https://example.org/y" uri="y.ttl"/><nextCatalog catalog="b/catalog-v001.xml"/>'),
        "b/catalog-v001.xml": catalog('<uri name="https://example.org/z" uri="z.ttl"/>'),
      }),
      "a/spec/catalog-v001.xml",
    );
    expect([...result.lookup]).toEqual([
      ["https://example.org/x", "a/spec/x.ttl"],
      ["https://example.org/y", "y.ttl"],
      ["https://example.org/z", "b/z.ttl"],
    ]);
    expect(result.missingCatalogs).toEqual([]);
  });

  it("ends a cycle of catalogs", () => {
    const result = buildCatalogLookup(
      files({
        "a.xml": catalog('<uri name="https://example.org/a" uri="a.ttl"/><nextCatalog catalog="b.xml"/>'),
        "b.xml": catalog('<uri name="https://example.org/b" uri="b.ttl"/><nextCatalog catalog="a.xml"/>'),
      }),
      "a.xml",
    );
    expect([...result.lookup.keys()]).toEqual(["https://example.org/a", "https://example.org/b"]);
  });

  it("lists a nextCatalog that was not dropped, and a start catalog that was not", () => {
    const chained = buildCatalogLookup(
      files({ "a.xml": catalog('<nextCatalog catalog="gone/c.xml"/><nextCatalog catalog="gone/c.xml"/>') }),
      "a.xml",
    );
    expect(chained.missingCatalogs).toEqual(["gone/c.xml"]);
    expect(buildCatalogLookup(files({}), "none.xml").missingCatalogs).toEqual(["none.xml"]);
  });

  it("lists a catalog that cannot be read and carries on", () => {
    const result = buildCatalogLookup(files({ "a.xml": catalog('<nextCatalog catalog="b.xml"/>'), "b.xml": "not xml" }), "a.xml");
    expect(result.errors.map((e) => e.path)).toEqual(["b.xml"]);
  });

  it("normalises the paths of the dropped files and of the start", () => {
    const result = buildCatalogLookup(files({ "./x/../catalog-v001.xml": catalog('<uri name="https://example.org/a" uri="a.ttl"/>') }), "catalog-v001.xml");
    expect(result.lookup.get("https://example.org/a")).toBe("a.ttl");
  });
});
