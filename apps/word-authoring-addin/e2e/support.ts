/**
 * Shared Playwright test support for the word authoring add-in: a fake of the Configuration
 * Studio's service (contracts/config-studio/README.md) behind `page.route`, answering from the
 * real templates, samples and analysis goldens.
 */
import type { Page, Route } from "@playwright/test";
import { expect } from "@playwright/test";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { readMarkup, type AnalysisView, type DocumentSnapshot } from "@lattice/authoring-domain";
import { loadSample, loadTemplate, readRepoFile } from "../src/domain/fixtures/studio";

export { loadSample, loadTemplate };

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const GOLDENS_DIR = path.join(__dirname, "../../../workers/tests/fixtures/wording_le");
const CST = "https://www.nebularis.org/neuro-semantic/lattice/config-studio#";
const PREFIXES = `@prefix cst: <${CST}> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> . @prefix sh: <http://www.w3.org/ns/shacl#> .`;

export const WORKSPACE_ID = "0a1b2c3d-0000-4000-8000-000000000001";
const JOB_ID = "0a1b2c3d-0000-4000-8000-0000000000aa";

export function loadFacilityAnalysis(): AnalysisView["analysis"] {
  return JSON.parse(readFileSync(path.join(GOLDENS_DIR, "facility-agreement.analysis.json"), "utf-8"));
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

const turtle = (route: Route, body: string, status = 200, headers: Record<string, string> = {}) =>
  route.fulfill({ status, contentType: "text/turtle", headers, body: `${PREFIXES}\n${body}` });

function view(analysis: AnalysisView["analysis"], conformance: AnalysisView["conformance"]): AnalysisView {
  return {
    documentId: "00000001-0000-4000-8000-000000000000",
    revision: 1,
    analysis,
    conformance,
    proposalGraph: { tenantId: "poc", projectId: "word-authoring", graphIri: "urn:x", revisionHash: `sha256:${"b".repeat(64)}` },
  };
}

const DOC_NODE = "urn:lattice:studio:documents/doc/d/";

/** A report as the studio gives it, from the results' Turtle bodies (each the properties of one result). */
export function reportTurtle(results: string[]): string {
  const names = results.map((_, index) => `<${DOC_NODE}report/result-${index + 1}>`);
  return (
    `<${DOC_NODE}report> a sh:ValidationReport ; sh:conforms true${names.map((name) => ` ; sh:result ${name}`).join("")} .\n` +
    results.map((body, index) => `${names[index]} a sh:ValidationResult ; ${body} .`).join("\n")
  );
}

export const UNMARKED_TEXT_RESULT = `sh:resultSeverity sh:Info ; sh:resultMessage "Unmarked text outside every section" ; cst:code "unmarked-text" ; cst:check "template" ; sh:focusNode <${DOC_NODE}wording>`;

/** The result for an unmarked construct, as the detector reports it. */
export function detectionResult(elementId: string, d: { kind: string; text: string; start: number; end: number; partIndex: number; action: string; valueType?: string; key?: string }): string {
  return (
    `sh:resultSeverity sh:Info ; sh:resultMessage "Unmarked ${d.kind}: ${d.text}" ; cst:code "detection" ; cst:check "detection" ; sh:focusNode <${DOC_NODE}element/${elementId}> ; ` +
    `cst:detectionKind "${d.kind}" ; sh:value "${d.text}" ; cst:action "${d.action}" ; cst:partIndex ${d.partIndex} ; cst:start ${d.start} ; cst:end ${d.end}` +
    (d.valueType ? ` ; cst:suggestedValueType "${d.valueType}" ; cst:suggestedKey "${d.key}"` : "")
  );
}

export interface StudioMockOptions {
  /** The report `GET .../report` gives, as Turtle. Default one template finding. */
  report?: string;
  /** The status the PUT of a document answers with. Default 204. */
  putStatus?: number;
  /** The statuses `GET /api/jobs/{job}` answers with in turn, the last one repeating. Default succeeded. */
  jobStatuses?: Array<"Queued" | "Running" | "Succeeded" | "Failed">;
  /** The analysis view the job gives. Default the facility golden with one finding. */
  analysis?: AnalysisView;
  /** Make `GET /api/workspaces` fail at the network. */
  workspacesDown?: boolean;
}

export interface StudioMock {
  /** Each PUT of a document: its If-Match, its content type and its markup. */
  puts: Array<{ ifMatch: string | null; contentType: string | null; body: string }>;
  jobSubmissions: string[];
}

/** Fakes the studio's service for one page. */
export async function mockStudio(page: Page, options: StudioMockOptions = {}): Promise<StudioMock> {
  const mock: StudioMock = { puts: [], jobSubmissions: [] };
  const statuses = options.jobStatuses ?? ["Succeeded"];
  let jobPolls = 0;
  let revision = 0;
  const analysis =
    options.analysis ?? view(loadFacilityAnalysis(), []);

  await page.route("**/api/workspaces", (route) => {
    if (options.workspacesDown) return route.abort();
    if (route.request().method() === "POST") {
      return route.fulfill({ status: 201, headers: { Location: `/api/workspaces/${WORKSPACE_ID}` }, body: "" });
    }
    return turtle(route, `<urn:lattice:studio:ws:${WORKSPACE_ID}> a cst:Workspace ; rdfs:label "Lending" .`);
  });
  await page.route("**/api/document-templates", (route) => turtle(route, readRepoFile("contracts/config-studio/document-templates.ttl")));
  await page.route("**/api/document-samples", (route) => turtle(route, readRepoFile("contracts/config-studio/document-templates.ttl")));
  await page.route("**/api/document-samples/*", (route) => {
    const id = route.request().url().split("/").pop()!;
    return route.fulfill({ status: 200, contentType: "application/xml", body: readRepoFile(`contracts/document/samples/${id}.xml`) });
  });

  await page.route("**/api/workspaces/*/documents/*/report", (route) =>
    turtle(route, options.report ?? reportTurtle([UNMARKED_TEXT_RESULT]), 200, { ETag: `"${revision}"` }),
  );
  await page.route("**/api/workspaces/*/documents/*", async (route) => {
    const request = route.request();
    if (request.method() !== "PUT") return turtle(route, `<urn:lattice:studio:ws:${WORKSPACE_ID}:document:d> cst:revision ${revision} .`, 200, { ETag: `"${revision}"` });
    const body = request.postData() ?? "";
    expect(() => readMarkup(body), "the PUT body is markup").not.toThrow();
    mock.puts.push({ ifMatch: request.headers()["if-match"] ?? null, contentType: request.headers()["content-type"] ?? null, body });
    if ((options.putStatus ?? 204) !== 204) return route.fulfill({ status: options.putStatus, body: "" });
    revision += 1;
    return route.fulfill({ status: 204, headers: { ETag: `"${revision}"` } });
  });

  await page.route("**/api/workspaces/*/jobs?*", (route) => {
    mock.jobSubmissions.push(route.request().url());
    return route.fulfill({ status: 202, headers: { Location: `/api/jobs/${JOB_ID}` }, body: "" });
  });
  await page.route("**/api/jobs/*", (route) => {
    const status = statuses[Math.min(jobPolls, statuses.length - 1)];
    jobPolls += 1;
    const literal = (text: string) => JSON.stringify(text);
    const artefacts =
      status === "Succeeded"
        ? `; cst:artefact [ cst:path "analysis.json" ; cst:mediaType "application/json" ; cst:content ${literal(JSON.stringify(analysis))} ] ,
            [ cst:path "proposals.ttl" ; cst:mediaType "text/turtle" ; cst:content ${literal(loadFacilityTurtle())} ]`
        : status === "Failed"
          ? '; cst:failureMessage "mocked failure"'
          : "";
    return turtle(route, `<urn:lattice:studio:job:${JOB_ID}> a cst:Job ; cst:status cst:${status} ${artefacts} .`);
  });
  return mock;
}

export { view as analysisView };
