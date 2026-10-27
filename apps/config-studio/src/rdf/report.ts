// SPDX-License-Identifier: MPL-2.0
// Reads a job graph (contracts/config-studio/README.md, "Jobs") into what the studio shows:
// status, findings, artefacts and gaps.

import { Graph, type Term } from "./graph";
import { CST, SH, compact, localName } from "./ns";

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

export interface Job {
  iri: string;
  kind: "Validate" | "Compile";
  target: "Persistence" | "Surface";
  status: JobStatus;
  submittedAt?: string;
  finishedAt?: string;
  conforms?: boolean;
  failure?: string;
  issues: Issue[];
  artefacts: Artefact[];
  gaps: Gap[];
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
