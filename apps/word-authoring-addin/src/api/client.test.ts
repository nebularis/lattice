import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { readMarkup } from "@lattice/authoring-domain";
import { loadSample, readRepoFile } from "../domain/fixtures/studio";
import { ApiError, HttpStudioClient, parseJob } from "./client";

const BASE = "http://studio.test";
const CST = "https://www.nebularis.org/neuro-semantic/lattice/config-studio#";
const PREFIXES = `@prefix cst: <${CST}> . @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .`;

interface Call {
  url: string;
  init: RequestInit;
}

type Reply = Response | ((call: Call) => Response);

/** A fake fetch answering from a route table keyed "METHOD path", recording what it was asked. */
function fakeFetch(routes: Record<string, Reply | Reply[]>) {
  const calls: Call[] = [];
  const impl = vi.fn(async (url: string, init: RequestInit = {}) => {
    const call = { url: url.slice(BASE.length), init };
    calls.push(call);
    const key = `${init.method ?? "GET"} ${call.url}`;
    const entry = routes[key];
    if (entry === undefined) return new Response(`no route ${key}`, { status: 404 });
    const reply = Array.isArray(entry) ? (entry.length > 1 ? entry.shift()! : entry[0]) : entry;
    return typeof reply === "function" ? reply(call) : reply.clone();
  });
  return { calls, client: new HttpStudioClient(BASE, impl as unknown as typeof fetch) };
}

const ttl = (body: string, init: ResponseInit = {}) =>
  new Response(`${PREFIXES}\n${body}`, { status: 200, headers: { "Content-Type": "text/turtle" }, ...init });

const header = (call: Call, name: string) => (call.init.headers as Record<string, string>)[name];

const job = (status: string, extra = "") => ttl(`<urn:lattice:studio:job:j1> a cst:Job ; cst:status cst:${status} ${extra} .`);

describe("HttpStudioClient", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("lists workspaces from their descriptions", async () => {
    const { client } = fakeFetch({
      "GET /api/workspaces": ttl(`<urn:lattice:studio:ws:w2> a cst:Workspace ; rdfs:label "Beta" .
        <urn:lattice:studio:ws:w1> a cst:Workspace ; rdfs:label "Alpha" .`),
    });
    expect(await client.listWorkspaces()).toEqual([
      { id: "w1", label: "Alpha" },
      { id: "w2", label: "Beta" },
    ]);
  });

  it("creates a workspace with an empty Turtle baseline and a percent-encoded Slug", async () => {
    const { client, calls } = fakeFetch({
      "POST /api/workspaces": new Response("", { status: 201, headers: { Location: "/api/workspaces/w9" } }),
    });
    expect(await client.createWorkspace("Café lending")).toEqual({ id: "w9", label: "Café lending" });
    expect(calls[0].init.body).toBe("");
    expect(header(calls[0], "Content-Type")).toBe("text/turtle");
    expect(header(calls[0], "Slug")).toBe("Caf%C3%A9%20lending");
  });

  it("reads the studio's templates, in section order, and its samples", async () => {
    const { client, calls } = fakeFetch({
      "GET /api/document-templates": ttl(readRepoFile("contracts/config-studio/document-templates.ttl")),
      "GET /api/document-samples": ttl(readRepoFile("contracts/config-studio/document-templates.ttl")),
    });
    const templates = await client.listTemplates();
    await client.listTemplates();
    expect(calls.filter((call) => call.url === "/api/document-templates")).toHaveLength(1);
    const facility = templates.find((template) => template.templateId === "facility-agreement")!;
    expect(facility.title).toBe("Facility Agreement");
    expect(facility.sections.map((section) => section.sectionKey)).toEqual([
      "definitions",
      "commitment",
      "interest",
      "repayment",
      "undertakings",
      "events-of-default",
    ]);
    expect(facility.sections[1]).toMatchObject({
      heading: "Commitment",
      elementKinds: ["clause"],
      allowedTermKinds: ["Obligation", "Permission"],
      required: true,
    });
    expect(facility.variables.map((variable) => variable.variableKey)).toEqual(["facility-amount", "margin", "notice-period", "repayment-period"]);
    expect(await client.listSamples()).toEqual([
      { sampleId: "facility-agreement", title: "Facility Agreement (sample)" },
      { sampleId: "software-licence", title: "Software Licence (sample)" },
    ]);
  });

  it("reads a sample's markup into the document model", async () => {
    const xml = readRepoFile("contracts/document/samples/software-licence.xml");
    const { client } = fakeFetch({
      "GET /api/document-samples/software-licence": new Response(xml, { headers: { "Content-Type": "application/xml" } }),
    });
    expect(await client.getSample("software-licence")).toEqual(readMarkup(xml));
  });

  it("saves a document as markup with If-Match 0 when new, and keeps the ETag", async () => {
    const sample = loadSample("software-licence");
    const { client, calls } = fakeFetch({
      [`PUT /api/workspaces/w1/documents/${sample.documentId}`]: new Response(null, { status: 204, headers: { ETag: '"1"' } }),
    });
    expect(await client.saveDocument("w1", sample, null)).toBe(1);
    expect(header(calls[0], "If-Match")).toBe('"0"');
    expect(header(calls[0], "Content-Type")).toBe("application/xml");
    expect(calls[0].init.body).toBe(readRepoFile("contracts/document/samples/software-licence.xml"));
  });

  it("sends the revision it holds, and shows a 412 as a conflict", async () => {
    const sample = loadSample("software-licence");
    const path = `PUT /api/workspaces/w1/documents/${sample.documentId}`;
    const { client, calls } = fakeFetch({ [path]: new Response("", { status: 412 }) });
    const failure = await client.saveDocument("w1", sample, 3).catch((e: unknown) => e);
    expect(header(calls[0], "If-Match")).toBe('"3"');
    expect(failure).toBeInstanceOf(ApiError);
    expect(failure).toMatchObject({ status: 412 });
    expect((failure as Error).message).toMatch(/^Conflict/);
  });

  it("reads the document's graph as Turtle", async () => {
    const { client, calls } = fakeFetch({ "GET /api/workspaces/w1/documents/d1": ttl("<urn:x> cst:template \"t\" .") });
    expect(await client.getDocumentGraph("w1", "d1")).toContain("cst:template");
    expect(header(calls[0], "Accept")).toBe("text/turtle");
  });

  it("submits an analyse job, polls it, and reads the analysis and the proposals from its artefacts", async () => {
    const view = { documentId: "d1", revision: 2, analysis: { elements: [] }, conformance: [], proposalGraph: {} };
    const succeeded = job(
      "Succeeded",
      `; cst:artefact [ cst:path "analysis.json" ; cst:mediaType "application/json" ; cst:content ${JSON.stringify(JSON.stringify(view))} ] ,
         [ cst:path "proposals.ttl" ; cst:mediaType "text/turtle" ; cst:content "<urn:p> a <urn:q> ." ]`,
    );
    const { client, calls } = fakeFetch({
      "POST /api/workspaces/w1/jobs?kind=analyse&target=d1": new Response("", { status: 202, headers: { Location: "/api/jobs/j1" } }),
      "GET /api/jobs/j1": [job("Queued"), job("Running"), succeeded],
    });
    const promise = client.analyse("w1", "d1", { intervalMs: 100, timeoutMs: 5000 });
    await vi.advanceTimersByTimeAsync(300);
    expect(await promise).toEqual({ view, proposals: "<urn:p> a <urn:q> ." });
    expect(calls.filter((call) => call.url === "/api/jobs/j1")).toHaveLength(3);
  });

  it("reports a failed job's message", async () => {
    const { client } = fakeFetch({
      "POST /api/workspaces/w1/jobs?kind=analyse&target=d1": new Response("", { status: 202, headers: { Location: "/api/jobs/j1" } }),
      "GET /api/jobs/j1": job("Failed", '; cst:failureMessage "no such document"'),
    });
    await expect(client.analyse("w1", "d1")).rejects.toThrow("no such document");
  });

  it("times out when the job never ends", async () => {
    const { client } = fakeFetch({
      "POST /api/workspaces/w1/jobs?kind=analyse&target=d1": new Response("", { status: 202, headers: { Location: "/api/jobs/j1" } }),
      "GET /api/jobs/j1": job("Running"),
    });
    const assertion = expect(client.analyse("w1", "d1", { intervalMs: 100, timeoutMs: 500 })).rejects.toThrow("timeout");
    await vi.advanceTimersByTimeAsync(700);
    await assertion;
  });

  it("rejects with a timeout when the fetch never settles", async () => {
    const client = new HttpStudioClient(BASE, vi.fn(() => new Promise<Response>(() => {})) as unknown as typeof fetch, 1000);
    const assertion = expect(client.listWorkspaces()).rejects.toThrow("timeout");
    await vi.advanceTimersByTimeAsync(1100);
    await assertion;
  });

  it("carries the service's message on another failure", async () => {
    const { client } = fakeFetch({ "GET /api/workspaces": new Response("store unavailable", { status: 503 }) });
    await expect(client.listWorkspaces()).rejects.toMatchObject({ status: 503, message: "store unavailable" });
  });
});

describe("parseJob", () => {
  it("reads the status, the failure message and the artefacts", () => {
    const state = parseJob(`${PREFIXES} <urn:lattice:studio:job:j1> a cst:Job ; cst:status cst:Running ; cst:artefact [ cst:path "a" ; cst:content "x" ] .`);
    expect(state).toMatchObject({ status: "running", failureMessage: null, artefacts: { a: "x" } });
  });
});
