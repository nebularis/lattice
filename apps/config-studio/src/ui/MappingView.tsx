// SPDX-License-Identifier: MPL-2.0
// Mapping mode's view: the source concepts a MORK mapping scheme reads on the left, its mappings drawn as the tree their
// parent links make, each with the terms it writes and its latest review, and for the mapping picked its review and its
// editor, whose findings come from compiling the part with mork_rdf as it is edited. Given a sample source, the part runs
// over it whenever either changes, and the author steps through the run's strata, each mapping showing what it wrote. A
// language model proposes a scheme from a source vocabulary with MORK's proposal tools, and the author reviews each of
// its mappings here, each review a mork:MappingReview the next proposal learns from.

import { useEffect, useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Hammer, Network, Plus, Sparkles } from "lucide-react";
import { CST, Graph, LABEL, MORK, PREFIXES, TYPE, compact, iri, literal, namespaceOf } from "@lattice/authoring-domain";
import { api, awaitJob } from "../api";
import { applyArtefacts, importDocument, mediaTypeOf } from "../rdf/odrl";
import { mint } from "../rdf/editors";
import { reviewGraph, schemesOf, written, type MappingNode, type RunCost, type Scheme } from "../rdf/mapping";
import { Spinner, go } from "./kit";
import { NodeEditor } from "./ConfigView";
import { MappingCanvas } from "./MappingCanvas";
import { useStudio } from "./Workspace";

const INDENT = 28;
const BOX_W = 240;
const BOX_H = 26;
const ROW_H = 34;
const MARGIN = 16;

export function MappingView({ selected }: { selected?: string }) {
  const studio = useStudio();
  const graph = studio.model.state.configs.mapping!.current;
  const schemes = useMemo(() => schemesOf(graph), [graph]);
  const prefixes = useMemo(() => ({ ...PREFIXES, ...graph.prefixes }), [graph]);
  const [schemeIri, setSchemeIri] = useState<string>();
  const [source, setSource] = useState<string>();
  // The picked mapping's scheme, so a correction's link opens the scheme it is in.
  const scheme = schemes.find((s) => s.mappings.some((m) => m.iri === selected)) ?? schemes.find((s) => s.iri === schemeIri) ?? schemes[0];
  const open = (node: string) => go("w", studio.id, "mapping", node);
  const picked = scheme?.mappings.find((m) => m.iri === selected);
  const [busy, setBusy] = useState(false);
  const sampleRun = useSampleRun(studio.id, graph);
  const [drawing, setDrawing] = useState<"tree" | "canvas">(() => {
    try {
      return localStorage.getItem("lattice-studio:mapping-drawing") === "canvas" ? "canvas" : "tree";
    } catch {
      return "tree";
    }
  });
  const draw = (to: "tree" | "canvas") => {
    setDrawing(to);
    try {
      localStorage.setItem("lattice-studio:mapping-drawing", to);
    } catch {
      // The drawing is remembered for this visit only.
    }
  };

  /** A new mapping in the scheme, under `parent` when one is given, named by the author. */
  const add = (type: "Datum" | "DataMapping", parent?: string) => {
    const name = window.prompt(`Name the new ${type === "Datum" ? "datum" : "data mapping"}`);
    if (!name?.trim() || !scheme) return;
    const node = mint(graph, namespaceOf(scheme.iri), name.trim());
    studio.model.edit("mapping", (g) =>
      g.edit((e) => {
        e.add(node, TYPE, iri(MORK(type)));
        e.add(node, MORK("mappingScheme"), iri(scheme.iri));
        e.add(node, LABEL, literal(name.trim()));
        if (parent) e.add(node, MORK("compositeBroaderMapping"), iri(parent));
      }),
    );
    open(node);
  };

  /** Compiles the part as edited, saved or not, and opens the build view on the job. */
  const compile = async () => {
    setBusy(true);
    try {
      await api.submit(studio.id, "compile", "mapping", graph);
      go("w", studio.id, "build");
    } finally {
      setBusy(false);
    }
  };

  const proposed = (iri?: string) => iri && go("w", studio.id, "mapping", iri);
  if (!scheme) {
    return (
      <div className="empty">
        <Network size={28} color="var(--accent)" />
        <h3>No mapping scheme yet</h3>
        <p className="small">Import a file holding a MORK mapping scheme, such as a mapping pack, or have a language model propose one from a source vocabulary.</p>
        <div style={{ maxWidth: 420, width: "100%", textAlign: "left" }}>
          <SamplePanel run={sampleRun} />
          <ProposePanel sample={sampleRun.sample} onProposed={proposed} />
        </div>
      </div>
    );
  }
  return (
    <div className="split" style={{ gridTemplateColumns: "minmax(280px, 340px) 1fr" }}>
      <div className="list" aria-label="Source">
        <div className="list-head">
          <div className="row">
            <Network size={16} />
            <strong className="grow">Mapping</strong>
            <span className="small muted">{scheme.mappings.length} mappings</span>
          </div>
          {schemes.length > 1 && (
            <select value={scheme.iri} onChange={(e) => {
              setSchemeIri(e.target.value);
              go("w", studio.id, "mapping");
            }} aria-label="Mapping scheme">
              {schemes.map((s) => (
                <option key={s.iri} value={s.iri}>{s.label}</option>
              ))}
            </select>
          )}
          <div className="small muted">{scheme.label}</div>
          {scheme.run && <div className="small muted">{cost(scheme.run)}</div>}
          <div className="row" style={{ gap: 6 }}>
            <button className="btn sm" onClick={() => add("Datum")}><Plus size={13} /> Root datum</button>
            <button className="btn sm" disabled={busy} onClick={() => void compile()}>{busy ? <Spinner /> : <Hammer size={13} />} Compile</button>
          </div>
        </div>
        <SamplePanel run={sampleRun} />
        <ProposePanel sample={sampleRun.sample} onProposed={proposed} />
        <h4>Source concepts it maps</h4>
        {scheme.sources.length === 0 && <div className="empty small">No mapping of the scheme names a source concept.</div>}
        {scheme.sources.map((s) => {
          const readers = scheme.mappings.filter((m) => m.source === s.iri).length;
          return (
            <div key={s.iri} className="list-item" aria-selected={s.iri === source} onClick={() => setSource(s.iri === source ? undefined : s.iri)}>
              <div className="grow" style={{ minWidth: 0 }}>
                <div className="name">{s.label}</div>
                <div className="detail mono" style={{ overflowWrap: "anywhere" }}>{s.path ?? s.representedAs.map((r) => compact(r, prefixes)).join(", ")}</div>
              </div>
              <span className="count small muted">{readers}</span>
            </div>
          );
        })}
      </div>
      <div className="detail-pane">
        <div className="editor" style={{ maxWidth: "none" }}>
          {picked && <MappingCard node={picked} schemes={schemes} prefixes={prefixes} open={open} add={add} output={sampleRun.output(picked.iri)} />}
          {picked && <div style={{ margin: "0 -28px" }}><NodeEditor key={picked.iri} part="mapping" node={picked.iri} /></div>}
          <section className="card section" aria-label={`Mappings of ${scheme.label}`}>
            <header>
              <h3 className="grow">Mappings</h3>
              {sampleRun.result && <Stepper run={sampleRun} />}
              <div className="mode-switch" role="group" aria-label="Drawing" style={{ margin: 0 }}>
                <button aria-pressed={drawing === "tree"} onClick={() => draw("tree")}>Tree</button>
                <button aria-pressed={drawing === "canvas"} onClick={() => draw("canvas")}>Canvas</button>
              </div>
            </header>
            {drawing === "tree" ? (
              <>
                <p className="small muted" style={{ margin: "8px 16px 0" }}>Indented under their parent. a writes a type, → a property, ← an inverse property, = an individual. The bar on the left is the latest review.</p>
                <div style={{ padding: "8px 16px", overflowX: "auto" }}>
                  <Tree scheme={scheme} prefixes={prefixes} selected={selected} source={source} open={open} run={sampleRun} />
                </div>
              </>
            ) : (
              <>
                <p className="small muted" style={{ margin: "8px 16px 0" }}>Drag from a mapping's right edge to another mapping to make it the parent, or from a source concept to say what a mapping maps for. Right-click a mapping, a link or the canvas for what fits there.</p>
                <MappingCanvas workspace={studio.id} scheme={scheme} graph={graph} prefixes={prefixes} selected={selected} open={open} add={add}
                  edit={(change) => studio.model.edit("mapping", change)} counts={sampleRun.result ? (m) => sampleRun.output(m).length : undefined} />
              </>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

function Tree({ scheme, prefixes, selected, source, open, run }: { scheme: Scheme; prefixes: Record<string, string>; selected?: string; source?: string; open: (n: string) => void; run: SampleRun }) {
  const row = new Map(scheme.mappings.map((m) => [m.iri, m]));
  const depth = Math.max(0, ...scheme.mappings.map((m) => m.depth));
  const width = MARGIN * 2 + depth * INDENT + BOX_W + 520;
  const height = MARGIN * 2 + scheme.mappings.length * ROW_H;
  const x = (m: MappingNode) => MARGIN + m.depth * INDENT;
  const y = (m: MappingNode) => MARGIN + m.row * ROW_H;
  const press = (n: string) => (e: React.KeyboardEvent) => (e.key === "Enter" || e.key === " ") && open(n);
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="tree" aria-label={`Mappings of ${scheme.label}`} style={{ display: "block", font: "12px system-ui, sans-serif" }}>
      {scheme.mappings
        .filter((m) => m.parent && row.has(m.parent))
        .map((m) => {
          const p = row.get(m.parent!)!;
          const px = x(p) + 10;
          return <path key={`e-${m.iri}`} d={`M${px} ${y(p) + BOX_H} L${px} ${y(m) + BOX_H / 2} L${x(m)} ${y(m) + BOX_H / 2}`} fill="none" style={{ stroke: "var(--border-strong)" }} strokeWidth={1.2} />;
        })}
      {scheme.mappings.map((m) => {
        const on = m.iri === selected;
        const lit = !!source && m.source === source;
        const terms = written(m, prefixes).map((w) => `${w.box} ${w.term}`).join("   ");
        const extra = [m.template && `uses ${compact(m.template, prefixes)}`, m.guard && `when ${compact(m.guard, prefixes)}`].filter(Boolean).join(", ");
        // In a sample run, a mapping that has not run by the current step is dimmed, and one that has shows how much it wrote.
        const wrote = run.result ? run.output(m.iri).length : undefined;
        const ran = !run.result || run.result.ran.get(m.iri) !== undefined && run.result.ran.get(m.iri)! <= run.step;
        return (
          <g key={m.iri} role="treeitem" aria-level={m.depth + 1} aria-selected={on} tabIndex={0} onClick={() => open(m.iri)} onKeyDown={press(m.iri)} style={{ cursor: "pointer", opacity: ran ? 1 : 0.4 }}>
            <title>{`${m.label} (${m.kind})${m.reads ? `\nreads ${m.reads}` : ""}`}</title>
            <rect x={x(m)} y={y(m)} width={BOX_W} height={BOX_H} rx={6}
              style={{ fill: lit ? "var(--accent-2)" : m.isTemplate ? "var(--surface-2)" : "var(--surface)", stroke: on ? "var(--accent)" : "var(--border-strong)", strokeDasharray: m.isTemplate ? "4 3" : undefined }}
              strokeWidth={on ? 2.5 : 1.2} />
            {m.review && <rect x={x(m) + 1} y={y(m) + 4} width={4} height={BOX_H - 8} rx={2} style={{ fill: DECISION[m.review.decision] ?? "var(--text-3)" }}><title>{m.review.decision}</title></rect>}
            <text x={x(m) + 10} y={y(m) + BOX_H / 2 + 4} style={{ fill: "var(--text)", fontWeight: m.kind === "Datum" ? 600 : 400 }}>
              {m.label.length > 28 ? m.label.slice(0, 27) + "…" : m.label}
            </text>
            {wrote !== undefined && ran && (
              <text x={x(m) + BOX_W - 8} y={y(m) + BOX_H / 2 + 4} textAnchor="end" style={{ fill: wrote ? "var(--accent)" : "var(--text-3)", fontWeight: 600 }}>
                <title>{`${wrote} ${wrote === 1 ? "triple" : "triples"} written on the sample`}</title>
                {wrote}
              </text>
            )}
            <text x={x(m) + BOX_W + 12} y={y(m) + BOX_H / 2 + 4} style={{ fill: "var(--text-2, var(--text))" }}>
              {terms || (m.template ? "" : "writes nothing")}
              {extra && <tspan style={{ fill: "var(--text-3)" }}>{`   ${extra}`}</tspan>}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

const DECISION: Record<string, string> = { Accepted: "var(--ok)", Corrected: "var(--warn)", Rejected: "var(--bad)", Deferred: "var(--text-3)" };

/** The picked mapping's name, its children to add, and its latest review. Its fields and findings are in its editor. */
function MappingCard({ node, schemes, prefixes, open, add, output }: { node: MappingNode; schemes: Scheme[]; prefixes: Record<string, string>; open: (n: string) => void; add: (type: "Datum" | "DataMapping", parent?: string) => void; output?: string[] }) {
  const all = schemes.flatMap((s) => s.mappings);
  const r = node.review;
  return (
    <section className="card section" aria-label={`Mapping ${node.label}`} style={{ marginBottom: 16 }}>
      <header style={{ flexWrap: "wrap" }}>
        <h3 className="grow">{node.label}</h3>
        <button className="btn sm" onClick={() => add("Datum", node.iri)}><Plus size={13} /> Child datum</button>
        <button className="btn sm" onClick={() => add("DataMapping", node.iri)}><Plus size={13} /> Child data mapping</button>
      </header>
      {node.generatedBy && <ReviewControls node={node} scheme={schemes.find((s) => s.mappings.some((m) => m.iri === node.iri))!} prefixes={prefixes} />}
      {r && (
        <div className="fields">
          <div className="field">
            <div className="label"><div className="name">Review</div></div>
            <div>
              <span className="chip" style={{ color: DECISION[r.decision] }}>{r.decision}</span>
              {r.correctedBy && (
                <> by {all.some((m) => m.iri === r.correctedBy) ? <button className="link" onClick={() => open(r.correctedBy!)}>{all.find((m) => m.iri === r.correctedBy)!.label}</button> : <span className="mono">{compact(r.correctedBy, prefixes)}</span>}</>
              )}
              {r.note && <p className="small" style={{ margin: "6px 0 0" }}>{r.note}</p>}
              {(r.reviewer || r.at) && <div className="small muted">{[r.reviewer && compact(r.reviewer, prefixes), r.at?.slice(0, 10)].filter(Boolean).join(", ")}</div>}
            </div>
          </div>
        </div>
      )}
      {output && (
        <div className="fields">
          <div className="field">
            <div className="label"><div className="name">On the sample</div></div>
            {output.length === 0 ? (
              <span className="muted small">Wrote nothing by this step.</span>
            ) : (
              <pre className="mono small" style={{ margin: 0, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{output.map((t) => readable(t, prefixes)).join("\n")}</pre>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

/** The namespace the worker's run mints under (config_studio_jobs.py). */
const MINTED = "urn:lattice:studio:mapping/";

/** An N-Triples line with each IRI compacted where a prefix covers it, and each IRI the run minted shown by its path with
 * long hashes cut, since two nodes minted from one source node share their hash. */
function readable(line: string, prefixes: Record<string, string>): string {
  return line
    .replace(/<([^>]+)>/g, (whole, iri: string) => {
      if (iri.startsWith(MINTED)) return `new:${iri.slice(MINTED.length).replace(/([0-9a-f]{8})[0-9a-f]{8,}/g, "$1…")}`;
      return Object.values(prefixes).some((base) => iri.startsWith(base)) ? compact(iri, prefixes) : whole;
    })
    .replace(/ \.$/, "");
}

interface RunResult {
  /** Each mapping's output lines, by the stratum that wrote them. */
  lines: Map<string, { stratum: number; lines: string[] }[]>;
  /** The first stratum each mapping ran in. */
  ran: Map<string, number>;
  strata: number;
}

interface SampleRun {
  sample?: string;
  setSample: (text?: string) => void;
  state: "idle" | "running" | "failed";
  message?: string;
  result?: RunResult;
  step: number;
  setStep: (n: number) => void;
  /** What a mapping wrote by the current step. */
  output: (mapping: string) => string[];
}

/** The sample source, kept in this browser for the workspace, and the dry run of the mapping part over it, rerun 800 ms
 * after the part or the sample last changed. */
function useSampleRun(workspace: string, graph: Graph): SampleRun {
  const key = `lattice-studio:mapping-sample:${workspace}`;
  const [sample, setSampleState] = useState<string | undefined>(() => {
    try {
      return localStorage.getItem(key) ?? undefined;
    } catch {
      return undefined;
    }
  });
  const [state, setState] = useState<SampleRun["state"]>("idle");
  const [message, setMessage] = useState<string>();
  const [result, setResult] = useState<RunResult>();
  const [step, setStep] = useState(0);
  const setSample = (text?: string) => {
    setSampleState(text);
    if (!text) setResult(undefined);
    try {
      if (text) localStorage.setItem(key, text);
      else localStorage.removeItem(key);
    } catch {
      // A browser that keeps nothing still runs the sample for this visit.
    }
  };
  useEffect(() => {
    if (!sample?.trim() || graph.size === 0) return;
    let stale = false;
    const timer = setTimeout(async () => {
      setState("running");
      try {
        const id = await api.submit(workspace, "dry-run", "mapping", graph.merge(importDocument(workspace, sample, "text/turtle", false)));
        const job = await awaitJob(id);
        void api.deleteJob(id).catch(() => undefined);
        if (stale) return;
        if (job.status === "Failed") {
          setState("failed");
          setMessage(job.failure);
          return;
        }
        const lines = new Map<string, { stratum: number; lines: string[] }[]>();
        const ran = new Map<string, number>();
        let strata = 0;
        for (const a of job.artefacts) {
          const stratum = a.stratum ?? 0;
          strata = Math.max(strata, stratum + 1);
          lines.set(a.group, [...(lines.get(a.group) ?? []), { stratum, lines: a.content.split("\n").filter(Boolean) }]);
          ran.set(a.group, Math.min(ran.get(a.group) ?? stratum, stratum));
        }
        setResult({ lines, ran, strata });
        setStep((s) => (result && s < result.strata - 1 ? Math.min(s, strata - 1) : strata - 1));
        setState("idle");
        setMessage(undefined);
      } catch (error) {
        if (!stale) {
          setState("failed");
          setMessage(error instanceof Error ? error.message : String(error));
        }
      }
    }, 800);
    return () => {
      stale = true;
      clearTimeout(timer);
    };
  }, [workspace, graph, sample]); // eslint-disable-line react-hooks/exhaustive-deps
  const output = (mapping: string) => (result?.lines.get(mapping) ?? []).filter((o) => o.stratum <= step).flatMap((o) => o.lines);
  return { sample, setSample, state, message, result, step, setStep, output };
}

function SamplePanel({ run }: { run: SampleRun }) {
  const [draft, setDraft] = useState(run.sample ?? "");
  useEffect(() => setDraft(run.sample ?? ""), [run.sample]);
  const load = async (file?: File) => file && run.setSample(await file.text());
  return (
    <>
      <h4>Sample source</h4>
      <div style={{ padding: "0 14px 8px", display: "flex", flexDirection: "column", gap: 6 }}>
        <textarea className="mono small" rows={4} value={draft} placeholder="Paste a source in Turtle to run the mappings over it" aria-label="Sample source in Turtle" onChange={(e) => setDraft(e.target.value)} onBlur={() => draft !== (run.sample ?? "") && run.setSample(draft || undefined)} />
        <div className="row" style={{ gap: 6 }}>
          <label className="btn sm">
            Load a file
            <input type="file" accept=".ttl,.nt" hidden onChange={(e) => void load(e.target.files?.[0])} />
          </label>
          {run.sample && <button className="btn sm ghost" onClick={() => run.setSample(undefined)}>Clear</button>}
          <span className="grow small muted" role="status">
            {run.state === "running" ? <><Spinner size={12} /> Running</> : run.state === "failed" ? <span style={{ color: "var(--bad)" }}>{run.message ?? "The run failed."}</span> : run.result ? "Ran on the sample" : ""}
          </span>
        </div>
      </div>
    </>
  );
}

function Stepper({ run }: { run: SampleRun }) {
  const strata = run.result!.strata;
  return (
    <div className="row" style={{ gap: 4 }} aria-label="Step through the run">
      <button className="btn ghost icon sm" aria-label="Previous stratum" disabled={run.step <= 0} onClick={() => run.setStep(run.step - 1)}><ChevronLeft size={14} /></button>
      <span className="small">Stratum {run.step + 1} of {Math.max(strata, 1)}</span>
      <button className="btn ghost icon sm" aria-label="Next stratum" disabled={run.step >= strata - 1} onClick={() => run.setStep(run.step + 1)}><ChevronRight size={14} /></button>
    </div>
  );
}

/** A run's model, tokens and time, as a line. */
function cost(run: RunCost): string {
  const tokens = run.totalTokens ?? (run.inputTokens !== undefined || run.outputTokens !== undefined ? (run.inputTokens ?? 0) + (run.outputTokens ?? 0) : undefined);
  return [run.model && `proposed by ${run.model}`, tokens !== undefined && `${tokens.toLocaleString()} tokens`, run.seconds !== undefined && `${run.seconds} s`].filter(Boolean).join(", ");
}

/** One document a mapping proposal reads, with what it is read as. */
function document(node: string, content: string, media: string, role: "SourceVocabulary" | "SampleSource", namespace = ""): Graph {
  return Graph.empty().edit((e) => {
    e.add(node, TYPE, iri(CST("ImportDocument")));
    e.add(node, CST("documentContent"), literal(content));
    e.add(node, CST("documentMediaType"), literal(media));
    e.add(node, CST("documentRole"), iri(CST(role)));
    if (namespace) e.add(node, CST("sourceNamespace"), literal(namespace));
  });
}

/** Has a language model propose a scheme from a source vocabulary, checked over the sample source when there is one, and adds
 * it to the mapping part as an unsaved edit. The deployment configures the model. */
function ProposePanel({ sample, onProposed }: { sample?: string; onProposed: (scheme?: string) => void }) {
  const studio = useStudio();
  const [file, setFile] = useState<{ name: string; text: string }>();
  const [namespace, setNamespace] = useState("");
  const [state, setState] = useState<"idle" | "running" | "failed" | "done">("idle");
  const [message, setMessage] = useState<string>();
  const propose = async () => {
    const media = file && mediaTypeOf(file.name);
    if (!file || !media || media === "application/ld+json") {
      setState("failed");
      setMessage("Give the source vocabulary as Turtle or N-Triples.");
      return;
    }
    setState("running");
    setMessage(undefined);
    try {
      const id = studio.id;
      const source = document(`urn:lattice:studio:ws:${id}:import/1`, file.text, media, "SourceVocabulary", namespace.trim());
      const samples = sample ? document(`urn:lattice:studio:ws:${id}:import/2`, sample, "text/turtle", "SampleSource") : undefined;
      const current = studio.model.state.configs.mapping!.current;
      const body = [source, samples].reduce((g: Graph, d) => (d ? g.merge(d) : g), current);
      const job = await awaitJob(await api.submit(id, "propose", "mapping-language-model", body));
      if (job.status === "Failed") {
        setState("failed");
        setMessage(job.failure ?? "The proposal failed.");
        return;
      }
      const applied = applyArtefacts(job.artefacts, { mapping: current });
      if (applied.edits.mapping) studio.model.edit("mapping", () => applied.edits.mapping!);
      const errors = job.issues.filter((i) => i.severity === "Violation").length;
      setState("done");
      setMessage(`Proposed${errors ? `, with ${errors} ${errors === 1 ? "error" : "errors"} left` : ", and its check passed"}. Review each mapping, then save.`);
      onProposed(applied.edits.mapping?.ofType(MORK("MappingScheme")).find((s) => !current.has(s))?.value);
    } catch (error) {
      setState("failed");
      setMessage(error instanceof Error ? error.message : String(error));
    }
  };
  return (
    <>
      <h4>Propose with a language model</h4>
      <div style={{ padding: "0 14px 8px", display: "flex", flexDirection: "column", gap: 6 }}>
        <label className="btn sm" style={{ alignSelf: "flex-start" }}>
          {file ? file.name : "Source vocabulary"}
          <input type="file" accept=".ttl,.nt" hidden onChange={async (e) => {
            const f = e.target.files?.[0];
            if (f) setFile({ name: f.name, text: await f.text() });
          }} />
        </label>
        <input className="input mono small" placeholder="Its namespace, to read only its own terms" aria-label="Source namespace" value={namespace} onChange={(e) => setNamespace(e.target.value)} />
        <div className="row" style={{ gap: 6 }}>
          <button className="btn sm primary" disabled={!file || state === "running"} onClick={() => void propose()}>
            {state === "running" ? <Spinner size={12} /> : <Sparkles size={13} />} Propose
          </button>
          <span className="grow small muted" role="status">
            {state === "running" ? "The model is proposing, which takes minutes" : state === "failed" ? <span style={{ color: "var(--bad)" }}>{message}</span> : message ?? (sample ? "It is checked over the sample source." : "Give a sample source above to have it checked on data.")}
          </span>
        </div>
      </div>
    </>
  );
}

/** Accept, correct, reject or defer a proposed mapping, with a note, as a mork:MappingReview in the mapping part. */
function ReviewControls({ node, scheme, prefixes }: { node: MappingNode; scheme: Scheme; prefixes: Record<string, string> }) {
  const studio = useStudio();
  const [note, setNote] = useState("");
  const [correctedBy, setCorrectedBy] = useState("");
  const decide = (decision: "Accepted" | "Corrected" | "Rejected" | "Deferred") => {
    const graph = studio.model.state.configs.mapping!.current;
    const n = graph.subjects(MORK("reviewOf"), node.iri).length + 1;
    studio.model.edit("mapping", (g) => g.merge(reviewGraph(node.iri, decision, note, new Date().toISOString(), n, decision === "Corrected" && correctedBy ? correctedBy : undefined)));
    setNote("");
  };
  return (
    <div className="fields">
      <div className="field">
        <div className="label"><div className="name">Your review</div></div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <textarea className="small" rows={2} value={note} placeholder="Why, which the next proposal is told" aria-label="Review note" onChange={(e) => setNote(e.target.value)} />
          <select className="select small" value={correctedBy} onChange={(e) => setCorrectedBy(e.target.value)} aria-label="Corrected by">
            <option value="">Corrected by no mapping of the scheme</option>
            {scheme.mappings.filter((m) => m.iri !== node.iri).map((m) => (
              <option key={m.iri} value={m.iri}>{m.label} ({compact(m.iri, prefixes)})</option>
            ))}
          </select>
          <div className="row" style={{ gap: 6, flexWrap: "wrap" }}>
            {(["Accepted", "Corrected", "Rejected", "Deferred"] as const).map((d) => (
              <button key={d} className="btn sm" style={{ color: DECISION[d] }} onClick={() => decide(d)}>{d === "Accepted" ? "Accept" : d === "Corrected" ? "Correct" : d === "Rejected" ? "Reject" : "Defer"}</button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
