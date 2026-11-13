// SPDX-License-Identifier: MPL-2.0
// An in-memory stand-in for the studio's service (contracts/config-studio/README.md), installed
// into the page with page.route, so the browser tests need no Fuseki, RabbitMQ or worker. The
// vocabulary and samples are the staged ones the real service serves. Jobs finish on their first
// poll: a validation reports a violation when the submitted Turtle says dal:NoErasure, as the
// compiler would, and a compilation returns one SPARQL artefact.

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { Page, Route } from "@playwright/test";
import { DataFactory, Parser, Store, Writer } from "n3";

const assets = process.env.LATTICE_STUDIO_ASSETS ?? join(import.meta.dirname, "../../../.build/config-studio");
const CST = "https://www.nebularis.org/neuro-semantic/lattice/config-studio#";
const PARTS = ["library", "assembly", "meaning", "review", "vocabulary", "quantification", "eligibility", "surface", "persistence", "mapping"];
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

const A = "https://example.org/lattice/studio/assembly/";
const E_BUILDER = "https://example.org/lattice/wording/facility-form/";
const TARGETS: Record<string, string> = { baseline: "Baseline", "sentence-forms": "SentenceFormProposer", "language-model": "LanguageModelProposer", "mapping-language-model": "MappingLanguageModelProposer", surface: "Surface", assembly: "AssemblyTarget", meaning: "Meaning", review: "Review" };

/** The recorded result of assembling the builder sample: the assembly with a lender count assembles, and the
 * one without is refused at the decide stage, naming the governing variable. Each assembly is answered by its IRI. */
const RECORD = `@prefix wrd: <https://www.nebularis.org/neuro-semantic/lattice/wording#> .\n<urn:r> a wrd:AssembledWording .\n`;
const DOCUMENT = `<?xml version="1.0" encoding="UTF-8"?>
<document xmlns="https://www.nebularis.org/neuro-semantic/lattice/document/1" id="00000000-0000-4000-8000-000000000001">
  <meta><title>Syndicated, three lenders, UK and Ireland</title><template>form</template>
    <variable key="permitted-jurisdictions" type="text">permitted-jurisdictions</variable></meta>
  <body>
    <section key="section-5">
      <clause id="00000000-0000-4000-8000-000000000002">5.1 Interest accrues daily on each loan.</clause>
      <clause id="00000000-0000-4000-8000-000000000003">5.2 Each interest period is three months.</clause>
    </section>
    <section key="section-12">
      <clause id="00000000-0000-4000-8000-000000000004">12.1 The borrower may operate in <var key="permitted-jurisdictions">United Kingdom, Ireland</var></clause>
    </section>
  </body>
</document>
`;

/** A sentence-form propose job proposes a permission for clause 12.1 and finds nothing for 5.2A. */
function proposeResults(job: string): string {
  const payload = `@prefix ins: <${INS}> .
@prefix ins-voc: <https://www.nebularis.org/neuro-semantic/lattice/instrument/vocab#> .
@prefix f: <https://example.org/lattice/wording/facility-form/> .
@prefix r: <https://example.org/lattice/studio/roles/> .
@prefix m: <https://example.org/lattice/studio/meaning/> .
m:term-12-1 a ins:Term , ins:Template ; ins:expressedIn f:cl-12-1 .
m:permit-operate a ins:Permission , ins:Template ; ins:arisesUnder m:term-12-1 ; ins:holder r:Borrower ; ins:counterparty r:Lender ; ins:activity ins-voc:Report .
`;
  const p = `<${job.slice(1, -1)}:proposal/1>`;
  const m = "<https://example.org/lattice/studio/meaning/";
  return `${job} cst:artefact [ cst:path "review.ttl" ; cst:mediaType "text/turtle" ; cst:group "" ; cst:content ${JSON.stringify(
    `@prefix cst: <${CST}> .\n@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n${p} a cst:Proposal ; cst:span <https://example.org/lattice/wording/facility-form/cl-12-1> ; cst:proposes ${m}term-12-1> , ${m}permit-operate> ; cst:proposer "sentence-forms" ; cst:proposerVersion "sentence-forms 1" ; cst:evidence "may operate in" ; cst:proposedAt "2026-10-28T12:00:00Z"^^xsd:dateTime ; cst:payload ${JSON.stringify(payload)} .\n`,
  )} ] .
<urn:r> sh:result [ sh:resultSeverity sh:Info ; sh:resultMessage "No candidate for clause 5.2A" ; cst:code "propose" ; sh:focusNode <https://example.org/lattice/wording/facility-form/cl-5-2a> ] .
`;
}

/** A small regime under clause 9.1's term, so the builder sample has one: in force, a notice period and terminated, with the
 * obligation of 9.1 gated to the first state. */
const REGIME = `
@prefix ins: <https://www.nebularis.org/neuro-semantic/lattice/instrument#> .
@prefix ins-voc: <https://www.nebularis.org/neuro-semantic/lattice/instrument/vocab#> .
@prefix bhv: <https://www.nebularis.org/neuro-semantic/lattice/behaviour#> .
@prefix m: <https://example.org/lattice/studio/meaning/> .
m:facility-regime a ins:Regime , bhv:StateSpace , ins:Template ; ins:arisesUnder m:term-9-1 ; bhv:initialState m:fr-in-force .
m:fr-in-force a bhv:State ; bhv:inStateSpace m:facility-regime ; ins:stateKind ins-voc:InForce .
m:fr-notice a bhv:State ; bhv:inStateSpace m:facility-regime ; ins:stateKind ins-voc:NoticePeriod .
m:fr-terminated a bhv:State ; bhv:inStateSpace m:facility-regime ; ins:stateKind ins-voc:Terminated .
m:fr-on-breach a ins:OnBreach , bhv:TriggerDefinition ; bhv:triggerKind bhv:DerivedTrigger ; ins:ofObligation m:act-for-lenders .
m:fr-on-expiry a ins:OnExpiry , bhv:TriggerDefinition ; bhv:triggerKind bhv:ScheduledTrigger .
m:fr-give a ins:RegimeTransition , bhv:TransitionDefinition ; bhv:fromState m:fr-in-force ; bhv:toState m:fr-notice ; bhv:hasTrigger m:fr-on-breach .
m:fr-end a ins:RegimeTransition , bhv:TransitionDefinition ; bhv:fromState m:fr-notice ; bhv:toState m:fr-terminated ; bhv:hasTrigger m:fr-on-expiry .
m:act-for-lenders ins:appliesInState m:fr-in-force .
`;

/** A dry-run job decides the condition its facts name, so a renamed sample needs no change here, from the one number it is given, Permitted above one lender, and reports as
 * information a condition with no fact, which reads Undetermined, as the worker does. */
function dryRunResults(job: string, body: string): string {
  const quads = new Parser().parse(body);
  const facts = quads.filter((q) => q.predicate.value === CST + "forCondition");
  const interval = quads.find((q) => q.predicate.value === RDF_TYPE && q.object.value === ELG + "IntervalCondition");
  const condition = facts[0]?.object.value ?? interval?.subject.value ?? E_BUILDER + "more-than-one-lender";
  const name = condition.slice(condition.lastIndexOf("/") + 1);
  const number = facts.map((f) => quads.find((q) => q.subject.value === f.subject.value && q.predicate.value === CST + "number")?.object.value).find((v) => v !== undefined);
  const decision = number === undefined ? "Undetermined" : Number(number) > 1 ? "Permitted" : "Denied";
  const node = `${job.slice(0, -1)}#t0>`;
  const info = number === undefined ? `<urn:r> sh:result [ sh:resultSeverity sh:Info ; sh:resultMessage "No sample fact for ${name}" ; cst:code "dry-run" ; sh:focusNode <${condition}> ] .\n` : "";
  return `${job} cst:testResult ${node} . ${node} cst:condition <${condition}> ; cst:decision cst:${decision}${decision === "Undetermined" ? ' ; cst:diagnostic "no fact"' : ""} .\n${info}`;
}

function assembleResults(job: string, body: string): { turtle: string; conforms: boolean } {
  const quads = new Parser().parse(body);
  const assemblies = quads.filter((q) => q.predicate.value === RDF_TYPE && q.object.value === CST + "Assembly").map((q) => q.subject.value).sort();
  let conforms = true;
  const lines: string[] = [];
  for (const assembly of assemblies) {
    if (assembly === A + "unsettled") {
      conforms = false;
      lines.push(`<urn:r> sh:result [ sh:resultSeverity sh:Violation ; sh:resultMessage "${assembly}: the value of lender-count is Undetermined" ; cst:code "decide" ; sh:focusNode <https://example.org/lattice/wording/facility-form/gv-lender-count> ] .`);
      continue;
    }
    const artefact = (path: string, type: string, content: string) =>
      `${job} cst:artefact [ cst:path "${path}" ; cst:mediaType "${type}" ; cst:group "${assembly}" ; cst:content ${JSON.stringify(content)} ] .`;
    lines.push(artefact("record.ttl", "text/turtle", RECORD), artefact("document.xml", "application/xml", DOCUMENT));
  }
  return { turtle: lines.join("\n") + "\n", conforms };
}

const INS = "https://www.nebularis.org/neuro-semantic/lattice/instrument#";
const RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type";
const PREFIX = `@prefix cst: <${CST}> .\n@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n@prefix sh: <http://www.w3.org/ns/shacl#> .\n@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n`;

interface Held {
  digest: string;
  label: string;
  text: string;
  mediaType: string;
  ontology?: string;
  version?: string;
}

interface Workspace {
  label: string;
  graphs: Record<string, string>;
  revisions: Record<string, number>;
  /** The imports it holds, in the order they were held. */
  imports: Held[];
}

const OWL_ONTOLOGY = "http://www.w3.org/2002/07/owl#Ontology";
const OWL_VERSION = "http://www.w3.org/2002/07/owl#versionIRI";

/** What a fence job would digest from a body: a digest of its text, and the one named owl:Ontology it declares with its version IRI.
 * A fake reads RDF/XML by its header with regular expressions. A Turtle body that does not parse fails the job, as the service's does. */
function fence(body: string, mediaType: string): { digest: string; ontology?: string; version?: string } | { failure: string } {
  const digest = createHash("sha256").update(body).digest("hex");
  if (mediaType.includes("xml")) {
    const ontology = /<owl:Ontology[^>]*rdf:about="([^"]+)"/.exec(body)?.[1];
    const version = /<owl:versionIRI[^>]*rdf:resource="([^"]+)"/.exec(body)?.[1];
    return { digest, ontology, version };
  }
  try {
    const quads = new Parser().parse(body);
    const named = [...new Set(quads.filter((q) => q.predicate.value === RDF_TYPE && q.object.value === OWL_ONTOLOGY && q.subject.termType === "NamedNode").map((q) => q.subject.value))];
    if (named.length !== 1) return { digest };
    const versions = quads.filter((q) => q.subject.value === named[0] && q.predicate.value === OWL_VERSION).map((q) => q.object.value);
    return { digest, ontology: named[0], version: versions.length === 1 ? versions[0] : undefined };
  } catch (error) {
    return { failure: error instanceof Error ? error.message.split("\n")[0] : String(error) };
  }
}

/** The ontology documents the fake stages, as the service's index and files would hold them (SVA-B2b): the first imports the second. */
export const STAGED_FIRST = "https://example.org/lattice/staged/alpha";
export const STAGED_FIRST_VERSION = "https://example.org/lattice/staged/alpha/1.0";
export const STAGED_SECOND = "https://example.org/lattice/staged/beta";
const OWL_HEAD = "@prefix owl: <http://www.w3.org/2002/07/owl#> .\n";
const STAGED: { iri: string; version?: string; imports: string[]; text: string }[] = [
  { iri: STAGED_FIRST, version: STAGED_FIRST_VERSION, imports: [STAGED_SECOND], text: `${OWL_HEAD}<${STAGED_FIRST}> a owl:Ontology ; owl:versionIRI <${STAGED_FIRST_VERSION}> ; owl:imports <${STAGED_SECOND}> .\n` },
  { iri: STAGED_SECOND, imports: [], text: `${OWL_HEAD}<${STAGED_SECOND}> a owl:Ontology .\n` },
];
const OWL_IMPORTS = "http://www.w3.org/2002/07/owl#imports";

/** What the worker's validation of a baseline reports: each owl:imports of a named ontology of the baseline or of a held import that no held
 * import declares, as an ImportNotHeld warning on the importing ontology. A document that does not parse holds and states nothing. */
function importWarnings(baseline: string, held: Held[]): string {
  const read = (text: string): { ontologies: { iri: string; versions: string[]; imports: string[] }[] } => {
    try {
      const quads = new Parser().parse(text);
      const iris = [...new Set(quads.filter((q) => q.predicate.value === RDF_TYPE && q.object.value === OWL_ONTOLOGY && q.subject.termType === "NamedNode").map((q) => q.subject.value))];
      return {
        ontologies: iris.map((iri) => ({
          iri,
          versions: quads.filter((q) => q.subject.value === iri && q.predicate.value === OWL_VERSION).map((q) => q.object.value),
          imports: quads.filter((q) => q.subject.value === iri && q.predicate.value === OWL_IMPORTS && q.object.termType === "NamedNode").map((q) => q.object.value),
        })),
      };
    } catch {
      return { ontologies: [] };
    }
  };
  const own = read(baseline).ontologies;
  const documents = held.filter((h) => !h.mediaType.includes("xml")).map((h) => read(h.text).ontologies);
  const known = new Set([...own.flatMap((o) => [o.iri, ...o.versions]), ...documents.filter((d) => d.length === 1).flatMap((d) => [d[0].iri, ...d[0].versions])]);
  const found = [...own, ...documents.flat()].flatMap((o) => o.imports.filter((i) => !known.has(i)).map((i) => [o.iri, i]));
  return [...new Set(found.map((f) => JSON.stringify(f)))]
    .sort()
    .map((f) => {
      const [importer, target] = JSON.parse(f) as string[];
      return `<urn:r> sh:result [ sh:resultSeverity sh:Warning ; sh:resultMessage "${importer} imports ${target}, and no held document declares that IRI." ; cst:code "ImportNotHeld" ; sh:focusNode <${importer}> ; sh:resultPath <${OWL_IMPORTS}> ; sh:value <${target}> ] .`;
    })
    .join("\n");
}

export interface Submitted {
  kind: string;
  target: string;
  body: string;
  mediaType?: string;
}

export class FakeService {
  readonly workspaces = new Map<string, Workspace>();
  readonly jobs = new Map<string, { ws: string; kind: string; target: string; body: string; mediaType?: string; finished: boolean }>();
  /** Each request that held imports, with the jobs and labels it named in order. */
  readonly holds: { ws: string; jobs: string[]; labels: string[] }[] = [];
  readonly submitted: Submitted[] = [];
  readonly deletedJobs: string[] = [];
  readonly saves: { name: string; ifMatch: string | null; body: string }[] = [];
  /** Jobs that never finish while held, as a proposal that waits on a model does not (plan studio-worker-liveness): a kind, or `kind:target`. */
  readonly hold = new Set<string>();
  /** Whether the service stages LATTICE's ontology documents, and so answers the two reads of /api/ontologies. Off, it answers 404 as an older one does. */
  stagedOntologies = true;
  /** Whether a language model is configured, so that a proposal by it succeeds. */
  modelConfigured = false;
  /** What the service's status reports, such as a queue no worker consumes. */
  warnings: string[] = [];
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
    const held = w.imports.map((i) => `cst:holdsImport <urn:lattice:studio:import:${i.digest}> ;`).join(" ");
    const roots = w.imports
      .map(
        (i) =>
          `<urn:lattice:studio:import:${i.digest}> rdfs:label ${JSON.stringify(i.label)}${i.ontology ? ` ; cst:declaresOntology <${i.ontology}>` : ""}${i.version ? ` ; cst:declaresVersion <${i.version}>` : ""} .\n`,
      )
      .join("");
    return `<urn:lattice:studio:ws:${id}> a cst:Workspace ; rdfs:label ${JSON.stringify(w.label)} ;
      ${held} cst:modifiedAt "2026-10-27T10:00:00Z"^^xsd:dateTime ; ${revisions} .\n${roots}`;
  }

  private jobGraph(id: string): string {
    const job = this.jobs.get(id)!;
    const iri = `<urn:lattice:studio:job:${id}>`;
    const kind = job.kind === "validate" ? "Validate" : job.kind === "assemble" ? "Assemble" : job.kind === "propose" ? "Propose" : job.kind === "dry-run" ? "DryRunJob" : job.kind === "fence" ? "Fence" : "Compile";
    const head = `${iri} a cst:Job ; cst:kind cst:${kind} ; cst:target cst:${TARGETS[job.target] ?? "Persistence"} ;
      cst:submittedAt "2026-10-27T10:00:00Z"^^xsd:dateTime`;
    if (this.hold.has(job.kind) || this.hold.has(`${job.kind}:${job.target}`)) {
      return `${PREFIX}${head} ; cst:status cst:Running .\n`;
    }
    if (!job.finished) {
      job.finished = true;
      return `${PREFIX}${head} ; cst:status cst:Running .\n`;
    }
    if (job.kind === "fence") {
      const result = fence(job.body, job.mediaType ?? "text/turtle");
      if ("failure" in result) return `${PREFIX}${head} ; cst:status cst:Failed ; cst:failureMessage ${JSON.stringify(result.failure)} .\n`;
      const declared = `${result.ontology ? ` ; cst:declaresOntology <${result.ontology}>` : ""}${result.version ? ` ; cst:declaresVersion <${result.version}>` : ""}`;
      return `${PREFIX}${head} ; cst:status cst:Succeeded ; cst:conforms true ; cst:digest "${result.digest}"${declared} .\n`;
    }
    if (job.kind === "validate" && job.target === "baseline") {
      const held = this.workspaces.get(job.ws)?.imports ?? [];
      return `${PREFIX}${head} ; cst:status cst:Succeeded ; cst:conforms true ; cst:report <urn:r> .\n<urn:r> a sh:ValidationReport .\n${importWarnings(job.body, held)}\n`;
    }
    if (job.kind === "dry-run") return `${PREFIX}${head} ; cst:status cst:Succeeded ; cst:conforms true ; cst:report <urn:r> .\n<urn:r> a sh:ValidationReport .\n${dryRunResults(iri, job.body)}`;
    if (job.kind === "propose") {
      if (job.target === "language-model" && !this.modelConfigured) return `${PREFIX}${head} ; cst:status cst:Failed ; cst:failureMessage "no language model is configured" .\n`;
      return `${PREFIX}${head} ; cst:status cst:Succeeded ; cst:conforms true ; cst:report <urn:r> .\n<urn:r> a sh:ValidationReport .\n${proposeResults(iri)}`;
    }
    if (job.kind === "assemble") {
      const result = assembleResults(iri, job.body);
      return `${PREFIX}${head} ; cst:status cst:Succeeded ; cst:conforms ${result.conforms} ; cst:report <urn:r> .\n<urn:r> a sh:ValidationReport .\n${result.turtle}`;
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

    // the service's local authentication with one developer signed in, as `mise run studio:up` gives (ADR-A149 decision 9)
    const json = (body: unknown) => route.fulfill({ status: 200, body: JSON.stringify(body), headers: { "Content-Type": "application/json" } });
    if (parts[0] === "session") return json({ provider: "local", principal: "developer", admin: true, principalOption: ["developer"], administrator: ["developer"] });
    if (parts[0] === "status") return json({ warnings: this.warnings });
    if (parts[0] === "features") return json({ features: [] });
    if (parts[0] === "vocabulary") return turtle(readFileSync(join(assets, "vocabulary.ttl"), "utf-8"));
    if (parts[0] === "ontologies") {
      if (!this.stagedOntologies) return route.fulfill({ status: 404, body: "not found" });
      const iri = url.searchParams.get("iri");
      if (iri === null) {
        const rows = STAGED.map((o) => `<${o.iri}> a owl:Ontology${o.version ? ` ; owl:versionIRI <${o.version}>` : ""}${o.imports.map((i) => ` ; owl:imports <${i}>`).join("")} .\n`).join("");
        return turtle(`${OWL_HEAD}${rows}`);
      }
      if (!/^[A-Za-z][A-Za-z0-9+.-]*:\S+$/.test(iri)) return route.fulfill({ status: 400, body: "iri must be one absolute IRI" });
      const found = STAGED.find((o) => o.iri === iri || o.version === iri);
      return found ? turtle(found.text) : route.fulfill({ status: 404, body: "not found" });
    }
    if (parts[0] === "samples" && parts.length === 1) return turtle(readFileSync(join(assets, "samples.ttl"), "utf-8"));
    if (parts[0] === "samples") return turtle(readFileSync(join(assets, "samples", `${parts[1]}.ttl`), "utf-8") + (parts[1] === "builder" ? REGIME : ""));
    if (parts[0] === "workspaces" && parts.length === 1) {
      if (method === "POST") {
        const id = this.id();
        this.workspaces.set(id, {
          label: decodeURIComponent(request.headers()["slug"] ?? "Untitled workspace"),
          graphs: { baseline: request.postData() ?? "", ...Object.fromEntries(PARTS.map((p) => [p, ""])) },
          revisions: { baseline: 1, ...Object.fromEntries(PARTS.map((p) => [p, 0])) },
          imports: [],
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
        if (method === "PUT" || method === "PATCH") {
          const ifMatch = request.headers()["if-match"] ?? null;
          // a patch is applied to the stored part, so a test reads the part a save of the same change would leave (DR-Q5 (c))
          const body = method === "PATCH" ? applyPatch(ws.graphs[name], request.postData() ?? "") : request.postData() ?? "";
          this.saves.push({ name, ifMatch, body });
          if (ifMatch !== `"${ws.revisions[name]}"`) return route.fulfill({ status: 412, body: "stale" });
          ws.graphs[name] = body;
          ws.revisions[name] += 1;
          return route.fulfill({ status: 204, headers: { ETag: `"${ws.revisions[name]}"` } });
        }
        return turtle(ws.graphs[name], 200, { ETag: `"${ws.revisions[name]}"` });
      }
      if (parts[2] === "imports" && parts.length === 3 && method === "POST") {
        // all or nothing, as the service's one command is: every job must be a finished fence job of this workspace
        const names = url.searchParams.getAll("job");
        const labels = url.searchParams.getAll("label");
        if (names.length === 0) return route.fulfill({ status: 404, body: "no job" });
        if (names.length > 64 || (labels.length !== names.length && !(labels.length === 0 && names.length === 1))) return route.fulfill({ status: 400, body: "the labels do not match the jobs" });
        const found: Held[] = [];
        for (const [i, name] of names.entries()) {
          const job = this.jobs.get(name);
          if (!job || job.ws !== parts[1]) return route.fulfill({ status: 404, body: `no job ${name}` });
          const result = job.kind === "fence" ? fence(job.body, job.mediaType ?? "text/turtle") : { failure: "not a fence job" };
          if ("failure" in result) return route.fulfill({ status: 409, body: `${name} has no import to hold` });
          found.push({ digest: result.digest, label: labels[i] ?? "Import", text: job.body, mediaType: job.mediaType ?? "text/turtle", ontology: result.ontology, version: result.version });
        }
        this.holds.push({ ws: parts[1], jobs: names, labels });
        for (const held of found) if (!ws.imports.some((i) => i.digest === held.digest)) ws.imports.push(held);
        return turtle(PREFIX + this.describe(parts[1]), 201, { Location: `/api/workspaces/${parts[1]}/imports/${found[0].digest}` });
      }
      if (parts[2] === "imports" && parts.length === 4) {
        const held = ws.imports.find((i) => i.digest === parts[3]);
        if (!held) return route.fulfill({ status: 404, body: "not held" });
        if (method === "DELETE") {
          ws.imports = ws.imports.filter((i) => i !== held);
          return route.fulfill({ status: 204 });
        }
        // the service gives the converted graph, so an RDF/XML document is a header only here
        const header = held.mediaType.includes("xml") ? `<${held.ontology ?? "urn:x"}> a <${OWL_ONTOLOGY}> .\n` : held.text;
        return turtle(header);
      }
      if (parts[2] === "jobs" && method === "POST") {
        const id = this.id();
        const job = { ws: parts[1], kind: url.searchParams.get("kind")!, target: url.searchParams.get("target")!, body: request.postData() ?? "", mediaType: request.headers()["content-type"], finished: false };
        this.jobs.set(id, job);
        this.submitted.push(job);
        return turtle(PREFIX, 202, { Location: `/api/jobs/${id}` });
      }
      if (parts[2] === "jobs" && url.searchParams.get("unfinished") === "true") {
        const open = [...this.jobs.entries()].filter(([id, j]) => j.ws === parts[1] && !this.deletedJobs.includes(id) && (this.hold.has(j.kind) || this.hold.has(`${j.kind}:${j.target}`)));
        const kindOf = (k: string) => (k === "validate" ? "Validate" : k === "propose" ? "Propose" : k === "compile" ? "Compile" : "Assemble");
        return turtle(PREFIX + open.map(([id, j]) => `<urn:lattice:studio:job:${id}> a cst:Job ; cst:kind cst:${kindOf(j.kind)} ; cst:target cst:${TARGETS[j.target] ?? "Persistence"} ; cst:status cst:Running ; cst:submittedAt "2026-10-27T10:00:00Z"^^xsd:dateTime .\n`).join(""));
      }
      if (parts[2] === "jobs") {
        const compiles = [...this.jobs.entries()].filter(([, j]) => j.ws === parts[1] && j.kind === "compile");
        return turtle(PREFIX + compiles.map(([id, j]) => `<urn:lattice:studio:job:${id}> a cst:Job ; cst:kind cst:Compile ; cst:target cst:${j.target === "surface" ? "Surface" : "Persistence"} ; cst:status cst:Succeeded ; cst:submittedAt "2026-10-27T10:00:00Z"^^xsd:dateTime .\n`).join(""));
      }
    }
    if (parts[0] === "jobs") {
      if (!this.jobs.has(parts[1])) return route.fulfill({ status: 404, body: "not found" });
      if (method === "DELETE") {
        this.deletedJobs.push(parts[1]);
        return route.fulfill({ status: 204 });
      }
      return turtle(this.jobGraph(parts[1]));
    }
    return route.fulfill({ status: 404, body: "not found" });
  }
}

/** The Turtle `stored` with the patch's removed triples taken out and its added ones put in, as the service applies one. */
function applyPatch(stored: string, trig: string): string {
  const { namedNode, quad, defaultGraph } = DataFactory;
  const prefixes: Record<string, string> = {};
  const store = new Store(new Parser().parse(stored, null, (prefix, iri) => (prefixes[prefix] = iri.value)));
  new Parser({ format: "application/trig" }).parse(trig, null, (prefix, iri) => (prefixes[prefix] ??= iri.value));
  for (const q of new Parser({ format: "application/trig" }).parse(trig)) {
    const triple = quad(q.subject, q.predicate, q.object, defaultGraph());
    if (q.graph.equals(namedNode("urn:lattice:studio:patch:add"))) store.addQuad(triple);
    else store.removeQuad(triple);
  }
  const writer = new Writer({ prefixes });
  writer.addQuads(store.getQuads(null, null, null, null));
  let out = "";
  writer.end((_, result) => (out = result ?? ""));
  return out;
}
