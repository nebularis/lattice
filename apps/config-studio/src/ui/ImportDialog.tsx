// SPDX-License-Identifier: MPL-2.0
// Importing ontologies into a workspace (SVA-B3, ADR-A149 decision 6, SVA-Q5 to SVA-Q7). The author chooses files or a folder,
// sees how every owl:imports of the baseline resolves and what is missing, and only then confirms. Each distinct document is
// fenced by its own job, at most four at a time, and one request holds every job's import or none. Nothing is fetched from the
// web, the baseline is never written, and the view shows an import as held only after the service has answered.

import { useRef, useState } from "react";
import { Check, CircleDashed, FileUp, FolderOpen, TriangleAlert, X } from "lucide-react";
import type { Graph } from "@lattice/authoring-domain";
import { api, awaitJob, type WorkspaceSummary } from "../api";
import { isAbort, useUnmountSignal } from "../jobs";
import { buildCatalogLookup, normalisePath } from "../rdf/catalog";
import { heldByIri, shortIri, shortLabel, type HeldImport } from "../rdf/held";
import { mediaTypeOf, resolveImports, type ImportPlan, type ImportStatus, type MediaType, type PlanNode } from "../rdf/imports";
import { Modal, Spinner } from "./kit";

/**
 * The IRIs of the documents the service stages. LATTICE's own documents are staged by a later slice (SVA-B2b), so none is offered
 * here yet, and an import that only a staged document could give is reported missing.
 */
export const STAGED_DOCUMENTS: readonly string[] = [];

/** The workspace's own baseline takes part in the plan as one more file, under a name that a dropped file may not use. */
export const BASELINE_PATH = "(workspace baseline).ttl";

/** The most fence jobs in flight at once. */
export const MAX_IN_FLIGHT = 4;

const ACCEPTED = /\.(ttl|owl|rdf|xml)$/i;
const CATALOG = /(^|\/)catalog-v001\.xml$|catalog\.xml$/i;
const compare = (a: string, b: string): number => (a < b ? -1 : a > b ? 1 : 0);

interface Chosen {
  path: string;
  text: string;
}

interface Ignored {
  path: string;
  reason: string;
}

interface HoldFile {
  path: string;
  text: string;
  mediaType: MediaType;
  /** The ontology IRI the document declares, which labels the import. */
  ontology?: string;
}

interface Planned {
  plan: ImportPlan;
  catalog?: string;
  problems: string[];
  toHold: HoldFile[];
}

type FileState = { state: "queued" } | { state: "running" } | { state: "digested" } | { state: "failed"; message: string };
type Step = "choose" | "plan" | "hold";
type Phase = "digesting" | "holding" | "failed" | "refused";

const base = (path: string): string => path.slice(path.lastIndexOf("/") + 1);

/** What a plan's status says in plain words. */
export function describeStatus(status: ImportStatus): string {
  switch (status) {
    case "catalog":
      return "from the catalog";
    case "file":
      return "from a dropped file";
    case "held":
      return "already held";
    case "staged":
      return "staged by the service";
    case "missing":
      return "missing";
  }
}

/** The plan for the workspace's baseline from what was chosen. Pure, so the same files in any order give the same plan. */
export function planImports(baseline: Graph, chosen: readonly Chosen[], held: readonly HeldImport[]): Planned {
  const dropped = chosen.map((f) => ({ path: normalisePath(f.path), text: f.text }));
  const catalogs = dropped
    .filter((f) => CATALOG.test(f.path))
    .sort((a, b) => a.path.split("/").length - b.path.split("/").length || compare(a.path, b.path));
  const start = catalogs[0];
  const lookup = start ? buildCatalogLookup(new Map(dropped.map((f) => [f.path, f.text])), start.path) : { lookup: new Map<string, string>(), missingCatalogs: [], errors: [] };
  const documents = dropped.filter((f) => !CATALOG.test(f.path));
  const plan = resolveImports({
    roots: [BASELINE_PATH],
    files: [...documents, { path: BASELINE_PATH, text: baseline.toTurtle(), mediaType: "text/turtle" }],
    catalog: lookup.lookup,
    held: heldByIri(held),
    staged: STAGED_DOCUMENTS,
  });
  const problems = [
    ...lookup.errors.map((e) => `The catalog ${e.path} could not be read: ${e.message}.`),
    ...lookup.missingCatalogs.map((p) => `A catalog names the catalog ${p}, which was not dropped.`),
    ...plan.problems.map((p) => (p.kind === "root-without-ontology" ? "The workspace's baseline declares no ontology, so it has no imports to resolve." : p.message)),
  ];
  const texts = new Map(documents.map((f) => [f.path, f.text]));
  const byPath = new Map<string, HoldFile>();
  for (const node of plan.nodes) {
    if ((node.status !== "catalog" && node.status !== "file") || node.path === undefined || byPath.has(node.path)) continue;
    const mediaType = mediaTypeOf(node.path);
    const text = texts.get(node.path);
    if (mediaType === undefined || text === undefined) continue;
    byPath.set(node.path, { path: node.path, text, mediaType, ontology: node.ontologyIri });
  }
  return { plan, catalog: start?.path, problems, toHold: [...byPath.values()].sort((a, b) => compare(a.path, b.path)) };
}

/** The label an import is held under, which is at most 200 characters. */
export function labelOf(file: HoldFile): string {
  return shortLabel(file.ontology ?? base(file.path));
}

function Status({ state }: { state: FileState }) {
  switch (state.state) {
    case "queued":
      return <span className="chip"><CircleDashed size={12} /> queued</span>;
    case "running":
      return <span className="chip accent"><Spinner size={12} /> running</span>;
    case "digested":
      return <span className="chip ok"><Check size={12} /> digested</span>;
    case "failed":
      return <span className="chip bad"><X size={12} /> failed</span>;
  }
}

export function ImportDialog(props: { workspace: string; baseline: Graph; held: HeldImport[]; onHeld: (summary: WorkspaceSummary) => void; onClose: () => void }) {
  const { workspace, baseline, held, onHeld, onClose } = props;
  const [step, setStep] = useState<Step>("choose");
  const [chosen, setChosen] = useState<Chosen[]>([]);
  const [ignored, setIgnored] = useState<Ignored[]>([]);
  const [planned, setPlanned] = useState<Planned>();
  const [states, setStates] = useState<Record<string, FileState>>({});
  const [phase, setPhase] = useState<Phase>("digesting");
  const [error, setError] = useState<string>();
  const digested = useRef(new Map<string, string>());
  const signal = useUnmountSignal();

  const add = async (list: FileList | null) => {
    if (!list?.length) return;
    const files = [...list];
    const accepted: Chosen[] = [];
    const left: Ignored[] = [];
    for (const f of files) {
      const path = normalisePath((f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name);
      if (!ACCEPTED.test(path)) left.push({ path, reason: "not a Turtle or RDF/XML file" });
      else if (path === BASELINE_PATH) left.push({ path, reason: "the name stands for the workspace's own baseline" });
      else {
        try {
          accepted.push({ path, text: await f.text() });
        } catch {
          left.push({ path, reason: "could not be read" });
        }
      }
    }
    setChosen((c) => [...c.filter((x) => !accepted.some((a) => a.path === x.path)), ...accepted].sort((a, b) => compare(a.path, b.path)));
    setIgnored((i) => [...i, ...left]);
  };

  const showPlan = () => {
    digested.current.clear();
    setPlanned(planImports(baseline, chosen, held));
    setStep("plan");
  };

  const hold = async () => {
    if (!planned) return;
    const files = planned.toHold;
    setStep("hold");
    setPhase("digesting");
    setError(undefined);
    setStates(Object.fromEntries(files.map((f) => [f.path, digested.current.has(f.path) ? { state: "digested" } : { state: "queued" }])));
    const set = (path: string, state: FileState) => setStates((s) => ({ ...s, [path]: state }));
    const queue = files.filter((f) => !digested.current.has(f.path));
    let failed = false;
    const worker = async () => {
      for (;;) {
        const file = queue.shift();
        if (!file || failed || signal().aborted) return;
        set(file.path, { state: "running" });
        try {
          const job = await api.submitFence(workspace, file.text, file.mediaType);
          const done = await awaitJob(job, signal());
          if (done.status === "Failed") throw new Error(done.failure ?? "The document could not be read.");
          digested.current.set(file.path, job);
          set(file.path, { state: "digested" });
        } catch (e) {
          if (isAbort(e)) return;
          failed = true;
          set(file.path, { state: "failed", message: e instanceof Error ? e.message : String(e) });
        }
      }
    };
    await Promise.all(Array.from({ length: Math.min(MAX_IN_FLIGHT, queue.length) }, worker));
    if (signal().aborted) return;
    if (failed) {
      setPhase("failed");
      return;
    }
    setPhase("holding");
    try {
      const jobs = files.map((f) => digested.current.get(f.path)!);
      const summary = await api.holdImports(workspace, files.map((f, i) => ({ job: jobs[i], label: labelOf(f) })));
      for (const job of jobs) void api.deleteJob(job).catch(() => undefined);
      onHeld(summary);
      onClose();
    } catch (e) {
      if (signal().aborted) return;
      setError(e instanceof Error ? e.message : String(e));
      setPhase("refused");
    }
  };

  const back = () => {
    digested.current.clear();
    setStep("plan");
  };

  const rows = planned?.plan.nodes.filter((n) => !planned.plan.roots.includes(n.iri)) ?? [];
  const count = (status: ImportStatus) => rows.filter((n) => n.status === status).length;
  const toHold = planned?.toHold.length ?? 0;
  const label = (iri: string) => (planned?.plan.roots.includes(iri) ? "this workspace" : shortIri(iri));

  const footer =
    step === "choose" ? (
      <>
        <button className="btn" onClick={onClose}>Cancel</button>
        <button className="btn primary" onClick={showPlan}>Show the plan</button>
      </>
    ) : step === "plan" ? (
      <>
        <button className="btn" onClick={() => setStep("choose")}>Back</button>
        <button className="btn" onClick={onClose}>Cancel</button>
        <button className="btn primary" disabled={toHold === 0} onClick={() => void hold()}>
          Hold {toHold} {toHold === 1 ? "import" : "imports"}
        </button>
      </>
    ) : (
      <>
        {phase === "refused" && <button className="btn primary" onClick={() => void hold()}>Try again</button>}
        {(phase === "failed" || phase === "refused") && <button className="btn" onClick={back}>Back to the plan</button>}
        <button className="btn" onClick={onClose}>{phase === "digesting" || phase === "holding" ? "Cancel" : "Close"}</button>
      </>
    );

  return (
    <Modal
      wide
      title="Import ontologies"
      subtitle="Choose the files, check how each import of the baseline resolves, then confirm. Nothing is written before you confirm and nothing is fetched from the web."
      onClose={onClose}
      footer={footer}
    >
      {step === "choose" && (
        <div className="import-step">
          <div className="import-inputs">
            <label className="field-label" htmlFor="import-files"><FileUp size={14} /> Files</label>
            <input id="import-files" type="file" multiple aria-label="Files" onChange={(e) => { const list = e.target.files; void add(list).then(() => { e.target.value = ""; }); }} />
            <label className="field-label" htmlFor="import-folder"><FolderOpen size={14} /> Folder</label>
            <input
              id="import-folder"
              type="file"
              multiple
              aria-label="Folder"
              {...({ webkitdirectory: "" } as Record<string, string>)}
              onChange={(e) => { const list = e.target.files; void add(list).then(() => { e.target.value = ""; }); }}
            />
          </div>
          <p className="small muted">
            A catalog named catalog-v001.xml among the files says where each import is. Turtle and RDF/XML files (.ttl, .owl, .rdf, .xml) are read.
          </p>
          {chosen.length > 0 && (
            <ul className="import-files" aria-label="Chosen files">
              {chosen.map((f) => (
                <li key={f.path}>
                  <span className="mono">{f.path}</span> {CATALOG.test(f.path) && <span className="chip">catalog</span>}
                </li>
              ))}
            </ul>
          )}
          {ignored.length > 0 && (
            <div className="small muted" role="note">
              Ignored: {ignored.map((i) => `${i.path} (${i.reason})`).join(", ")}
            </div>
          )}
        </div>
      )}

      {step === "plan" && planned && (
        <div className="import-step">
          <p className="small muted">
            {planned.catalog ? <>Catalog: <span className="mono">{planned.catalog}</span>.</> : "No catalog was chosen."} The workspace's own baseline is the root of the plan.
          </p>
          {rows.length === 0 ? (
            <div className="empty small">The baseline imports nothing, so there is nothing to resolve.</div>
          ) : (
            <table className="grid import-plan" aria-label="Import plan">
              <thead>
                <tr><th>Import</th><th>Resolved</th><th>File</th><th>Imported by</th></tr>
              </thead>
              <tbody>
                {rows.map((n: PlanNode) => (
                  <tr key={n.iri} className={n.status === "missing" ? "missing" : undefined}>
                    <td className="mono" title={n.iri}>{shortIri(n.iri, 56)}</td>
                    <td>{n.status === "missing" ? <span className="chip warn">{describeStatus(n.status)}</span> : describeStatus(n.status)}</td>
                    <td className="mono">{n.path ?? ""}</td>
                    <td className="small" title={n.importedBy.join(", ")}>{n.importedBy.map(label).join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {planned.problems.length > 0 && (
            <ul className="import-problems" aria-label="Problems with the plan">
              {planned.problems.map((p, i) => (
                <li key={i}><TriangleAlert size={13} /> {p}</li>
              ))}
            </ul>
          )}
          <p role="status" className="import-summary">
            {toHold} to hold now, {count("held")} already held, {count("missing")} missing.
          </p>
          <p className="small muted">What is missing stays missing until its file is supplied. A missing import does not stop the others from being held.</p>
        </div>
      )}

      {step === "hold" && planned && (
        <div className="import-step">
          <table className="grid" aria-label="Documents being held">
            <thead>
              <tr><th>File</th><th>Held as</th><th>State</th></tr>
            </thead>
            <tbody>
              {planned.toHold.map((f) => {
                const state = states[f.path] ?? { state: "queued" };
                return (
                  <tr key={f.path}>
                    <td className="mono">{f.path}</td>
                    <td className="small" title={f.ontology}>{labelOf(f)}</td>
                    <td>
                      <Status state={state} />
                      {state.state === "failed" && <div className="small import-failure">{f.path}: {state.message}</div>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {phase === "holding" && <p className="small muted"><Spinner size={12} /> Holding every import in one request.</p>}
          {phase === "failed" && <p className="small import-failure" role="alert">A document could not be digested, so nothing was held.</p>}
          {phase === "refused" && <p className="small import-failure" role="alert">{error}</p>}
        </div>
      )}
    </Modal>
  );
}
