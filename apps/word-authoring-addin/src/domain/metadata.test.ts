import { describe, expect, it } from "vitest";
import { fromXml, toXml } from "./metadata";
import type { AuthoringMetadata } from "../word/port";

describe("metadata toXml/fromXml round trip", () => {
  it("round-trips a metadata object with a revision and variables", () => {
    const metadata: AuthoringMetadata = {
      documentId: "00000001-0000-4000-8000-000000000000",
      templateId: "facility-agreement",
      title: "Facility Agreement (sample)",
      revision: 3,
      variables: [
        { variableKey: "facility-amount", label: "Facility amount", valueType: "money" },
        { variableKey: "margin", label: "Margin", valueType: "percentage" },
      ],
    };

    expect(fromXml(toXml(metadata))).toEqual(metadata);
  });

  it("round-trips a null revision and no variables", () => {
    const metadata: AuthoringMetadata = {
      documentId: "00000001-0000-4000-8000-000000000000",
      templateId: "facility-agreement",
      title: "t",
      revision: null,
      variables: [],
    };

    expect(fromXml(toXml(metadata))).toEqual(metadata);
  });
});
