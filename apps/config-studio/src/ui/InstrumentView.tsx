// SPDX-License-Identifier: MPL-2.0
// Builder mode's instrument view (ADR-A138 decisions 6 and 7): the stated terms of the meaning part in their tier, the
// regimes it states drawn as state machines, what each term reads, and a dry run of a term's eligibility conditions over
// sample facts. Bound meaning comes only from instantiating an assembled wording, which the builder never does, so that tier
// is empty here.

import { useMemo, useState } from "react";
import { Play, Workflow } from "lucide-react";
import { INS, localName } from "@lattice/authoring-domain";
import { api, awaitJob } from "../api";
import { conceptsForCondition, dryRunGraph, isIntervalCondition, regimeOfNode, regimesOf, type Regime, type Sample } from "../rdf/instrument";
import { readsOf, relationsOf, say, termsOf } from "../rdf/meaning";
import type { Issue, TestResult } from "../rdf/report";
import { NodeEditor, PART_INFO } from "./ConfigView";
import { ReadsCard, useMeaning, type M } from "./MeaningView";
import { SeverityIcon, Spinner, go } from "./kit";
import { UnderConstruction } from "./Specials";

export function InstrumentView({ selected, field }: { selected?: string; field?: string }) {
  const m = useMeaning();
  const { studio, meaning, lex, clauses } = m;
  const terms = useMemo(() => termsOf(meaning), [meaning]);
  const regimes = useMemo(() => regimesOf(meaning, lex), [meaning, lex]);
  const open = (node: string) => go("w", studio.id, "instrument", node);
  const clauseOf = (term: string) => clauses.find((c) => c.node.iri === meaning.value(term, INS("expressedIn")))?.node;
  const isTerm = !!selected && meaning.types(selected).includes(INS("Term"));
  const regime = selected ? regimeOfNode(regimes, selected) : undefined;

  return (
    <div className="split" style={{ gridTemplateColumns: "minmax(380px, 460px) 1fr" }}>
      <div className="list" role="tree" aria-label="Instrument">
        <div className="list-head">
          <div className="row">
            <Workflow size={16} />
            <strong className="grow">Instrument</strong>
            <span className="small muted">{terms.length} {terms.length === 1 ? "term" : "terms"}, {regimes.length} {regimes.length === 1 ? "regime" : "regimes"}</span>
          </div>
        </div>
        <h4>Stated meaning</h4>
        {terms.length === 0 && <div className="empty small">No stated term yet. State meaning for a clause in the Meaning view.</div>}
        {terms.map((t) => {
          const clause = clauseOf(t);
          const relations = relationsOf(meaning, lex, t);
          return (
            <div key={t} className="list-item outline-row" role="treeitem" aria-level={1} aria-selected={t === selected} onClick={() => open(t)}>
              <span className="mono outline-id">{clause?.objectId ?? "-"}</span>
              <div className="grow" style={{ minWidth: 0 }}>
                <div className="outline-text">{clause?.text ?? localName(t)}</div>
                <div className="row" style={{ gap: 6, flexWrap: "wrap", marginTop: 4 }}>
                  {relations.map((r) => (
                    <span key={r.iri} className="chip ok">{say(r, lex)}</span>
                  ))}
                  {relations.length === 0 && <span className="chip">Term, no relation</span>}
                </div>
              </div>
            </div>
          );
        })}
        <h4>Bound meaning</h4>
        <div className="empty small" style={{ textAlign: "left" }}>
          Empty here. Bound meaning comes only from instantiating an assembled wording, which the builder never does.
        </div>
        <h4>Regimes</h4>
        {regimes.length === 0 && <div className="empty small">No regime stated.</div>}
        {regimes.map((r) => (
          <div key={r.iri} className="list-item" role="treeitem" aria-level={1} aria-selected={regime?.iri === r.iri} onClick={() => open(r.iri)}>
            <div className="grow">
              <div className="name">{r.label}</div>
              <div className="detail">{r.states.length} states, {r.transitions.length} transitions</div>
            </div>
          </div>
        ))}
      </div>
      <div className="detail-pane">
        {selected && meaning.has(selected) ? (
          <>
            {isTerm && <TermPane key={selected} term={selected} m={m} regimes={regimes.filter((r) => r.term === selected)} open={open} />}
            {regime && <RegimeCard regime={regime} selected={selected} open={open} lexLabel={lex.label} />}
            <NodeEditor key={`edit-${selected}`} part="meaning" node={selected} focusField={field} />
          </>
        ) : regimes.length > 0 && !selected ? (
          <div className="editor">
            <p className="small muted">Pick a term to see what it reads and to run a dry run, or a regime to edit it.</p>
            {regimes.map((r) => (
              <RegimeCard key={r.iri} regime={r} open={open} lexLabel={lex.label} />
            ))}
          </div>
        ) : (
          <div className="empty">
            {PART_INFO.meaning.icon(28)}
            <h3>{selected ? "This node is not in the meaning configuration" : "Pick a term to see what it reads"}</h3>
            <p className="small">A term's conditions can be decided over sample facts without instantiating anything.</p>
          </div>
        )}
      </div>
    </div>
  );
}

function TermPane({ term, m, regimes, open }: { term: string; m: M; regimes: Regime[]; open: (node: string) => void }) {
  return (
    <div className="editor" style={{ paddingBottom: 0 }}>
      <ReadsCard term={term} m={m} />
      <DryRun term={term} m={m} />
      {regimes.map((r) => (
        <RegimeCard key={r.iri} regime={r} open={open} lexLabel={m.lex.label} />
      ))}
    </div>
  );
}

// ---- Regimes ------------------------------------------------------------------------------------

const BOX_W = 150;
const BOX_H = 44;
const COL_W = 340;
const ROW_H = 96;
const MARGIN = 28;
const TOP = 72;

/** A regime as a state machine in inline SVG, and under it the relations each state gates. A state and a transition open in the editor. */
function RegimeCard({ regime, selected, open, lexLabel }: { regime: Regime; selected?: string; open: (node: string) => void; lexLabel: (node: string) => string }) {
  const at = new Map(regime.states.map((s) => [s.iri, s]));
  const width = MARGIN * 2 + Math.max(0, regime.columns - 1) * COL_W + BOX_W;
  const height = TOP + MARGIN + Math.max(0, regime.rows - 1) * ROW_H + BOX_H;
  const x = (iri: string) => MARGIN + at.get(iri)!.column * COL_W;
  const y = (iri: string) => TOP + at.get(iri)!.row * ROW_H;
  const seen = new Map<string, number>();
  const press = (node: string) => (e: React.KeyboardEvent) => (e.key === "Enter" || e.key === " ") && open(node);
  return (
    <section className="card section" aria-label={`Regime ${regime.label}`}>
      <header>
        <h3 className="grow">
          <button className="link" onClick={() => open(regime.iri)}>{regime.label}</button>
        </h3>
        {regime.term && <button className="link small" onClick={() => open(regime.term!)}>Arises under {lexLabel(regime.term)}</button>}
      </header>
      <div style={{ padding: "8px 16px 4px", overflowX: "auto" }}>
        <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="group" aria-label={`State machine of ${regime.label}`} style={{ display: "block", font: "12px system-ui, sans-serif" }}>
          <defs>
            <marker id={`arrow-${localName(regime.iri)}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
              <path d="M0 0 L10 5 L0 10 z" style={{ fill: "var(--text-2, var(--border-strong))" }} />
            </marker>
          </defs>
          {regime.transitions
            .filter((t) => at.has(t.from) && at.has(t.to))
            .map((t) => {
              const key = `${t.from}>${t.to}`;
              const index = seen.get(key) ?? 0;
              seen.set(key, index + 1);
              const forward = at.get(t.to)!.column > at.get(t.from)!.column;
              let d: string;
              let lx: number;
              let ly: number;
              if (forward) {
                const x1 = x(t.from) + BOX_W, y1 = y(t.from) + BOX_H / 2, x2 = x(t.to), y2 = y(t.to) + BOX_H / 2;
                const bend = index * 18;
                lx = (x1 + x2) / 2;
                ly = (y1 + y2) / 2 + bend - 6;
                d = `M${x1} ${y1} Q${lx} ${(y1 + y2) / 2 + bend * 2} ${x2} ${y2}`;
              } else {
                // Backward and sideways transitions arch over the top of the boxes.
                const self = t.from === t.to;
                const x1 = x(t.from) + BOX_W / 2 - (self ? 18 : 0), x2 = x(t.to) + BOX_W / 2 + (self ? 18 : 0);
                const peak = Math.min(y(t.from), y(t.to)) - 34 - index * 18;
                lx = (x1 + x2) / 2;
                ly = peak + 8;
                d = `M${x1} ${y(t.from)} Q${lx} ${peak - 10} ${x2} ${y(t.to)}`;
              }
              const picked = selected === t.iri || selected === t.trigger;
              return (
                <g key={t.iri} role="button" tabIndex={0} aria-label={`Transition: ${t.label}`} onClick={() => open(t.iri)} onKeyDown={press(t.iri)} style={{ cursor: "pointer" }}>
                  <title>{t.label}</title>
                  <path d={d} fill="none" style={{ stroke: picked ? "var(--accent)" : "var(--border-strong)" }} strokeWidth={picked ? 2.5 : 1.5} markerEnd={`url(#arrow-${localName(regime.iri)})`} />
                  <path d={d} fill="none" stroke="transparent" strokeWidth={12} />
                  <text x={lx} y={ly} textAnchor="middle" style={{ fill: "var(--text)", paintOrder: "stroke", stroke: "var(--surface)", strokeWidth: 4 }}>
                    {t.label}
                  </text>
                </g>
              );
            })}
          {regime.states.map((s) => (
            <g key={s.iri} role="button" tabIndex={0} aria-label={`State ${s.label}${s.initial ? ", initial" : ""}`} onClick={() => open(s.iri)} onKeyDown={press(s.iri)} style={{ cursor: "pointer" }}>
              {s.initial && (
                <>
                  <circle cx={x(s.iri) - 14} cy={y(s.iri) + BOX_H / 2} r={5} style={{ fill: "var(--text)" }} />
                  <path d={`M${x(s.iri) - 9} ${y(s.iri) + BOX_H / 2} L${x(s.iri)} ${y(s.iri) + BOX_H / 2}`} style={{ stroke: "var(--text)" }} strokeWidth={1.5} />
                </>
              )}
              <rect x={x(s.iri)} y={y(s.iri)} width={BOX_W} height={BOX_H} rx={10} style={{ fill: "var(--surface)", stroke: selected === s.iri ? "var(--accent)" : "var(--border-strong)" }} strokeWidth={selected === s.iri ? 2.5 : 1.5} />
              <text x={x(s.iri) + BOX_W / 2} y={y(s.iri) + BOX_H / 2 + 4} textAnchor="middle" style={{ fill: "var(--text)", fontWeight: 600 }}>
                {s.label}
              </text>
            </g>
          ))}
        </svg>
      </div>
      <div className="fields" aria-label={`Gating in ${regime.label}`}>
        {regime.states.map((s) => (
          <div className="field" key={s.iri}>
            <div className="label">
              <div className="name">In {s.label}</div>
            </div>
            <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
              {s.gates.length === 0 ? (
                <span className="muted small">Gates no relation</span>
              ) : (
                s.gates.map((g) => (
                  <button key={g.iri} className="chip warn" onClick={() => open(g.iri)} title="Applies only in this state">
                    {g.text}
                  </button>
                ))
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ---- Dry run ---------------------------------------------------------------------------------------

interface DryOutcome {
  state: "running" | "done" | "failed";
  tests?: TestResult[];
  issues?: Issue[];
  message?: string;
}

/** Decides a term's conditions over sample facts (ADR-A138 decision 7). The facts go in the job's input only, and the job is deleted once read. */
function DryRun({ term, m }: { term: string; m: M }) {
  const { studio, world, vocab, lex } = m;
  const conditions = useMemo(
    () =>
      readsOf(world, vocab, lex, term).conditions.map((c) => {
        const interval = isIntervalCondition(world, c.iri);
        return { ...c, interval, concepts: interval ? [] : conceptsForCondition(world, c.iri) };
      }),
    [world, vocab, lex, term],
  );
  const [samples, setSamples] = useState<Record<string, Sample>>({});
  const [outcome, setOutcome] = useState<DryOutcome>();
  const sample = (condition: string): Sample => samples[condition] ?? { condition };
  const set = (condition: string, change: Partial<Sample>) => setSamples({ ...samples, [condition]: { ...sample(condition), ...change } });

  const run = async () => {
    setOutcome({ state: "running" });
    try {
      const body = world.merge(dryRunGraph(term, conditions.map((c) => sample(c.iri))));
      const jobId = await api.submit(studio.id, "dry-run", "meaning", body);
      const job = await awaitJob(jobId);
      void api.deleteJob(jobId).catch(() => undefined);
      setOutcome(job.status === "Failed" ? { state: "failed", message: job.failure ?? "The dry run failed." } : { state: "done", tests: job.tests, issues: job.issues });
    } catch (error) {
      setOutcome({ state: "failed", message: error instanceof Error ? error.message : String(error) });
    }
  };

  return (
    <section className="card section" aria-label="Dry run">
      <header>
        <h3 className="grow">Dry run</h3>
        <button className="btn sm primary" disabled={conditions.length === 0 || outcome?.state === "running"} onClick={() => void run()}>
          {outcome?.state === "running" ? <Spinner /> : <Play size={13} />} Run
        </button>
      </header>
      <div className="fields">
        {conditions.length === 0 ? (
          <p className="muted small">This term reads no eligibility condition, so there is nothing to decide.</p>
        ) : (
          <p className="small muted">Give each condition a sample fact. Nothing is saved and nothing is instantiated.</p>
        )}
        {conditions.map((c) => (
          <div className="field" key={c.iri}>
            <div className="label">
              <div className="name">{c.label}</div>
            </div>
            {c.interval ? (
              <input className="input" type="number" aria-label={`Number for ${c.label}`} value={sample(c.iri).number ?? ""} onChange={(e) => set(c.iri, { number: e.target.value })} />
            ) : (
              <fieldset aria-label={`Concepts for ${c.label}`} style={{ border: 0, margin: 0, padding: 0, display: "flex", flexWrap: "wrap", gap: 10 }}>
                {c.concepts.length === 0 && <span className="muted small">The condition's scheme holds no concept.</span>}
                {c.concepts.map((k) => (
                  <label key={k.iri} className="row small" style={{ gap: 4 }}>
                    <input
                      type="checkbox"
                      checked={sample(c.iri).concepts?.includes(k.iri) ?? false}
                      onChange={(e) => set(c.iri, { concepts: e.target.checked ? [...(sample(c.iri).concepts ?? []), k.iri] : (sample(c.iri).concepts ?? []).filter((x) => x !== k.iri) })}
                    />
                    {k.label}
                  </label>
                ))}
              </fieldset>
            )}
          </div>
        ))}
        {outcome?.state === "failed" && <p className="small" style={{ color: "var(--bad)" }} role="alert">The dry run could not run: {outcome.message}</p>}
        {outcome?.state === "done" && (
          <div role="status" aria-label="Dry run outcome">
            {outcome.tests!.length === 0 && <p className="small muted">No condition was decided.</p>}
            {outcome.tests!.map((t) => (
              <div key={t.condition} className="row" style={{ padding: "4px 0" }}>
                <span className="grow">{lex.label(t.condition)}</span>
                <span className={`chip ${t.decision === "Permitted" ? "ok" : t.decision === "Denied" ? "bad" : "warn"}`}>{t.decision}</span>
                {t.diagnostic && <span className="small muted">{t.diagnostic}</span>}
              </div>
            ))}
            {outcome.issues!.map((i, n) => (
              <div key={n} className="row small" style={{ alignItems: "flex-start", marginTop: 4 }}>
                <SeverityIcon severity={i.severity} />
                <span className="grow">{i.message}</span>
              </div>
            ))}
          </div>
        )}
        <UnderConstruction waitsOn="a compiled path for stepping a regime, which the dry run does not have yet">
          Stepping a regime over sample events is not available yet. The dry run decides conditions only.
        </UnderConstruction>
      </div>
    </section>
  );
}
