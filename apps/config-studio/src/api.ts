// SPDX-License-Identifier: MPL-2.0
// The service's HTTP API (contracts/config-studio/README.md). Every body is Turtle.

import { COMMENT, CST, Graph, LABEL, localName } from "@lattice/authoring-domain";
import { readJob, type Job } from "./rdf/report";
import { CONFIG_PARTS, type ConfigPart, type Part } from "./rdf/split";
import { authHeaders } from "./session";

export type GraphName = Part;
export type Target = ConfigPart;

const TURTLE = "text/turtle";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

/** A conditional write lost to another: the caller holds a stale revision. */
export class Conflict extends ApiError {}

async function request(path: string, init: RequestInit = {}): Promise<Response> {
  const response = await fetch(path, { ...init, headers: { Accept: TURTLE, ...authHeaders(), ...init.headers } });
  if (response.status === 412) throw new Conflict(412, "The graph changed since it was loaded.");
  if (!response.ok) throw new ApiError(response.status, (await response.text()) || response.statusText);
  return response;
}

async function turtle(path: string): Promise<{ graph: Graph; text: string; etag: string | null }> {
  const response = await request(path);
  const text = await response.text();
  return { graph: Graph.parse(text), text, etag: response.headers.get("ETag") };
}

export interface WorkspaceSummary {
  id: string;
  iri: string;
  label: string;
  modifiedAt?: string;
  revisions: Record<GraphName, number>;
  /** The id of the sample it was made from, if it was. */
  sample?: string;
  /** Who owns it, if anyone does, and who may read and write it (ADR-A149 decision 9). */
  owner?: string;
  mode: Mode;
}

export type Mode = "locked" | "read-only" | "shared";
export const MODES: Mode[] = ["shared", "read-only", "locked"];
const MODE_NODES: Record<string, Mode> = { Locked: "locked", ReadOnly: "read-only", Shared: "shared" };

export interface Sample {
  id: string;
  label: string;
  comment: string;
}

function summary(graph: Graph, iri: string): WorkspaceSummary {
  const n = (name: GraphName) => Number(graph.value(iri, CST(`${name}Revision`)) ?? 0);
  return {
    id: iri.replace("urn:lattice:studio:ws:", ""),
    iri,
    label: graph.value(iri, LABEL) ?? "Untitled workspace",
    modifiedAt: graph.value(iri, CST("modifiedAt")),
    sample: graph.value(iri, CST("fromSample"))?.replace("urn:lattice:studio:sample:", ""),
    owner: graph.value(iri, CST("owner")),
    mode: MODE_NODES[localName(graph.value(iri, CST("mode")) ?? "")] ?? "shared",
    revisions: Object.fromEntries((["baseline", ...CONFIG_PARTS] as GraphName[]).map((name) => [name, n(name)])) as Record<GraphName, number>,
  };
}

export const api = {
  async vocabulary(): Promise<string> {
    return (await request("/api/vocabulary")).text();
  },

  async samples(): Promise<Sample[]> {
    const { graph } = await turtle("/api/samples");
    return graph
      .ofType(CST("Sample"))
      .map((s) => ({ id: localName(s.value).replace(/^.*:/, ""), label: graph.value(s, LABEL) ?? "", comment: graph.value(s, COMMENT) ?? "" }))
      .sort((a, b) => a.label.localeCompare(b.label));
  },

  async sample(id: string): Promise<Graph> {
    return (await turtle(`/api/samples/${encodeURIComponent(id)}`)).graph;
  },

  async workspaces(): Promise<WorkspaceSummary[]> {
    const { graph } = await turtle("/api/workspaces");
    return graph
      .ofType(CST("Workspace"))
      .map((w) => summary(graph, w.value))
      .sort((a, b) => (b.modifiedAt ?? "").localeCompare(a.modifiedAt ?? ""));
  },

  async workspace(id: string): Promise<WorkspaceSummary> {
    const { graph } = await turtle(`/api/workspaces/${id}`);
    return summary(graph, `urn:lattice:studio:ws:${id}`);
  },

  async createWorkspace(label: string, baseline: Graph, sample?: string): Promise<string> {
    const query = sample ? `?sample=${encodeURIComponent(sample)}` : "";
    const response = await request(`/api/workspaces${query}`, {
      method: "POST",
      headers: { "Content-Type": TURTLE, Slug: encodeURIComponent(label) },
      body: baseline.toTurtle(),
    });
    return (response.headers.get("Location") ?? "").split("/").pop() ?? "";
  },

  /** Recreates a workspace from a file `exportUrl` gave, under a new id. */
  async importWorkspace(trig: string, label?: string): Promise<string> {
    const headers: Record<string, string> = { "Content-Type": "application/trig" };
    if (label) headers.Slug = encodeURIComponent(label);
    const response = await request("/api/workspaces", { method: "POST", headers, body: trig });
    return (response.headers.get("Location") ?? "").split("/").pop() ?? "";
  },

  /** Every graph of a workspace but its jobs, as a TriG file to download. */
  exportUrl(id: string): string {
    return `/api/workspaces/${id}/export`;
  },

  /** Sets the workspace's mode. Only its owner or an administrator may. */
  async setMode(id: string, mode: Mode): Promise<WorkspaceSummary> {
    const response = await request(`/api/workspaces/${id}/access?mode=${mode}`, { method: "POST" });
    return summary(Graph.parse(await response.text()), `urn:lattice:studio:ws:${id}`);
  },

  async deleteWorkspace(id: string): Promise<void> {
    await request(`/api/workspaces/${id}`, { method: "DELETE" });
  },

  /** The optional features the deployment turned on. An old service without the endpoint has none. */
  async features(): Promise<string[]> {
    try {
      const response = await fetch("/api/features", { headers: authHeaders() });
      return response.ok ? ((await response.json()) as { features?: string[] }).features ?? [] : [];
    } catch {
      return [];
    }
  },

  async graph(id: string, name: GraphName): Promise<{ graph: Graph; revision: string }> {
    const { graph, etag } = await turtle(`/api/workspaces/${id}/graphs/${name}`);
    return { graph, revision: etag ?? '"0"' };
  },

  /** Returns the new revision's ETag. Throws Conflict when `revision` is stale. */
  async save(id: string, name: GraphName, graph: Graph, revision: string): Promise<string> {
    const response = await request(`/api/workspaces/${id}/graphs/${name}`, {
      method: "PUT",
      headers: { "Content-Type": TURTLE, "If-Match": revision },
      body: graph.toTurtle(),
    });
    return response.headers.get("ETag") ?? revision;
  },

  async submit(id: string, kind: "validate" | "compile" | "assemble" | "propose" | "dry-run", target: Target | "sentence-forms" | "language-model" | "odrl" | "mapping-language-model" | "rml", config: Graph): Promise<string> {
    const response = await request(`/api/workspaces/${id}/jobs?kind=${kind}&target=${target}`, {
      method: "POST",
      headers: { "Content-Type": TURTLE },
      body: config.toTurtle(),
    });
    return (response.headers.get("Location") ?? "").split("/").pop() ?? "";
  },

  /** Runs a finished compile job's XSLT stylesheets or JOLT chains over a sample in XML or JSON, through the transforms
   * worker, and answers at once. The run is never stored (ADR-A148). */
  async transform(id: string, compileJob: string, mediaType: string, sample: string): Promise<Job> {
    const response = await request(`/api/workspaces/${id}/transforms?job=${encodeURIComponent(compileJob)}`, {
      method: "POST",
      headers: { "Content-Type": mediaType },
      body: sample,
    });
    const graph = Graph.parse(await response.text());
    const run = graph.ofType(CST("Transform"))[0];
    if (!run) throw new ApiError(502, "the reply does not describe the run");
    return readJob(graph, run.value);
  },

  async job(jobId: string): Promise<Job> {
    const { graph } = await turtle(`/api/jobs/${jobId}`);
    return readJob(graph, `urn:lattice:studio:job:${jobId}`);
  },

  async compileJobs(id: string): Promise<Job[]> {
    const { graph } = await turtle(`/api/workspaces/${id}/jobs`);
    return graph
      .ofType(CST("Job"))
      .map((j) => readJob(graph, j.value))
      .sort((a, b) => (b.submittedAt ?? "").localeCompare(a.submittedAt ?? ""));
  },

  async deleteJob(jobId: string): Promise<void> {
    await request(`/api/jobs/${jobId}`, { method: "DELETE" });
  },
};

export function jobId(iri: string): string {
  return iri.replace("urn:lattice:studio:job:", "");
}

/** Poll a job until it finishes. Each poll waits a little longer, up to a second. */
export async function awaitJob(id: string, signal?: AbortSignal): Promise<Job> {
  let delay = 150;
  for (;;) {
    const job = await api.job(id);
    if (job.status === "Succeeded" || job.status === "Failed") return job;
    await new Promise((resolve) => setTimeout(resolve, delay));
    if (signal?.aborted) throw new DOMException("aborted", "AbortError");
    delay = Math.min(delay * 1.5, 1000);
  }
}
