// SPDX-License-Identifier: MPL-2.0
// Mapping mode's view: the source concepts a MORK mapping scheme reads on the left, its mappings drawn as the tree their
// parent links make, each with the terms it writes and its latest review, and for the mapping picked its review and its
// editor, whose findings come from compiling the part with mork_rdf as it is edited. Stepping a sample through it comes later.

import { useMemo, useState } from "react";
import { Hammer, Network, Plus } from "lucide-react";
import { LABEL, MORK, PREFIXES, TYPE, compact, iri, literal, namespaceOf } from "@lattice/authoring-domain";
import { api } from "../api";
import { mint } from "../rdf/editors";
import { schemesOf, written, type MappingNode, type Scheme } from "../rdf/mapping";
import { Spinner, go } from "./kit";
import { NodeEditor } from "./ConfigView";
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

  if (!scheme) {
    return (
      <div className="empty">
        <Network size={28} color="var(--accent)" />
        <h3>No mapping scheme yet</h3>
        <p className="small">Import a file holding a MORK mapping scheme, such as a mapping pack, and its mappings are drawn here.</p>
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
          <div className="row" style={{ gap: 6 }}>
            <button className="btn sm" onClick={() => add("Datum")}><Plus size={13} /> Root datum</button>
            <button className="btn sm" disabled={busy} onClick={() => void compile()}>{busy ? <Spinner /> : <Hammer size={13} />} Compile</button>
          </div>
        </div>
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
          {picked && <MappingCard node={picked} schemes={schemes} prefixes={prefixes} open={open} add={add} />}
          {picked && <div style={{ margin: "0 -28px" }}><NodeEditor key={picked.iri} part="mapping" node={picked.iri} /></div>}
          <section className="card section" aria-label={`Mappings of ${scheme.label}`}>
            <header>
              <h3 className="grow">Mappings</h3>
            </header>
            <p className="small muted" style={{ margin: "8px 16px 0" }}>Indented under their parent. a writes a type, → a property, ← an inverse property, = an individual. The bar on the left is the latest review.</p>
            <div style={{ padding: "8px 16px", overflowX: "auto" }}>
              <Tree scheme={scheme} prefixes={prefixes} selected={selected} source={source} open={open} />
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function Tree({ scheme, prefixes, selected, source, open }: { scheme: Scheme; prefixes: Record<string, string>; selected?: string; source?: string; open: (n: string) => void }) {
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
        return (
          <g key={m.iri} role="treeitem" aria-level={m.depth + 1} aria-selected={on} tabIndex={0} onClick={() => open(m.iri)} onKeyDown={press(m.iri)} style={{ cursor: "pointer" }}>
            <title>{`${m.label} (${m.kind})${m.reads ? `\nreads ${m.reads}` : ""}`}</title>
            <rect x={x(m)} y={y(m)} width={BOX_W} height={BOX_H} rx={6}
              style={{ fill: lit ? "var(--accent-2)" : m.isTemplate ? "var(--surface-2)" : "var(--surface)", stroke: on ? "var(--accent)" : "var(--border-strong)", strokeDasharray: m.isTemplate ? "4 3" : undefined }}
              strokeWidth={on ? 2.5 : 1.2} />
            {m.review && <rect x={x(m) + 1} y={y(m) + 4} width={4} height={BOX_H - 8} rx={2} style={{ fill: DECISION[m.review.decision] ?? "var(--text-3)" }}><title>{m.review.decision}</title></rect>}
            <text x={x(m) + 10} y={y(m) + BOX_H / 2 + 4} style={{ fill: "var(--text)", fontWeight: m.kind === "Datum" ? 600 : 400 }}>
              {m.label.length > 30 ? m.label.slice(0, 29) + "…" : m.label}
            </text>
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
function MappingCard({ node, schemes, prefixes, open, add }: { node: MappingNode; schemes: Scheme[]; prefixes: Record<string, string>; open: (n: string) => void; add: (type: "Datum" | "DataMapping", parent?: string) => void }) {
  const all = schemes.flatMap((s) => s.mappings);
  const r = node.review;
  return (
    <section className="card section" aria-label={`Mapping ${node.label}`} style={{ marginBottom: 16 }}>
      <header style={{ flexWrap: "wrap" }}>
        <h3 className="grow">{node.label}</h3>
        <button className="btn sm" onClick={() => add("Datum", node.iri)}><Plus size={13} /> Child datum</button>
        <button className="btn sm" onClick={() => add("DataMapping", node.iri)}><Plus size={13} /> Child data mapping</button>
      </header>
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
    </section>
  );
}
