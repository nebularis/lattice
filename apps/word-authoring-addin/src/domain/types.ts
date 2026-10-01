/**
 * TypeScript types for every schema under `contracts/authoring` and `contracts/events` used by
 * the word authoring add-in (ADR-A114, plan WA8). Hand-written, not generated: each name matches
 * the schema's own `$defs` name. Kept free of any dependency on `schemas.ts` so these types can be
 * used (and the modules importing them tested) without an Ajv instance.
 */

// --- common.schema.json -------------------------------------------------------------------------

export type Uuid = string;
export type Key = string;
export type SectionKey = string;
export type RevisionHash = string;
export type Timestamp = string;

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

export interface ValidationResult {
  shapeId: string;
  severity: Severity;
  focusNode: string;
  elementId: Uuid | null;
  message: string;
}

export interface ValidationReport {
  conforms: boolean;
  results: ValidationResult[];
}

export type SuggestionAction = "mark-variable" | "mark-reference" | "none";

export interface Suggestion {
  action: SuggestionAction;
  valueType: ValueType | null;
  suggestedKey: Key | null;
  targetElementId: Uuid | null;
}

export type DetectionKind =
  | "placeholder"
  | "money"
  | "percentage"
  | "date"
  | "duration"
  | "defined-term"
  | "cross-reference";

export interface Detection {
  elementId: Uuid;
  partIndex: number;
  start: number;
  end: number;
  text: string;
  kind: DetectionKind;
  suggestion: Suggestion;
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

export type JobStatus = "queued" | "completed" | "failed";

export interface Job {
  jobId: Uuid;
  status: JobStatus;
}

export interface TemplateSummary {
  templateId: Key;
  title: string;
  domain: Key;
  version: string;
}

export interface SampleSummary {
  sampleId: Key;
  title: string;
  templateId: Key;
}

// --- document-snapshot.schema.json --------------------------------------------------------------

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

// --- snapshot-submission.schema.json ------------------------------------------------------------

export interface SnapshotSubmission {
  baseRevision: number | null;
  snapshot: DocumentSnapshot;
}

// --- snapshot-accepted.schema.json --------------------------------------------------------------

export interface SnapshotAccepted {
  documentId: Uuid;
  revision: number;
  wordingGraph: GraphRef;
  validation: ValidationReport;
  detections: Detection[];
  templateFindings: Finding[];
  job: Job;
}

// --- job-view.schema.json ------------------------------------------------------------------------

export interface JobView {
  jobId: Uuid;
  documentId: Uuid;
  revision: number;
  status: JobStatus;
  error: string | null;
}

// --- document-view.schema.json -------------------------------------------------------------------

export interface DocumentView {
  documentId: Uuid;
  title: string;
  templateId: Key;
  latestRevision: number;
}

// --- analysis-view.schema.json -------------------------------------------------------------------

export interface AnalysisView {
  documentId: Uuid;
  revision: number;
  analysis: Analysis;
  conformance: Finding[];
  proposalGraph: GraphRef;
}

// --- authoring-template.schema.json ---------------------------------------------------------------

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
  version: string;
  title: string;
  domain: Key;
  sections: TemplateSection[];
  variables: VariableDeclaration[];
}

// --- sample-list.schema.json / template-list.schema.json ------------------------------------------

export type SampleList = SampleSummary[];
export type TemplateList = TemplateSummary[];

// --- health.schema.json --------------------------------------------------------------------------

export interface Health {
  status: "ok" | "degraded";
  fuseki: "up" | "down";
  amqp: "up" | "down";
}

// --- error.schema.json ---------------------------------------------------------------------------

export interface ApiErrorBody {
  error: string;
  details: string[];
}

// --- events/wording-analysis-request.schema.json ---------------------------------------------------

export interface WordingAnalysisRequest {
  jobId: Uuid;
  correlationId: string;
  documentId: Uuid;
  revision: number;
  wordingGraph: GraphRef;
  wordingIri: string;
  proposalGraphIri: string;
  requestedAt: Timestamp;
}

// --- events/wording-analysis-result.schema.json ----------------------------------------------------

export interface WordingAnalysisResult {
  jobId: Uuid;
  correlationId: string;
  documentId: Uuid;
  revision: number;
  status: "completed" | "failed";
  error: string | null;
  proposalGraph: GraphRef | null;
  analysis: Analysis | null;
  completedAt: Timestamp;
}
