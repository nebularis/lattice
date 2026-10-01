import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { COMMAND_IDS } from "./commands/ids";

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

describe("manifest.xml: the shared-runtime V1_1 override (S9a-01)", () => {
  function v1_1(doc: Document): Element {
    const overrides = Array.from(doc.getElementsByTagName("VersionOverrides"));
    const found = overrides.find((el) => el.getAttribute("xsi:type") === "VersionOverridesV1_1");
    if (!found) {
      throw new Error("no VersionOverridesV1_1 found");
    }
    return found;
  }

  it("requires SharedRuntime 1.1", () => {
    const override = v1_1(parseManifest());
    const set = Array.from(override.getElementsByTagName("bt:Set")).find((el) => el.getAttribute("Name") === "SharedRuntime");
    expect(set?.getAttribute("MinVersion")).toBe("1.1");
  });

  it("declares exactly one long-lived runtime and the function file, both on Taskpane.Url", () => {
    const override = v1_1(parseManifest());
    const runtimes = Array.from(override.getElementsByTagName("Runtime"));
    expect(runtimes).toHaveLength(1);
    expect(runtimes[0].getAttribute("resid")).toBe("Taskpane.Url");
    expect(runtimes[0].getAttribute("lifetime")).toBe("long");

    const functionFile = override.getElementsByTagName("FunctionFile")[0];
    expect(functionFile.getAttribute("resid")).toBe("Taskpane.Url");
  });

  it("puts every ShowTaskpane action on Taskpane.Url", () => {
    const override = v1_1(parseManifest());
    const showTaskpanes = Array.from(override.getElementsByTagName("Action")).filter(
      (el) => el.getAttribute("xsi:type") === "ShowTaskpane",
    );
    expect(showTaskpanes.length).toBeGreaterThan(0);
    for (const action of showTaskpanes) {
      const sourceLocation = action.getElementsByTagName("SourceLocation")[0];
      expect(sourceLocation.getAttribute("resid")).toBe("Taskpane.Url");
    }
  });

  it("has eight controls in LatticeGroup", () => {
    const override = v1_1(parseManifest());
    const group = Array.from(override.getElementsByTagName("Group")).find((el) => el.getAttribute("id") === "LatticeGroup");
    expect(group).toBeTruthy();
    expect(group!.getElementsByTagName("Control")).toHaveLength(8);
  });

  it("has six items under ContextMenuText", () => {
    const override = v1_1(parseManifest());
    const officeMenu = Array.from(override.getElementsByTagName("OfficeMenu")).find((el) => el.getAttribute("id") === "ContextMenuText");
    expect(officeMenu).toBeTruthy();
    expect(officeMenu!.getElementsByTagName("Item")).toHaveLength(6);
  });

  it("uses exactly COMMAND_IDS without showPane as its set of FunctionNames", () => {
    const override = v1_1(parseManifest());
    const names = new Set(Array.from(override.getElementsByTagName("FunctionName")).map((el) => el.textContent ?? ""));
    const expected = new Set(COMMAND_IDS.filter((id) => id !== "showPane"));
    expect(names).toEqual(expected);
  });

  it("defines every referenced resid, each at most 32 characters", () => {
    const override = v1_1(parseManifest());
    const definedIds = new Set(
      ["bt:Image", "bt:Url", "bt:String"]
        .flatMap((tag) => Array.from(override.getElementsByTagName(tag)))
        .map((el) => el.getAttribute("id"))
        .filter((id): id is string => id !== null),
    );

    const referencedResids = ["bt:Image", "Runtime", "FunctionFile", "SourceLocation", "Label", "Title", "Description"]
      .flatMap((tag) => Array.from(override.getElementsByTagName(tag)))
      .map((el) => el.getAttribute("resid"))
      .filter((resid): resid is string => resid !== null);

    expect(referencedResids.length).toBeGreaterThan(0);
    for (const resid of referencedResids) {
      expect(resid.length).toBeLessThanOrEqual(32);
      expect(definedIds.has(resid), `resid "${resid}" is not defined in Resources`).toBe(true);
    }
  });
});
