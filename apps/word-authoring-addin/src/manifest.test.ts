import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const MANIFEST_PATH = path.join(__dirname, "..", "manifest", "manifest.xml");

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function parseManifest(): Document {
  const xml = readFileSync(MANIFEST_PATH, "utf-8");
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  const parserError = doc.getElementsByTagName("parsererror")[0];
  if (parserError) {
    throw new Error(`manifest.xml did not parse: ${parserError.textContent}`);
  }
  return doc;
}

describe("manifest.xml (S8-11)", () => {
  it("has a GUID Id", () => {
    const doc = parseManifest();
    const id = doc.getElementsByTagName("Id")[0].textContent ?? "";
    expect(id).toMatch(UUID_PATTERN);
  });

  it("declares ReadWriteDocument and WordApi 1.4", () => {
    const doc = parseManifest();
    expect(doc.getElementsByTagName("Permissions")[0].textContent).toBe("ReadWriteDocument");
    const set = doc.getElementsByTagName("Set")[0];
    expect(set.getAttribute("Name")).toBe("WordApi");
    expect(set.getAttribute("MinVersion")).toBe("1.4");
  });

  it("puts every URL under https://localhost:3443/addin/, except the bare AppDomain", () => {
    const doc = parseManifest();
    const origin = "https://localhost:3443/addin/";

    const sourceLocation = doc.getElementsByTagName("SourceLocation")[0].getAttribute("DefaultValue") ?? "";
    expect(sourceLocation.startsWith(origin)).toBe(true);

    const iconUrl = doc.getElementsByTagName("IconUrl")[0].getAttribute("DefaultValue") ?? "";
    const highResIconUrl = doc.getElementsByTagName("HighResolutionIconUrl")[0].getAttribute("DefaultValue") ?? "";
    const supportUrl = doc.getElementsByTagName("SupportUrl")[0].getAttribute("DefaultValue") ?? "";
    expect(iconUrl.startsWith(origin)).toBe(true);
    expect(highResIconUrl.startsWith(origin)).toBe(true);
    expect(supportUrl.startsWith(origin)).toBe(true);

    for (const url of Array.from(doc.getElementsByTagName("bt:Url"))) {
      const value = url.getAttribute("DefaultValue") ?? "";
      expect(value.startsWith(origin)).toBe(true);
    }
    for (const image of Array.from(doc.getElementsByTagName("bt:Image"))) {
      const value = image.getAttribute("DefaultValue");
      if (value) {
        expect(value.startsWith(origin)).toBe(true);
      }
    }

    const appDomain = doc.getElementsByTagName("AppDomain")[0].textContent ?? "";
    expect(appDomain).toBe("https://localhost:3443");
  });
});
