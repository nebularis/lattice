// SPDX-License-Identifier: MPL-2.0
// One control per field kind (rdf/vocabulary.ts). Each reads its values from the node and writes
// through `onChange`, which makes one undoable edit. Text commits on blur or Enter, so one word
// typed is one edit, not one per keystroke.

import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Plus, X } from "lucide-react";
import type { Baseline } from "../rdf/baseline";
import { KINDS, create } from "../rdf/editors";
import { Graph, XSD, compact, iri, literal, localName, type Term, typed } from "@lattice/authoring-domain";
import type { Field, Vocabulary } from "../rdf/vocabulary";
import { useDismiss } from "./kit";

export interface FieldProps {
  field: Field;
  graph: Graph;
  node: string;
  baseline: Baseline;
  vocab: Vocabulary;
  /** The baseline class the node is about, to offer its properties first. */
  context?: string;
  edit: (change: (g: Graph) => Graph) => void;
  /** Open a node in whichever configuration holds it. */
  open: (node: string) => void;
  /** The baseline and every configuration, where a reference may point. */
  world: Graph;
  /** The configuration the node belongs to, where a new referenced node is made. */
  part: string;
}

export function FieldControl(props: FieldProps) {
  const { field, graph, node } = props;
  const values = graph.objects(node, field.property);
  if (field.readOnly) {
    return (
      <div className="readonly-field">
        {values.length === 0 ? <div className="unset">Not set.</div> : values.map((v) => <div key={v.id} className="mono small">{compact(v.value)}</div>)}
        <div className="small muted" style={{ marginTop: 4 }}>{field.readOnly}</div>
      </div>
    );
  }
  const set = (objects: Term[]) => props.edit((g) => g.edit((e) => e.setAll(node, field.property, objects)));
  switch (field.kind) {
    case "text":
    case "number":
      return <TextValue {...props} value={values[0]?.value} onCommit={(v) => set(v === "" ? [] : [literalFor(field, v)])} />;
    case "iri":
      return field.single ? (
        <TextValue {...props} value={values[0]?.value} iri onCommit={(v) => set(v === "" ? [] : [iri(v)])} />
      ) : (
        <TextList values={values.map((v) => v.value)} placeholder="An IRI" onChange={(vs) => set(vs.map((v) => iri(v)))} />
      );
    case "boolean":
      return <BooleanValue value={values[0]?.value} onChange={(v) => set(v === undefined ? [] : [typed(String(v), XSD("boolean"))])} />;
    case "choice":
      return <Choice field={field.openToWorld ? withWorld(field, props) : field} selected={values.map((v) => v.value)} onChange={(vs) => set(vs.map((v) => iri(v)))} />;
    case "class":
      return (
        <TermPicker
          single={field.single}
          selected={values.map((v) => v.value)}
          options={[...props.baseline.classes.values()].map((c) => ({ iri: c.iri, label: c.label, group: "Classes" }))}
          placeholder="Pick a class of the baseline"
          onChange={(vs) => set(vs.map((v) => iri(v)))}
        />
      );
    case "property":
      return (
        <TermPicker
          single={field.single}
          selected={values.map((v) => v.value)}
          options={propertyOptions(props.baseline, props.context)}
          placeholder="Pick a property of the baseline"
          onChange={(vs) => set(vs.map((v) => iri(v)))}
        />
      );
    case "targetClass":
    case "targetProperty":
    case "targetIndividual": {
      // A mapping's target terms: the layers' own, then the baseline's.
      const which = field.kind === "targetClass" ? "class" : field.kind === "targetProperty" ? "property" : "individual";
      const own = which === "class" ? [...props.baseline.classes.values()] : which === "property" ? [...props.baseline.properties.values()] : [];
      const options = [
        ...props.vocab.targets(which).map((o) => ({ iri: o.iri, label: o.label, group: compact(o.iri).split(":")[0] })),
        ...own.map((t) => ({ iri: t.iri, label: t.label, group: "Baseline" })),
      ];
      return <TermPicker single={field.single} selected={values.map((v) => v.value)} options={options} placeholder={`Pick a ${which} it writes`} onChange={(vs) => set(vs.map((v) => iri(v)))} />;
    }
    case "propertyList": {
      const head = values[0];
      const list = head ? (graph.list(head) ?? []).map((t) => t.value) : [];
      return (
        <TermPicker
          single={false}
          ordered
          selected={list}
          options={propertyOptions(props.baseline, props.context)}
          placeholder="Add a property to the key"
          onChange={(vs) => props.edit((g) => g.edit((e) => e.setList(node, field.property, vs.map((v) => iri(v)))))}
        />
      );
    }
    case "textList": {
      const head = values[0];
      const list = head ? (graph.list(head) ?? []).map((t) => t.value) : [];
      return <TextList values={list} placeholder="A string" onChange={(vs) => props.edit((g) => g.edit((e) => e.setList(node, field.property, vs.map((v) => literal(v)))))} />;
    }
    case "reference":
      return <Reference {...props} selected={values.map((v) => v.value)} onChange={(vs) => set(vs.map((v) => iri(v)))} />;
  }
}

function literalFor(field: Field, value: string): Term {
  if (field.lang) return literal(value, field.lang);
  return field.datatype && field.datatype !== XSD("string") ? typed(value, field.datatype) : literal(value);
}

function propertyOptions(baseline: Baseline, context?: string): Option[] {
  const own = new Set(context ? baseline.propertiesOf(context).map((p) => p.iri) : []);
  const contextLabel = context ? (baseline.classes.get(context)?.label ?? compact(context)) : "";
  return [...baseline.properties.values()]
    .map((p) => ({ iri: p.iri, label: p.label, group: own.has(p.iri) ? `Of ${contextLabel}` : "Other properties" }))
    .sort((a, b) => (a.group === b.group ? a.label.localeCompare(b.label) : a.group.startsWith("Of") ? -1 : 1));
}

function TextValue(props: FieldProps & { value?: string; iri?: boolean; onCommit: (v: string) => void }) {
  const [draft, setDraft] = useState(props.value ?? "");
  useEffect(() => setDraft(props.value ?? ""), [props.value]);
  const number = props.field.kind === "number";
  const invalid = (number && draft !== "" && !/^[+-]?\d+(\.\d+)?$/.test(draft)) || (props.iri && draft !== "" && !/^[a-z][a-z0-9+.-]*:\S+$/i.test(draft));
  const commit = () => {
    if (draft.trim() !== (props.value ?? "") && !invalid) props.onCommit(draft.trim());
  };
  return (
    <input
      className={`input${invalid ? " invalid" : ""}${props.iri || number ? " mono" : ""}`}
      value={draft}
      inputMode={number ? "numeric" : undefined}
      placeholder={number ? "Not set, the default applies" : props.iri ? "An absolute IRI" : "Not set"}
      aria-label={props.field.label}
      aria-invalid={invalid || undefined}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") commit();
        if (e.key === "Escape") setDraft(props.value ?? "");
      }}
    />
  );
}

function BooleanValue({ value, onChange }: { value?: string; onChange: (v?: boolean) => void }) {
  const on = value === "true" || value === "1";
  return (
    <div className="row">
      <button type="button" role="switch" className="switch" aria-checked={value === undefined ? "mixed" : on} onClick={() => onChange(!on)} aria-label="Toggle" />
      <span className="small muted">{value === undefined ? "Not set, the default applies" : on ? "Yes" : "No"}</span>
      {value !== undefined && (
        <button className="btn ghost sm" onClick={() => onChange(undefined)}>
          Clear
        </button>
      )}
    </div>
  );
}

/** The field with the world's members of its range added to the layers' own, once each. */
function withWorld(field: Field, props: FieldProps): Field {
  const known = new Set(field.options.map((o) => o.iri));
  const extra = props.world
    .quads(null, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    .filter((q) => q.subject.termType === "NamedNode" && !known.has(q.subject.value) && !!field.range && props.vocab.ancestors(q.object.value).includes(field.range))
    .map((q) => q.subject.value)
    .filter((v, i, a) => a.indexOf(v) === i)
    .map((iri) => ({ iri, label: props.world.value(iri, "http://www.w3.org/2004/02/skos/core#prefLabel") ?? localName(iri), comment: iri }));
  return extra.length ? { ...field, options: [...field.options, ...extra] } : field;
}

function Choice({ field, selected, onChange }: { field: Field; selected: string[]; onChange: (v: string[]) => void }) {
  const chosen = field.options.filter((o) => selected.includes(o.iri));
  const toggle = (o: string) => {
    if (field.single) onChange(selected.includes(o) ? [] : [o]);
    else onChange(selected.includes(o) ? selected.filter((s) => s !== o) : [...selected, o]);
  };
  return (
    <div>
      {field.options.length <= 5 || !field.single ? (
        <div className="segmented" role={field.single ? "radiogroup" : "group"} aria-label={field.label}>
          {field.options.map((o) => (
            <button key={o.iri} type="button" aria-pressed={selected.includes(o.iri)} title={o.comment} onClick={() => toggle(o.iri)}>
              {o.label}
            </button>
          ))}
        </div>
      ) : (
        <select className="select" aria-label={field.label} value={selected[0] ?? ""} onChange={(e) => onChange(e.target.value ? [e.target.value] : [])}>
          <option value="">Not set, the default applies</option>
          {field.options.map((o) => (
            <option key={o.iri} value={o.iri}>
              {o.label}
            </option>
          ))}
        </select>
      )}
      {selected.filter((s) => !field.options.some((o) => o.iri === s)).map((s) => (
        <div key={s} className="field-error warn">
          {compact(s)} is not one of this property's values.
        </div>
      ))}
      {chosen.length === 1 && chosen[0].comment && <div className="option-desc">{chosen[0].comment}</div>}
      {chosen.length === 0 && field.single && <div className="unset" style={{ marginTop: 4 }}>Not set, the compiler's baseline default applies.</div>}
    </div>
  );
}

export interface Option {
  iri: string;
  label: string;
  group: string;
}

export function TermPicker(props: { single: boolean; ordered?: boolean; selected: string[]; options: Option[]; placeholder: string; onChange: (v: string[]) => void }) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [index, setIndex] = useState(0);
  const ref = useDismiss(open, () => setOpen(false));
  const byIri = useMemo(() => new Map(props.options.map((o) => [o.iri, o])), [props.options]);
  const q = query.toLowerCase();
  const results = props.options.filter((o) => !props.selected.includes(o.iri) && (!q || o.label.toLowerCase().includes(q) || o.iri.toLowerCase().includes(q))).slice(0, 60);
  const pick = (o: string) => {
    props.onChange(props.single ? [o] : [...props.selected, o]);
    setQuery("");
    setOpen(false);
  };
  const remove = (o: string) => props.onChange(props.selected.filter((s) => s !== o));
  const move = (i: number, d: number) => {
    const next = [...props.selected];
    [next[i], next[i + d]] = [next[i + d], next[i]];
    props.onChange(next);
  };
  const free = /^[a-z][a-z0-9+.-]*:\S+$/i.test(query) && !byIri.has(query);
  let lastGroup = "";
  return (
    <div className="picker" ref={ref}>
      {props.selected.length > 0 && (
        <div className="values" style={{ marginBottom: 6 }}>
          {props.selected.map((s, i) => (
            <span key={s} className={`chip ${byIri.has(s) ? "baseline" : "warn"}`} title={s}>
              {props.ordered && <span className="muted">{i + 1}.</span>}
              {byIri.get(s)?.label ?? compact(s)}
              {props.ordered && i > 0 && (
                <button aria-label="Move earlier" onClick={() => move(i, -1)}>
                  ←
                </button>
              )}
              <button aria-label={`Remove ${byIri.get(s)?.label ?? localName(s)}`} onClick={() => remove(s)}>
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
      )}
      {(!props.single || props.selected.length === 0 || open) && (
        <input
          className="input"
          placeholder={props.placeholder}
          value={query}
          role="combobox"
          aria-expanded={open}
          onFocus={() => setOpen(true)}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
            setIndex(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") setIndex(Math.min(index + 1, results.length - 1));
            else if (e.key === "ArrowUp") setIndex(Math.max(index - 1, 0));
            else if (e.key === "Enter" && results[index]) pick(results[index].iri);
            else if (e.key === "Enter" && free) pick(query);
            else if (e.key === "Escape") setOpen(false);
          }}
        />
      )}
      {props.single && props.selected.length > 0 && !open && (
        <button className="btn ghost sm" onClick={() => setOpen(true)}>
          Change
        </button>
      )}
      {open && (results.length > 0 || free) && (
        <div className="results" role="listbox">
          {results.map((o, i) => {
            const head = o.group !== lastGroup ? o.group : undefined;
            lastGroup = o.group;
            return (
              <div key={o.iri}>
                {head && <div className="small muted" style={{ padding: "6px 8px 2px", fontWeight: 600 }}>{head}</div>}
                <button role="option" aria-selected={i === index} onMouseDown={(e) => e.preventDefault()} onClick={() => pick(o.iri)}>
                  <span>{o.label}</span>
                  <span className="sub">{compact(o.iri)}</span>
                </button>
              </div>
            );
          })}
          {free && (
            <button role="option" aria-selected={false} onMouseDown={(e) => e.preventDefault()} onClick={() => pick(query)}>
              <span>Use {query}</span>
              <span className="sub">not in the baseline</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function TextList({ values, placeholder, onChange }: { values: string[]; placeholder: string; onChange: (v: string[]) => void }) {
  const [draft, setDraft] = useState("");
  const add = () => {
    if (draft.trim()) onChange([...values, draft.trim()]);
    setDraft("");
  };
  return (
    <div>
      {values.length > 0 && (
        <div className="values" style={{ marginBottom: 6 }}>
          {values.map((v, i) => (
            <span key={i} className="chip">
              {v}
              <button aria-label={`Remove ${v}`} onClick={() => onChange(values.filter((_, j) => j !== i))}>
                <X size={12} />
              </button>
            </span>
          ))}
        </div>
      )}
      <div className="row">
        <input className="input" placeholder={placeholder} value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === "Enter" && add()} />
        <button className="btn icon" aria-label="Add" onClick={add}>
          <Plus size={14} />
        </button>
      </div>
    </div>
  );
}

function Reference(props: FieldProps & { selected: string[]; onChange: (v: string[]) => void }) {
  const { field, vocab, baseline, world } = props;
  const range = field.range;
  const candidates = world
    .quads(null, "http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
    .filter((q) => q.subject.termType === "NamedNode" && q.subject.value !== props.node && (!range || vocab.ancestors(q.object.value).includes(range)))
    .map((q) => q.subject.value)
    .filter((v, i, a) => a.indexOf(v) === i);
  const creatable = KINDS.find((k) => range && k.part === props.part && k.creatable && vocab.ancestors(k.type).includes(range));
  if (!field.single) {
    return (
      <TermPicker
        single={false}
        selected={props.selected}
        options={candidates.map((c) => ({ iri: c, label: world.value(c, "http://www.w3.org/2004/02/skos/core#prefLabel") ?? localName(c), group: compact(world.types(c)[0] ?? "") }))}
        placeholder={`Add ${field.label.toLowerCase()}`}
        onChange={props.onChange}
      />
    );
  }
  const label = (n: string) => {
    const target = world.value(n, "https://www.nebularis.org/neuro-semantic/lattice/persistence#targetClass");
    const pref = world.value(n, "http://www.w3.org/2004/02/skos/core#prefLabel");
    return target ? `${localName(n)} (class ${baseline.classes.get(target)?.label ?? localName(target)})` : pref ? `${pref} (${localName(n)})` : localName(n);
  };
  return (
    <div className="row" style={{ flexWrap: "wrap" }}>
      <select
        className="select grow"
        aria-label={field.label}
        value={props.selected[0] ?? ""}
        onChange={(e) => {
          if (e.target.value === "__new" && creatable) {
            let made = "";
            props.edit((g) => {
              const c = create(g, creatable, `${creatable.title}`, baseline.namespace, props.context);
              made = c.iri;
              return c.graph.edit((ed) => ed.setAll(props.node, field.property, [iri(c.iri)]));
            });
            if (made) props.open(made);
          } else props.onChange(e.target.value ? [e.target.value] : []);
        }}
      >
        <option value="">Not set</option>
        {candidates.map((c) => (
          <option key={c} value={c}>
            {label(c)}
          </option>
        ))}
        {props.selected.filter((s) => !candidates.includes(s)).map((s) => (
          <option key={s} value={s}>
            {compact(s)} (declared nowhere)
          </option>
        ))}
        {creatable && <option value="__new">New {creatable.title.toLowerCase()}…</option>}
      </select>
      {props.selected[0] && world.has(props.selected[0]) && field.single && (
        <button className="btn sm" onClick={() => props.open(props.selected[0])}>
          Open <ArrowRight size={13} />
        </button>
      )}
    </div>
  );
}
