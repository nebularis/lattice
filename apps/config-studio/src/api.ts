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
  /** The published lineages it follows and the versions it pins (ADR-A149 decision 7). */
  dependsOn: string[];
  /** The imports it holds, fenced and stored once by digest (ADR-A149 decision 6). */
  imports: { graph: string; digest: string; label: string }[];
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
    dependsOn: graph.objects(iri, CST("dependsOn")).map((d) => d.value).sort(),
    imports: graph
      .objects(iri, CST("holdsImport"))
      .map((g) => ({ graph: g.value, digest: g.value.replace("urn:lattice:studio:import:", ""), label: graph.value(g.value, LABEL) ?? "Import" }))
      .sort((a, b) => a.label.localeCompare(b.label)),
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

  /** The units a workspace publishes (ADR-A149), `contracts/config-studio/publication-units.ttl`. */
  async publicationUnits(): Promise<Graph> {
    return (await turtle("/api/publication-units")).graph;
  },

  /** Names the version a unit of the saved part, or of a held import, would be published as, as a job. */
  async preparePublication(id: string, part: ConfigPart | "import", unit: string, importDigest?: string): Promise<string> {
    const from = part === "import" ? `import&graph=${importDigest}` : part;
    const response = await request(`/api/workspaces/${id}/jobs?kind=publish&target=${from}&unit=${encodeURIComponent(unit)}`, { method: "POST" });
    return (response.headers.get("Location") ?? "").split("/").pop() ?? "";
  },

  /** Publishes what a finished publish job named, and gives the lineage's registry graph. */
  async publish(id: string, job: string): Promise<Graph> {
    const response = await request(`/api/workspaces/${id}/publications?job=${job}`, { method: "POST" });
    return Graph.parse(await response.text());
  },

  /** Fences an import: digested by a job, then held by the workspace, stored once whichever workspaces hold it. */
  async fenceImport(id: string, text: string, mediaType: string, label: string): Promise<WorkspaceSummary> {
    const response = await request(`/api/workspaces/${id}/jobs?kind=fence&target=import`, { method: "POST", headers: { "Content-Type": mediaType }, body: text });
    const job = (response.headers.get("Location") ?? "").split("/").pop() ?? "";
    const done = await awaitJob(job);
    if (done.status === "Failed") throw new Error(done.failure ?? "The import could not be read.");
    const held = await request(`/api/workspaces/${id}/imports?job=${job}&label=${encodeURIComponent(label)}`, { method: "POST" });
    void api.deleteJob(job).catch(() => undefined);
    return summary(Graph.parse(await held.text()), `urn:lattice:studio:ws:${id}`);
  },

  async importGraph(id: string, digest: string): Promise<Graph> {
    return (await turtle(`/api/workspaces/${id}/imports/${digest}`)).graph;
  },

  async releaseImport(id: string, digest: string): Promise<void> {
    await request(`/api/workspaces/${id}/imports/${digest}`, { method: "DELETE" });
  },

  /** Every published lineage, by its current version. */
  async registry(): Promise<{ lineage: string; current: string }[]> {
    const { graph } = await turtle("/api/registry");
    return graph.quads(null, CST("current")).map((q) => ({ lineage: q.subject.value, current: q.object.value })).sort((a, b) => a.lineage.localeCompare(b.lineage));
  },

  /** Sets what the workspace depends on: lineages it follows and versions it pins. */
  async setDependencies(id: string, iris: string[]): Promise<WorkspaceSummary> {
    const iri = `urn:lattice:studio:ws:${id}`;
    const body = iris.map((d) => `<${iri}> <${CST("dependsOn")}> <${d}> .`).join("\n");
    const response = await request(`/api/workspaces/${id}/dependencies`, { method: "PUT", headers: { "Content-Type": TURTLE }, body });
    return summary(Graph.parse(await response.text()), iri);
  },

  /** A version and every version it pins, as TriG, each graph named by its version. */
  async bundle(iri: string): Promise<string> {
    const response = await request(`/api/registry/bundle?iri=${encodeURIComponent(iri)}`, { headers: { Accept: "application/trig" } });
    return response.text();
  },

  /** A published version's content. */
  async version(iri: string): Promise<Graph> {
    return (await turtle(`/api/registry/version?iri=${encodeURIComponent(iri)}`)).graph;
  },

  /** A lineage's registry graph: its versions, its current version and its publications. Null when it was never published. */
  async lineage(iri: string): Promise<Graph | null> {
    try {
      return (await turtle(`/api/registry/lineage?iri=${encodeURIComponent(iri)}`)).graph;
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }
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
