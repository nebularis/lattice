/**
 * The document model the Word add-in edits, the analysis view the studio's `analyse` job gives
 * back, and the template and sample summaries the studio serves. The document travels as XML in
 * LATTICE's markup (`markup.ts`), never as JSON.
 */

export type Uuid = string;
export type Key = string;
export type SectionKey = string;
export type RevisionHash = string;
export type ValueType = "money" | "percentage" | "date" | "duration" | "number" | "text" | "party";

export type TermKind =
  | "Obligation"
  | "Prohibition"
  | "Permission"
  | "Exclusion"
  | "Power"
  | "Definition"
  | "Deeming";

export type ElementKind = "clause" | "definition";

export type Severity = "violation" | "warning" | "info";

export interface GraphRef {
  tenantId: "poc";
  projectId: "word-authoring";
  graphIri: string;
  revisionHash: RevisionHash;
}

export interface VariableDeclaration {
  variableKey: Key;
  label: string;
  valueType: ValueType;
}

export type FindingKind =
  | "unknown-section"
  | "required-section-empty"
  | "element-kind-not-allowed"
  | "unmarked-text"
  | "term-kind-not-allowed"
  | "no-term-kind";

export interface Finding {
  kind: FindingKind;
  severity: Severity;
  sectionKey: SectionKey | null;
  elementId: Uuid | null;
  message: string;
}

export type SpanRole =
  | "fixed"
  | "ignorable"
  | "slot-variable"
  | "slot-constant"
  | "slot-text"
  | "modal"
  | "connective"
  | "unmatched";

export interface Span {
  start: number;
  end: number;
  role: SpanRole;
  partIndex: number;
}

export type AnalysisBasis = "form" | "keyword" | "none";

export interface ElementAnalysis {
  elementId: Uuid;
  objectId: string;
  sectionKey: SectionKey;
  kind: ElementKind;
  text: string;
  relationClass: TermKind | null;
  basis: AnalysisBasis;
  formId: string | null;
  leTemplate: string | null;
  leSentence: string | null;
  spans: Span[];
}

export type GraphNodeKind = "relation" | "element" | "role" | "variable";

export interface GraphNode {
  id: string;
  label: string;
  kind: GraphNodeKind;
}

export interface GraphEdge {
  from: string;
  to: string;
  label: string;
}

export interface GraphView {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface FormsProfile {
  profileId: string;
  version: string;
}

export interface Analysis {
  formsProfile: FormsProfile;
  elements: ElementAnalysis[];
  leProgram: string;
  graphView: GraphView;
}

// --- the document model ------------------------------------------------------------------------

export interface LiteralPart {
  kind: "literal";
  text: string;
}

export interface VariablePart {
  kind: "variable";
  variableKey: Key;
  text: string;
}

export interface ReferencePart {
  kind: "reference";
  targetElementId: Uuid;
  text: string;
}

export type Part = LiteralPart | VariablePart | ReferencePart;

export interface DocumentElement {
  elementId: Uuid;
  kind: ElementKind;
  definedTerm: string | null;
  parts: Part[];
}

export interface Section {
  sectionKey: SectionKey;
  elements: DocumentElement[];
}

export interface Unmarked {
  sectionKey: SectionKey | null;
  text: string;
}

export interface DocumentSnapshot {
  schemaVersion: "0.1.0";
  documentId: Uuid;
  templateId: Key;
  title: string;
  sections: Section[];
  variables: VariableDeclaration[];
  unmarked: Unmarked[];
}

// --- analysis.json, the analyse job's analysis view -----------------------------------------------

export interface AnalysisView {
  documentId: Uuid;
  revision: number;
  analysis: Analysis;
  conformance: Finding[];
  proposalGraph: GraphRef;
}

// --- the studio's document templates and samples ---------------------------------------------------

export interface TemplateSection {
  sectionKey: SectionKey;
  heading: string;
  elementKinds: ElementKind[];
  allowedTermKinds: TermKind[];
  required: boolean;
  guidance: string;
}

export interface AuthoringTemplate {
  templateId: Key;
  title: string;
  sections: TemplateSection[];
  variables: VariableDeclaration[];
}

export interface SampleSummary {
  sampleId: Key;
  title: string;
}
