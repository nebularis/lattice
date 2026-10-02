/**
 * Shared Playwright test support for the word authoring add-in (plan WA9 "Playwright"): mocks
 * `/api/**` from the real WA1 samples/templates and the WA6 goldens, validating request bodies
 * against the WA8 Ajv module.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { Page, Route } from "@playwright/test";
import { expect } from "@playwright/test";
import { validate } from "../src/domain/schemas";
import type {
  AnalysisView,
  AuthoringTemplate,
  DocumentSnapshot,
  Health,
  JobView,
  JobStatus,
  SampleList,
  TemplateList,
} from "../src/domain/types";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../../..");
const TEMPLATES_DIR = path.join(REPO_ROOT, "contracts/authoring/templates");
const SAMPLES_DIR = path.join(REPO_ROOT, "contracts/authoring/samples");
const GOLDENS_DIR = path.join(REPO_ROOT, "workers/tests/fixtures/wording_le");

function load<T>(file: string): T {
  return JSON.parse(readFileSync(file, "utf-8")) as T;
}

export function loadTemplate(templateId: string): AuthoringTemplate {
  return load<AuthoringTemplate>(path.join(TEMPLATES_DIR, `${templateId}.json`));
}

export function loadSample(sampleId: string): DocumentSnapshot {
  return load<DocumentSnapshot>(path.join(SAMPLES_DIR, `${sampleId}.json`));
}

export function loadFacilityAnalysis(): AnalysisView["analysis"] {
  return load(path.join(GOLDENS_DIR, "facility-agreement.analysis.json"));
}

export function loadFacilityTurtle(): string {
  return readFileSync(path.join(GOLDENS_DIR, "facility-agreement.proposal.ttl"), "utf-8");
}

/** Finds the `[start, end)` of `needle`'s first occurrence in an element's full text. */
export function textOffsetOf(sample: DocumentSnapshot, elementId: string, needle: string): { start: number; end: number } {
  const element = sample.sections.flatMap((section) => section.elements).find((candidate) => candidate.elementId === elementId);
  if (!element) throw new Error(`no element ${elementId} in the fixture sample`);
  const text = element.parts.map((part) => part.text).join("");
  const start = text.indexOf(needle);
  if (start === -1) throw new Error(`"${needle}" not found in element ${elementId}'s text`);
  return { start, end: start + needle.length };
}

async function fulfilJson(route: Route, body: unknown, status = 200): Promise<void> {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

export async function mockHealth(page: Page, health: Health): Promise<void> {
  await page.route("**/api/health", (route) => fulfilJson(route, health));
}

export async function mockCatalog(page: Page): Promise<void> {
  const templateIds = ["facility-agreement", "software-licence", "property-policy"];
  const templates = templateIds.map(loadTemplate);
  const samples = templateIds.map(loadSample);

  const templateList: TemplateList = templates.map((template) => ({
    templateId: template.templateId,
    title: template.title,
    domain: template.domain,
    version: template.version,
  }));
  const sampleList: SampleList = samples.map((sample) => ({
    sampleId: sample.templateId,
    title: sample.title,
    templateId: sample.templateId,
  }));

  await page.route("**/api/templates", (route) => fulfilJson(route, templateList));
  await page.route("**/api/templates/*", (route) => {
    const templateId = new URL(route.request().url()).pathname.split("/").pop()!;
    const template = templates.find((candidate) => candidate.templateId === templateId);
    if (!template) return route.fulfill({ status: 404, body: "{}" });
    return fulfilJson(route, template);
  });
  await page.route("**/api/samples", (route) => fulfilJson(route, sampleList));
  await page.route("**/api/samples/*", (route) => {
    const sampleId = new URL(route.request().url()).pathname.split("/").pop()!;
    const sample = samples.find((candidate) => candidate.templateId === sampleId);
    if (!sample) return route.fulfill({ status: 404, body: "{}" });
    return fulfilJson(route, sample);
  });
}

export interface SnapshotMockOptions {
  detections?: unknown[];
  status?: number;
  errorBody?: { error: string; details: string[] };
}

let revisionCounter = 0;

/** Mocks the `PUT /api/documents/{id}/snapshot` route, validating the request body against
 * `snapshot-submission` before answering. */
export async function mockSnapshotSubmission(page: Page, options: SnapshotMockOptions = {}): Promise<void> {
  revisionCounter = 0;
  await page.route("**/api/documents/*/snapshot", async (route) => {
    const body = route.request().postDataJSON();
    const errors = validate("snapshot-submission", body);
    expect(errors, `submitted body failed snapshot-submission: ${errors.join("; ")}`).toEqual([]);

    if (options.status && options.status >= 400) {
      await fulfilJson(route, options.errorBody ?? { error: "mocked failure", details: [] }, options.status);
      return;
    }

    revisionCounter += 1;
    const documentId = body.snapshot.documentId as string;
    await fulfilJson(route, {
      documentId,
      revision: revisionCounter,
      wordingGraph: {
        tenantId: "poc",
        projectId: "word-authoring",
        graphIri: `https://example.org/lattice/authoring/doc/${documentId}/rev/${revisionCounter}/wording-graph`,
        revisionHash: `sha256:${"a".repeat(64)}`,
      },
      validation: { conforms: true, results: [] },
      detections: options.detections ?? [],
      templateFindings: [],
      job: { jobId: "00000009-0000-4000-8000-000000000099", status: "queued" },
    });
  });
}

export async function mockJob(page: Page, statuses: JobStatus[]): Promise<void> {
  let call = 0;
  await page.route("**/api/jobs/*", (route) => {
    const status = statuses[Math.min(call, statuses.length - 1)];
    call += 1;
    const job: JobView = {
      jobId: "00000009-0000-4000-8000-000000000099",
      documentId: "00000001-0000-4000-8000-000000000000",
      revision: revisionCounter || 1,
      status,
      error: status === "failed" ? "mocked failure" : null,
    };
    return fulfilJson(route, job);
  });
}

export async function mockAnalysis(page: Page): Promise<void> {
  const analysis = loadFacilityAnalysis();
  await page.route("**/api/documents/*/revisions/*/analysis", (route) => {
    const view: AnalysisView = {
      documentId: "00000001-0000-4000-8000-000000000000",
      revision: revisionCounter || 1,
      analysis,
      conformance: [],
      proposalGraph: {
        tenantId: "poc",
        projectId: "word-authoring",
        graphIri: "https://example.org/lattice/authoring/doc/00000001-0000-4000-8000-000000000000/rev/1/proposal-graph",
        revisionHash: `sha256:${"b".repeat(64)}`,
      },
    };
    return fulfilJson(route, view);
  });
}

export async function mockGraph(page: Page): Promise<void> {
  const turtle = loadFacilityTurtle();
  await page.route("**/api/documents/*/revisions/*/graph/*", (route) =>
    route.fulfill({ status: 200, contentType: "text/turtle", body: turtle }),
  );
}
