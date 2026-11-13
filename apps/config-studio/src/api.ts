// SPDX-License-Identifier: MPL-2.0
// The service's HTTP API (contracts/config-studio/README.md). Every body is Turtle.

import { COMMENT, CST, Graph, LABEL, OWL, localName } from "@lattice/authoring-domain";
import type { OntologyHeader } from "./rdf/imports";
import { patchOf, patchTrig } from "./rdf/patch";
import { readJob, type Job } from "./rdf/report";
import { CONFIG_PARTS, type ConfigPart, type Part } from "./rdf/split";
import { authHeaders } from "./session";
import { connected, watch } from "./events";

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
  imports: { graph: string; digest: string; label: string; ontology?: string; version?: string }[];
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
      .map((g) => ({
        graph: g.value,
        digest: g.value.replace("urn:lattice:studio:import:", ""),
        label: graph.value(g.value, LABEL) ?? "Import",
        ontology: graph.value(g.value, CST("declaresOntology")),
        version: graph.value(g.value, CST("declaresVersion")),
      }))
      .sort((a, b) => a.label.localeCompare(b.label)),
    revisions: Object.fromEntries((["baseline", ...CONFIG_PARTS] as GraphName[]).map((name) => [name, n(name)])) as Record<GraphName, number>,
  };
}

export const api = {
  async vocabulary(): Promise<string> {
    return (await request("/api/vocabulary")).text();
  },

  /**
   * LATTICE's own ontology documents the service stages (SVA-B2b), from each document's ontology IRI and each version IRI it declares to
   * its header. Empty when the service stages none, which it says with 404, so an older service behaves as it did.
   */
  async stagedOntologies(): Promise<Map<string, OntologyHeader>> {
    let text: string;
    try {
      text = await (await request("/api/ontologies")).text();
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return new Map();
      throw e;
    }
    const graph = Graph.parse(text);
    const staged = new Map<string, OntologyHeader>();
    for (const node of graph.ofType(OWL("Ontology"))) {
      const version = graph.value(node, OWL("versionIRI"));
      const header: OntologyHeader = {
        ontologyIri: node.value,
        imports: graph.objects(node, OWL("imports")).map((o) => o.value).sort(),
        ...(version === undefined ? {} : { versionIri: version }),
      };
      staged.set(node.value, header);
      if (version !== undefined) staged.set(version, header);
    }
    return staged;
  },

  /** The text of the staged document whose ontology IRI or version IRI is `iri`, as Turtle. */
  async stagedOntology(iri: string): Promise<string> {
    return (await request(`/api/ontologies?${new URLSearchParams({ iri })}`)).text();
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

  /** What the service's start found that an administrator should know (PM-Q3). An old service without the endpoint has none. */
  async warnings(): Promise<string[]> {
    try {
      const response = await fetch("/api/status", { headers: authHeaders() });
      return response.ok ? ((await response.json()) as { warnings?: string[] }).warnings ?? [] : [];
    } catch {
      return [];
    }
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

  /**
   * Returns the new revision's ETag. Throws Conflict when `revision` is stale. Given `saved`, the graph as stored at `revision`, it
   * sends what changed as a patch (DR-Q5 (c)), and the whole graph when the change names a blank node or there is no base.
   */
  async save(id: string, name: GraphName, graph: Graph, revision: string, saved?: Graph): Promise<string> {
    const patch = saved && revision !== '"0"' ? patchOf(saved, graph) : undefined;
    const response = await request(`/api/workspaces/${id}/graphs/${name}`, patch
      ? { method: "PATCH", headers: { "Content-Type": "application/trig", "If-Match": revision }, body: patchTrig(patch, graph.prefixes) }
      : { method: "PUT", headers: { "Content-Type": TURTLE, "If-Match": revision }, body: graph.toTurtle() });
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

  /** Submits a fence job for one imported document and gives the job's id. The body is the document as the author supplied it. */
  async submitFence(id: string, text: string, mediaType: string): Promise<string> {
    const response = await request(`/api/workspaces/${id}/jobs?kind=fence&target=import`, { method: "POST", headers: { "Content-Type": mediaType }, body: text });
    return (response.headers.get("Location") ?? "").split("/").pop() ?? "";
  },

  /** Holds the imports that finished fence jobs digested, all in one request and all or none (at most 64), each under its label. */
  async holdImports(id: string, imports: { job: string; label: string }[]): Promise<WorkspaceSummary> {
    const query = new URLSearchParams();
    for (const i of imports) query.append("job", i.job);
    for (const i of imports) query.append("label", i.label);
    const held = await request(`/api/workspaces/${id}/imports?${query}`, { method: "POST" });
    return summary(Graph.parse(await held.text()), `urn:lattice:studio:ws:${id}`);
  },

  /** Fences an import: digested by a job, then held by the workspace, stored once whichever workspaces hold it. */
  async fenceImport(id: string, text: string, mediaType: string, label: string): Promise<WorkspaceSummary> {
    const job = await api.submitFence(id, text, mediaType);
    const done = await awaitJob(job);
    if (done.status === "Failed") throw new Error(done.failure ?? "The import could not be read.");
    const held = await api.holdImports(id, [{ job, label }]);
    void api.deleteJob(job).catch(() => undefined);
    return held;
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

  /** The workspace's jobs that are queued or running, of every kind, which a view that opens reads to find the job it started before it was closed. */
  async unfinishedJobs(id: string): Promise<Job[]> {
    const { graph } = await turtle(`/api/workspaces/${id}/jobs?unfinished=true`);
    return graph
      .ofType(CST("Job"))
      .map((j) => readJob(graph, j.value))
      .sort((a, b) => (a.submittedAt ?? "").localeCompare(b.submittedAt ?? ""));
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

/** How long a job is left between reads while the service's events reach the tab, which wake it as soon as the job changes (PM3). */
export const EVENT_FALLBACK_MS = 5000;

/** A promise that rejects as soon as `signal` aborts, so a wait ends then and not at the end of its timer. */
function whenAborted(signal: AbortSignal | undefined, cancel: { off?: () => void }): Promise<never> {
  return new Promise((_, reject) => {
    if (!signal) return;
    const abort = () => reject(new DOMException("aborted", "AbortError"));
    if (signal.aborted) return abort();
    signal.addEventListener("abort", abort, { once: true });
    cancel.off = () => signal.removeEventListener("abort", abort);
  });
}

/**
 * Read a job until it finishes, again on each of its events, or, with no events, after a wait that grows to a second. With a `signal`,
 * which a view aborts when it goes, the wait ends at once with an AbortError and the job is read no more.
 */
export async function awaitJob(id: string, signal?: AbortSignal): Promise<Job> {
  const events = watch(`urn:lattice:studio:job:${id}`);
  const cancel: { off?: () => void } = {};
  try {
    let delay = 150;
    const aborted = whenAborted(signal, cancel);
    aborted.catch(() => undefined);
    for (;;) {
      if (signal?.aborted) throw new DOMException("aborted", "AbortError");
      const job = await api.job(id);
      if (job.status === "Succeeded" || job.status === "Failed") return job;
      await Promise.race([events.next(connected() ? EVENT_FALLBACK_MS : delay), aborted]);
      delay = Math.min(delay * 1.5, 1000);
    }
  } finally {
    cancel.off?.();
    events.close();
  }
}
