/**
 * The HTTP client for `authoring-service`'s API (plan WA8 section "`api/client.ts`"). One method
 * per route of `contracts/openapi/authoring-service.openapi.json`.
 */
import type {
  AnalysisView,
  AuthoringTemplate,
  DocumentSnapshot,
  DocumentView,
  Health,
  JobView,
  SampleList,
  SnapshotAccepted,
  SnapshotSubmission,
  TemplateList,
} from "../domain/types";

export class ApiError extends Error {
  readonly status: number;
  readonly details: string[];

  constructor(status: number, message: string, details: string[]) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

export interface ApiClient {
  health(): Promise<Health>;
  listTemplates(): Promise<TemplateList>;
  getTemplate(templateId: string): Promise<AuthoringTemplate>;
  listSamples(): Promise<SampleList>;
  getSample(sampleId: string): Promise<DocumentSnapshot>;
  getDocument(documentId: string): Promise<DocumentView>;
  submitSnapshot(documentId: string, submission: SnapshotSubmission): Promise<SnapshotAccepted>;
  getJob(jobId: string): Promise<JobView>;
  getAnalysis(documentId: string, revision: number): Promise<AnalysisView>;
  getGraph(documentId: string, revision: number, kind: "wording" | "proposal"): Promise<string>;
}

type FetchLike = typeof fetch;

interface ErrorBody {
  error?: string;
  details?: string[];
}

export class HttpApiClient implements ApiClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: FetchLike;
  private readonly timeoutMs: number;

  constructor(baseUrl: string, fetchImpl: FetchLike = fetch, timeoutMs = 10000) {
    this.baseUrl = baseUrl;
    this.fetchImpl = fetchImpl;
    this.timeoutMs = timeoutMs;
  }

  health(): Promise<Health> {
    return this.getJson<Health>("/api/health");
  }

  listTemplates(): Promise<TemplateList> {
    return this.getJson<TemplateList>("/api/templates");
  }

  getTemplate(templateId: string): Promise<AuthoringTemplate> {
    return this.getJson<AuthoringTemplate>(`/api/templates/${encodeURIComponent(templateId)}`);
  }

  listSamples(): Promise<SampleList> {
    return this.getJson<SampleList>("/api/samples");
  }

  getSample(sampleId: string): Promise<DocumentSnapshot> {
    return this.getJson<DocumentSnapshot>(`/api/samples/${encodeURIComponent(sampleId)}`);
  }

  getDocument(documentId: string): Promise<DocumentView> {
    return this.getJson<DocumentView>(`/api/documents/${encodeURIComponent(documentId)}`);
  }

  async submitSnapshot(documentId: string, submission: SnapshotSubmission): Promise<SnapshotAccepted> {
    const response = await this.request(`/api/documents/${encodeURIComponent(documentId)}/snapshot`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(submission),
    });
    return (await response.json()) as SnapshotAccepted;
  }

  getJob(jobId: string): Promise<JobView> {
    return this.getJson<JobView>(`/api/jobs/${encodeURIComponent(jobId)}`);
  }

  getAnalysis(documentId: string, revision: number): Promise<AnalysisView> {
    return this.getJson<AnalysisView>(`/api/documents/${encodeURIComponent(documentId)}/revisions/${revision}/analysis`);
  }

  async getGraph(documentId: string, revision: number, kind: "wording" | "proposal"): Promise<string> {
    const response = await this.request(
      `/api/documents/${encodeURIComponent(documentId)}/revisions/${revision}/graph/${kind}`,
      { method: "GET" },
    );
    return response.text();
  }

  private async getJson<T>(path: string): Promise<T> {
    const response = await this.request(path, { method: "GET" });
    return (await response.json()) as T;
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
        let body: ErrorBody = {};
        try {
          body = (await response.json()) as ErrorBody;
        } catch {
          // non-JSON error body: fall through with the defaults below
        }
        throw new ApiError(
          response.status,
          body.error ?? `request to ${path} failed with status ${response.status}`,
          body.details ?? [],
        );
      }
      return response;
    } finally {
      clearTimeout(timer);
    }
  }
}
