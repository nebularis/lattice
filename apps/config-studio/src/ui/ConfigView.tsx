// SPDX-License-Identifier: MPL-2.0
// A configuration's nodes, listed by kind, and the editor of the selected one. The editor's
// sections and fields come from the vocabulary (rdf/editors.ts, rdf/vocabulary.ts).

import { useEffect, useMemo, useState } from "react";
import { ArrowLeftRight, ArrowRight, BookOpen, ChevronDown, ChevronRight, Database, ListChecks, Plus, Ruler, Sparkles, Trash2, X } from "lucide-react";
import { KINDS, classOf, concerns, create, describe, kindOf, nameOf, sectionsFor, type Kind, type Special as SpecialKind } from "../rdf/editors";
import { DAL, SRF, compact, type Graph } from "@lattice/authoring-domain";
import { readPath, writePath, type Step } from "../rdf/path";
import type { Issue } from "../rdf/report";
import type { Part } from "../state";
import { FieldControl, TermPicker } from "./Fields";
import { ConceptsSection, ExpansionSection, LineSection, ProfileTestsSection, RangesSection, ResolutionSection, TemporalSection, TestsSection } from "./Specials";
import { Modal, SeverityIcon, useDismiss } from "./kit";
import { useStudio } from "./Workspace";

export function ConfigView({ part, selected, field }: { part: Part; selected?: string; field?: string }) {
  const studio = useStudio();
  const list = studio.items[part];
  const [filter, setFilter] = useState("");
  const [adding, setAdding] = useState<Kind>();
  const [menu, setMenu] = useState(false);
  const menuRef = useDismiss(menu, () => setMenu(false));
  const issues = studio.model.issues[part];
  const graph = studio.model.state.configs[part]!.current;
  const q = filter.toLowerCase();
  const shown = list.filter((i) => !q || i.name.toLowerCase().includes(q) || i.detail.toLowerCase().includes(q) || i.kind.title.toLowerCase().includes(q));
  let group = "";

  return (
    <div className="split">
      <div className="list">
        <div className="list-head">
          <div className="row" style={{ position: "relative" }} ref={menuRef}>
            {PART_INFO[part].icon(16)}
            <strong className="grow">{PART_INFO[part].title}</strong>
            <button className="btn sm primary" aria-haspopup="menu" aria-expanded={menu} onClick={() => setMenu(!menu)}>
              <Plus size={13} /> Add
            </button>
            {menu && (
              <div className="menu" role="menu" style={{ top: 32, right: 0 }}>
                {KINDS.filter((k) => k.part === part && k.creatable).map((k) => (
                  <button
                    key={k.type}
                    role="menuitem"
                    onClick={() => {
                      setMenu(false);
                      setAdding(k);
                    }}
                  >
                    <span>{k.title}</span>
                    <span className="hint">{compact(k.type)}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
          <input className="input" placeholder="Filter" value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter nodes" />
        </div>
        {shown.length === 0 && (
          <div className="empty small">
            {list.length === 0 ? `No ${part} configuration yet. Add a node, or start from a class on the Overview.` : "Nothing matches."}
          </div>
        )}
        {shown.map((item) => {
          const head = item.kind.plural !== group ? item.kind.plural : undefined;
          group = item.kind.plural;
          const mine = issues.filter((i) => concerns(graph, item.iri, i));
          const worst = mine.find((i) => i.severity === "Violation") ?? mine[0];
          return (
            <div key={item.iri}>
              {head && <h4>{head}</h4>}
              <div className="list-item" aria-selected={item.iri === selected} onClick={() => studio.open(part, item.iri)}>
                <div className="grow" style={{ minWidth: 0 }}>
                  <div className="name ellipsis">{item.name}</div>
                  <div className="detail ellipsis">{item.detail}</div>
                </div>
                {worst && <SeverityIcon severity={worst.severity} size={14} />}
              </div>
            </div>
          );
        })}
      </div>
      <div className="detail-pane">
        {selected && graph.has(selected) ? (
          <NodeEditor key={selected} part={part} node={selected} focusField={field} />
        ) : (
          <div className="empty">
            {PART_INFO[part].icon(28)}
            <h3>{selected ? "This node is not in the configuration" : "Pick a node to edit it"}</h3>
            <p className="small">{PART_INFO[part].empty}</p>
          </div>
        )}
      </div>
      {adding && <AddNode part={part} kind={adding} onClose={() => setAdding(undefined)} />}
    </div>
  );
}

function AddNode({ part, kind, onClose }: { part: Part; kind: Kind; onClose: () => void }) {
  const studio = useStudio();
  const [name, setName] = useState("");
  const [forClass, setForClass] = useState<string[]>([]);
  const wantsClass = (part === "persistence" || part === "surface") && kind.type !== DAL("ClaimScheme") && kind.type !== DAL("DigestScheme") && kind.type !== SRF("SurfaceProfile") && !kind.type.endsWith("Population") && kind.type !== DAL("NamespaceScope") && kind.type !== DAL("GraphPatternScope");
  const submit = () => {
    const cls = forClass[0];
    const label = name.trim() || `${cls ? studio.baseline.classes.get(cls)?.label + " " : ""}${kind.title}`;
    let made = "";
    studio.model.edit(part, (g) => {
      const c = create(g, kind, label, studio.baseline.namespace, cls);
      made = c.iri;
      return c.graph;
    });
    onClose();
    studio.open(part, made);
  };
  return (
    <Modal
      title={`New ${kind.title.toLowerCase()}`}
      subtitle={describe(studio.vocab, kind.type)}
      onClose={onClose}
      footer={
        <>
          <button className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" onClick={submit}>
            Create
          </button>
        </>
      }
    >
      <label className="field-label" htmlFor="node-name">
        Name
      </label>
      <input id="node-name" className="input" autoFocus value={name} onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && submit()} placeholder={kind.title} />
      <p className="small muted">
        The node's IRI is minted from the name in the baseline's namespace, <span className="mono">{studio.baseline.namespace}</span>.
      </p>
      {wantsClass && (
        <>
          <div className="field-label" style={{ marginTop: 14 }}>
            For class
          </div>
          <TermPicker
            single
            selected={forClass}
            options={[...studio.baseline.classes.values()].map((c) => ({ iri: c.iri, label: c.label, group: "Classes" }))}
            placeholder="Optional: the baseline class it is for"
            onChange={setForClass}
          />
          <p className="small muted">{part === "persistence" ? "A class scope for it is reused or made, and the new node applies to it." : "The class becomes the contract's carrier."}</p>
        </>
      )}
    </Modal>
  );
}

function NodeEditor({ part, node, focusField }: { part: Part; node: string; focusField?: string }) {
  const studio = useStudio();
  const { vocab, baseline, model } = studio;
  const graph = model.state.configs[part]!.current;
  const kind = kindOf(graph, node, part);
  const sections = useMemo(() => (kind ? sectionsFor(kind, vocab) : []), [kind?.type, vocab]); // eslint-disable-line react-hooks/exhaustive-deps
  const issues = model.issues[part].filter((i) => concerns(graph, node, i));
  const placed = new Set(sections.flatMap((s) => s.fields.map((f) => f.property)));
  const loose = issues.filter((i) => !i.path || !placed.has(i.path));
  const edit = (change: (g: Graph) => Graph) => model.edit(part, change);
  const context = graph.value(node, SRF("carrier")) ?? classOf(graph, node);

  useEffect(() => {
    if (!focusField) return;
    const el = document.getElementById(fieldId(focusField));
    el?.scrollIntoView({ block: "center", behavior: "smooth" });
    el?.classList.add("flash");
    const t = setTimeout(() => el?.classList.remove("flash"), 1500);
    return () => clearTimeout(t);
  }, [focusField, node]);

  if (!kind) return null;
  const remove = () => {
    if (!window.confirm(`Delete ${nameOf(graph, node)}? References to it are removed too. You can undo this.`)) return;
    model.edit(part, (g) => g.edit((e) => e.remove(node)));
    studio.open(part);
  };

  return (
    <div className="editor">
      <div className="editor-head">
        <div className="grow">
          <span className={`chip ${PART_INFO[part].tone}`}>{kind.title}</span>
          <h2 style={{ marginTop: 8 }}>{nameOf(graph, node)}</h2>
          <div className="iri">{node}</div>
          {describe(vocab, kind.type) && <p className="type-desc">{describe(vocab, kind.type)}</p>}
        </div>
        <button className="btn danger sm" onClick={remove}>
          <Trash2 size={13} /> Delete
        </button>
      </div>
      {loose.length > 0 && (
        <div className="card" style={{ padding: "8px 14px", marginBottom: 16 }}>
          {loose.map((i, n) => (
            <IssueLine key={n} issue={i} />
          ))}
        </div>
      )}
      {sections.map((s) => (
        <SectionCard key={s.title} title={s.title} set={s.fields.filter((f) => graph.objects(node, f.property).length > 0).length} total={s.special ? undefined : s.fields.length} startOpen={s.fields.some((f) => graph.objects(node, f.property).length > 0) || !!s.special || sections.indexOf(s) < 3 || s.fields.some((f) => f.property === focusField)}>
          {s.special ? (
            <Special kind={s.special} part={part} node={node} />
          ) : (
            <div className="fields">
              {s.fields.map((f) => {
                const errors = issues.filter((i) => i.path === f.property);
                return (
                  <div className="field" key={f.property} id={fieldId(f.property)}>
                    <div className="label">
                      <div className="name">
                        {f.label[0].toUpperCase() + f.label.slice(1)}
                        {!f.single && <span className="chip" style={{ height: 18 }}>many</span>}
                      </div>
                      <div className="prop">{compact(f.property)}</div>
                    </div>
                    <div>
                      <FieldControl field={f} graph={graph} node={node} baseline={baseline} vocab={vocab} context={context} edit={edit} part={part} world={studio.world} open={(n) => studio.open(studio.partOf(n) ?? part, n)} />
                    </div>
                    {errors.length > 0 && (
                      <div className="errors">
                        {errors.map((e, n) => (
                          <div key={n} className={`field-error${e.severity === "Violation" ? "" : " warn"}`}>
                            <SeverityIcon severity={e.severity} size={13} /> {e.message}
                          </div>
                        ))}
                      </div>
                    )}
                    {f.comment && <div className="help">{f.comment}</div>}
                  </div>
                );
              })}
              {s.fields.length === 0 && <p className="muted small">The vocabulary declares no properties here.</p>}
            </div>
          )}
        </SectionCard>
      ))}
    </div>
  );
}

function Special({ kind, part, node }: { kind: SpecialKind; part: Part; node: string }) {
  switch (kind) {
    case "path":
      return <PathBuilder part={part} node={node} />;
    case "concepts":
      return <ConceptsSection node={node} />;
    case "temporal":
      return <TemporalSection part={part} node={node} />;
    case "resolution":
      return <ResolutionSection node={node} />;
    case "expansion":
      return <ExpansionSection node={node} />;
    case "tests":
      return <TestsSection node={node} />;
    case "ranges":
      return <RangesSection part={part} node={node} />;
    case "line":
      return <LineSection node={node} />;
    case "profileTests":
      return <ProfileTestsSection />;
  }
}

const PART_INFO: Record<Part, { title: string; tone: string; icon: (size: number) => React.ReactNode; empty: string }> = {
  vocabulary: {
    title: "Vocabulary",
    tone: "baseline",
    icon: (n) => <BookOpen size={n} color="var(--baseline-c)" />,
    empty: "A concept scheme holds concepts in a hierarchy. A scheme contract says which scheme a property's values come from, and its bindings choose an edition by scope and time.",
  },
  quantification: {
    title: "Quantification",
    tone: "accent",
    icon: (n) => <Ruler size={n} color="var(--accent)" />,
    empty: "A value space declares an order, a density and units. A range set is a set of ranges on one space, each between two bounds.",
  },
  eligibility: {
    title: "Eligibility",
    tone: "ok",
    icon: (n) => <ListChecks size={n} color="var(--ok)" />,
    empty: "A condition admits candidates by concept or by range. Add questions to it as tests, and the compiled query decides each as you edit.",
  },
  persistence: {
    title: "Persistence",
    tone: "persist",
    icon: (n) => <Database size={n} color="var(--persist)" />,
    empty: "A data access profile declares how a class is stored: its aggregate boundary, concurrency, ordering and more.",
  },
  surface: {
    title: "Surface",
    tone: "surface",
    icon: (n) => <Sparkles size={n} color="var(--surface-c)" />,
    empty: "A promotion restates a value reached by a read path. An index makes carriers retrievable by a value.",
  },
};

export function fieldId(property: string): string {
  return "field-" + property.replace(/[^a-zA-Z0-9]+/g, "-");
}

function SectionCard(props: { title: string; set: number; total?: number; startOpen: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(props.startOpen);
  return (
    <section className="card section" aria-label={props.title}>
      <header onClick={() => setOpen(!open)} role="button" aria-expanded={open}>
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        <h3 className="grow">{props.title}</h3>
        {props.total !== undefined && (
          <span className="set">
            {props.set} of {props.total} set
          </span>
        )}
      </header>
      {open && props.children}
    </section>
  );
}

function IssueLine({ issue }: { issue: Issue }) {
  return (
    <div className="row small" style={{ padding: "4px 0", alignItems: "flex-start" }}>
      <SeverityIcon severity={issue.severity} size={14} />
      <span className="grow">
        {issue.message}
        {issue.path && <span className="muted"> ({compact(issue.path)})</span>}
      </span>
    </div>
  );
}

/** The read path from the carrier, one hop at a time. Each hop offers the properties whose domain
 * is the class reached so far, or any property. */
function PathBuilder({ part, node }: { part: Part; node: string }) {
  const studio = useStudio();
  const { baseline, model } = studio;
  const graph = model.state.configs[part]!.current;
  const steps = readPath(graph, node);
  const carrier = graph.value(node, SRF("carrier"));
  const [anyProperty, setAnyProperty] = useState(false);
  const write = (next: Step[]) => model.edit(part, (g) => writePath(g, node, next));

  // The class reached after each step, where the baseline's domains and ranges say.
  const reached: (string | undefined)[] = [carrier];
  for (const s of steps) {
    const p = baseline.properties.get(s.property);
    reached.push(s.inverse ? p?.domains[0] : p?.ranges[0]);
  }
  const last = reached[reached.length - 1];
  const label = (c?: string) => (c ? (baseline.classes.get(c)?.label ?? compact(c)) : "value");
  const options = [...baseline.properties.values()]
    .filter((p) => anyProperty || !last || p.domains.length === 0 || p.domains.some((d) => baseline.ancestors(last).includes(d)))
    .map((p) => ({ iri: p.iri, label: p.label, group: anyProperty || !last ? "Properties" : `Of ${label(last)}` }));

  return (
    <div>
      <div className="path" aria-label="Read path">
        <span className="node">{carrier ? label(carrier) : "Pick a carrier first"}</span>
        {steps.map((s, i) => (
          <span key={i} className="row" style={{ gap: 6 }}>
            <span className="edge">
              <span className="arrow">{s.inverse ? "←" : "→"}</span>
              {baseline.properties.get(s.property)?.label ?? compact(s.property)}
              <button
                className="btn ghost icon sm"
                title={s.inverse ? "Traverse forward" : "Traverse inversely"}
                aria-label="Reverse direction"
                onClick={() => write(steps.map((x, j) => (j === i ? { ...x, inverse: !x.inverse } : x)))}
              >
                <ArrowLeftRight size={12} />
              </button>
              {i === steps.length - 1 && (
                <button className="btn ghost icon sm" aria-label="Remove the last step" onClick={() => write(steps.slice(0, -1))}>
                  <X size={12} />
                </button>
              )}
            </span>
            <span className={`node${reached[i + 1] ? "" : " value"}`}>{label(reached[i + 1])}</span>
          </span>
        ))}
        <ArrowRight size={14} className="muted" />
      </div>
      <div style={{ padding: "0 16px 16px" }}>
        <TermPicker single={false} selected={[]} options={options} placeholder={steps.length ? "Add a hop" : "Pick the first property to read"} onChange={(vs) => write([...steps, { property: vs[0], inverse: false }])} />
        <label className="row small muted" style={{ marginTop: 8 }}>
          <input type="checkbox" checked={anyProperty} onChange={(e) => setAnyProperty(e.target.checked)} /> Offer every property, not only those whose domain is {label(last)}
        </label>
        <p className="small muted">
          {steps.length === 1 && !steps[0].inverse ? "One forward hop is written as srf:readProperty." : steps.length ? `${steps.length} hops are written as srf:PathStep nodes.` : "No read path yet."}
        </p>
      </div>
    </div>
  );
}
