import { describe, expect, it } from "vitest";
import { escapeWordSearch, occurrenceIndex } from "./offsets";

describe("occurrenceIndex", () => {
  it("finds the right occurrence among repeated text, past an astral character", () => {
    const text = "\u{1F600}a cat sat on a cat near the cathedral";
    const first = text.indexOf("cat");
    const second = text.indexOf("cat", first + 1);

    expect(occurrenceIndex(text, first, "cat")).toBe(0);
    expect(occurrenceIndex(text, second, "cat")).toBe(1);
  });

  it("throws when the text does not occur at the given offset", () => {
    expect(() => occurrenceIndex("abc", 1, "zzz")).toThrow();
  });
});

describe("escapeWordSearch", () => {
  it("doubles a literal caret", () => {
    expect(escapeWordSearch("a^b")).toBe("a^^b");
  });

  it("leaves text with no caret unchanged", () => {
    expect(escapeWordSearch("GBP 250")).toBe("GBP 250");
  });
});
