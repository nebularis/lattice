/**
 * The HTTP client for the Configuration Studio's service (contracts/config-studio/README.md, plan
 * CS12d). A Word document lives in a studio workspace. It is saved as markup with `If-Match`,
 * analysed by a job of kind `analyse`, and read back as RDF. Everything but the markup and the
 * analysis view is Turtle.
 */
import {
  CST,
  Graph,
  LABEL,
  readMarkup,
  writeMarkup,
  type AnalysisView,
  type AuthoringTemplate,
  type DocumentSnapshot,
  type ElementKind,
  type SampleSummary,
  type TermKind,
  type ValueType,
} from "@lattice/authoring-domain";
import { pollJob, type JobStatus, type PollOptions } from "../domain/poll";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export interface Workspace {
  id: string;
  label: string;
}

export interface AnalysisResult {
  view: AnalysisView;
  /** The relations the analysis proposes, as Turtle. */
  proposals: string;
}

export interface StudioClient {
  listWorkspaces(): Promise<Workspace[]>;
  createWorkspace(label: string): Promise<Workspace>;
  listTemplates(): Promise<AuthoringTemplate[]>;
  listSamples(): Promise<SampleSummary[]>;
  getSample(sampleId: string): Promise<DocumentSnapshot>;
  /** Saves the document as markup and gives its new revision. `revision` is null for a new document. */
  saveDocument(workspaceId: string, document: DocumentSnapshot, revision: number | null): Promise<number>;
  /** The document's graph, as Turtle. */
  getDocumentGraph(workspaceId: string, documentId: string): Promise<string>;
  analyse(workspaceId: string, documentId: string, options?: PollOptions): Promise<AnalysisResult>;
}

type FetchLike = typeof fetch;

const WORKSPACE_PREFIX = "urn:lattice:studio:ws:";
const TURTLE = "text/turtle";

// --- reading the studio's RDF -------------------------------------------------------------------

function workspaceOf(graph: Graph, node: string): Workspace {
  return { id: node.startsWith(WORKSPACE_PREFIX) ? node.slice(WORKSPACE_PREFIX.length) : node, label: graph.value(node, LABEL) ?? "" };
}

export function parseWorkspaces(turtle: string): Workspace[] {
  const graph = Graph.parse(turtle);
  return graph
    .ofType(CST("Workspace"))
    .map((node) => workspaceOf(graph, node.value))
    .sort((a, b) => a.label.localeCompare(b.label) || a.id.localeCompare(b.id));
}

export function parseTemplates(turtle: string): AuthoringTemplate[] {
  const graph = Graph.parse(turtle);
  const text = (node: string, predicate: string): string => graph.value(node, CST(predicate)) ?? "";
  return graph.ofType(CST("DocumentTemplate")).map((template) => ({
    templateId: text(template.value, "templateKey"),
    title: graph.value(template, LABEL) ?? "",
    sections: graph
      .objects(template, CST("section"))
      .sort((a, b) => Number(text(a.value, "order")) - Number(text(b.value, "order")))
      .map((section) => ({
        sectionKey: text(section.value, "sectionKey"),
        heading: graph.value(section, LABEL) ?? "",
        elementKinds: [text(section.value, "elementKind") as ElementKind],
        allowedTermKinds: graph
          .objects(section, CST("termKind"))
          .map((kind) => kind.value as TermKind)
          .sort(),
        required: text(section.value, "required") === "true",
        guidance: graph.value(section, "http://www.w3.org/2000/01/rdf-schema#comment") ?? "",
      })),
    variables: graph
      .objects(template, CST("variable"))
      .map((variable) => ({
        variableKey: text(variable.value, "variableKey"),
        label: graph.value(variable, LABEL) ?? "",
        valueType: text(variable.value, "valueType") as ValueType,
      }))
      .sort((a, b) => a.variableKey.localeCompare(b.variableKey)),
  }));
}

export function parseSamples(turtle: string): SampleSummary[] {
  const graph = Graph.parse(turtle);
  return graph
    .ofType(CST("DocumentSample"))
    .map((sample) => ({ sampleId: graph.value(sample, CST("sampleKey")) ?? "", title: graph.value(sample, LABEL) ?? "" }))
    .sort((a, b) => a.sampleId.localeCompare(b.sampleId));
}

export interface JobState {
  jobId: string;
  status: JobStatus;
  failureMessage: string | null;
  artefacts: Record<string, string>;
}

const STATUSES: Record<string, JobStatus> = { Queued: "queued", Running: "running", Succeeded: "succeeded", Failed: "failed" };

export function parseJob(turtle: string): JobState {
  const graph = Graph.parse(turtle);
  const job = graph.ofType(CST("Job"))[0];
  if (!job) throw new Error("the job graph holds no cst:Job");
  const status = graph.value(job, CST("status"))?.slice(CST("").length) ?? "";
  const artefacts: Record<string, string> = {};
  for (const artefact of graph.objects(job, CST("artefact"))) {
    const path = graph.value(artefact, CST("path"));
    if (path) artefacts[path] = graph.value(artefact, CST("content")) ?? "";
  }
  return {
    jobId: job.value,
    status: STATUSES[status] ?? "queued",
    failureMessage: graph.value(job, CST("failureMessage")) ?? null,
    artefacts,
  };
}

// --- the client ---------------------------------------------------------------------------------

function revisionOf(response: Response): number {
  const etag = response.headers.get("ETag") ?? "";
  const revision = Number(/^(?:W\/)?"(\d+)"$/.exec(etag)?.[1]);
  if (!Number.isInteger(revision)) throw new Error(`the service gave no revision, ETag is "${etag}"`);
  return revision;
}

export class HttpStudioClient implements StudioClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: FetchLike;
  private readonly timeoutMs: number;
  private templates: Promise<AuthoringTemplate[]> | null = null;

  constructor(baseUrl: string, fetchImpl?: FetchLike, timeoutMs = 10000) {
    this.baseUrl = baseUrl;
    // The global `fetch` throws "Illegal invocation" if called detached from `window`, which
    // `this.fetchImpl(...)` below is. Wrapping it keeps the default usable.
    this.fetchImpl = fetchImpl ?? ((...args) => fetch(...args));
    this.timeoutMs = timeoutMs;
  }

  async listWorkspaces(): Promise<Workspace[]> {
    return parseWorkspaces(await (await this.request("/api/workspaces", { headers: { Accept: TURTLE } })).text());
  }

  async createWorkspace(label: string): Promise<Workspace> {
    const response = await this.request("/api/workspaces", {
      method: "POST",
      headers: { "Content-Type": TURTLE, Accept: TURTLE, Slug: encodeURIComponent(label) },
      body: "",
    });
    const id = /\/api\/workspaces\/([^/?#]+)/.exec(response.headers.get("Location") ?? "")?.[1];
    if (id) return { id, label };
    const created = parseWorkspaces(await response.text())[0];
    if (!created) throw new Error("the service did not say which workspace it created");
    return created;
  }

  listTemplates(): Promise<AuthoringTemplate[]> {
    this.templates ??= this.request("/api/document-templates", { headers: { Accept: TURTLE } })
      .then((response) => response.text())
      .then(parseTemplates);
    this.templates.catch(() => (this.templates = null));
    return this.templates;
  }

  async listSamples(): Promise<SampleSummary[]> {
    return parseSamples(await (await this.request("/api/document-samples", { headers: { Accept: TURTLE } })).text());
  }

  async getSample(sampleId: string): Promise<DocumentSnapshot> {
    const response = await this.request(`/api/document-samples/${encodeURIComponent(sampleId)}`, {
      headers: { Accept: "application/xml" },
    });
    return readMarkup(await response.text());
  }

  async saveDocument(workspaceId: string, document: DocumentSnapshot, revision: number | null): Promise<number> {
    const response = await this.request(this.documentPath(workspaceId, document.documentId), {
      method: "PUT",
      headers: { "Content-Type": "application/xml", "If-Match": `"${revision ?? 0}"` },
      body: writeMarkup(document),
    });
    return revisionOf(response);
  }

  async getDocumentGraph(workspaceId: string, documentId: string): Promise<string> {
    const response = await this.request(this.documentPath(workspaceId, documentId), { headers: { Accept: TURTLE } });
    return response.text();
  }

  async analyse(workspaceId: string, documentId: string, options: PollOptions = {}): Promise<AnalysisResult> {
    const query = `kind=analyse&target=${encodeURIComponent(documentId)}`;
    const submitted = await this.request(`/api/workspaces/${encodeURIComponent(workspaceId)}/jobs?${query}`, {
      method: "POST",
      headers: { Accept: TURTLE },
    });
    const jobId = /\/api\/jobs\/([^/?#]+)/.exec(submitted.headers.get("Location") ?? "")?.[1];
    if (!jobId) throw new Error("the service did not say where the job is");

    const job = await pollJob(async () => {
      const response = await this.request(`/api/jobs/${encodeURIComponent(jobId)}`, { headers: { Accept: TURTLE } });
      return parseJob(await response.text());
    }, options);
    if (job.status === "failed") throw new Error(job.failureMessage ?? "the analysis failed");
    const analysis = job.artefacts["analysis.json"];
    if (analysis === undefined) throw new Error("the analysis job gave no analysis.json");
    return { view: JSON.parse(analysis) as AnalysisView, proposals: job.artefacts["proposals.ttl"] ?? "" };
  }

  private documentPath(workspaceId: string, documentId: string): string {
    return `/api/workspaces/${encodeURIComponent(workspaceId)}/documents/${encodeURIComponent(documentId)}`;
  }

  private async request(path: string, init: RequestInit): Promise<Response> {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    const timeout = new Promise<never>((_, reject) => {
      timer = setTimeout(() => {
        controller.abort();
        reject(new Error("timeout"));
      }, this.timeoutMs);
    });
    try {
      const response = await Promise.race([
        this.fetchImpl(`${this.baseUrl}${path}`, { ...init, signal: controller.signal }),
        timeout,
      ]);
      if (!response.ok) {
        throw new ApiError(response.status, await errorMessage(path, response));
      }
      return response;
    } finally {
      clearTimeout(timer);
    }
  }
}

async function errorMessage(path: string, response: Response): Promise<string> {
  if (response.status === 412) return "Conflict: the document in the workspace changed since this copy was saved.";
  if (response.status === 428) return "The service needs the document's revision, and none was sent.";
  let detail = "";
  try {
    detail = (await response.text()).trim().slice(0, 300);
  } catch {
    // an unreadable error body leaves the status alone
  }
  return detail || `request to ${path} failed with status ${response.status}`;
}
