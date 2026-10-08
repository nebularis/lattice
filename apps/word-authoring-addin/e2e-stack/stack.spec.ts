/**
 * End-to-end tests against the real Word authoring POC stack (plan WA10), started with
 * `mise run authoring:up`. No mocking: every request hits the real Caddy proxy, the real
 * `authoring-service`, the real `authoring-worker`, and real Fuseki/RabbitMQ containers.
 */
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test, type APIRequestContext } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../../..");
const COMPOSE_FILE = path.join(REPO_ROOT, "deployment/compose/authoring/docker-compose.yml");

const FACILITY_SAMPLE_ID = "facility-agreement";
const LICENCE_SAMPLE_ID = "software-licence";

interface AnalysisResponse {
  analysis: {
    elements: { relationClass: string | null; basis: string }[];
  };
  conformance: { kind: string; sectionKey: string | null }[];
}

async function pollAnalysis(
  request: APIRequestContext,
  documentId: string,
  revision: number,
  timeoutMs = 60000,
): Promise<AnalysisResponse> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const response = await request.get(`/api/documents/${documentId}/revisions/${revision}/analysis`);
    if (response.status() === 200) {
      return (await response.json()) as AnalysisResponse;
    }
    if (Date.now() >= deadline) {
      throw new Error(`analysis for ${documentId}@${revision} did not appear within ${timeoutMs}ms`);
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
}

async function pollJobCompleted(request: APIRequestContext, jobId: string, timeoutMs = 20000): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const response = await request.get(`/api/jobs/${jobId}`);
    const body = await response.json();
    if (body.status === "completed") return;
    if (body.status === "failed") throw new Error(`job ${jobId} failed: ${body.error}`);
    if (Date.now() >= deadline) {
      throw new Error(`job ${jobId} did not complete within ${timeoutMs}ms`);
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
}

function sampleDocumentId(sampleId: string): string {
  // Sample k has documentId 0000000k-0000-4000-8000-000000000000 (plan §2.4).
  const index = { "facility-agreement": 1, "software-licence": 2, "property-policy": 3 }[sampleId];
  return `0000000${index}-0000-4000-8000-000000000000`;
}

test("S10-03: health is ok, with the CSP and nosniff headers", async ({ request }) => {
  const response = await request.get("/api/health");
  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(body.status).toBe("ok");
  // The proxy and the service each set nosniff independently (defence in depth); Caddy appends
  // to the upstream's value rather than replacing it.
  expect(response.headers()["x-content-type-options"]).toContain("nosniff");
  expect(response.headers()["content-security-policy"]).toContain("default-src 'self'");
});

test("S10-04: templates, samples and the three seeded documents are available", async ({ request }) => {
  const templates = await (await request.get("/api/templates")).json();
  const samples = await (await request.get("/api/samples")).json();
  expect(templates).toHaveLength(3);
  expect(samples).toHaveLength(3);

  for (const sample of samples as { sampleId: string }[]) {
    const documentId = sampleDocumentId(sample.sampleId);
    const view = await (await request.get(`/api/documents/${documentId}`)).json();
    expect(view.latestRevision).toBeGreaterThanOrEqual(1);
  }
});

test("S10-05: the seeded facility and licence are analysed and checked for conformance", async ({ request }) => {
  const facility = await pollAnalysis(request, sampleDocumentId(FACILITY_SAMPLE_ID), 1);
  expect(facility.analysis.elements.some((element) => element.relationClass === "Obligation" && element.basis === "form")).toBe(true);

  const licence = await pollAnalysis(request, sampleDocumentId(LICENCE_SAMPLE_ID), 1);
  expect(
    licence.conformance.some((finding) => finding.kind === "term-kind-not-allowed" && finding.sectionKey === "grant"),
  ).toBe(true);
});

test("S10-06: a new snapshot completes and its proposal graph contains ins: Obligation", async ({ request }) => {
  const sample = await (await request.get(`/api/samples/${FACILITY_SAMPLE_ID}`)).json();
  const documentId = crypto.randomUUID();
  const snapshot = { ...sample, documentId };

  const response = await request.put(`/api/documents/${documentId}/snapshot`, {
    data: { baseRevision: null, snapshot },
  });
  expect(response.status()).toBe(200);
  const accepted = await response.json();

  await pollJobCompleted(request, accepted.job.jobId, 20000);

  const turtle = await (await request.get(`/api/documents/${documentId}/revisions/1/graph/proposal`)).text();
  expect(turtle).toContain("instrument#");
  expect(turtle).toContain("Obligation");
});

test("S10-07: the proxy serves the add-in and the manifest's icon and help URLs", async ({ request }) => {
  for (const path of [
    "/addin/taskpane.html",
    "/addin/harness.html",
    "/addin/assets/icon-32.png",
    "/addin/assets/icon-80.png",
    "/addin/help.html",
  ]) {
    const response = await request.get(path);
    expect(response.status(), path).toBe(200);
  }
});

test("S10-08: the harness, through the proxy, analyses the facility sample and shows coloured spans", async ({ page }) => {
  await page.goto("/addin/harness.html");
  const doc = page.locator('section[aria-label="Document"]');
  await doc.getByRole("listitem").filter({ hasText: "Facility Agreement (sample)" }).getByRole("button", { name: "Insert sample" }).click();
  await expect(doc.getByText("Sections")).toBeVisible();

  await page.locator("nav.tab-bar").getByRole("button", { name: "Analyse" }).click();
  await page.locator('section[aria-label="Analyse"]').getByRole("button", { name: "Analyse" }).click();
  await expect(page.getByText("Job: completed")).toBeVisible({ timeout: 30000 });

  await page.locator("nav.tab-bar").getByRole("button", { name: "Logical English" }).click();
  const le = page.locator('section[aria-label="Logical English"]');
  await expect(le.getByRole("listitem").first()).toBeVisible();
  await expect(le.locator(".role-fixed, .role-slot-variable, .role-slot-constant").first()).toBeVisible();
});

test("S10-09: restarting authoring-service still serves the seeded analysis from Fuseki, without double-seeding", async ({ request }) => {
  const documentId = sampleDocumentId(FACILITY_SAMPLE_ID);
  const before = await pollAnalysis(request, documentId, 1);
  expect(before.analysis.elements.length).toBeGreaterThan(0);

  execFileSync("docker", ["compose", "-f", COMPOSE_FILE, "restart", "authoring-service"], { stdio: "inherit" });

  const deadline = Date.now() + 60000;
  for (;;) {
    const response = await request.get("/api/health").catch(() => null);
    if (response && response.status() === 200 && (await response.json()).status === "ok") break;
    if (Date.now() >= deadline) throw new Error("authoring-service did not become healthy again");
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  const after = await pollAnalysis(request, documentId, 1);
  expect(after.analysis).toEqual(before.analysis);

  const view = await (await request.get(`/api/documents/${documentId}`)).json();
  expect(view.latestRevision).toBe(1);
});
