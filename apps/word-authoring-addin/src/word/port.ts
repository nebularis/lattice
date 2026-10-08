/**
 * The seam between the add-in's domain logic and Word (plan WA8 section "`DocumentPort`"). WA9
 * implements this over Office.js (`officePort.ts`) and over an in-memory model for tests and the
 * harness (`fakePort.ts`); WA8 only defines the shape.
 */
import type { VariableDeclaration } from "../domain/types";

export type MarkResultReason = "no-selection" | "outside-element" | "outside-section" | "already-marked" | "spans-parts";

export type MarkResult = { ok: true } | { ok: false; reason: MarkResultReason };

export type InlineMark =
  | { kind: "variable"; variableKey: string; label: string }
  | { kind: "reference"; targetElementId: string; term: string }
  | { kind: "term" };

/** The document's own metadata, stored as a custom XML part in namespace
 * `urn:nebularis:lattice:authoring:1` (`metadata.ts`). */
export interface AuthoringMetadata {
  documentId: string;
  templateId: string;
  title: string;
  revision: number | null;
  variables: VariableDeclaration[];
}

export interface DocumentPort {
  readBodyOoxml(): Promise<string>;
  readMetadata(): Promise<AuthoringMetadata | null>;
  writeMetadata(metadata: AuthoringMetadata): Promise<void>;
  insertOoxml(packageXml: string): Promise<void>;
  /** The selected text, and the id of the clause or definition that contains it (null outside one). */
  readSelection(): Promise<{ text: string; elementId: string | null }>;
  wrapSelectionAsElement(kind: "clause" | "definition", elementId: string): Promise<MarkResult>;
  markSelection(mark: InlineMark): Promise<MarkResult>;
  markOccurrence(elementId: string, text: string, occurrence: number, mark: InlineMark): Promise<boolean>;
  unmarkSelection(): Promise<MarkResult>;
}
