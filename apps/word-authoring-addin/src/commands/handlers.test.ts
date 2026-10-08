import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it, vi } from "vitest";
import { writePackage, writeSections, type WritableSection } from "../domain/ooxml";
import { markResultMessage } from "../app/markMessages";
import { UiBridge } from "../app/uiBridge";
import type { AuthoringTemplate, DocumentSnapshot } from "../domain/types";
import { FakeWordPort } from "../word/fakePort";
import type { DocumentPort, MarkResult } from "../word/port";
import { createHandlers } from "./handlers";
import type { CommandEvent, HandlerDeps } from "./handlers";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../../../..");

function loadJson<T>(relativePath: string): T {
  return JSON.parse(readFileSync(path.join(REPO_ROOT, relativePath), "utf-8")) as T;
}

const SAMPLE = loadJson<DocumentSnapshot>("contracts/authoring/samples/facility-agreement.json");
const TEMPLATE = loadJson<AuthoringTemplate>("contracts/authoring/templates/facility-agreement.json");

function offsetOf(elementId: string, needle: string): { start: number; end: number } {
  const element = SAMPLE.sections.flatMap((section) => section.elements).find((candidate) => candidate.elementId === elementId)!;
  const text = element.parts.map((part) => part.text).join("");
  const start = text.indexOf(needle);
  if (start === -1) throw new Error(`"${needle}" not found in element ${elementId}`);
  return { start, end: start + needle.length };
}

async function insertFacility(port: FakeWordPort): Promise<void> {
  const headingBySectionKey = new Map(TEMPLATE.sections.map((section) => [section.sectionKey, section.heading]));
  const writable: WritableSection[] = SAMPLE.sections.map((section) => ({
    sectionKey: section.sectionKey,
    heading: headingBySectionKey.get(section.sectionKey) ?? section.sectionKey,
    elements: section.elements,
  }));
  await port.insertOoxml(writePackage(writeSections(writable)));
}

function makeDeps(): HandlerDeps & { port: FakeWordPort; bridge: UiBridge; showPane: ReturnType<typeof vi.fn> } {
  const port = new FakeWordPort();
  const bridge = new UiBridge();
  const showPane = vi.fn();
  return { port, bridge, showPane, newUuid: () => "00000009-0000-4000-8000-000000000099" };
}

function fakeEvent(): { event: CommandEvent; completedCount: () => number } {
  let completedCount = 0;
  return { event: { completed: () => (completedCount += 1) }, completedCount: () => completedCount };
}

class ThrowingPort implements DocumentPort {
  async readBodyOoxml(): Promise<string> {
    throw new Error("boom");
  }
  async readMetadata(): Promise<null> {
    throw new Error("boom");
  }
  async writeMetadata(): Promise<void> {
    throw new Error("boom");
  }
  async insertOoxml(): Promise<void> {
    throw new Error("boom");
  }
  async readSelection(): Promise<{ text: string; elementId: string | null }> {
    throw new Error("boom");
  }
  async wrapSelectionAsElement(): Promise<MarkResult> {
    throw new Error("boom");
  }
  async markSelection(): Promise<MarkResult> {
    throw new Error("boom");
  }
  async markOccurrence(): Promise<boolean> {
    throw new Error("boom");
  }
  async unmarkSelection(): Promise<MarkResult> {
    throw new Error("boom");
  }
}

// S9a-03 ----------------------------------------------------------------------------------------

describe("handlers over the fake port, a valid selection (S9a-03)", () => {
  it("markClause wraps the unmarked selection into a new clause, and completes once", async () => {
    const deps = makeDeps();
    await deps.port.insertOoxml(writePackage(writeSections([{ sectionKey: "commitment", heading: "Commitment", elements: [] }])));
    deps.port.selectUnmarked("commitment", "Borrower shall pay the fee.");
    const handlers = createHandlers(deps);
    const { event, completedCount } = fakeEvent();

    await handlers.markClause(event);

    expect(completedCount()).toBe(1);
    const model = deps.port.model();
    expect(model.sections[0].elements).toHaveLength(1);
    expect(model.sections[0].elements[0].kind).toBe("clause");
  });

  it("markDefinition wraps the unmarked selection into a new definition, and completes once", async () => {
    const deps = makeDeps();
    await deps.port.insertOoxml(writePackage(writeSections([{ sectionKey: "definitions", heading: "Definitions", elements: [] }])));
    deps.port.selectUnmarked("definitions", "\u201cBorrower\u201d means the company.");
    const handlers = createHandlers(deps);
    const { event, completedCount } = fakeEvent();

    await handlers.markDefinition(event);

    expect(completedCount()).toBe(1);
    const model = deps.port.model();
    expect(model.sections[0].elements[0].kind).toBe("definition");
  });

  it("markTerm sets the defined term on a valid selection, and completes once", async () => {
    const deps = makeDeps();
    await insertFacility(deps.port);
    const { start, end } = offsetOf("00000001-0000-4000-8000-000000000001", "Borrower");
    deps.port.select("00000001-0000-4000-8000-000000000001", start, end);
    const handlers = createHandlers(deps);
    const { event, completedCount } = fakeEvent();

    await handlers.markTerm(event);

    expect(completedCount()).toBe(1);
    const model = deps.port.model();
    const element = model.sections.flatMap((s) => s.elements).find((e) => e.elementId === "00000001-0000-4000-8000-000000000001")!;
    expect(element.definedTerm).toBe("Borrower");
  });

  it("unmark reverts a marked part on a valid selection, and completes once", async () => {
    const deps = makeDeps();
    await insertFacility(deps.port);
    const { start, end } = offsetOf("00000001-0000-4000-8000-000000000006", "GBP 10,000,000");
    deps.port.select("00000001-0000-4000-8000-000000000006", start, end);
    const handlers = createHandlers(deps);
    const { event, completedCount } = fakeEvent();

    await handlers.unmark(event);

    expect(completedCount()).toBe(1);
    const model = deps.port.model();
    const element = model.sections.flatMap((s) => s.elements).find((e) => e.elementId === "00000001-0000-4000-8000-000000000006")!;
    expect(element.parts.some((part) => part.kind === "variable")).toBe(false);
  });

  it("a port that throws posts a message, opens the pane, and still completes once", async () => {
    const bridge = new UiBridge();
    const showPane = vi.fn();
    const handlers = createHandlers({ port: new ThrowingPort(), bridge, showPane, newUuid: () => "x" });
    const { event, completedCount } = fakeEvent();

    await handlers.markClause(event);

    expect(completedCount()).toBe(1);
    expect(showPane).toHaveBeenCalledTimes(1);
    expect(bridge.getState().tab).toBe("markup");
    expect(bridge.getState().message).toBe("boom");
  });
});

// S9a-04 ------------------------------------------------------------------------------------------

describe("markVariable (S9a-04)", () => {
  it("posts a draft from the selection, opens the pane, and marks nothing yet", async () => {
    const deps = makeDeps();
    await deps.port.insertOoxml(
      writePackage(
        writeSections([
          {
            sectionKey: "commitment",
            heading: "Commitment",
            elements: [
              { elementId: "00000009-0000-4000-8000-000000000001", kind: "clause", definedTerm: null, parts: [{ kind: "literal", text: "Pay GBP 250 now." }] },
            ],
          },
        ]),
      ),
    );
    deps.port.select("00000009-0000-4000-8000-000000000001", 4, 11);
    const handlers = createHandlers(deps);

    await handlers.markVariable({ completed: () => {} });

    expect(deps.bridge.getState().variableDraft).toEqual({ key: "gbp-250", label: "GBP 250", valueType: "money" });
    expect(deps.bridge.getState().tab).toBe("markup");
    expect(deps.showPane).toHaveBeenCalledTimes(1);
    const model = deps.port.model();
    expect(model.sections[0].elements[0].parts).toEqual([{ kind: "literal", text: "Pay GBP 250 now." }]);
  });

  it("an empty selection shows the no-selection message", async () => {
    const deps = makeDeps();
    const handlers = createHandlers(deps);

    await handlers.markVariable({ completed: () => {} });

    expect(deps.bridge.getState().message).toBe(markResultMessage("no-selection"));
    expect(deps.showPane).toHaveBeenCalledTimes(1);
  });
});

// S9a-05 ------------------------------------------------------------------------------------------

describe("markDefinedTerm against the facility sample (S9a-05)", () => {
  it("on 'Loans' marks a reference part to the Loan definition", async () => {
    const deps = makeDeps();
    await insertFacility(deps.port);
    const { start, end } = offsetOf("00000001-0000-4000-8000-000000000014", "Loans");
    deps.port.select("00000001-0000-4000-8000-000000000014", start, end);
    const handlers = createHandlers(deps);

    await handlers.markDefinedTerm({ completed: () => {} });

    const model = deps.port.model();
    const element = model.sections.flatMap((s) => s.elements).find((e) => e.elementId === "00000001-0000-4000-8000-000000000014")!;
    const referencePart = element.parts.find((part) => part.kind === "reference" && part.text === "Loans");
    expect(referencePart && "targetElementId" in referencePart ? referencePart.targetElementId : undefined).toBe(
      "00000001-0000-4000-8000-000000000003",
    );
  });

  it("on 'Agent' (no single match) posts a reference draft, opens the pane, and marks nothing", async () => {
    const deps = makeDeps();
    await insertFacility(deps.port);
    const { start, end } = offsetOf("00000001-0000-4000-8000-000000000013", "Agent");
    deps.port.select("00000001-0000-4000-8000-000000000013", start, end);
    const handlers = createHandlers(deps);

    await handlers.markDefinedTerm({ completed: () => {} });

    expect(deps.bridge.getState().referenceDraft).toEqual({ text: "Agent" });
    expect(deps.bridge.getState().tab).toBe("markup");
    expect(deps.showPane).toHaveBeenCalledTimes(1);
    const model = deps.port.model();
    const element = model.sections.flatMap((s) => s.elements).find((e) => e.elementId === "00000001-0000-4000-8000-000000000013")!;
    const originalElement = SAMPLE.sections.flatMap((s) => s.elements).find((e) => e.elementId === "00000001-0000-4000-8000-000000000013")!;
    expect(element.parts).toEqual(originalElement.parts);
  });
});
