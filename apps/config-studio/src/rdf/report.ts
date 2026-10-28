// SPDX-License-Identifier: MPL-2.0
// Reads a job graph (contracts/config-studio/README.md, "Jobs") into what the studio shows:
// status, findings, artefacts and gaps.

import { CST, Graph, SH, compact, localName, type Term } from "@lattice/authoring-domain";

export type JobStatus = "Queued" | "Running" | "Succeeded" | "Failed";
export type Severity = "Violation" | "Warning" | "Info";

export interface Issue {
  severity: Severity;
  message: string;
  focus?: string;
  path?: string;
  code?: string;
  source: "shacl" | "compiler" | "studio";
  shape?: string;
}

export interface Artefact {
  path: string;
  mediaType: string;
  content: string;
  group: string;
}

export interface Gap {
  group: string;
  obligation: string;
  message: string;
}

export type Outcome = "Resolved" | "Fallback" | "Conflict" | "Unresolved";

/** A contract's resolution for one time segment and one set of active scopes. */
export interface Resolution {
  contract: string;
  from?: string;
  to?: string;
  context: string[];
  outcome: Outcome;
  scheme?: string;
  binding?: string;
  tied: string[];
}

export type Decision = "Permitted" | "Denied" | "Undetermined";

/** A concept condition's decision for one member of its resolved scheme. */
export interface Expansion {
  condition: string;
  concept: string;
  decision: Decision;
}

/** A question decided by its condition's compiled query. */
export interface TestResult {
  question: string;
  condition: string;
  decision: Decision | "NotTested";
  diagnostic?: string;
  passed?: boolean;
}

export interface Job {
  iri: string;
  kind: "Validate" | "Compile" | "Assemble";
  target: "Persistence" | "Surface" | "Vocabulary" | "Quantification" | "Eligibility";
  status: JobStatus;
  submittedAt?: string;
  finishedAt?: string;
  conforms?: boolean;
  failure?: string;
  issues: Issue[];
  artefacts: Artefact[];
  gaps: Gap[];
  resolutions: Resolution[];
  expansions: Expansion[];
  tests: TestResult[];
}

export function readJob(graph: Graph, iri: string): Job {
  const local = (p: string) => {
    const v = graph.value(iri, CST(p));
    return v ? localName(v) : undefined;
  };
  const report = graph.object(iri, CST("report"));
  const conforms = graph.value(iri, CST("conforms"));
  return {
    iri,
    kind: (local("kind") ?? "Validate") as Job["kind"],
    target: (local("target") ?? "Persistence") as Job["target"],
    status: (local("status") ?? "Queued") as JobStatus,
    submittedAt: graph.value(iri, CST("submittedAt")),
    finishedAt: graph.value(iri, CST("finishedAt")),
    conforms: conforms === undefined ? undefined : conforms === "true",
    failure: graph.value(iri, CST("failureMessage")),
    issues: report ? readIssues(graph, report) : [],
    artefacts: graph
      .objects(iri, CST("artefact"))
      .map((a) => ({
        path: graph.value(a, CST("path")) ?? "",
        mediaType: graph.value(a, CST("mediaType")) ?? "text/plain",
        content: graph.value(a, CST("content")) ?? "",
        group: graph.value(a, CST("group")) ?? "",
      }))
      .sort((a, b) => a.group.localeCompare(b.group) || a.path.localeCompare(b.path)),
    gaps: graph
      .objects(iri, CST("gap"))
      .map((g) => ({
        group: graph.value(g, CST("group")) ?? "",
        obligation: graph.value(g, CST("obligation")) ?? "",
        message: graph.value(g, CST("message")) ?? "",
      }))
      .sort((a, b) => a.group.localeCompare(b.group) || a.obligation.localeCompare(b.obligation)),
    resolutions: graph.objects(iri, CST("resolution")).map((r) => ({
      contract: graph.value(r, CST("contract")) ?? "",
      from: graph.value(r, CST("validFrom")),
      to: graph.value(r, CST("validTo")),
      context: graph.objects(r, CST("context")).map((t) => t.value).sort(),
      outcome: localName(graph.value(r, CST("outcome")) ?? CST("Unresolved")) as Outcome,
      scheme: graph.value(r, CST("scheme")),
      binding: graph.value(r, CST("binding")),
      tied: graph.objects(r, CST("tied")).map((t) => t.value).sort(),
    })),
    expansions: graph.objects(iri, CST("expansion")).map((e) => ({
      condition: graph.value(e, CST("condition")) ?? "",
      concept: graph.value(e, CST("concept")) ?? "",
      decision: localName(graph.value(e, CST("decision")) ?? CST("Undetermined")) as Decision,
    })),
    tests: graph.objects(iri, CST("testResult")).map((t) => {
      const passed = graph.value(t, CST("passed"));
      return {
        question: graph.value(t, CST("question")) ?? "",
        condition: graph.value(t, CST("condition")) ?? "",
        decision: localName(graph.value(t, CST("decision")) ?? CST("Undetermined")) as TestResult["decision"],
        diagnostic: graph.value(t, CST("diagnostic")),
        passed: passed === undefined ? undefined : passed === "true",
      };
    }),
  };
}

export function readIssues(graph: Graph, report: Term): Issue[] {
  return graph
    .objects(report, SH("result"))
    .map((r): Issue => {
      const code = graph.value(r, CST("code"));
      const path = graph.object(r, SH("resultPath"));
      const shape = graph.object(r, SH("sourceShape"));
      return {
        severity: (localName(graph.value(r, SH("resultSeverity")) ?? SH("Violation")) as Severity) ?? "Violation",
        message: friendly(graph.value(r, SH("sourceConstraintComponent")), graph.value(r, SH("resultMessage")) ?? code ?? "A constraint is not met."),
        focus: graph.value(r, SH("focusNode")),
        path: path?.termType === "NamedNode" ? path.value : undefined,
        code,
        source: code ? "compiler" : "shacl",
        shape: shape?.termType === "NamedNode" ? compact(shape.value) : undefined,
      };
    })
    .sort(bySeverity);
}

const RANK: Record<Severity, number> = { Violation: 0, Warning: 1, Info: 2 };

export function bySeverity(a: Issue, b: Issue): number {
  return RANK[a.severity] - RANK[b.severity] || (a.focus ?? "").localeCompare(b.focus ?? "") || a.message.localeCompare(b.message);
}

export function finished(job: Job): boolean {
  return job.status === "Succeeded" || job.status === "Failed";
}

/** pySHACL writes its core components' messages in terms of the focus node's IRI, which the field
 * the finding sits on already shows. These say what to do instead. */
const PHRASES: Record<string, string> = {
  MinCountConstraintComponent: "Required. Set a value.",
  MaxCountConstraintComponent: "Too many values. Keep one.",
  ClassConstraintComponent: "The value is not of the class this property expects.",
  DatatypeConstraintComponent: "The value is not of the datatype this property expects.",
  InConstraintComponent: "The value is not one this property allows.",
  NodeKindConstraintComponent: "The value is not the kind of term this property expects.",
};

function friendly(component: string | undefined, message: string): string {
  const phrase = component ? PHRASES[localName(component)] : undefined;
  return phrase && /^(Less|More) than \d+ values|^Value .* (does not|not)/.test(message) ? phrase : message;
}
