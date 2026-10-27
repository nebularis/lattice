// SPDX-License-Identifier: MPL-2.0
// An in-memory stand-in for the studio's service (contracts/config-studio/README.md), installed
// into the page with page.route, so the browser tests need no Fuseki, RabbitMQ or worker. The
// vocabulary and samples are the staged ones the real service serves. Jobs finish on their first
// poll: a validation reports a violation when the submitted Turtle says dal:NoErasure, as the
// compiler would, and a compilation returns one SPARQL artefact.

import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { Page, Route } from "@playwright/test";
import { Parser } from "n3";

const assets = process.env.LATTICE_STUDIO_ASSETS ?? join(import.meta.dirname, "../../../.build/config-studio");
const CST = "https://www.nebularis.org/neuro-semantic/lattice/poc/config-studio#";
const PARTS = ["vocabulary", "quantification", "eligibility", "persistence", "surface"];
const E = "https://example.org/lattice/eligibility/";
const ELG = "https://www.nebularis.org/neuro-semantic/lattice/eligibility#";
const QNT = "https://www.nebularis.org/neuro-semantic/lattice/quantification#";

/** What the worker's engines would add, for the lending eligibility sample: the sector contract's
 * resolutions, the sector condition's expansion, and a decision for every question in the body, by
 * a small oracle (a candidate concept is Permitted when retail or food processing, a candidate value
 * when at least 700). */
function layerResults(job: string, target: string, body: string): string {
  if (target === "vocabulary") {
    const row = (n: number, from: string | null, scope: boolean, outcome: string, scheme: string) =>
      `${job.slice(0, -1)}#res-${n}> cst:contract <${E}sector-contract> ; ${from ? `cst:${from === "before" ? "validTo" : "validFrom"} "2026-01-01T00:00:00Z"^^xsd:dateTime ;` : ""} ${scope ? `cst:context <${E}lender-b> ;` : ""} cst:outcome cst:${outcome} ; cst:scheme <${E}${scheme}>${outcome === "Resolved" ? ` ; cst:binding <${E}lender-b-binding>` : ""} .`;
    const rows = [row(1, "before", false, "Fallback", "industry-classification"), row(2, "before", true, "Fallback", "industry-classification"), row(3, "after", false, "Fallback", "industry-classification"), row(4, "after", true, "Resolved", "lender-b-sectors")];
    return rows.map((r, i) => `${job} cst:resolution ${job.slice(0, -1)}#res-${i + 1}> .\n${r}\n`).join("");
  }
  const quads = new Parser().parse(body);
  const value = (s: string, p: string) => quads.find((q) => q.subject.value === s && q.predicate.value === p)?.object.value;
  const lines = [`${job} cst:expansion ${job.slice(0, -1)}#e1> . ${job.slice(0, -1)}#e1> cst:condition <${E}eligible-sector> ; cst:concept <${E}retail> ; cst:decision cst:Permitted .`,
    `${job} cst:expansion ${job.slice(0, -1)}#e2> . ${job.slice(0, -1)}#e2> cst:condition <${E}eligible-sector> ; cst:concept <${E}textiles> ; cst:decision cst:Denied .`];
  const questions = quads.filter((q) => q.predicate.value === RDF_TYPE && q.object.value === ELG + "Question").map((q) => q.subject.value);
  questions.forEach((question, i) => {
    const concept = value(question, ELG + "candidateConcept");
    const set = value(question, ELG + "candidateRangeSet");
    const range = set && value(set, QNT + "hasRange");
    const bound = range && value(range, QNT + "lowerBound");
    const number = bound ? Number(value(value(bound, QNT + "boundValue") ?? "", QNT + "numericValue")) : 0;
    const decided = concept ? ([E + "retail", E + "food-processing"].includes(concept) ? "Permitted" : "Denied") : number >= 700 ? "Permitted" : "Denied";
    const expected = value(question, CST + "expectedDecision")?.split("#")[1];
    const node = `${job.slice(0, -1)}#t${i}>`;
    lines.push(`${job} cst:testResult ${node} . ${node} cst:question <${question}> ; cst:condition <${value(question, ELG + "forCondition")}> ; cst:decision cst:${decided}${expected ? ` ; cst:passed ${expected === decided}` : ""} .`);
  });
  return lines.join("\n") + "\n";
}

const RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const PREFIX = `@prefix cst: <${CST}> .\n@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n@prefix sh: <http://www.w3.org/ns/shacl#> .\n@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n`;

interface Workspace {
  label: string;
  graphs: Record<string, string>;
  revisions: Record<string, number>;
}

export interface Submitted {
  kind: string;
  target: string;
  body: string;
}

export class FakeService {
  readonly workspaces = new Map<string, Workspace>();
  readonly jobs = new Map<string, { ws: string; kind: string; target: string; body: string; finished: boolean }>();
  readonly submitted: Submitted[] = [];
  readonly saves: { name: string; ifMatch: string | null; body: string }[] = [];
  private next = 1;

  async install(page: Page): Promise<void> {
    await page.route("**/api/**", (route) => this.handle(route));
  }

  /** Save a graph as another author would, moving its revision on. */
  saveElsewhere(ws: string, name: string, turtle: string): void {
    const w = this.workspaces.get(ws)!;
    w.graphs[name] = turtle;
    w.revisions[name] += 1;
  }

  private id(): string {
    return `00000000-0000-4000-8000-${String(this.next++).padStart(12, "0")}`;
  }

  private describe(id: string): string {
    const w = this.workspaces.get(id)!;
    const revisions = Object.entries(w.revisions).map(([name, n]) => `cst:${name}Revision ${n}`).join(" ; ");
    return `<urn:lattice:studio:ws:${id}> a cst:Workspace ; rdfs:label ${JSON.stringify(w.label)} ;
      cst:modifiedAt "2026-10-27T10:00:00Z"^^xsd:dateTime ; ${revisions} .\n`;
  }

  private jobGraph(id: string): string {
    const job = this.jobs.get(id)!;
    const iri = `<urn:lattice:studio:job:${id}>`;
    const head = `${iri} a cst:Job ; cst:kind cst:${job.kind === "validate" ? "Validate" : "Compile"} ; cst:target cst:${job.target === "surface" ? "Surface" : "Persistence"} ;
      cst:submittedAt "2026-10-27T10:00:00Z"^^xsd:dateTime`;
    if (!job.finished) {
      job.finished = true;
      return `${PREFIX}${head} ; cst:status cst:Running .\n`;
    }
    if (job.target === "vocabulary" || job.target === "eligibility") return `${PREFIX}${head} ; cst:status cst:Succeeded ; cst:conforms true ; cst:report <urn:r> .\n${layerResults(iri, job.target, job.body)}`;
    const refused = job.body.includes("NoErasure");
    const finding = refused
      ? `<urn:r> sh:result [ sh:resultSeverity sh:Violation ; sh:resultMessage "Personal data has no lawful erasure path." ;
          sh:focusNode <https://example.org/lending#LoanApplicationStrongProfile> ;
          sh:resultPath <https://www.nebularis.org/neuro-semantic/lattice/persistence#erasureStrategy> ] .`
      : "";
    const artefact =
      job.kind === "compile" && !refused
        ? ` ; cst:artefact [ cst:path "LoanApplication/cas-replace.rq" ; cst:mediaType "application/sparql-query" ; cst:group "LoanApplication" ; cst:content "SELECT ?s WHERE { ?s ?p ?o }" ]`
        : "";
    return `${PREFIX}${head} ; cst:status cst:Succeeded ; cst:conforms ${!refused} ; cst:report <urn:r> ; cst:finishedAt "2026-10-27T10:00:01Z"^^xsd:dateTime${artefact} .\n${finding}\n`;
  }

  private async handle(route: Route): Promise<void> {
    const request = route.request();
    const url = new URL(request.url());
    const parts = url.pathname.replace(/^\/api\//, "").split("/");
    const method = request.method();
    const turtle = (body: string, status = 200, headers: Record<string, string> = {}) =>
      route.fulfill({ status, body, headers: { "Content-Type": "text/turtle", ...headers } });

    if (parts[0] === "vocabulary") return turtle(readFileSync(join(assets, "vocabulary.ttl"), "utf-8"));
    if (parts[0] === "samples" && parts.length === 1) return turtle(readFileSync(join(assets, "samples.ttl"), "utf-8"));
    if (parts[0] === "samples") return turtle(readFileSync(join(assets, "samples", `${parts[1]}.ttl`), "utf-8"));
    if (parts[0] === "workspaces" && parts.length === 1) {
      if (method === "POST") {
        const id = this.id();
        this.workspaces.set(id, {
          label: decodeURIComponent(request.headers()["slug"] ?? "Untitled workspace"),
          graphs: { baseline: request.postData() ?? "", ...Object.fromEntries(PARTS.map((p) => [p, ""])) },
          revisions: { baseline: 1, ...Object.fromEntries(PARTS.map((p) => [p, 0])) },
        });
        return turtle(PREFIX + this.describe(id), 201, { Location: `/api/workspaces/${id}` });
      }
      return turtle(PREFIX + [...this.workspaces.keys()].map((id) => this.describe(id)).join(""));
    }
    if (parts[0] === "workspaces") {
      const ws = this.workspaces.get(parts[1]);
      if (!ws) return route.fulfill({ status: 404, body: "not found" });
      if (parts.length === 2) return turtle(PREFIX + this.describe(parts[1]));
      if (parts[2] === "graphs") {
        const name = parts[3];
        if (method === "PUT") {
          const ifMatch = request.headers()["if-match"] ?? null;
          this.saves.push({ name, ifMatch, body: request.postData() ?? "" });
          if (ifMatch !== `"${ws.revisions[name]}"`) return route.fulfill({ status: 412, body: "stale" });
          ws.graphs[name] = request.postData() ?? "";
          ws.revisions[name] += 1;
          return route.fulfill({ status: 204, headers: { ETag: `"${ws.revisions[name]}"` } });
        }
        return turtle(ws.graphs[name], 200, { ETag: `"${ws.revisions[name]}"` });
      }
      if (parts[2] === "jobs" && method === "POST") {
        const id = this.id();
        const job = { ws: parts[1], kind: url.searchParams.get("kind")!, target: url.searchParams.get("target")!, body: request.postData() ?? "", finished: false };
        this.jobs.set(id, job);
        this.submitted.push(job);
        return turtle(PREFIX, 202, { Location: `/api/jobs/${id}` });
      }
      if (parts[2] === "jobs") {
        const compiles = [...this.jobs.entries()].filter(([, j]) => j.ws === parts[1] && j.kind === "compile");
        return turtle(PREFIX + compiles.map(([id, j]) => `<urn:lattice:studio:job:${id}> a cst:Job ; cst:kind cst:Compile ; cst:target cst:${j.target === "surface" ? "Surface" : "Persistence"} ; cst:status cst:Succeeded ; cst:submittedAt "2026-10-27T10:00:00Z"^^xsd:dateTime .\n`).join(""));
      }
    }
    if (parts[0] === "jobs") {
      if (!this.jobs.has(parts[1])) return route.fulfill({ status: 404, body: "not found" });
      if (method === "DELETE") return route.fulfill({ status: 204 });
      return turtle(this.jobGraph(parts[1]));
    }
    return route.fulfill({ status: 404, body: "not found" });
  }
}
