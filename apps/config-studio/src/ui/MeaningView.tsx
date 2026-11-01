// SPDX-License-Identifier: MPL-2.0
// Builder mode's meaning view (ADR-A138 decisions 1, 2, 4 and 6): the library's clauses with the meaning each states, a
// template edited with the forms the studio derives from Instrument's shapes, manual entry as a proposal confirmed at once,
// the review of waiting proposals, and what a stated term reads. The review is one component, ProposalCard, which later
// proposers share (ADR-A42).

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Check, Plus, Sparkles } from "lucide-react";
import { Graph, INS, compact, localName } from "@lattice/authoring-domain";
import { api, awaitJob } from "../api";
import type { Issue } from "../rdf/report";
import { PARTS } from "../state";
import { SeverityIcon, Spinner } from "./kit";
import { flatten, formsOf, outline, type OutlineNode } from "../rdf/builder";
import {
  DECISIONS,
  activitiesOf,
  addRole,
  decide,
  isWaiting,
  lexiconOf,
  mergeProposals,
  proposalsOf,
  propose,
  readsOf,
  relationKinds,
  relationsOf,
  rolesOf,
  say,
  termsFor,
  type Decision,
  type Proposal,
} from "../rdf/meaning";
import { applyArtefacts, importDocument, mediaTypeOf } from "../rdf/odrl";
import { NodeEditor, PART_INFO } from "./ConfigView";
import { useStudio } from "./Workspace";

const now = () => new Date().toISOString().replace(/\.\d+Z$/, "Z");

const clauseName = (n: OutlineNode) => n.objectId ?? n.label ?? localName(n.iri);

/** Everything the meaning view derives from the workspace, once per change. */
export function useMeaning() {
  const studio = useStudio();
  const { model, world, vocab } = studio;
  const meaning = model.state.configs.meaning!.current;
  const review = model.state.configs.review!.current;
  const lex = useMemo(() => lexiconOf(world, vocab), [world, vocab]);
  const forms = useMemo(() => formsOf(world).map((f) => outline(world, f)), [world]);
  const clauses = useMemo(() => forms.flatMap((form) => flatten(form.elements).filter((n) => n.text).map((node) => ({ form, node }))), [forms]);
  const proposals = useMemo(() => proposalsOf(review), [review]);
  const kinds = useMemo(() => relationKinds(vocab), [vocab]);
  const roles = useMemo(() => rolesOf(world, lex), [world, lex]);
  const activities = useMemo(() => activitiesOf(world, vocab, lex), [world, vocab, lex]);
  return { studio, model, world, vocab, meaning, review, lex, clauses, proposals, kinds, roles, activities };
}
export type M = ReturnType<typeof useMeaning>;

// ---- Proposers ---------------------------------------------------------------------------

type Proposer = "sentence-forms" | "language-model";
const PROPOSERS: { id: Proposer; label: string }[] = [
  { id: "sentence-forms", label: "Sentence forms" },
  { id: "language-model", label: "Language model" },
];

interface ProposeRun {
  state: "running" | "done" | "failed";
  proposer: Proposer;
  added?: number;
  issues?: Issue[];
  message?: string;
}

/** Submits every configuration to a propose job and adds the proposals of its `review.ttl` to the review part as an unsaved
 * edit. The job is kept, as the assemble job is, since its proposals are minted under it. */
function usePropose(m: M) {
  const [run, setRun] = useState<ProposeRun>();
  const latest = useRef(m);
  latest.current = m;
  const id = m.studio.id;
  const start = useCallback(
    async (proposer: Proposer) => {
      const { model } = latest.current;
      let body = Graph.empty();
      for (const p of PARTS) body = body.merge(model.state.configs[p]?.current ?? Graph.empty());
      setRun({ state: "running", proposer });
      try {
        const job = await awaitJob(await api.submit(id, "propose", proposer, body));
        if (job.status === "Failed") return setRun({ state: "failed", proposer, message: job.failure ?? "The propose job failed." });
        const file = job.artefacts.find((a) => a.path === "review.ttl");
        const current = latest.current.model.state.configs.review!.current;
        const merged = mergeProposals(current, file ? Graph.parse(file.content) : Graph.empty());
        if (merged.added > 0) latest.current.model.edit("review", (g) => mergeProposals(g, Graph.parse(file!.content)).review);
        setRun({ state: "done", proposer, added: merged.added, issues: job.issues });
      } catch (error) {
        setRun({ state: "failed", proposer, message: error instanceof Error ? error.message : String(error) });
      }
    },
    [id],
  );
  return { run, start };
}

interface ImportRun {
  state: "running" | "done" | "failed";
  added?: number;
  issues?: Issue[];
  message?: string;
  /** The roles of parties that match no workspace role, which the author saves to the baseline deliberately, since the
   * baseline saves at once and is never an unsaved edit. */
  roles?: Graph;
  rolesSaved?: boolean;
}

/** Submits an ODRL policy with the configurations and adds the job's artefacts to the configurations they belong to. The
 * worker reuses each workspace role a party's name matches. The rest come back for the baseline, which saves at once, so the
 * author saves them with a button of their own. */
function useImportOdrl(m: M) {
  const [run, setRun] = useState<ImportRun>();
  const latest = useRef(m);
  latest.current = m;
  const id = m.studio.id;
  const start = useCallback(
    async (file: File, confirmed: boolean, into?: string) => {
      const { model } = latest.current;
      const mediaType = mediaTypeOf(file.name);
      if (!mediaType) return setRun({ state: "failed", message: "The file must be .jsonld, .json, .ttl or .nt." });
      setRun({ state: "running" });
      try {
        let body = importDocument(id, await file.text(), mediaType, confirmed, into);
        for (const p of PARTS) body = body.merge(model.state.configs[p]?.current ?? Graph.empty());
        const job = await awaitJob(await api.submit(id, "propose", "odrl", body));
        if (job.status === "Failed") return setRun({ state: "failed", message: job.failure ?? "The import failed." });
        const current = Object.fromEntries(PARTS.map((p) => [p, latest.current.model.state.configs[p]?.current]));
        const applied = applyArtefacts(job.artefacts, current);
        for (const [part, graph] of Object.entries(applied.edits) as [typeof PARTS[number], Graph][]) latest.current.model.edit(part, () => graph);
        const roles = applied.unapplied.filter((a) => a.group === "baseline").reduce((g, a) => g.merge(Graph.parse(a.content)), Graph.empty());
        setRun({ state: "done", added: applied.added, issues: job.issues, roles });
      } catch (error) {
        setRun({ state: "failed", message: error instanceof Error ? error.message : String(error) });
      }
    },
    [id],
  );
  const saveRoles = useCallback(async () => {
    const roles = run?.roles;
    const baseline = latest.current.model.state.baseline?.graph;
    if (!roles || !baseline) return;
    try {
      await latest.current.model.replaceBaseline(baseline.merge(roles));
      setRun((r) => r && { ...r, rolesSaved: true });
    } catch (error) {
      setRun((r) => r && { ...r, state: "failed", message: error instanceof Error ? error.message : String(error) });
    }
  }, [run]);
  return { run, start, saveRoles };
}

function ImportOdrl({ m }: { m: M }) {
  const { studio } = m;
  const { run, start, saveRoles } = useImportOdrl(m);
  const [file, setFile] = useState<File>();
  const [confirmed, setConfirmed] = useState(false);
  const [into, setInto] = useState("");
  return (
    <div style={{ marginTop: 10 }} aria-label="Import ODRL policy" role="group">
      <div className="row">
        <label className="small muted" htmlFor="odrl-file">Import ODRL policy</label>
        <input id="odrl-file" type="file" className="grow" accept=".jsonld,.json,.ttl,.nt" onChange={(e) => setFile(e.target.files?.[0])} />
      </div>
      <div className="row" style={{ marginTop: 6 }}>
        <label className="small">
          <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} /> This file is an ODRL 2.2 policy
        </label>
      </div>
      <div className="row" style={{ marginTop: 6 }}>
        <label className="small muted" htmlFor="odrl-into">Clause</label>
        <select id="odrl-into" className="select grow" value={into} onChange={(e) => setInto(e.target.value)}>
          <option value="">Generate a form</option>
          {m.clauses.map(({ node }) => (
            <option key={node.iri} value={node.iri}>{clauseName(node)}</option>
          ))}
        </select>
        <button className="btn sm primary" disabled={!file || !confirmed || run?.state === "running"} onClick={() => void start(file!, confirmed, into || undefined)}>
          {run?.state === "running" ? <Spinner /> : <Sparkles size={13} />} Import
        </button>
      </div>
      {run?.state === "failed" && (
        <p className="small" style={{ color: "var(--bad)", margin: "8px 0 0" }} role="alert">The ODRL import could not run: {run.message}</p>
      )}
      {run?.state === "done" && (
        <div role="status" aria-label="Import outcome" style={{ marginTop: 8 }}>
          <div className="small">
            {run.added} {run.added === 1 ? "proposal" : "proposals"} added from the policy. Save each changed part to keep them.
          </div>
          {run.roles && run.roles.size > 0 && (
            <div className="row small" style={{ marginTop: 4 }}>
              <span className="grow">
                {run.rolesSaved
                  ? "The new roles are saved to the baseline."
                  : "Some parties match no role of the workspace. The proposals name new roles for them, which the baseline must hold."}
              </span>
              {!run.rolesSaved && (
                <button className="btn sm" onClick={() => void saveRoles()}>Save the new roles to the baseline</button>
              )}
            </div>
          )}
          {run.issues!.map((i, n) => (
            <div key={n} className="row small" style={{ alignItems: "flex-start", marginTop: 4 }}>
              <SeverityIcon severity={i.severity} />
              <span className="grow">
                {i.message}{" "}
                {i.focus && <button className="link" onClick={() => studio.open("meaning", i.focus!)}>{compact(i.focus)}</button>}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ProposeBar({ m }: { m: M }) {
  const [features, setFeatures] = useState<string[]>([]);
  useEffect(() => {
    void api.features().then(setFeatures);
  }, []);
  const { studio } = m;
  const { run, start } = usePropose(m);
  const [proposer, setProposer] = useState<Proposer>("sentence-forms");
  return (
    <div style={{ marginTop: 10 }} aria-label="Propose" role="group">
      <div className="row">
        <label className="small muted" htmlFor="proposer">Proposer</label>
        <select id="proposer" className="select grow" value={proposer} onChange={(e) => setProposer(e.target.value as Proposer)}>
          {PROPOSERS.map((p) => (
            <option key={p.id} value={p.id}>{p.label}</option>
          ))}
        </select>
        <button className="btn sm primary" disabled={run?.state === "running"} onClick={() => void start(proposer)}>
          {run?.state === "running" ? <Spinner /> : <Sparkles size={13} />} Propose
        </button>
      </div>
      {run?.state === "failed" && (
        <p className="small" style={{ color: "var(--bad)", margin: "8px 0 0" }} role="alert">The {run.proposer} proposer could not run: {run.message}</p>
      )}
      {run?.state === "done" && (
        <div role="status" aria-label="Propose outcome" style={{ marginTop: 8 }}>
          <div className="small">
            {run.added} {run.added === 1 ? "proposal" : "proposals"} added from {run.proposer}.{run.added ? " Save to keep them." : ""}
          </div>
          {run.issues!.map((i, n) => (
            <div key={n} className="row small" style={{ alignItems: "flex-start", marginTop: 4 }}>
              <SeverityIcon severity={i.severity} />
              <span className="grow">
                {i.message}{" "}
                {i.focus && <button className="link" onClick={() => studio.open("meaning", i.focus!)}>{compact(i.focus)}</button>}
              </span>
            </div>
          ))}
        </div>
      )}
      {features.includes("odrl") && <ImportOdrl m={m} />}
    </div>
  );
}

export function MeaningView({ selected, field }: { selected?: string; field?: string }) {
  const m = useMeaning();
  const { studio, meaning, clauses, proposals } = m;
  const waiting = proposals.filter(isWaiting);
  const asProposal = proposals.find((p) => p.iri === selected);
  const clause = clauses.find((c) => c.node.iri === (asProposal?.span ?? selected));
  const terms = meaning.ofType(INS("Term")).length;
  let group = "";

  return (
    <div className="split" style={{ gridTemplateColumns: "minmax(380px, 460px) 1fr" }}>
      <div className="list" role="tree" aria-label="Meaning">
        <div className="list-head">
          <div className="row">
            {PART_INFO.meaning.icon(16)}
            <strong className="grow">Meaning</strong>
            <span className="small muted">{terms} {terms === 1 ? "term" : "terms"}</span>
            {waiting.length > 0 && <span className="chip warn">{waiting.length} waiting</span>}
          </div>
          <ProposeBar m={m} />
        </div>
        {clauses.length === 0 && <div className="empty small">No clause in the library yet. Import a document or a sample that holds a Wording form.</div>}
        {clauses.map(({ form, node }) => {
          const head = form.iri !== group ? form.label : undefined;
          group = form.iri;
          const relations = termsFor(meaning, node.iri).flatMap((t) => relationsOf(meaning, m.lex, t));
          const hasTerm = termsFor(meaning, node.iri).length > 0;
          const waits = waiting.some((p) => p.span === node.iri);
          return (
            <div key={node.iri}>
              {head && <h4>{head}</h4>}
              <div className="list-item outline-row" role="treeitem" aria-level={1} aria-selected={node.iri === clause?.node.iri} onClick={() => studio.open("meaning", node.iri)}>
                <span className="mono outline-id">{clauseName(node)}</span>
                <div className="grow" style={{ minWidth: 0 }}>
                  <div className="outline-text">{node.text}</div>
                  <div className="row" style={{ gap: 6, flexWrap: "wrap", marginTop: 4 }}>
                    {relations.map((r) => (
                      <span key={r.iri} className="chip ok">{say(r, m.lex)}</span>
                    ))}
                    {hasTerm && relations.length === 0 && <span className="chip">Term, no relation</span>}
                    {!hasTerm && <span className="chip">No stated meaning</span>}
                    {waits && <span className="chip warn">Proposal waiting</span>}
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="detail-pane">
        {selected && meaning.has(selected) ? (
          <TemplatePane key={selected} node={selected} m={m} field={field} />
        ) : clause ? (
          <ClausePane key={clause.node.iri} node={clause.node} m={m} />
        ) : (
          <div className="editor">
            <p className="small muted">{selected ? "This node is neither a clause of the library nor a template." : "Pick a clause to read its meaning, or review what waits."}</p>
            <ReviewQueue proposals={waiting} m={m} />
          </div>
        )}
      </div>
    </div>
  );
}

// ---- A clause ------------------------------------------------------------------------------

function ClausePane({ node, m }: { node: OutlineNode; m: M }) {
  const { studio, meaning, lex, proposals } = m;
  const terms = termsFor(meaning, node.iri);
  const mine = proposals.filter((p) => p.span === node.iri);
  const decided = mine.filter((p) => !isWaiting(p));
  return (
    <div className="editor">
      <div className="editor-head">
        <div className="grow">
          <span className="chip ok">Clause</span>
          <h2 style={{ marginTop: 8 }}>{clauseName(node)}</h2>
          <div className="iri">{node.iri}</div>
          <p className="type-desc">{node.text}</p>
        </div>
      </div>

      <section className="card section" aria-label="Stated meaning">
        <header>
          <h3 className="grow">Stated meaning</h3>
        </header>
        <div className="fields">
          {terms.length === 0 && <p className="muted small">No stated meaning.{mine.some(isWaiting) ? " A proposal waits for review." : ""}</p>}
          {terms.map((t) => (
            <div key={t}>
              <div className="row" style={{ marginBottom: 6 }}>
                <button className="link" onClick={() => studio.open("meaning", t)}>Stated term {localName(t)}</button>
              </div>
              {relationsOf(meaning, lex, t).map((r) => (
                <div key={r.iri} className="row" style={{ padding: "4px 0" }}>
                  <span className="grow">{say(r, lex)}</span>
                  <span className="chip">{r.kind.label}</span>
                  <button className="link" onClick={() => studio.open("meaning", r.iri)}>Edit</button>
                </div>
              ))}
              {relationsOf(meaning, lex, t).length === 0 && <p className="muted small">No relation arises under this term yet.</p>}
            </div>
          ))}
        </div>
      </section>

      {terms.map((t) => (
        <ReadsCard key={t} term={t} m={m} />
      ))}

      <ManualEntry node={node} m={m} />

      <ReviewQueue proposals={mine.filter(isWaiting)} m={m} />

      {decided.length > 0 && (
        <section className="card section" aria-label="Decided proposals">
          <header>
            <h3 className="grow">Decided</h3>
          </header>
          <div className="fields">
            {decided.map((p) => (
              <div key={p.iri} className="row">
                <span className="grow small">{p.proposer}, {when(p.decidedAt ?? p.proposedAt)}</span>
                <span className={`chip ${p.decision === "Confirm" || p.decision === "Retarget" ? "ok" : ""}`}>{p.decision}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

// ---- What a term reads --------------------------------------------------------------------------

export function ReadsCard({ term, m }: { term: string; m: M }) {
  const reads = useMemo(() => readsOf(m.world, m.vocab, m.lex, term), [m.world, m.vocab, m.lex, term]);
  const rows: [string, { iri: string; label: string }[]][] = [
    ["Roles", reads.roles],
    ["Concepts", reads.concepts],
    ["Ranges", reads.ranges],
    ["Eligibility conditions", reads.conditions],
  ];
  return (
    <section className="card section" aria-label="What the term reads">
      <header>
        <h3 className="grow">What {localName(term)} reads</h3>
      </header>
      <div className="fields">
        {rows.map(([title, items]) => (
          <div className="field" key={title}>
            <div className="label">
              <div className="name">{title}</div>
            </div>
            <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
              {items.length === 0 ? <span className="muted small">None</span> : items.map((i) => <span key={i.iri} className="chip" title={i.iri}>{i.label}</span>)}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ---- A template -------------------------------------------------------------------------------------

function TemplatePane({ node, m, field }: { node: string; m: M; field?: string }) {
  const { studio, meaning } = m;
  const isTerm = meaning.types(node).includes(INS("Term"));
  const term = isTerm ? node : meaning.value(node, INS("arisesUnder"));
  const clause = term ? meaning.value(term, INS("expressedIn")) : undefined;
  const name = m.clauses.find((c) => c.node.iri === clause)?.node;
  return (
    <>
      <div className="editor" style={{ paddingBottom: 0 }}>
        {clause && (
          <button className="link" onClick={() => studio.open("meaning", clause)}>
            Back to clause {name ? clauseName(name) : localName(clause)}
          </button>
        )}
        {isTerm && <ReadsCard term={node} m={m} />}
      </div>
      <NodeEditor part="meaning" node={node} focusField={field} />
    </>
  );
}

// ---- Manual entry -------------------------------------------------------------------------------------

function ManualEntry({ node, m }: { node: OutlineNode; m: M }) {
  const { studio, model, world, meaning, review, lex, kinds, roles, activities } = m;
  const [kindIri, setKindIri] = useState(() => kinds.find((k) => k.label === "Obligation")?.iri ?? kinds[0]?.iri ?? "");
  const [role, setRole] = useState("");
  const [counter, setCounter] = useState("");
  const [activity, setActivity] = useState("");
  const [newRole, setNewRole] = useState("");
  const [problem, setProblem] = useState<string>();
  const kind = kinds.find((k) => k.iri === kindIri);
  const ready = !!kind && !!role && !!counter && !!activity;

  const submit = () => {
    if (!kind || !ready) return;
    const out = propose(meaning, review, world, studio.baseline.namespace, { clause: node.iri, name: clauseName(node), kind, role, counter, activity }, lex, now());
    model.edit("meaning", () => out.meaning);
    model.edit("review", () => out.review);
    setRole("");
    setCounter("");
    setActivity("");
  };

  // A role is a party-layer individual, so it belongs to the baseline, which is written at once.
  const add = async () => {
    const label = newRole.trim();
    const baseline = model.state.baseline;
    if (!label || !baseline) return;
    const made = addRole(baseline.graph, world, studio.baseline.namespace, label);
    try {
      await model.replaceBaseline(made.graph);
      setProblem(undefined);
      setNewRole("");
      if (!role) setRole(made.iri);
      else if (!counter) setCounter(made.iri);
    } catch (error) {
      setProblem(`The role could not be added: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  const pick = (id: string, label: string, value: string, set: (v: string) => void, options: { iri: string; label: string }[], placeholder: string) => (
    <div className="field">
      <div className="label">
        <label className="name" htmlFor={id}>{label}</label>
      </div>
      <select id={id} className="select" value={value} onChange={(e) => set(e.target.value)}>
        <option value="">{placeholder}</option>
        {options.map((o) => (
          <option key={o.iri} value={o.iri}>{o.label}</option>
        ))}
      </select>
    </div>
  );

  return (
    <section className="card section" aria-label="Manual entry">
      <header>
        <h3 className="grow">Manual entry</h3>
      </header>
      <div className="fields">
        {pick("entry-kind", "Relation kind", kindIri, setKindIri, kinds, "Choose a kind")}
        {pick("entry-role", kind?.obligation === false ? "Holder" : "Obligor", role, setRole, roles, "Choose a role")}
        {pick("entry-counter", kind?.obligation === false ? "Counterparty" : "Obligee", counter, setCounter, roles, "Choose a role")}
        {pick("entry-activity", "Activity", activity, setActivity, activities, "Choose an activity")}
        <div className="field">
          <div className="label">
            <label className="name" htmlFor="entry-new-role">New role</label>
          </div>
          <div className="row">
            <input id="entry-new-role" className="input grow" value={newRole} placeholder="A label" onChange={(e) => setNewRole(e.target.value)} onKeyDown={(e) => e.key === "Enter" && void add()} />
            <button className="btn sm" disabled={!newRole.trim()} onClick={() => void add()}>
              <Plus size={13} /> Add role
            </button>
          </div>
          <div className="help">A role is written to the baseline as soon as it is added.</div>
          {problem && <div className="field-error">{problem}</div>}
        </div>
        {ready && kind && (
          <p className="small">
            <strong>Reads:</strong> {say({ iri: "", kind, roles: [role], counters: [counter], activity }, lex)}
          </p>
        )}
        <div className="row">
          <button className="btn primary" disabled={!ready} onClick={submit}>
            <Check size={14} /> Confirm entry
          </button>
          <span className="small muted">A manual entry is a proposal confirmed at once.</span>
        </div>
      </div>
    </section>
  );
}

// ---- Review -----------------------------------------------------------------------------------------------

function ReviewQueue({ proposals, m }: { proposals: Proposal[]; m: M }) {
  return (
    <section aria-label="Review" style={{ marginBottom: 16 }}>
      <h3 style={{ margin: "0 0 8px" }}>Waiting for review ({proposals.length})</h3>
      {proposals.length === 0 && <p className="muted small">Nothing waits for review.</p>}
      {proposals.map((p) => (
        <ProposalCard key={p.iri} proposal={p} m={m} />
      ))}
    </section>
  );
}

/** A waiting proposal and the four decisions of ADR-A42. Confirm writes its payload into the meaning configuration. Retarget
 * records the decision, writes the payload there and opens it to be corrected with the forms. Decline and Defer record the
 * decision only. */
function ProposalCard({ proposal: p, m }: { proposal: Proposal; m: M }) {
  const { studio, model, meaning, review, lex, clauses } = m;
  const clause = clauses.find((c) => c.node.iri === p.span)?.node;
  const source: Graph | undefined = p.payload;
  const lines = source ? relationsOf(source, lex).filter((r) => p.proposes.includes(r.iri)) : [];
  const record = (decision: Decision) => {
    const out = decide(meaning, review, p.iri, decision, now());
    if (out.meaning !== meaning) model.edit("meaning", () => out.meaning);
    model.edit("review", () => out.review);
  };
  const retarget = () => {
    record("Retarget");
    studio.open("meaning", lines[0]?.iri ?? p.proposes[0]);
  };
  const label = `Proposal by ${p.proposer} for ${clause ? clauseName(clause) : "an unknown clause"}`;
  return (
    <section className="card" style={{ marginBottom: 12, padding: 14 }} aria-label={label}>
      <div className="row" style={{ marginBottom: 8, flexWrap: "wrap" }}>
        <span className="chip accent">{p.proposer}</span>
        {clause ? (
          <button className="link" onClick={() => studio.open("meaning", clause.iri)}>Clause {clauseName(clause)}</button>
        ) : (
          <span className="small muted">No clause</span>
        )}
        <span className="grow" />
        <span className="small muted">{when(p.proposedAt)}</span>
      </div>
      {p.problem && <p className="small" style={{ color: "var(--bad)" }}>{p.problem}</p>}
      {p.evidence && <p className="small" style={{ margin: "0 0 8px" }}>Evidence: <q>{p.evidence}</q></p>}
      {p.proposerVersion && <p className="small muted" style={{ margin: "0 0 8px" }}>Proposer version: {p.proposerVersion}</p>}
      <ul style={{ margin: "0 0 10px", paddingLeft: 18 }} aria-label="Proposed templates">
        {lines.map((r) => (
          <li key={r.iri}>{say(r, lex)}</li>
        ))}
        {source && lines.length === 0 && <li className="muted">{p.proposes.length} {p.proposes.length === 1 ? "template" : "templates"}, none a relation</li>}
      </ul>
      <div className="row" style={{ flexWrap: "wrap" }}>
        {DECISIONS.map((d) => (
          <button
            key={d}
            className={`btn sm${d === "Confirm" ? " primary" : ""}`}
            disabled={(d === "Confirm" || d === "Retarget") && !p.payload}
            onClick={() => (d === "Retarget" ? retarget() : record(d))}
          >
            {d}
          </button>
        ))}
      </div>
    </section>
  );
}

/** A time as the reader's locale writes it, or the stored text when it does not parse. */
function when(at?: string): string {
  if (!at) return "no time";
  const d = new Date(at);
  return Number.isNaN(d.getTime()) ? at : d.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
