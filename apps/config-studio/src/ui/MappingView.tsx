// SPDX-License-Identifier: MPL-2.0
// Mapping mode's view, read only: the source concepts a MORK mapping scheme reads on the left, its mappings drawn as the
// tree their parent links make, each with the terms it writes, and the findings of the mapping part's validation for the
// mapping picked. Editing, compiling and stepping a sample through it come later.

import { useMemo, useState } from "react";
import { Network } from "lucide-react";
import { PREFIXES, compact } from "@lattice/authoring-domain";
import { schemesOf, written, type MappingNode, type Scheme } from "../rdf/mapping";
import { SeverityIcon, go } from "./kit";
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
  const scheme = schemes.find((s) => s.iri === schemeIri) ?? schemes.find((s) => s.mappings.some((m) => m.iri === selected)) ?? schemes[0];
  const open = (node: string) => go("w", studio.id, "mapping", node);
  const picked = scheme?.mappings.find((m) => m.iri === selected);

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
            <select value={scheme.iri} onChange={(e) => setSchemeIri(e.target.value)} aria-label="Mapping scheme">
              {schemes.map((s) => (
                <option key={s.iri} value={s.iri}>{s.label}</option>
              ))}
            </select>
          )}
          <div className="small muted">{scheme.label}</div>
        </div>
        <h4>Source concepts</h4>
        {scheme.sources.length === 0 && <div className="empty small">The scheme names no source concept.</div>}
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
          {picked && <MappingCard node={picked} scheme={scheme} prefixes={prefixes} open={open} />}
          <section className="card section" aria-label={`Mappings of ${scheme.label}`}>
            <header>
              <h3 className="grow">Mappings</h3>
              <span className="small muted">Indented under their parent. a writes a type, → a property, ← an inverse property, = an individual.</span>
            </header>
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
            <text x={x(m) + 8} y={y(m) + BOX_H / 2 + 4} style={{ fill: "var(--text)", fontWeight: m.kind === "Datum" ? 600 : 400 }}>
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

function MappingCard({ node, scheme, prefixes, open }: { node: MappingNode; scheme: Scheme; prefixes: Record<string, string>; open: (n: string) => void }) {
  const { model } = useStudio();
  const issues = model.issues.mapping.filter((i) => i.focus === node.iri);
  const label = (iri: string) => scheme.mappings.find((m) => m.iri === iri)?.label ?? compact(iri, prefixes);
  const link = (iri?: string) => (iri && scheme.mappings.some((m) => m.iri === iri) ? <button className="link" onClick={() => open(iri)}>{label(iri)}</button> : iri ? <span className="mono">{compact(iri, prefixes)}</span> : <span className="muted">none</span>);
  const rows: [string, React.ReactNode][] = [
    ["Kind", node.kind],
    ["Parent", link(node.parent)],
    ["Template", link(node.template)],
    ["Maps for", link(node.source)],
    ["Reads", node.reads ? <span className="mono">{node.reads}</span> : <span className="muted">its parent's subject</span>],
    ["Guard", link(node.guard)],
    ["Writes", written(node, prefixes).map((w) => `${w.box} ${w.term}`).join(", ") || <span className="muted">nothing</span>],
  ];
  return (
    <section className="card section" aria-label={`Mapping ${node.label}`} style={{ marginBottom: 16 }}>
      <header>
        <h3 className="grow">{node.label}</h3>
        <span className="mono small muted">{compact(node.iri, prefixes)}</span>
      </header>
      <div className="fields">
        {rows.map(([k, v]) => (
          <div className="field" key={k}>
            <div className="label"><div className="name">{k}</div></div>
            <div>{v}</div>
          </div>
        ))}
        <div className="field">
          <div className="label"><div className="name">Findings</div></div>
          <div>
            {issues.length === 0 ? <span className="muted small">None</span> : issues.map((i, n) => (
              <div key={n} className="row small" style={{ gap: 6 }}><SeverityIcon severity={i.severity} /> {i.message}</div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
