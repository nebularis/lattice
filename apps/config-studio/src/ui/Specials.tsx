// SPDX-License-Identifier: MPL-2.0
// The editor sections the vocabularies cannot derive: a scheme's concepts, a binding's validity,
// how a contract resolves, how a condition decides each concept, a condition's tests, and ranges on
// a number line. Each reads the latest validation job of its part for what the layer's engine said.

import { useMemo, useState } from "react";
import { Check, ChevronRight, Construction, FlaskConical, Plus, Trash2, X } from "lucide-react";
import { conceptForest, conceptsOf, addQuestion, questionsFor, removeQuestion, setContext, setExpected, type ConceptNode } from "../rdf/eligibility";
import { mint } from "../rdf/editors";
import { CST, ELG, FND, Graph, QNT, SKOS, TYPE, VOC, XSD, blankNode, compact, iri, literal, localName, typed } from "@lattice/authoring-domain";
import { addRange, conditionSpace, contains, rangesOf, readRange, removeRange, type End, type RangeView } from "../rdf/quantity";
import type { Decision, Expansion, Resolution, TestResult } from "../rdf/report";
import type { Part } from "../state";
import { TermPicker } from "./Fields";
import { useStudio } from "./Workspace";

const DECISIONS: Decision[] = ["Permitted", "Denied", "Undetermined"];
const TONE: Record<string, string> = { Permitted: "ok", Denied: "bad", Undetermined: "warn", NotTested: "" };

export function UnderConstruction({ children, waitsOn }: { children: React.ReactNode; waitsOn: string }) {
  return (
    <div className="construction" role="note">
      <Construction size={16} />
      <div>
        <strong>Under construction.</strong> {children}
        <div className="small">Waits on {waitsOn}.</div>
      </div>
    </div>
  );
}

function label(world: Graph, node?: string): string {
  if (!node) return "";
  return world.value(node, SKOS("prefLabel")) ?? world.value(node, "http://www.w3.org/2000/01/rdf-schema#label") ?? compact(node);
}

// --- vocabulary --------------------------------------------------------------------------------

export function ConceptsSection({ node }: { node: string }) {
  const { model, world, baseline, open } = useStudio();
  const graph = model.state.configs.vocabulary!.current;
  const forest = useMemo(() => conceptForest(world, conceptsOf(world, node)), [world, node]);
  const [name, setName] = useState("");
  const [parent, setParent] = useState<string>("");
  const add = () => {
    if (!name.trim()) return;
    model.edit("vocabulary", (g) => {
      const concept = mint(g, baseline.namespace, name);
      return g.edit((e) => {
        e.add(concept, TYPE, iri(SKOS("Concept")));
        e.add(concept, SKOS("prefLabel"), literal(name.trim(), "en"));
        e.add(concept, SKOS("inScheme"), iri(node));
        if (parent) e.add(concept, SKOS("broader"), iri(parent));
      });
    });
    setName("");
  };
  const tree = (n: ConceptNode, depth: number): React.ReactNode => (
    <div key={n.iri}>
      <div className="concept-row" style={{ paddingLeft: 8 + depth * 18 }}>
        {n.children.length ? <ChevronRight size={12} className="muted" /> : <span style={{ width: 12 }} />}
        <button className="link" onClick={() => open("vocabulary", n.iri)}>
          {n.label}
        </button>
        <span className="small muted mono">{localName(n.iri)}</span>
        <span className="spacer" />
        {graph.has(n.iri) && (
          <>
            <button className="btn ghost sm" title="Add a narrower concept" onClick={() => setParent(n.iri)}>
              <Plus size={12} /> Narrower
            </button>
            <button
              className="btn ghost icon sm"
              aria-label={`Delete ${n.label}`}
              onClick={() => model.edit("vocabulary", (g) => g.edit((e) => e.remove(n.iri)))}
            >
              <Trash2 size={12} />
            </button>
          </>
        )}
      </div>
      {n.children.map((c) => tree(c, depth + 1))}
    </div>
  );
  return (
    <div className="fields">
      {forest.length === 0 && <p className="muted small">No concept is in this scheme yet.</p>}
      <div className="concept-tree">{forest.map((n) => tree(n, 0))}</div>
      <div className="row" style={{ marginTop: 10 }}>
        <input className="input" placeholder={parent ? `A concept narrower than ${label(world, parent)}` : "A new top concept"} value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && add()} aria-label="New concept" />
        {parent && (
          <button className="btn ghost sm" onClick={() => setParent("")}>
            <X size={12} /> Top level
          </button>
        )}
        <button className="btn" onClick={add}>
          <Plus size={14} /> Add concept
        </button>
      </div>
    </div>
  );
}

function toInput(value?: string): string {
  return value ? value.replace(/(:\d\d)(\.\d+)?(Z|[+-]\d\d:\d\d)$/, "$1").slice(0, 16) : "";
}

function fromInput(value: string): string | undefined {
  return value ? `${value.length === 16 ? value + ":00" : value}Z` : undefined;
}

export function TemporalSection({ part, node }: { part: Part; node: string }) {
  const { model } = useStudio();
  const graph = model.state.configs[part]!.current;
  const scope = graph.object(node, FND("hasTemporalScope"));
  const from = scope && graph.value(scope, FND("validFrom"));
  const to = scope && graph.value(scope, FND("validTo"));
  const write = (nextFrom?: string, nextTo?: string) =>
    model.edit(part, (g) =>
      g.edit((e) => {
        if (!nextFrom && !nextTo) return e.set(node, FND("hasTemporalScope"), undefined);
        const b = blankNode();
        e.set(node, FND("hasTemporalScope"), b);
        e.add(b, TYPE, iri(FND("TemporalScope")));
        if (nextFrom) e.add(b, FND("validFrom"), typed(nextFrom, XSD("dateTime")));
        if (nextTo) e.add(b, FND("validTo"), typed(nextTo, XSD("dateTime")));
      }),
    );
  return (
    <div className="fields">
      <div className="field">
        <div className="label">
          <div className="name">Valid from</div>
          <div className="prop">fnd:validFrom</div>
        </div>
        <input className="input" type="datetime-local" aria-label="Valid from" value={toInput(from)} onChange={(e) => write(fromInput(e.target.value), to)} />
        <div className="help">The first instant the binding applies, in UTC. Not set, it applies from the beginning of time.</div>
      </div>
      <div className="field">
        <div className="label">
          <div className="name">Valid to</div>
          <div className="prop">fnd:validTo</div>
        </div>
        <input className="input" type="datetime-local" aria-label="Valid to" value={toInput(to)} onChange={(e) => write(from, fromInput(e.target.value))} />
        <div className="help">The first instant it no longer applies, exclusive. Not set, it applies until replaced.</div>
      </div>
    </div>
  );
}

const PALETTE = ["#4f46e5", "#0e7c86", "#b4541a", "#6d4bd6", "#18794e", "#a3410f", "#1662c4"];

function segmentLabel(r: Resolution): string {
  const d = (v?: string) => (v ? new Date(v).toISOString().slice(0, 10) : "");
  if (!r.from && !r.to) return "Always";
  if (!r.from) return `Before ${d(r.to)}`;
  if (!r.to) return `From ${d(r.from)}`;
  return `${d(r.from)} to ${d(r.to)}`;
}

/** Every resolution of a contract: one column per time segment, one row per set of active scopes,
 * and a chooser for a moment and a set that picks one cell out. */
export function ResolutionSection({ node }: { node: string }) {
  const { model, world } = useStudio();
  const validation = model.state.configs.vocabulary!.validation;
  const rows = (validation.job?.resolutions ?? []).filter((r) => r.contract === node);
  const segments = [...new Map(rows.map((r) => [`${r.from ?? ""}|${r.to ?? ""}`, r])).values()].sort((a, b) => (a.from ?? "").localeCompare(b.from ?? ""));
  const contexts = [...new Map(rows.map((r) => [r.context.join(" "), r.context])).values()].sort((a, b) => a.length - b.length || a.join().localeCompare(b.join()));
  const schemes = [...new Set(rows.map((r) => r.scheme).filter(Boolean))] as string[];
  const colour = (s?: string) => (s ? PALETTE[schemes.indexOf(s) % PALETTE.length] : undefined);
  const scopes = [...new Set(contexts.flat())].sort();
  const [at, setAt] = useState(() => new Date().toISOString().slice(0, 16));
  const [active, setActive] = useState<string[]>([]);
  const instant = Date.parse(fromInput(at) ?? "");
  const chosen = rows.find(
    (r) => (!r.from || Date.parse(r.from) <= instant) && (!r.to || instant < Date.parse(r.to)) && r.context.join(" ") === [...active].sort().join(" "),
  );

  if (!rows.length) {
    return (
      <div className="fields">
        <p className="muted small">{validation.state === "running" ? "Resolving…" : "The table appears once the vocabulary validates. A contract with no binding and no fallback scheme has nothing to resolve."}</p>
      </div>
    );
  }
  const cell = (key: string, r?: Resolution) => {
    if (!r) return <td key={key} />;
    const selected = r === chosen;
    const text = r.outcome === "Conflict" ? "Conflict" : r.outcome === "Unresolved" ? "No scheme" : label(world, r.scheme);
    return (
      <td key={key}>
        <span
          className={`res-cell ${r.outcome.toLowerCase()}${selected ? " selected" : ""}`}
          style={r.scheme ? ({ "--scheme": colour(r.scheme) } as React.CSSProperties) : undefined}
          title={r.outcome === "Conflict" ? `Tied: ${r.tied.map((t) => localName(t)).join(", ")}` : r.binding ? `by ${localName(r.binding)}` : r.outcome === "Fallback" ? "the contract's boundScheme" : undefined}
        >
          {text}
          {r.outcome === "Fallback" && <span className="small"> · fallback</span>}
        </span>
      </td>
    );
  };
  return (
    <div className="fields">
      <div style={{ overflowX: "auto" }}>
        <table className="grid res-table" aria-label="Resolution table">
          <thead>
            <tr>
              <th>Active scopes</th>
              {segments.map((s) => (
                <th key={segmentLabel(s)}>{segmentLabel(s)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {contexts.map((c) => (
              <tr key={c.join(" ")}>
                <td className="small">{c.length ? c.map((s) => label(world, s)).join(" + ") : <span className="muted">none</span>}</td>
                {segments.map((s) => cell(segmentLabel(s), rows.find((r) => r.from === s.from && r.to === s.to && r.context.join(" ") === c.join(" "))))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="try card">
        <div className="row" style={{ flexWrap: "wrap" }}>
          <strong>Try it</strong>
          <input className="input" style={{ width: 220 }} type="datetime-local" aria-label="Resolution time" value={at} onChange={(e) => setAt(e.target.value)} />
          {scopes.map((s) => (
            <label key={s} className="row small">
              <input type="checkbox" checked={active.includes(s)} onChange={(e) => setActive(e.target.checked ? [...active, s] : active.filter((x) => x !== s))} /> {label(world, s)}
            </label>
          ))}
        </div>
        {chosen && (
          <div className="small" style={{ marginTop: 8 }} role="status" aria-label="Resolution">
            {chosen.outcome === "Conflict" && <span className="chip bad">Conflict between {chosen.tied.map((t) => localName(t)).join(" and ")}: neither binding is more specific, so nothing resolves.</span>}
            {chosen.outcome === "Unresolved" && <span className="chip warn">No binding applies and the contract names no fallback scheme.</span>}
            {(chosen.outcome === "Resolved" || chosen.outcome === "Fallback") && (
              <>
                Resolves to <strong>{label(world, chosen.scheme)}</strong> {chosen.binding ? <>by binding {localName(chosen.binding)}</> : <>as the contract's fallback</>}, with its concepts:
                <SchemeTree scheme={chosen.scheme!} />
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function SchemeTree({ scheme, decide }: { scheme: string; decide?: (concept: string) => Decision | undefined }) {
  const { world } = useStudio();
  const forest = useMemo(() => conceptForest(world, conceptsOf(world, scheme)), [world, scheme]);
  const tree = (n: ConceptNode, depth: number): React.ReactNode => {
    const decision = decide?.(n.iri);
    return (
      <div key={n.iri}>
        <div className="concept-row" style={{ paddingLeft: 8 + depth * 18 }}>
          <span className={`dot ${decision ? TONE[decision] : ""}`} style={decision ? undefined : { background: "var(--baseline-c)" }} />
          {n.label}
          {decision && <span className={`chip ${TONE[decision]}`}>{decision}</span>}
        </div>
        {n.children.map((c) => tree(c, depth + 1))}
      </div>
    );
  };
  return <div className="concept-tree">{forest.length ? forest.map((n) => tree(n, 0)) : <span className="muted">no concepts</span>}</div>;
}

// --- eligibility -------------------------------------------------------------------------------

function useEligibilityJob() {
  const { model } = useStudio();
  const validation = model.state.configs.eligibility!.validation;
  return { validation, expansions: validation.job?.expansions ?? [], tests: validation.job?.tests ?? [] };
}

function ContextControls({ node }: { node: string }) {
  const { model, world } = useStudio();
  const graph = model.state.configs.eligibility!.current;
  const at = graph.value(node, CST("resolutionTime"));
  const scopes = graph.objects(node, CST("resolutionScope")).map((t) => t.value);
  const all = world.ofType(VOC("BindingScope")).map((s) => s.value);
  return (
    <div className="row small" style={{ flexWrap: "wrap" }}>
      <span className="muted">Resolve the scheme as of</span>
      <input
        className="input"
        style={{ width: 210 }}
        type="datetime-local"
        aria-label="Resolve as of"
        value={toInput(at)}
        onChange={(e) => model.edit("eligibility", (g) => setContext(g, node, fromInput(e.target.value), scopes))}
      />
      {all.map((s) => (
        <label key={s} className="row">
          <input
            type="checkbox"
            checked={scopes.includes(s)}
            onChange={(e) => model.edit("eligibility", (g) => setContext(g, node, at, e.target.checked ? [...scopes, s] : scopes.filter((x) => x !== s)))}
          />
          {label(world, s)}
        </label>
      ))}
      {!at && <span className="muted">(not set: the moment of validation)</span>}
    </div>
  );
}

/** Every member of the condition's resolved scheme, coloured by the compiler's decision for it. */
export function ExpansionSection({ node }: { node: string }) {
  const { world } = useStudio();
  const { validation, expansions } = useEligibilityJob();
  const mine = expansions.filter((e) => e.condition === node);
  const decided = new Map(mine.map((e: Expansion) => [e.concept, e.decision]));
  const scheme = mine.length ? world.value(mine[0].concept, SKOS("inScheme")) : undefined;
  const counts = DECISIONS.map((d) => [d, mine.filter((e) => e.decision === d).length] as const);
  return (
    <div className="fields">
      <ContextControls node={node} />
      {mine.length === 0 ? (
        <p className="muted small">
          {validation.state === "running"
            ? "Deciding…"
            : "The compiler expands a hierarchical condition, or one with exclusions only, over its resolved scheme. This condition has no expansion: it matches its required concepts exactly, or it does not compile yet."}
        </p>
      ) : (
        <>
          <div className="row" style={{ margin: "8px 0" }}>
            {counts.map(([d, n]) => (
              <span key={d} className={`chip ${TONE[d]}`}>
                {n} {d.toLowerCase()}
              </span>
            ))}
          </div>
          {scheme ? <SchemeTree scheme={scheme} decide={(c) => decided.get(c)} /> : null}
        </>
      )}
    </div>
  );
}

/** The condition's questions, each with a candidate, the decision expected of it and the decision
 * its compiled query gave. */
export function TestsSection({ node }: { node: string }) {
  const { model, world, baseline } = useStudio();
  const graph = model.state.configs.eligibility!.current;
  const { validation, tests } = useEligibilityJob();
  const questions = questionsFor(graph, node);
  const results = new Map(tests.map((t: TestResult) => [t.question, t]));
  const interval = graph.types(node).includes(ELG("IntervalCondition")) || graph.value(node, ELG("matchStrategy")) === ELG("IntervalContainment");
  const space = interval ? conditionSpace(world, node) : undefined;
  const concepts = world.ofType(SKOS("Concept")).map((c) => ({ iri: c.value, label: label(world, c.value), group: label(world, world.value(c, SKOS("inScheme"))) || "Concepts" }));
  const [candidate, setCandidate] = useState<string[]>([]);
  const [value, setValue] = useState("");
  const [expected, setExpectedNew] = useState<Decision | undefined>("Permitted");
  const add = () => {
    const name = interval ? `${localName(node)} ${value}` : `${localName(node)} ${localName(candidate[0] ?? "")}`;
    model.edit("eligibility", (g) => {
      if (interval) return space && value !== "" ? addQuestion(g, baseline.namespace, node, name, { value: Number(value), space }, expected).graph : g;
      return candidate[0] ? addQuestion(g, baseline.namespace, node, name, { concept: candidate[0] }, expected).graph : g;
    });
    setCandidate([]);
    setValue("");
  };
  const candidateLabel = (c?: string) => {
    if (!c) return "none";
    if (!interval) return label(world, c);
    const ranges = rangesOf(world, c);
    return ranges[0]?.lower ? String(ranges[0].lower.value) : compact(c);
  };
  const passed = questions.filter((q) => results.get(q.iri)?.passed === true).length;
  const failed = questions.filter((q) => results.get(q.iri)?.passed === false).length;
  return (
    <div className="fields">
      <div className="row" style={{ marginBottom: 8 }}>
        <FlaskConical size={15} />
        <span className="small">
          Each question is decided by the condition's compiled SPARQL, run on the configuration as edited.
        </span>
        <span className="spacer" />
        {validation.state === "running" ? <span className="chip accent">running</span> : null}
        {questions.length > 0 && (
          <>
            <span className="chip ok">{passed} pass</span>
            <span className={`chip ${failed ? "bad" : ""}`}>{failed} fail</span>
          </>
        )}
      </div>
      {questions.length > 0 && (
        <table className="grid" aria-label="Tests">
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Context</th>
              <th>Expect</th>
              <th>Decided</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {questions.map((q) => {
              const r = results.get(q.iri);
              return (
                <tr key={q.iri} aria-label={`Test ${localName(q.iri)}`}>
                  <td>
                    <strong>{candidateLabel(q.candidate)}</strong>
                    <div className="small muted mono">{localName(q.iri)}</div>
                  </td>
                  <td className="small">
                    {q.at ? new Date(q.at).toISOString().slice(0, 10) : <span className="muted">now</span>}
                    {q.scopes.length > 0 && <div>{q.scopes.map((s) => label(world, s)).join(" + ")}</div>}
                  </td>
                  <td>
                    <select className="select" aria-label="Expected decision" value={q.expected ?? ""} onChange={(e) => model.edit("eligibility", (g) => setExpected(g, q.iri, (e.target.value || undefined) as Decision | undefined))}>
                      <option value="">no expectation</option>
                      {DECISIONS.map((d) => (
                        <option key={d}>{d}</option>
                      ))}
                    </select>
                  </td>
                  <td>
                    {r ? (
                      <span className={`chip ${TONE[r.decision]}`} title={r.diagnostic}>
                        {r.decision === "NotTested" ? "not tested" : r.decision}
                        {r.diagnostic && ` · ${r.diagnostic}`}
                      </span>
                    ) : (
                      <span className="muted small">…</span>
                    )}
                    {r?.passed === true && <Check size={14} color="var(--ok)" aria-label="passes" style={{ marginLeft: 6 }} />}
                    {r?.passed === false && <X size={14} color="var(--bad)" aria-label="fails" style={{ marginLeft: 6 }} />}
                  </td>
                  <td>
                    <button className="btn ghost icon sm" aria-label={`Delete test ${localName(q.iri)}`} onClick={() => model.edit("eligibility", (g) => removeQuestion(g, q.iri))}>
                      <Trash2 size={12} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      <div className="row" style={{ marginTop: 10, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div className="grow" style={{ minWidth: 220 }}>
          {interval ? (
            space ? (
              <input className="input" inputMode="decimal" placeholder={`A value on ${label(world, space)}`} aria-label="Candidate value" value={value} onChange={(e) => setValue(e.target.value)} />
            ) : (
              <span className="small muted">Set the required range set first, so a candidate has a value space.</span>
            )
          ) : (
            <TermPicker single selected={candidate} options={concepts} placeholder="A candidate concept" onChange={setCandidate} />
          )}
        </div>
        <select className="select" style={{ width: 170 }} aria-label="Expect" value={expected ?? ""} onChange={(e) => setExpectedNew((e.target.value || undefined) as Decision | undefined)}>
          <option value="">no expectation</option>
          {DECISIONS.map((d) => (
            <option key={d} value={d}>
              expect {d}
            </option>
          ))}
        </select>
        <button className="btn" onClick={add}>
          <Plus size={14} /> Add test
        </button>
      </div>
    </div>
  );
}

export function ProfileTestsSection() {
  return (
    <div className="fields">
      <UnderConstruction waitsOn="a way to record a whole admission profile's expected decision for a set of answers, beside the condition tests">
        Testing a profile's composed decision is not yet available. Test each of its conditions instead. The build compiles the profile's query and shapes.
      </UnderConstruction>
    </div>
  );
}

// --- quantification ----------------------------------------------------------------------------

/** Ranges drawn on a number line, with test values marked by their decision. */
export function NumberLine({ ranges, marks = [] }: { ranges: RangeView[]; marks?: { value: number; decision?: string; label: string }[] }) {
  const ends = [...ranges.flatMap((r) => [r.lower?.value, r.upper?.value]), ...marks.map((m) => m.value)].filter((v): v is number => v !== undefined);
  if (!ends.length) return <p className="muted small">Nothing to draw: no range has a bound with a value.</p>;
  let min = Math.min(...ends);
  let max = Math.max(...ends);
  const pad = (max - min || Math.abs(max) || 1) * 0.15;
  min -= pad;
  max += pad;
  const W = 640;
  const x = (v: number) => 20 + ((v - min) / (max - min)) * (W - 40);
  const point = (e: End | undefined, side: "lower" | "upper", y: number) => {
    if (!e) return <path d={side === "lower" ? `M30 ${y} l8 -5 v10 z` : `M${W - 30} ${y} l-8 -5 v10 z`} fill="var(--accent)" />;
    return <circle cx={x(e.value)} cy={y} r={5} fill={e.closed ? "var(--accent)" : "var(--surface)"} stroke="var(--accent)" strokeWidth={2} />;
  };
  return (
    <svg viewBox={`0 0 ${W} ${40 + ranges.length * 22}`} className="numberline" role="img" aria-label="Ranges on a number line">
      <line x1={20} x2={W - 20} y1={18} y2={18} stroke="var(--border-strong)" />
      {[min + pad, (min + max) / 2, max - pad].map((t) => (
        <text key={t} x={x(t)} y={12} fontSize={10} textAnchor="middle" fill="var(--text-3)">
          {Number(t.toPrecision(6))}
        </text>
      ))}
      {ranges.map((r, i) => {
        const y = 38 + i * 22;
        const a = r.lower ? x(r.lower.value) : 30;
        const b = r.upper ? x(r.upper.value) : W - 30;
        return (
          <g key={r.iri}>
            <line x1={a} x2={b} y1={y} y2={y} stroke="var(--accent)" strokeWidth={4} strokeLinecap="round" opacity={0.5} />
            {point(r.lower, "lower", y)}
            {point(r.upper, "upper", y)}
            <text x={b + 8} y={y + 4} fontSize={10} fill="var(--text-3)">
              {r.lower ? `${r.lower.closed ? "[" : "("}${r.lower.value}` : "(−∞"}, {r.upper ? `${r.upper.value}${r.upper.closed ? "]" : ")"}` : "∞)"}
            </text>
          </g>
        );
      })}
      {marks.map((m) => (
        <g key={m.label}>
          <line x1={x(m.value)} x2={x(m.value)} y1={20} y2={30 + ranges.length * 22} stroke={`var(--${TONE[m.decision ?? ""] || "text-3"})`} strokeDasharray="3 3" />
          <circle cx={x(m.value)} cy={18} r={4} fill={`var(--${TONE[m.decision ?? ""] || "text-3"})`} />
        </g>
      ))}
    </svg>
  );
}

/** A range set's ranges, or a condition's required ones, with a form that writes a range's seven nodes. */
export function RangesSection({ part, node }: { part: Part; node: string }) {
  const { model, world, baseline, open } = useStudio();
  const isCondition = part === "eligibility";
  const rangeSet = isCondition ? world.value(node, ELG("requiredRangeSet")) : node;
  const ranges = rangeSet ? rangesOf(world, rangeSet) : [];
  const { tests } = useEligibilityJob();
  const marks = isCondition
    ? questionsFor(model.state.configs.eligibility!.current, node).flatMap((q) => {
        const r = q.candidate ? rangesOf(world, q.candidate)[0] : undefined;
        return r?.lower ? [{ value: r.lower.value, decision: tests.find((t) => t.question === q.iri)?.decision, label: q.iri }] : [];
      })
    : [];
  const spaces = world.ofType(QNT("ValueSpace")).map((s) => ({ iri: s.value, label: label(world, s.value), group: "Value spaces" }));
  const [space, setSpace] = useState<string[]>(rangeSet && world.value(rangeSet, QNT("onSpace")) ? [world.value(rangeSet, QNT("onSpace"))!] : []);
  const [lower, setLower] = useState("");
  const [upper, setUpper] = useState("");
  const [lowerClosed, setLowerClosed] = useState(true);
  const [upperClosed, setUpperClosed] = useState(true);
  const rangeSetPart = rangeSet && model.state.configs.quantification!.current.has(rangeSet) ? "quantification" : isCondition ? "quantification" : part;
  const add = () => {
    if (!space[0] || (lower === "" && upper === "")) return;
    const spec = {
      space: space[0],
      lower: lower === "" ? undefined : { value: Number(lower), closed: lowerClosed },
      upper: upper === "" ? undefined : { value: Number(upper), closed: upperClosed },
    };
    let set = rangeSet;
    if (!set) {
      model.edit("quantification", (g) => {
        set = mint(g, baseline.namespace, `${localName(node)} required`);
        return g.edit((e) => {
          e.add(set!, TYPE, iri(QNT("RangeSet")));
          e.add(set!, QNT("onSpace"), iri(space[0]));
        });
      });
      model.edit("eligibility", (g) => g.edit((e) => e.set(node, ELG("requiredRangeSet"), iri(set!))));
    }
    model.edit(rangeSetPart as Part, (g) => addRange(g, baseline.namespace, `${localName(set!)}`, spec, set).graph);
    setLower("");
    setUpper("");
  };
  return (
    <div className="fields">
      <NumberLine ranges={ranges} marks={marks} />
      {ranges.map((r) => (
        <div key={r.iri} className="row small" style={{ padding: "4px 0" }}>
          <button className="link" onClick={() => open("quantification", r.iri)}>
            {localName(r.iri)}
          </button>
          <span className="muted">
            {r.lower ? `${r.lower.closed ? "[" : "("}${r.lower.value}` : "(−∞"}, {r.upper ? `${r.upper.value}${r.upper.closed ? "]" : ")"}` : "∞)"}
          </span>
          {marks.map((m) => (
            <span key={m.label} className={`chip ${contains(r, m.value) ? "ok" : ""}`}>
              {m.value} {contains(r, m.value) ? "inside" : "outside"}
            </span>
          ))}
          <span className="spacer" />
          <button className="btn ghost icon sm" aria-label={`Delete range ${localName(r.iri)}`} onClick={() => model.edit(rangeSetPart as Part, (g) => removeRange(g, r.iri))}>
            <Trash2 size={12} />
          </button>
        </div>
      ))}
      <div className="range-form">
        <div style={{ minWidth: 220 }} className="grow">
          <TermPicker single selected={space} options={spaces} placeholder="On value space" onChange={setSpace} />
        </div>
        <label className="row small">
          <input type="checkbox" checked={lowerClosed} onChange={(e) => setLowerClosed(e.target.checked)} /> closed
        </label>
        <input className="input" style={{ width: 110 }} inputMode="decimal" placeholder="lower" aria-label="Lower bound" value={lower} onChange={(e) => setLower(e.target.value)} />
        <span className="muted">to</span>
        <input className="input" style={{ width: 110 }} inputMode="decimal" placeholder="upper" aria-label="Upper bound" value={upper} onChange={(e) => setUpper(e.target.value)} />
        <label className="row small">
          <input type="checkbox" checked={upperClosed} onChange={(e) => setUpperClosed(e.target.checked)} /> closed
        </label>
        <button className="btn" onClick={add} disabled={!space[0] || (lower === "" && upper === "")}>
          <Plus size={14} /> Add range
        </button>
      </div>
      <p className="small muted">A range writes its two bounds and their quantities with it. Leave a side empty for an unbounded range.</p>
      <UnderConstruction waitsOn="a reference implementation of quantification's comparisons and conversions, which the repository does not have yet">
        Comparing quantities across units, merging a range set into its canonical form, and checking a value against a space's granularity are not computed here.
      </UnderConstruction>
    </div>
  );
}

export function LineSection({ node }: { node: string }) {
  const { world } = useStudio();
  return (
    <div className="fields">
      <NumberLine ranges={[readRange(world, node)]} />
    </div>
  );
}
