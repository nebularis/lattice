import { describe, expect, it } from "vitest";
import { writePackage, writeSections } from "../domain/ooxml";
import { FakeWordPort } from "./fakePort";

const ELEMENT_ID = "00000009-0000-4000-8000-000000000010";

async function freshPort(): Promise<FakeWordPort> {
  const port = new FakeWordPort();
  await port.insertOoxml(
    writePackage(
      writeSections([
        {
          sectionKey: "commitment",
          heading: "Commitment",
          elements: [
            {
              elementId: ELEMENT_ID,
              kind: "clause",
              definedTerm: null,
              parts: [
                { kind: "literal", text: "Pay " },
                { kind: "variable", variableKey: "amt", text: "GBP 1" },
                { kind: "literal", text: " now." },
              ],
            },
          ],
        },
      ]),
    ),
  );
  return port;
}

describe("FakeWordPort.markSelection (S9-01)", () => {
  it("marks inside a literal, splitting the part", async () => {
    const port = await freshPort();
    port.select(ELEMENT_ID, 0, 3);

    const result = await port.markSelection({ kind: "variable", variableKey: "test-var", label: "Pay" });

    expect(result).toEqual({ ok: true });
    const element = port.model().sections[0].elements[0];
    expect(element.parts).toEqual([
      { kind: "variable", variableKey: "test-var", text: "Pay" },
      { kind: "literal", text: " " },
      { kind: "variable", variableKey: "amt", text: "GBP 1" },
      { kind: "literal", text: " now." },
    ]);
  });

  it("refuses a selection that crosses a part boundary", async () => {
    const port = await freshPort();
    port.select(ELEMENT_ID, 2, 6);

    const result = await port.markSelection({ kind: "variable", variableKey: "x", label: "x" });

    expect(result).toEqual({ ok: false, reason: "spans-parts" });
  });

  it("refuses a selection already inside a variable", async () => {
    const port = await freshPort();
    port.select(ELEMENT_ID, 4, 6);

    const result = await port.markSelection({ kind: "variable", variableKey: "x", label: "x" });

    expect(result).toEqual({ ok: false, reason: "already-marked" });
  });

  it("refuses with no selection", async () => {
    const port = await freshPort();

    const result = await port.markSelection({ kind: "variable", variableKey: "x", label: "x" });

    expect(result).toEqual({ ok: false, reason: "no-selection" });
  });

  it("refuses an unknown element id", async () => {
    const port = await freshPort();
    port.select("00000009-0000-4000-8000-000000000099", 0, 1);

    const result = await port.markSelection({ kind: "variable", variableKey: "x", label: "x" });

    expect(result).toEqual({ ok: false, reason: "outside-element" });
  });
});
