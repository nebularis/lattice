// SPDX-License-Identifier: MPL-2.0
// The workspace shell: top bar, navigation, the view, the inspector and the problems drawer, all
// sharing one selection, the route.

import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpen,
  ChevronDown,
  ListChecks,
  Ruler,
  ChevronUp,
  Database,
  FileCode2,
  Hammer,
  Layers,
  LayoutDashboard,
  Library,
  Network,
  PanelRight,
  Puzzle,
  Redo2,
  Save,
  Scale,
  Search,
  Shapes,
  Sparkles,
  Undo2,
  Workflow,
  X,
} from "lucide-react";
import { Baseline } from "../rdf/baseline";
import { items, nodeFor, type Item } from "../rdf/editors";
import { assembliesOf, formsOf } from "../rdf/builder";
import { termsOf } from "../rdf/meaning";
import { INS, MORK, compact, type Graph } from "@lattice/authoring-domain";
import type { Issue } from "../rdf/report";
import type { Vocabulary } from "../rdf/vocabulary";
import { PARTS, isDirty, useWorkspace, type Part, type WorkspaceModel } from "../state";
import { BaselineView } from "./BaselineView";
import { BuildView } from "./BuildView";
import { AssemblyView, LibraryView, useAssembler } from "./BuilderView";
import { InstrumentView } from "./InstrumentView";
import { MappingView } from "./MappingView";
import { MeaningView } from "./MeaningView";
import { ConfigView } from "./ConfigView";
import { Code, Diff, Modal, SeverityIcon, Spinner, go, href } from "./kit";
import { Overview } from "./Overview";

export interface Studio {
  id: string;
  model: WorkspaceModel;
  vocab: Vocabulary;
  baseline: Baseline;
  items: Record<Part, Item[]>;
  /** The baseline and every configuration as edited, merged, for references across parts. */
  world: Graph;
  /** The configuration that holds a node, if any does. */
  partOf: (node: string) => Part | undefined;
  /** Navigate to a node of a configuration, optionally flashing one of its fields. */
  open: (part: Part, node?: string, field?: string) => void;
}

const StudioContext = createContext<Studio | null>(null);

export function useStudio(): Studio {
  const studio = useContext(StudioContext);
  if (!studio) throw new Error("useStudio outside a workspace");
  return studio;
}

const VIEWS = ["overview", "baseline", "library", "assembly", "meaning", "instrument", "vocabulary", "quantification", "eligibility", "persistence", "surface", "mapping", "build"] as const;

/** The views of builder mode (ADR-A138), which share the workspace's state, inspector and problems drawer with the rest. */
const BUILDER_VIEWS: readonly string[] = ["library", "assembly", "meaning", "instrument"];

/** The views of mapping mode, MORK mapping schemes from a source's structure into LATTICE's terms. */
const MAPPING_VIEWS: readonly string[] = ["mapping"];

const PART_NAV: { part: Exclude<Part, "review" | "mapping">; label: string; icon: React.ReactNode }[] = [
  { part: "vocabulary", label: "Vocabulary", icon: <BookOpen size={16} /> },
  { part: "quantification", label: "Quantification", icon: <Ruler size={16} /> },
  { part: "eligibility", label: "Eligibility", icon: <ListChecks size={16} /> },
  { part: "persistence", label: "Persistence", icon: <Database size={16} /> },
  { part: "surface", label: "Surface", icon: <Sparkles size={16} /> },
];
type View = (typeof VIEWS)[number];

export function Workspace({ id, route, vocab }: { id: string; route: string[]; vocab: Vocabulary }) {
  const model = useWorkspace(id, vocab);
  const assembler = useAssembler(id, model);
  const { state } = model;
  const view: View = (VIEWS as readonly string[]).includes(route[0]) ? (route[0] as View) : "overview";
  const builder = BUILDER_VIEWS.includes(view);
  const mode = builder ? "builder" : MAPPING_VIEWS.includes(view) ? "mapping" : "configure";
  // The last view of each mode, so the switch returns to it.
  const lastView = useRef({ configure: "overview", builder: "library", mapping: "mapping" });
  lastView.current[mode] = view;
  const node = route[1];
  const activePart: Part = (PARTS as string[]).includes(view) ? (view as Part) : view === "instrument" ? "meaning" : "persistence";
  const [inspector, setInspector] = useState(() => window.innerWidth >= 1560);
  const [problemsOpen, setProblemsOpen] = useState(true);
  const [palette, setPalette] = useState(false);

  const baseline = state.baseline?.index;
  const itemLists = useMemo(
    () => Object.fromEntries(PARTS.map((p) => [p, state.configs[p] && baseline ? items(state.configs[p]!.current, p, baseline, vocab) : []])) as Record<Part, Item[]>,
    [state.configs, baseline, vocab],
  );
  const dirty = useMemo(() => Object.fromEntries(PARTS.map((p) => [p, isDirty(state.configs[p])])) as Record<Part, boolean>, [state.configs]);
  const anyDirty = PARTS.some((p) => dirty[p]);

  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      const typing = (e.target as HTMLElement).closest?.("input, textarea, select");
      if (mod && e.key.toLowerCase() === "s") {
        e.preventDefault();
        for (const part of PARTS) if (dirty[part]) void model.save(part);
      } else if (mod && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPalette(true);
      } else if (mod && e.key.toLowerCase() === "z" && !typing && (PARTS as string[]).includes(view)) {
        e.preventDefault();
        if (e.shiftKey) model.redo(activePart);
        else model.undo(activePart);
      }
    };
    const leave = (e: BeforeUnloadEvent) => {
      if (anyDirty) e.preventDefault();
    };
    window.addEventListener("keydown", key);
    window.addEventListener("beforeunload", leave);
    return () => {
      window.removeEventListener("keydown", key);
      window.removeEventListener("beforeunload", leave);
    };
  }, [dirty, anyDirty, model, view, activePart]);

  if (state.error && !state.summary) {
    return (
      <div className="empty" style={{ height: "100%" }}>
        <h3>This workspace could not be opened</h3>
        <p>{state.error}</p>
        <a href="#/">Back to workspaces</a>
      </div>
    );
  }
  if (!state.summary || !baseline || PARTS.some((p) => !state.configs[p])) {
    return (
      <div className="empty" style={{ height: "100%" }}>
        <Spinner size={22} />
      </div>
    );
  }

  const studio: Studio = {
    id,
    model,
    vocab,
    baseline,
    items: itemLists,
    world: model.world,
    partOf: (n) => PARTS.find((p) => state.configs[p]!.current.has(n)),
    // A proposal is reviewed in the meaning view.
    open: (part, n, field) => go("w", id, part === "review" ? "meaning" : part, ...(n ? [n] : []), ...(field ? [field] : [])),
  };
  const config = state.configs[activePart]!;
  const editing = (PARTS as string[]).includes(view);

  return (
    <StudioContext.Provider value={studio}>
      <div className="shell">
        <header className="topbar">
          <a href="#/" className="brand" style={{ textDecoration: "none", color: "inherit" }} aria-label="All workspaces">
            <span className="mark">
              <Layers size={16} />
            </span>
          </a>
          <div className="crumb">
            <a href="#/" style={{ color: "inherit", textDecoration: "none" }}>
              Workspaces
            </a>
            <span>/</span>
            <strong>{state.summary.label}</strong>
          </div>
          <div className="spacer" />
          <button className="btn ghost sm" onClick={() => setPalette(true)} aria-label="Go to anything">
            <Search size={14} /> Go to <span className="kbd">⌘K</span>
          </button>
          {editing && (
            <>
              <button className="btn ghost icon" aria-label="Undo" title="Undo (⌘Z)" disabled={!config.past.length} onClick={() => model.undo(activePart)}>
                <Undo2 size={16} />
              </button>
              <button className="btn ghost icon" aria-label="Redo" title="Redo (⇧⌘Z)" disabled={!config.future.length} onClick={() => model.redo(activePart)}>
                <Redo2 size={16} />
              </button>
            </>
          )}
          <ValidationPill model={model} />
          <SaveButton model={model} dirty={dirty} />
          <button className="btn primary" onClick={() => go("w", id, "build")}>
            <Hammer size={15} /> Build
          </button>
          <button className="btn ghost icon" aria-label="Toggle inspector" aria-pressed={inspector} onClick={() => setInspector(!inspector)}>
            <PanelRight size={16} />
          </button>
        </header>

        <nav className="nav" aria-label="Workspace">
          <div className="mode-switch" role="group" aria-label="Mode">
            <button aria-pressed={mode === "configure"} onClick={() => go("w", id, lastView.current.configure)}>
              Configure
            </button>
            <button aria-pressed={mode === "builder"} onClick={() => go("w", id, lastView.current.builder)}>
              Builder
            </button>
            <button aria-pressed={mode === "mapping"} onClick={() => go("w", id, lastView.current.mapping)}>
              Mapping
            </button>
          </div>
          {mode === "mapping" ? (
            <>
              <div className="group">Mapping</div>
              <NavLink to="mapping" view={view} id={id} icon={<Network size={16} />} label="Schemes" count={state.configs.mapping!.current.ofType(MORK("MappingScheme")).length} issues={model.issues.mapping} dirty={dirty.mapping} />
              <div className="group">Output</div>
              <NavLink to="build" view={view} id={id} icon={<FileCode2 size={16} />} label="Build" />
            </>
          ) : builder ? (
            <>
              <div className="group">Contract builder</div>
              <NavLink to="library" view={view} id={id} icon={<Library size={16} />} label="Library" count={formsOf(model.world).length} issues={model.issues.library} dirty={dirty.library} />
              <NavLink to="assembly" view={view} id={id} icon={<Puzzle size={16} />} label="Assemblies" count={assembliesOf(state.configs.assembly!.current).length} issues={model.issues.assembly} dirty={dirty.assembly} />
              <NavLink to="meaning" view={view} id={id} icon={<Scale size={16} />} label="Meaning" count={termsOf(state.configs.meaning!.current).length} issues={model.issues.meaning} dirty={dirty.meaning || dirty.review} />
              <NavLink to="instrument" view={view} id={id} icon={<Workflow size={16} />} label="Instrument" count={state.configs.meaning!.current.ofType(INS("Term")).length} />
            </>
          ) : (
            <>
              <NavLink to="overview" view={view} id={id} icon={<LayoutDashboard size={16} />} label="Overview" />
              <NavLink to="baseline" view={view} id={id} icon={<Shapes size={16} />} label="Baseline" count={baseline.classes.size} />
              <div className="group">Configuration</div>
              {PART_NAV.map((n) => (
                <NavLink key={n.part} to={n.part} view={view} id={id} icon={n.icon} label={n.label} count={itemLists[n.part].length} issues={model.issues[n.part]} dirty={dirty[n.part]} />
              ))}
              <div className="group">Output</div>
              <NavLink to="build" view={view} id={id} icon={<FileCode2 size={16} />} label="Build" />
            </>
          )}
        </nav>

        <main className="main" id="main">
          {view === "overview" && <Overview />}
          {view === "baseline" && <BaselineView selected={node} />}
          {view === "library" && <LibraryView selected={node} field={route[2]} />}
          {view === "assembly" && <AssemblyView selected={node} assembler={assembler} />}
          {view === "meaning" && <MeaningView selected={node} field={route[2]} />}
          {view === "instrument" && <InstrumentView selected={node} field={route[2]} />}
          {view === "mapping" && <MappingView selected={node} />}
          {editing && mode === "configure" && <ConfigView part={activePart} selected={node} field={route[2]} />}
          {view === "build" && <BuildView />}
        </main>

        <aside className={`side${inspector ? "" : " closed"}`} aria-label="Inspector">
          {inspector && <Inspector part={activePart} node={editing ? node : undefined} />}
        </aside>

        <Problems open={problemsOpen} toggle={() => setProblemsOpen(!problemsOpen)} />
      </div>

      {palette && <Palette onClose={() => setPalette(false)} />}
      {state.conflict && <ConflictDialog />}
      {state.error && (
        <div className="toast" role="alert">
          {state.error}
          <button className="btn ghost icon sm" style={{ color: "inherit" }} aria-label="Dismiss" onClick={model.dismissError}>
            <X size={14} />
          </button>
        </div>
      )}
    </StudioContext.Provider>
  );
}

function NavLink(props: { to: View; view: View; id: string; icon: React.ReactNode; label: string; count?: number; issues?: Issue[]; dirty?: boolean }) {
  const violations = props.issues?.filter((i) => i.severity === "Violation").length ?? 0;
  const warnings = props.issues?.filter((i) => i.severity === "Warning").length ?? 0;
  return (
    <a href={href("w", props.id, props.to)} aria-current={props.view === props.to ? "page" : undefined}>
      {props.icon}
      {props.label}
      {props.dirty && <span className="dot dirty" title="Unsaved changes" />}
      {violations > 0 ? <span className="dot bad" title={`${violations} violations`} /> : warnings > 0 ? <span className="dot warn" title={`${warnings} warnings`} /> : null}
      {props.count !== undefined && <span className="count">{props.count}</span>}
    </a>
  );
}

function ValidationPill({ model }: { model: WorkspaceModel }) {
  const running = PARTS.some((p) => model.state.configs[p]?.validation.state === "running");
  const failed = PARTS.find((p) => model.state.configs[p]?.validation.state === "failed");
  const all = PARTS.flatMap((p) => model.issues[p]);
  const violations = all.filter((i) => i.severity === "Violation").length;
  const warnings = all.filter((i) => i.severity === "Warning").length;
  if (running) {
    return (
      <span className="chip accent" role="status">
        <Spinner size={12} /> Validating
      </span>
    );
  }
  if (failed) {
    return (
      <span className="chip warn" role="status" title={model.state.configs[failed]?.validation.message}>
        Validation unavailable
      </span>
    );
  }
  if (violations) return <span className="chip bad" role="status">{violations} {violations === 1 ? "violation" : "violations"}</span>;
  if (warnings) return <span className="chip warn" role="status">{warnings} {warnings === 1 ? "warning" : "warnings"}</span>;
  return (
    <span className="chip ok" role="status">
      Conforms
    </span>
  );
}

function SaveButton({ model, dirty }: { model: WorkspaceModel; dirty: Record<Part, boolean> }) {
  const saving = PARTS.some((p) => model.state.configs[p]?.saving);
  const any = PARTS.some((p) => dirty[p]);
  return (
    <button
      className="btn"
      disabled={!any || saving}
      title="Save (⌘S)"
      onClick={() => {
        for (const part of PARTS) if (dirty[part]) void model.save(part);
      }}
    >
      {saving ? <Spinner /> : <Save size={15} />} {saving ? "Saving" : any ? "Save" : "Saved"}
    </button>
  );
}

function Inspector({ part, node }: { part: Part; node?: string }) {
  const { model } = useStudio();
  const config = model.state.configs[part]!;
  const [tab, setTab] = useState<"turtle" | "changes">("turtle");
  const subjects = node && config.current.has(node) ? config.current.quads(node).slice(0, 1).map((q) => q.subject) : undefined;
  const turtle = useMemo(() => config.current.toTurtle(subjects), [config.current, subjects?.[0]?.value]); // eslint-disable-line react-hooks/exhaustive-deps
  const before = useMemo(() => config.saved.toTurtle(), [config.saved]);
  const after = useMemo(() => config.current.toTurtle(), [config.current]);
  return (
    <>
      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "turtle"} onClick={() => setTab("turtle")}>
          Turtle
        </button>
        <button role="tab" aria-selected={tab === "changes"} onClick={() => setTab("changes")}>
          Unsaved changes {before !== after && <span className="dot dirty" />}
        </button>
      </div>
      <div className="panel">
        {tab === "turtle" && (
          <>
            <p className="small muted" style={{ marginTop: 0 }}>
              {subjects ? "The selected node, as it will be saved." : `The whole ${part} configuration, as it will be saved.`} Read-only: edit through the forms.
            </p>
            {config.current.size ? <Code text={turtle} /> : <p className="muted">Nothing yet.</p>}
          </>
        )}
        {tab === "changes" && <Diff before={before} after={after} />}
      </div>
    </>
  );
}

function Problems({ open, toggle }: { open: boolean; toggle: () => void }) {
  const { model, open: openNode } = useStudio();
  const jump = (part: Part, issue: Issue) => {
    const node = nodeFor(model.state.configs[part]!.current, issue);
    if (node) openNode(part, node, issue.path);
  };
  const rows = PARTS.flatMap((part) => model.issues[part].map((issue) => ({ part, issue })));
  const v = rows.filter((r) => r.issue.severity === "Violation").length;
  const w = rows.length - v;
  return (
    <section className="problems" aria-label="Problems">
      <div className="head" onClick={toggle} role="button" aria-expanded={open}>
        Problems
        <span className="chip bad">{v}</span>
        <span className="chip warn">{w}</span>
        <span className="spacer" />
        {open ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
      </div>
      {open && (
        <ul>
          {rows.length === 0 && <li className="issue muted">No problems in any part of the workspace.</li>}
          {rows.map(({ part, issue }, i) => (
            <li key={i} className="issue" onClick={() => jump(part, issue)}>
              <span className="sev">
                <SeverityIcon severity={issue.severity} />
              </span>
              <span className="grow">
                {issue.message}
                <div className="where">
                  {part} · {issue.focus ? compact(issue.focus) : "whole configuration"}
                  {issue.path && ` · ${compact(issue.path)}`}
                  {issue.code && ` · ${issue.code}`}
                  {issue.shape && ` · ${issue.shape}`}
                </div>
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Palette({ onClose }: { onClose: () => void }) {
  const { id, baseline, items: lists, open } = useStudio();
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState(0);
  const entries = useMemo(() => {
    const out: { label: string; hint: string; go: () => void }[] = [
      ...VIEWS.map((v) => ({ label: v[0].toUpperCase() + v.slice(1), hint: "view", go: () => go("w", id, v) })),
      ...PARTS.flatMap((part) => lists[part].map((it) => ({ label: it.name, hint: `${it.kind.title}`, go: () => open(part, it.iri) }))),
      ...[...baseline.classes.values()].map((c) => ({ label: c.label, hint: "class", go: () => go("w", id, "baseline", c.iri) })),
    ];
    const q = query.toLowerCase();
    return out.filter((e) => !q || e.label.toLowerCase().includes(q) || e.hint.toLowerCase().includes(q)).slice(0, 50);
  }, [query, id, baseline, lists, open]);
  const pick = (i: number) => {
    entries[i]?.go();
    onClose();
  };
  return (
    <div className="backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal palette" role="dialog" aria-label="Go to anything">
        <input
          autoFocus
          placeholder="Go to a view, a node or a class"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIndex(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") setIndex(Math.min(index + 1, entries.length - 1));
            else if (e.key === "ArrowUp") setIndex(Math.max(index - 1, 0));
            else if (e.key === "Enter") pick(index);
            else if (e.key === "Escape") onClose();
          }}
        />
        <ul role="listbox">
          {entries.map((e, i) => (
            <li key={i} role="option" aria-selected={i === index} onMouseEnter={() => setIndex(i)} onClick={() => pick(i)}>
              <span className="grow">{e.label}</span>
              <span className="small muted">{e.hint}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function ConflictDialog() {
  const { model } = useStudio();
  const conflict = model.state.conflict!;
  const mine = model.state.configs[conflict.part]!.current;
  return (
    <Modal
      wide
      title={`The ${conflict.part} configuration changed since you loaded it`}
      subtitle="Someone saved a newer revision. Compare it with yours, then keep yours, which overwrites theirs, or take theirs, which discards your unsaved edits."
      onClose={() => undefined}
      footer={
        <>
          <button className="btn" onClick={() => void model.resolve("theirs")}>
            Take theirs
          </button>
          <button className="btn primary" onClick={() => void model.resolve("mine")}>
            Keep mine
          </button>
        </>
      }
    >
      <p className="small muted">Lines marked - are only in theirs, + only in yours.</p>
      <Diff before={conflict.theirs.toTurtle()} after={mine.toTurtle()} />
    </Modal>
  );
}
