// SPDX-License-Identifier: MPL-2.0
// Builder mode (ADR-A138): the library's forms as outlines, edited with the forms the studio derives
// from the shapes, and assemblies of them, which an assemble job turns into assembled wording.
// Both views share the workspace's state, inspector and problems drawer.

import { useCallback, useMemo, useRef, useState } from "react";
import { Download, Play, Plus, Trash2 } from "lucide-react";
import { CST, Graph, LABEL, compact, localName } from "@lattice/authoring-domain";
import { api, awaitJob } from "../api";
import {
  addAssembly,
  assembliesOf,
  choicesMade,
  choicesOf,
  conceptsFor,
  datatypeOf,
  formsOf,
  nameOfAssembly,
  outline,
  removeAssembly,
  setForm,
  setLabel,
  settableOf,
  settingsMade,
  toggleChoice,
  writeSetting,
  type FormOutline,
  type OutlineNode,
  type VariableInfo,
} from "../rdf/builder";
import { readDocument, type AssembledDocument, type DocClause } from "../rdf/document";
import type { Issue, Job } from "../rdf/report";
import { PARTS, type WorkspaceModel } from "../state";
import { NodeEditor, PART_INFO } from "./ConfigView";
import { TermPicker } from "./Fields";
import { Code, Conforms, SeverityIcon, Spinner, download } from "./kit";
import { useStudio } from "./Workspace";

// ---- Running an assemble job -------------------------------------------------------

export interface Run {
  state: "running" | "done" | "failed";
  job?: Job;
  message?: string;
  /** The assembly and library graphs the run was for, to tell when they have been edited since. */
  inputs: Graph[];
}

/** Submits the assembly configuration with the library and the configurations a condition reads beside it. */
export function useAssembler(id: string, model: WorkspaceModel) {
  const [run, setRun] = useState<Run>();
  const latest = useRef(model);
  latest.current = model;
  const assemble = useCallback(async () => {
    const configs = latest.current.state.configs;
    let body = Graph.empty();
    for (const p of PARTS) body = body.merge(configs[p]?.current ?? Graph.empty());
    const inputs = [configs.assembly!.current, configs.library!.current];
    setRun({ state: "running", inputs });
    try {
      const jobId = await api.submit(id, "assemble", "assembly", body);
      // Kept, unlike a validation's, since the job holds the records it assembled until the writer's sweep (CS-B44).
      const job = await awaitJob(jobId);
      setRun(job.status === "Failed" ? { state: "failed", message: job.failure ?? "The assemble job failed.", inputs } : { state: "done", job, inputs });
    } catch (error) {
      setRun({ state: "failed", message: error instanceof Error ? error.message : String(error), inputs });
    }
  }, [id]);
  return { run, assemble };
}

export type Assembler = ReturnType<typeof useAssembler>;

// ---- The library --------------------------------------------------------------------

export function LibraryView({ selected, field }: { selected?: string; field?: string }) {
  const studio = useStudio();
  const library = studio.model.state.configs.library!.current;
  // A condition is eligibility's, so the outline reads the configurations as edited.
  const forms = useMemo(() => formsOf(studio.world).map((f) => outline(studio.world, f)), [studio.world]);
  return (
    <div className="split" style={{ gridTemplateColumns: "minmax(380px, 460px) 1fr" }}>
      <div className="list" role="tree" aria-label="Library">
        <div className="list-head">
          <div className="row">
            {PART_INFO.library.icon(16)}
            <strong className="grow">Library</strong>
            <span className="small muted">{forms.length} {forms.length === 1 ? "form" : "forms"}</span>
          </div>
        </div>
        {forms.length === 0 && <div className="empty small">No form in the library yet. Import a document or a sample that holds a Wording form.</div>}
        {forms.map((form) => (
          <FormOutlineView key={form.iri} form={form} selected={selected} />
        ))}
      </div>
      <div className="detail-pane">
        {selected && library.has(selected) ? (
          <NodeEditor key={selected} part="library" node={selected} focusField={field} />
        ) : (
          <div className="empty">
            {PART_INFO.library.icon(28)}
            <h3>{selected ? "This node is not in the library" : "Pick an element to edit it"}</h3>
            <p className="small">{PART_INFO.library.empty}</p>
          </div>
        )}
      </div>
    </div>
  );
}

function FormOutlineView({ form, selected }: { form: FormOutline; selected?: string }) {
  const studio = useStudio();
  const open = (node: string) => studio.open("library", node);
  return (
    <section aria-label={form.label}>
      <h4>{form.label}</h4>
      <div className={`list-item outline-form`} role="treeitem" aria-level={1} aria-selected={form.iri === selected} onClick={() => open(form.iri)}>
        <div className="grow">
          <div className="name">{form.label}</div>
          <div className="detail">
            Form · {form.elements.length} top-level {form.elements.length === 1 ? "element" : "elements"}
          </div>
        </div>
      </div>
      {form.elements.map((e) => (
        <ElementRow key={e.iri} node={e} depth={2} selected={selected} open={open} />
      ))}
      {form.variables.length > 0 && <div className="outline-group">Variables</div>}
      {form.variables.map((v) => (
        <div key={v.iri} className="list-item outline-row" role="treeitem" aria-level={2} aria-selected={v.iri === selected} onClick={() => open(v.iri)} style={{ paddingLeft: 14 + 18 }}>
          <span className="mono outline-id">{v.key}</span>
          <span className="grow small muted">{v.contract ? "concepts" : v.space ? "quantity" : "literal"}{v.multiValued ? ", several" : ""}</span>
          <span className={`chip ${v.governing ? "warn" : "accent"}`}>{v.governing ? "Governing" : "Embedded"}</span>
        </div>
      ))}
    </section>
  );
}

function ElementRow({ node, depth, selected, open }: { node: OutlineNode; depth: number; selected?: string; open: (iri: string) => void }) {
  const studio = useStudio();
  const shown = node.label ?? (node.text || "(no text)");
  return (
    <>
      <div className="list-item outline-row" role="treeitem" aria-level={depth} aria-selected={node.iri === selected} onClick={() => open(node.iri)} style={{ paddingLeft: 14 + (depth - 1) * 18 }}>
        <span className="mono outline-id">{node.objectId ?? "-"}</span>
        <span className="grow outline-text">{shown}</span>
        {node.slot && (
          <span className="chip baseline">
            Slot, {node.children.length} {node.children.length === 1 ? "variant" : "variants"}
          </span>
        )}
        <span className={`chip ${node.mode === "Mandatory" ? "" : node.mode === "Conditional" ? "warn" : "accent"}`}>{node.mode}</span>
        {node.condition && (
          <button
            className="chip ok outline-condition"
            title={`Included when ${node.condition.name}`}
            onClick={(e) => {
              e.stopPropagation();
              studio.open("eligibility", node.condition!.iri);
            }}
          >
            When {node.condition.name}
          </button>
        )}
      </div>
      {node.children.map((c) => (
        <ElementRow key={c.iri} node={c} depth={depth + 1} selected={selected} open={open} />
      ))}
    </>
  );
}

// ---- Assemblies -----------------------------------------------------------------------

export function AssemblyView({ selected, assembler }: { selected?: string; assembler: Assembler }) {
  const studio = useStudio();
  const { model, world } = studio;
  const graph = model.state.configs.assembly!.current;
  const assemblies = useMemo(() => assembliesOf(graph), [graph]);
  const forms = useMemo(() => formsOf(world).map((f) => outline(world, f)), [world]);
  const edit = (change: (g: Graph) => Graph) => model.edit("assembly", change);

  const add = () => {
    let made = "";
    edit((g) => {
      const created = addAssembly(g, world, studio.baseline.namespace, `Assembly ${assemblies.length + 1}`, forms[0]?.iri);
      made = created.iri;
      return created.graph;
    });
    studio.open("assembly", made);
  };
  const { run } = assembler;
  const stale = run && (run.inputs[0] !== graph || run.inputs[1] !== model.state.configs.library!.current);

  return (
    <div className="split">
      <div className="list">
        <div className="list-head">
          <div className="row">
            {PART_INFO.assembly.icon(16)}
            <strong className="grow">Assemblies</strong>
            <button className="btn sm" onClick={add} disabled={forms.length === 0} title={forms.length === 0 ? "The library holds no form" : undefined}>
              <Plus size={13} /> Add
            </button>
          </div>
          <button className="btn sm primary" style={{ marginTop: 8 }} disabled={assemblies.length === 0 || run?.state === "running"} onClick={() => void assembler.assemble()}>
            {run?.state === "running" ? <Spinner /> : <Play size={13} />} Assemble
          </button>
        </div>
        {assemblies.length === 0 && <div className="empty small">No assembly yet. Add one to choose a form's options and set its values.</div>}
        {assemblies.map((a) => (
          <div key={a} className="list-item" aria-selected={a === selected} onClick={() => studio.open("assembly", a)}>
            <div className="grow" style={{ minWidth: 0 }}>
              <div className="name ellipsis">{nameOfAssembly(graph, a)}</div>
              <div className="detail ellipsis">{formLabel(forms, graph.value(a, CST("assembles")))}</div>
            </div>
          </div>
        ))}
      </div>
      <div className="detail-pane">
        {selected && graph.has(selected) ? (
          <AssemblyEditor key={selected} assembly={selected} forms={forms} />
        ) : (
          <div className="empty">
            {PART_INFO.assembly.icon(28)}
            <h3>{selected ? "This assembly is not in the configuration" : "Pick an assembly to edit it"}</h3>
            <p className="small">{PART_INFO.assembly.empty}</p>
          </div>
        )}
        {run && <Outcome run={run} stale={!!stale} />}
      </div>
    </div>
  );
}

function formLabel(forms: FormOutline[], form?: string): string {
  if (!form) return "No form chosen";
  return forms.find((f) => f.iri === form)?.label ?? `Unknown form ${localName(form)}`;
}

/** A text field that writes on blur or Enter, so a typed value is one edit and one undo step. */
function Commit({ value, onCommit, ...props }: { value: string; onCommit: (v: string) => void } & Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "onChange">) {
  const [draft, setDraft] = useState(value);
  const [seen, setSeen] = useState(value);
  if (value !== seen) {
    setSeen(value);
    setDraft(value);
  }
  const commit = () => draft !== value && onCommit(draft);
  return <input {...props} className="input" value={draft} onChange={(e) => setDraft(e.target.value)} onBlur={commit} onKeyDown={(e) => e.key === "Enter" && commit()} />;
}

function AssemblyEditor({ assembly, forms }: { assembly: string; forms: FormOutline[] }) {
  const studio = useStudio();
  const { model, world } = studio;
  const graph = model.state.configs.assembly!.current;
  const edit = (change: (g: Graph) => Graph) => model.edit("assembly", change);
  const formIri = graph.value(assembly, CST("assembles"));
  const form = forms.find((f) => f.iri === formIri);
  const choices = useMemo(() => (form ? choicesOf(form) : []), [form]);
  const variables = useMemo(() => (form ? settableOf(world, form) : []), [form, world]);
  const made = choicesMade(graph, assembly);
  const settings = settingsMade(graph, assembly);

  const remove = () => {
    if (!window.confirm(`Delete ${nameOfAssembly(graph, assembly)}? You can undo this.`)) return;
    edit((g) => removeAssembly(g, assembly));
    studio.open("assembly");
  };

  return (
    <div className="editor">
      <div className="editor-head">
        <div className="grow">
          <span className="chip accent">Assembly</span>
          <h2 style={{ marginTop: 8 }}>{nameOfAssembly(graph, assembly)}</h2>
          <div className="iri">{assembly}</div>
        </div>
        <button className="btn danger sm" onClick={remove}>
          <Trash2 size={13} /> Delete
        </button>
      </div>

      <section className="card section" aria-label="Assembly">
        <div className="fields">
          <div className="field">
            <div className="label">
              <label className="name" htmlFor="assembly-label">Label</label>
              <div className="prop">rdfs:label</div>
            </div>
            <Commit id="assembly-label" value={graph.value(assembly, LABEL) ?? ""} onCommit={(v) => edit((g) => setLabel(g, assembly, v))} />
          </div>
          <div className="field">
            <div className="label">
              <label className="name" htmlFor="assembly-form">Form</label>
              <div className="prop">cst:assembles</div>
            </div>
            <select
              id="assembly-form"
              className="select"
              value={formIri ?? ""}
              onChange={(e) => {
                if (e.target.value !== (formIri ?? "")) edit((g) => setForm(g, assembly, e.target.value || undefined));
              }}
            >
              <option value="">Choose a form</option>
              {forms.map((f) => (
                <option key={f.iri} value={f.iri}>
                  {f.label}
                </option>
              ))}
              {formIri && !form && <option value={formIri}>{`Unknown form ${localName(formIri)}`}</option>}
            </select>
          </div>
        </div>
      </section>

      {form && (
        <>
          <section className="card section" aria-label="Choices">
            <header>
              <h3 className="grow">Choices</h3>
              <span className="set">{choices.filter((c) => made.has(c.iri)).length} of {choices.length} chosen</span>
            </header>
            <div className="fields">
              {choices.length === 0 && <p className="muted small">The form has no optional element and no variant to choose.</p>}
              {choices.map((c) => (
                <label key={c.iri} className="row choice-row">
                  <input type="checkbox" checked={made.has(c.iri)} onChange={(e) => edit((g) => toggleChoice(g, assembly, c.iri, e.target.checked))} />
                  <span className="mono outline-id">{c.objectId ?? "-"}</span>
                  <span className="grow">{c.title}</span>
                  <span className={`chip ${c.kind === "variant" ? "baseline" : "accent"}`}>{c.kind === "variant" ? "Variant" : "Optional"}</span>
                </label>
              ))}
            </div>
          </section>

          <section className="card section" aria-label="Values">
            <header>
              <h3 className="grow">Values</h3>
              <span className="set">{variables.filter((v) => settings.has(v.iri)).length} of {variables.length} set</span>
            </header>
            <div className="fields">
              {variables.length === 0 && <p className="muted small">No condition reads a variable of this form, and its text shows none.</p>}
              {variables.map((v) => (
                <div className="field" key={v.iri}>
                  <div className="label">
                    <label className="name" htmlFor={`value-${localName(v.iri)}`}>{v.key}</label>
                    <div className="prop">{v.governing ? "governing variable" : "embedded variable"}</div>
                  </div>
                  <ValueField assembly={assembly} variable={v} id={`value-${localName(v.iri)}`} />
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function ValueField({ assembly, variable, id }: { assembly: string; variable: VariableInfo; id: string }) {
  const studio = useStudio();
  const { model, world } = studio;
  const graph = model.state.configs.assembly!.current;
  const current = settingsMade(graph, assembly).get(variable.iri);
  const concepts = useMemo(() => conceptsFor(world, variable), [world, variable]);
  const write = (entry: Parameters<typeof writeSetting>[5]) => model.edit("assembly", (g) => writeSetting(g, world, studio.baseline.namespace, assembly, variable, entry));
  if (variable.contract && concepts.length > 0) {
    return (
      <TermPicker
        single={!variable.multiValued}
        selected={current?.values ?? []}
        options={concepts.map((c) => ({ iri: c.iri, label: c.label, group: "Concepts" }))}
        placeholder={variable.multiValued ? "Add a value" : "Pick a value"}
        onChange={(values) => write({ resources: values })}
      />
    );
  }
  if (variable.contract) {
    return (
      <>
        <Commit id={id} value={(current?.values ?? []).join(", ")} placeholder="An IRI" onCommit={(v) => write({ resources: variable.multiValued ? v.split(",").map((s) => s.trim()) : [v.trim()] })} />
        <div className="help">The contract binds no scheme with concepts, so the value is an IRI.</div>
      </>
    );
  }
  return (
    <>
      <Commit
        id={id}
        value={(current?.literals ?? []).join(", ")}
        inputMode={variable.space ? "decimal" : undefined}
        placeholder={variable.space ? "A number" : "Text"}
        onCommit={(v) => write({ literals: variable.multiValued ? v.split(",") : [v] })}
      />
      <div className="help">{datatypeOf(variable) ? `Written as ${compact(datatypeOf(variable)!)}, for the variable's value space.` : "Written as a string."}</div>
    </>
  );
}

// ---- The outcome -------------------------------------------------------------------------

function Outcome({ run, stale }: { run: Run; stale: boolean }) {
  const studio = useStudio();
  if (run.state === "running") {
    return (
      <div className="editor" style={{ paddingTop: 0 }} role="status">
        <Spinner /> Assembling
      </div>
    );
  }
  if (run.state === "failed") {
    return (
      <div className="editor" style={{ paddingTop: 0 }}>
        <p style={{ color: "var(--bad)" }}>The assemble job could not run: {run.message}</p>
      </div>
    );
  }
  const job = run.job!;
  const groups = new Map<string, { record?: string; document?: string }>();
  for (const a of job.artefacts) {
    const entry = groups.get(a.group) ?? {};
    if (a.path === "record.ttl") entry.record = a.content;
    if (a.path === "document.xml") entry.document = a.content;
    groups.set(a.group, entry);
  }
  const graph = studio.model.state.configs.assembly!.current;
  const link = (issue: Issue) => {
    const part = issue.focus ? studio.partOf(issue.focus) : undefined;
    if (part && issue.focus) studio.open(part, issue.focus);
  };
  return (
    <div className="editor" style={{ paddingTop: 0 }} aria-label="Assemble outcome" role="region">
      <div className="row" style={{ marginBottom: 10 }}>
        <h3 className="grow">Outcome</h3>
        <Conforms ok={!!job.conforms} /> <strong>{job.conforms ? "Assembled" : "Refused"}</strong>
        {stale && <span className="chip warn">Edited since</span>}
      </div>
      {job.issues.length > 0 && (
        <div className="card" style={{ padding: "6px 0", marginBottom: 14 }} role="list" aria-label="Findings">
          {job.issues.map((i, n) => (
            <div key={n} className="issue" role="listitem" onClick={() => link(i)}>
              <span className="sev">
                <SeverityIcon severity={i.severity} />
              </span>
              <span className="grow">
                {i.message}
                <div className="where">
                  {i.code && <span className="chip" style={{ marginRight: 6 }}>{i.code}</span>}
                  {i.focus && studio.partOf(i.focus) ? (
                    <button className="link" onClick={(e) => { e.stopPropagation(); link(i); }}>{compact(i.focus)}</button>
                  ) : i.focus ? compact(i.focus) : null}
                </div>
              </span>
            </div>
          ))}
        </div>
      )}
      {[...groups.entries()].map(([group, files]) => (
        <AssembledCard key={group} name={nameOfAssembly(graph, group)} files={files} />
      ))}
    </div>
  );
}

function AssembledCard({ name, files }: { name: string; files: { record?: string; document?: string } }) {
  const [showRecord, setShowRecord] = useState(false);
  const doc = useMemo(() => (files.document ? readDocument(files.document) : undefined), [files.document]);
  return (
    <section className="card" style={{ marginBottom: 14, padding: 16 }} aria-label={`Assembled ${name}`}>
      <div className="row" style={{ marginBottom: 10 }}>
        <strong className="grow">{name}</strong>
        {files.document && (
          <button className="btn sm" onClick={() => download("document.xml", files.document!, "application/xml")}>
            <Download size={13} /> document.xml
          </button>
        )}
        {files.record && (
          <>
            <button className="btn sm" aria-expanded={showRecord} onClick={() => setShowRecord(!showRecord)}>
              {showRecord ? "Hide record" : "View record"}
            </button>
            <button className="btn sm" onClick={() => download("record.ttl", files.record!)}>
              <Download size={13} /> record.ttl
            </button>
          </>
        )}
      </div>
      {doc ? <DocumentView doc={doc} /> : files.document ? <Code text={files.document} maxHeight={400} /> : null}
      {showRecord && files.record && (
        <div style={{ marginTop: 12 }}>
          <Code text={files.record} maxHeight={400} />
        </div>
      )}
    </section>
  );
}

function DocumentView({ doc }: { doc: AssembledDocument }) {
  return (
    <article className="assembled">
      <h4>{doc.title}</h4>
      {doc.sections.map((s, i) => (
        <section key={i}>
          {s.number && <h5>Section {s.number}</h5>}
          {s.clauses.map((c, j) => (
            <Clause key={j} clause={c} />
          ))}
        </section>
      ))}
    </article>
  );
}

function Clause({ clause }: { clause: DocClause }) {
  return (
    <p>
      {clause.number && <strong className="clause-number">{clause.number}</strong>}
      {clause.runs.map((r, i) =>
        r.kind === "var" ? (
          <mark key={i} className="doc-var" title={`Value of ${r.key}`}>
            {r.text}
          </mark>
        ) : r.kind === "ref" ? (
          <span key={i} className="doc-ref">{r.text}</span>
        ) : (
          r.text
        ),
      )}
    </p>
  );
}
