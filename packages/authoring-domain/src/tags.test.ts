import { describe, expect, it } from "vitest";
import { decode, encode, title } from "./tags";

describe("tag codec", () => {
  it("round-trips every kind", () => {
    expect(decode(encode("section", "definitions"))).toEqual({ kind: "section", value: "definitions" });

    const uuid = "00000001-0000-4000-8000-000000000001";
    expect(decode(encode("clause", uuid))).toEqual({ kind: "clause", value: uuid });
    expect(decode(encode("definition", uuid))).toEqual({ kind: "definition", value: uuid });
    expect(decode(encode("reference", uuid))).toEqual({ kind: "reference", value: uuid });

    expect(decode(encode("term"))).toEqual({ kind: "term", value: null });
    expect(decode(encode("variable", "facility-amount"))).toEqual({ kind: "variable", value: "facility-amount" });
  });

  it("throws encoding a value whose length exceeds the kind's own pattern (a 65-character attempt)", () => {
    expect(() => encode("variable", "a".repeat(65))).toThrow();
    expect(() => encode("section", "a".repeat(65))).toThrow();
  });

  it("throws encoding an upper-case key", () => {
    expect(() => encode("variable", "Facility-Amount")).toThrow();
  });

  it("returns null decoding an unrecognised tag", () => {
    expect(decode("lat:x:1")).toBeNull();
  });

  it("returns null decoding a recognised prefix with a value that fails the pattern", () => {
    expect(decode("lat:v:Upper-Case")).toBeNull();
    expect(decode("lat:e:not-a-uuid")).toBeNull();
  });
});

describe("title", () => {
  it("builds the title per kind and cuts it to 64 characters", () => {
    expect(title("clause", undefined)).toBe("Clause");
    expect(title("definition", undefined)).toBe("Definition");
    expect(title("term", undefined)).toBe("Term");
    expect(title("section", "Definitions")).toBe("Section: Definitions");
    expect(title("variable", "Facility amount")).toBe("Variable: Facility amount");
    expect(title("reference", "Borrower")).toBe("Defined term: Borrower");

    const long = "x".repeat(100);
    expect(title("variable", long).length).toBe(64);
  });
});
