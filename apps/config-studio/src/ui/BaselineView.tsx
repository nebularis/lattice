// SPDX-License-Identifier: MPL-2.0
// The baseline: its class tree and schemes, a class's properties and what configures it, and
// replacing the baseline with a new revision.

import { useMemo, useState } from "react";
import { ChevronRight, Download, Network, Plus, RefreshCw, Shapes, Upload } from "lucide-react";
import { Baseline, type BaselineClass } from "../rdf/baseline";
import { KINDS, checkReferences } from "../rdf/editors";
import { DAL, Graph, SRF, compact } from "@lattice/authoring-domain";
import { split } from "../rdf/split";
import { Modal, Spinner, download, go, readFiles } from "./kit";
import { addFor, declaredFor } from "./Overview";
import { useStudio } from "./Workspace";

const kind = (type: string) => KINDS.find((k) => k.type === type)!;

export function BaselineView({ selected }: { selected?: string }) {
  const studio = useStudio();
  const { baseline, id } = studio;
  const [filter, setFilter] = useState("");
  const [replacing, setReplacing] = useState(false);
  const roots = baseline.roots().sort((a, b) => a.label.localeCompare(b.label));
  const q = filter.toLowerCase();
  const matches = (c: BaselineClass): boolean => !q || c.label.toLowerCase().includes(q) || c.children.some((x) => matches(baseline.classes.get(x)!));
  const scheme = baseline.schemes.find((s) => s.iri === selected);
  const current = selected && baseline.classes.get(selected);

  return (
    <div className="split">
      <div className="list">
        <div className="list-head">
          <div className="row">
            <strong className="grow">Baseline</strong>
            <button className="btn ghost icon sm" aria-label="Download baseline" title="Download baseline" onClick={() => download("baseline.ttl", baseline.graph.toTurtle())}>
              <Download size={14} />
            </button>
            <button className="btn sm" onClick={() => setReplacing(true)}>
              <RefreshCw size={13} /> Replace
            </button>
          </div>
          <input className="input" placeholder="Filter classes" value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter classes" />
        </div>
        <h4>Classes</h4>
        {roots.filter(matches).map((c) => (
          <ClassNode key={c.iri} c={c} depth={0} selected={selected} matches={matches} />
        ))}
        {baseline.schemes.length > 0 && <h4>Concept schemes</h4>}
        {baseline.schemes.map((s) => (
          <div key={s.iri} className="list-item" aria-selected={s.iri === selected} onClick={() => go("w", id, "baseline", s.iri)}>
            <Network size={15} color="var(--baseline-c)" />
            <div className="grow">
              <div className="name">{s.label}</div>
              <div className="detail">{s.concepts.length} concepts</div>
            </div>
          </div>
        ))}
      </div>
      <div className="detail-pane">
        {current && <ClassDetail c={current} />}
        {scheme && (
          <div className="editor">
            <div className="editor-head">
              <div className="grow">
                <span className="chip baseline">Concept scheme</span>
                <h2 style={{ marginTop: 8 }}>{scheme.label}</h2>
                <div className="iri">{scheme.iri}</div>
              </div>
            </div>
            <div className="card" style={{ padding: 12 }}>
              <ConceptTree concepts={scheme.concepts} />
            </div>
          </div>
        )}
        {!current && !scheme && (
          <div className="empty">
            <Shapes size={28} />
            <h3>
              {baseline.classes.size} classes, {baseline.properties.size} properties, {baseline.schemes.length} concept schemes
            </h3>
            <p>Pick a class to see its properties and what configures it.</p>
          </div>
        )}
      </div>
      {replacing && <ReplaceBaseline onClose={() => setReplacing(false)} />}
    </div>
  );
}

function ClassNode({ c, depth, selected, matches }: { c: BaselineClass; depth: number; selected?: string; matches: (c: BaselineClass) => boolean }) {
  const { baseline, id } = useStudio();
  const children = c.children.map((x) => baseline.classes.get(x)!).filter(matches);
  return (
    <>
      <div className="list-item" aria-selected={c.iri === selected} onClick={() => go("w", id, "baseline", c.iri)} style={{ paddingLeft: 14 + depth * 16 }}>
        {children.length ? <ChevronRight size={13} className="muted" /> : <span style={{ width: 13 }} />}
        <span className="grow name ellipsis">{c.label}</span>
        {c.instances > 0 && <span className="small muted">{c.instances}</span>}
      </div>
      {children.map((x) => (
        <ClassNode key={x.iri} c={x} depth={depth + 1} selected={selected} matches={matches} />
      ))}
    </>
  );
}

function ClassDetail({ c }: { c: BaselineClass }) {
  const studio = useStudio();
  const { baseline, model } = studio;
  const persistence = model.state.configs.persistence!.current;
  const surface = model.state.configs.surface!.current;
  const properties = baseline.propertiesOf(c.iri);
  const declared = declaredFor(persistence, c.iri, baseline.ancestors(c.iri));
  const carried = [...surface.ofType(SRF("PromotionContract")), ...surface.ofType(SRF("IndexContract"))].filter((k) => surface.value(k, SRF("carrier")) === c.iri);
  const keys = persistence.ofType(DAL("UniquenessConstraint")).filter((u) => declared.includes(u.value));
  return (
    <div className="editor">
      <div className="editor-head">
        <div className="grow">
          <span className="chip baseline">Class</span>
          <h2 style={{ marginTop: 8 }}>{c.label}</h2>
          <div className="iri">{c.iri}</div>
          {c.comment && <p className="type-desc">{c.comment}</p>}
          {c.parents.length > 0 && (
            <p className="small muted">
              Subclass of {c.parents.map((p) => baseline.classes.get(p)?.label ?? compact(p)).join(", ")}
            </p>
          )}
        </div>
      </div>

      <div className="card section">
        <header>
          <h3 className="grow">Configured by</h3>
          <button className="btn sm" onClick={() => addFor(studio, "persistence", kind(DAL("DataAccessProfile")), c.iri)}>
            <Plus size={13} /> Profile
          </button>
          <button className="btn sm" onClick={() => addFor(studio, "persistence", kind(DAL("UniquenessConstraint")), c.iri)}>
            <Plus size={13} /> Key
          </button>
          <button className="btn sm" onClick={() => addFor(studio, "surface", kind(SRF("PromotionContract")), c.iri)}>
            <Plus size={13} /> Promotion
          </button>
          <button className="btn sm" onClick={() => addFor(studio, "surface", kind(SRF("IndexContract")), c.iri)}>
            <Plus size={13} /> Index
          </button>
        </header>
        <div className="fields">
          {declared.length + carried.length === 0 && <p className="muted small">Nothing yet. The compiler's baseline defaults apply to its persistence.</p>}
          <div className="values">
            {declared.map((n) => (
              <button key={n} className="chip persist" style={{ cursor: "pointer" }} onClick={() => studio.open("persistence", n)}>
                {studio.items.persistence.find((i) => i.iri === n)?.name ?? compact(n)}
              </button>
            ))}
            {carried.map((n) => (
              <button key={n.value} className="chip surface" style={{ cursor: "pointer" }} onClick={() => studio.open("surface", n.value)}>
                {studio.items.surface.find((i) => i.iri === n.value)?.name ?? compact(n.value)}
              </button>
            ))}
          </div>
          {keys.length > 0 && <p className="small muted">{keys.length} uniqueness key(s) declared.</p>}
        </div>
      </div>

      <div className="card" style={{ overflow: "hidden" }}>
        <table className="grid">
          <thead>
            <tr>
              <th>Property</th>
              <th>Range</th>
              <th>Declared on</th>
            </tr>
          </thead>
          <tbody>
            {properties.length === 0 && (
              <tr>
                <td colSpan={3} className="muted">
                  No property declares this class, or an ancestor, as its domain.
                </td>
              </tr>
            )}
            {properties.map((p) => (
              <tr key={p.iri}>
                <td>
                  <div style={{ fontWeight: 600 }}>{p.label}</div>
                  <div className="small muted mono">{compact(p.iri, { ...baseline.graph.prefixes })}</div>
                  {p.comment && <div className="small muted">{p.comment}</div>}
                </td>
                <td className="small">
                  {p.ranges.map((r) => baseline.classes.get(r)?.label ?? compact(r)).join(", ") || <span className="muted">any</span>}
                  {p.datatype && <span className="chip" style={{ marginLeft: 6 }}>value</span>}
                </td>
                <td className="small muted">{p.domains.map((d) => baseline.classes.get(d)?.label ?? compact(d)).join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ConceptTree({ concepts, parent, depth = 0 }: { concepts: { iri: string; label: string; broader: string[] }[]; parent?: string; depth?: number }) {
  const inScheme = new Set(concepts.map((c) => c.iri));
  const level = concepts.filter((c) => (parent ? c.broader.includes(parent) : !c.broader.some((b) => inScheme.has(b))));
  return (
    <>
      {level.map((c) => (
        <div key={c.iri}>
          <div className="row" style={{ paddingLeft: depth * 18, height: 28 }}>
            <span className="dot" style={{ background: "var(--baseline-c)" }} />
            {c.label}
            <span className="small muted mono">{compact(c.iri)}</span>
          </div>
          <ConceptTree concepts={concepts} parent={c.iri} depth={depth + 1} />
        </div>
      ))}
    </>
  );
}

function ReplaceBaseline({ onClose }: { onClose: () => void }) {
  const { baseline, model, vocab } = useStudio();
  const [next, setNext] = useState<Graph>();
  const [error, setError] = useState<string>();
  const [busy, setBusy] = useState(false);
  const summary = useMemo(() => {
    if (!next) return undefined;
    const b = new Baseline(next);
    const diff = (a: Iterable<string>, c: Iterable<string>) => [...a].filter((x) => !new Set(c).has(x));
    const dangling = (["persistence", "surface"] as const).flatMap((p) => checkReferences(model.state.configs[p]!.current, b, vocab).filter((i) => i.severity === "Warning"));
    return {
      addedClasses: diff(b.classes.keys(), baseline.classes.keys()),
      removedClasses: diff(baseline.classes.keys(), b.classes.keys()),
      addedProperties: diff(b.properties.keys(), baseline.properties.keys()),
      removedProperties: diff(baseline.properties.keys(), b.properties.keys()),
      dangling,
    };
  }, [next, baseline, model.state.configs, vocab]);

  const choose = async (files: FileList | null) => {
    if (!files?.length) return;
    try {
      let g = Graph.empty();
      for (const f of await readFiles(files)) g = g.merge(Graph.parse(f.text));
      setNext(split(g).baseline);
      setError(undefined);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <Modal
      title="Replace the baseline"
      subtitle="The new baseline becomes the next revision. Earlier revisions are kept, and compile jobs that read them keep pointing at them."
      onClose={onClose}
      footer={
        <>
          <button className="btn" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn primary"
            disabled={!next || busy}
            onClick={async () => {
              setBusy(true);
              try {
                await model.replaceBaseline(next!);
                onClose();
              } catch (e) {
                setError(e instanceof Error ? e.message : String(e));
                setBusy(false);
              }
            }}
          >
            {busy && <Spinner />} Replace
          </button>
        </>
      }
    >
      <label className="dropzone" style={{ display: "block" }}>
        <Upload size={20} />
        <div>Choose the new baseline's .ttl files. Any dal: or srf: subjects in them are ignored here.</div>
        <input type="file" accept=".ttl,text/turtle" multiple hidden onChange={(e) => void choose(e.target.files)} />
      </label>
      {error && <p style={{ color: "var(--bad)" }}>{error}</p>}
      {summary && (
        <div style={{ marginTop: 14, display: "grid", gap: 8 }}>
          <div className="row">
            <span className="chip ok">+{summary.addedClasses.length} classes</span>
            <span className="chip bad">−{summary.removedClasses.length} classes</span>
            <span className="chip ok">+{summary.addedProperties.length} properties</span>
            <span className="chip bad">−{summary.removedProperties.length} properties</span>
          </div>
          {summary.dangling.length > 0 ? (
            <div className="option-desc" style={{ background: "var(--warn-2)", color: "var(--warn)" }}>
              {summary.dangling.length} configuration reference(s) would name a term the new baseline does not declare, for example: {summary.dangling[0].message}
            </div>
          ) : (
            <p className="small muted">Every term the configuration refers to is still declared.</p>
          )}
        </div>
      )}
    </Modal>
  );
}
