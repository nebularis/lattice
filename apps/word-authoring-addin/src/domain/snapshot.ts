/**
 * Builds a `DocumentSnapshot` from a parsed document and the document's own metadata (plan WA8
 * section "Snapshot builder").
 */
import type { AuthoringMetadata } from "../word/port";
import { validate } from "./schemas";
import type { ParsedDocument } from "./ooxml";
import type { DocumentSnapshot, VariableDeclaration } from "./types";

export interface BuildSnapshotResult {
  snapshot: DocumentSnapshot;
  warnings: string[];
}

export function buildSnapshot(parsed: ParsedDocument, metadata: AuthoringMetadata): BuildSnapshotResult {
  const warnings = [...parsed.warnings];
  const declared = new Map<string, VariableDeclaration>(metadata.variables.map((v) => [v.variableKey, v]));

  for (const section of parsed.sections) {
    for (const element of section.elements) {
      for (const part of element.parts) {
        if (part.kind === "variable" && !declared.has(part.variableKey)) {
          declared.set(part.variableKey, { variableKey: part.variableKey, label: part.variableKey, valueType: "text" });
          warnings.push(`variable "${part.variableKey}" was not declared in the metadata; added with value type "text"`);
        }
      }
    }
  }

  const snapshot: DocumentSnapshot = {
    schemaVersion: "0.1.0",
    documentId: metadata.documentId,
    templateId: metadata.templateId,
    title: metadata.title,
    sections: parsed.sections,
    variables: [...declared.values()],
    unmarked: parsed.unmarked,
  };

  const errors = validate("document-snapshot", snapshot);
  if (errors.length > 0) {
    throw new Error(`built an invalid document-snapshot: ${errors.join("; ")}`);
  }

  return { snapshot, warnings };
}
