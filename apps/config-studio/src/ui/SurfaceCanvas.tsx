// SPDX-License-Identifier: MPL-2.0
// The surface canvas (SVA-S1, part 1). It draws a contract of the surface part, a promotion, an index or a projection of any kind, from the
// carrier class to what is read from it to what is written, in one grammar for every kind (SVA-Q59). It is drawn from the configuration as the
// author states it, so an edit in the form shows at once, and the browser never computes what a contract lowers to (SVA-Q58 (a)). The targets a
// contract writes are drawn as types from the ontology the workspace holds (SVA-Q62), and a small box for each projection reads the lowered
// scheme from the latest finished surface compilation, marked out of date when the surface part or the baseline has changed since. A finding the
// form shows is drawn on the element it concerns (SVA-Q61). The canvas edits nothing. Selecting a node selects the matching node in the form.

import { useEffect, useMemo, useState } from "react";
import { Handle, MarkerType, Position, type Edge, type Node, type NodeProps } from "@xyflow/react";
import { Calculator, Pencil, Plus, Route } from "lucide-react";
import { Graph, PREFIXES, SRF, compact } from "@lattice/authoring-domain";
import { api, awaitJob, jobId } from "../api";
import { Canvas, RoutedEdge, type LayoutHints, type LayoutOptions, type RoutedEdgeData } from "../canvas/kit";
import { concerns } from "../rdf/editors";
import type { Issue } from "../rdf/report";
import { fingerprint, readCompiled as readSent, writeCompiled } from "../persistence/landing";
import { noteCompiled, useCompilationEpoch } from "../persistence/compilation";
import { readSurface, type SurfaceLoad } from "../surface/compilation";
import { EDIT_WORDS, bindingsOf, contractOf, contractsOf, drawContracts, type DrawEdge, type DrawNode, type EditTarget, type PathPlace } from "../surface/drawing";
import { placeFindings, worst } from "../surface/findings";
import { boxesFor, schemeOf, staleMark } from "../surface/scheme";
import { ontologyOf, termsOf } from "../surface/terms";
import { statementContext, unreadEvidence } from "../surface/statement";
import { ConstructionEditor } from "./ConstructionEditor";
import { ExpansionEditor } from "./ExpansionEditor";
import { ExpressionEditor } from "./ExpressionEditor";
import { JoinEditor } from "./JoinEditor";
import { MappingCanvas } from "./MappingCanvas";
import { PathMode } from "./PathMode";
import { Modal, SeverityIcon, Spinner, ago, go } from "./kit";
import { useStudio } from "./Workspace";
import { PARTS } from "../state";

/** Left to right, the carrier, what is read, what is written and the lowered scheme. Each gap leaves room for an edge's label. */
const LAYOUT: LayoutOptions = { direction: "LR", columnGap: 130, rowGap: 30 };
const EDGE_TYPES = { link: RoutedEdge };

type BoxData = { node: DrawNode; issues: Issue[]; selected: boolean; stale: boolean; build?: (place: PathPlace) => void; edit?: (target: EditTarget) => void };

const WIDTH = 224;
/** The size the layout reserves, counting the rows a long line wraps to. */
const sizeOf = (n: DrawNode) => {
  const width = n.kind === "statement" || n.kind === "entries" ? 252 : WIDTH;
  const build = n.place || n.edit ? 1 : 0;
  const rows = n.lines.reduce((sum, l) => sum + Math.max(1, Math.ceil(l.length / (width / 6.3))), 0) + Math.max(0, Math.ceil(n.title.length / (width / 7.5)) - 1);
  return { width, height: 46 + 17 * rows + 22 * build };
};

function Box({ data }: NodeProps<Node<BoxData>>) {
  const n = data.node;
  const t = n.target;
  const level = worst(data.issues);
  const marks = [t && !t.declared ? "undeclared" : undefined, t?.disagrees ? "range disagrees" : undefined].filter(Boolean);
  return (
    <div
      className={`canvas-node surface-node ${n.kind}${data.selected ? " selected" : ""}${level ? ` found-${level.toLowerCase()}` : ""}${marks.length ? " marked" : ""}${data.stale ? " stale" : ""}`}
      data-kind={n.kind}
      data-title={n.title}
      title={[n.tag + ": " + n.title, ...n.lines, ...data.issues.map((i) => i.message)].join("\n")}
      style={{ width: sizeOf(n).width }}
    >
      <Handle type="target" position={Position.Left} />
      <div className="surface-tag">
        {n.tag}
        {data.stale && <span className="chip warn surface-stale">out of date</span>}
        {marks.map((m) => <span key={m} className="chip warn surface-mark">{m}</span>)}
        {level && <span className="surface-finding"><SeverityIcon severity={level} size={13} /> {data.issues.length}</span>}
      </div>
      <strong className="surface-title">{n.title}</strong>
      {n.lines.map((l, i) => <div key={i} className="small muted surface-line">{l}</div>)}
      {n.edit && data.edit && (
        <button
          className="btn ghost sm surface-build nodrag" aria-label={`Edit ${EDIT_WORDS[n.edit.kind]} of ${n.title}`} title={`Edit the ${EDIT_WORDS[n.edit.kind]} on the canvas`}
          onClick={(e) => {
            e.stopPropagation();
            data.edit!(n.edit!);
          }}
        >
          <Pencil size={12} /> Edit
        </button>
      )}
      {n.place && data.build && (
        <button
          className="btn ghost sm surface-build nodrag" aria-label={`Build ${n.place.label} from ${n.title}`} title={`Build ${n.place.label} by clicking`}
          onClick={(e) => {
            e.stopPropagation();
            data.build!(n.place!);
          }}
        >
          <Route size={12} /> Build path
        </button>
      )}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const NODE_TYPES = { box: Box };

const stroke = (e: DrawEdge, level?: Issue["severity"]): React.CSSProperties => ({
  stroke: level === "Violation" ? "var(--bad)" : level === "Warning" ? "var(--warn)" : e.kind === "hop" ? "var(--accent)" : e.kind === "write" ? "var(--surface-c)" : "var(--text-3)",
  strokeWidth: e.kind === "write" || e.kind === "hop" ? 1.8 : 1.4,
  strokeDasharray: e.dashed ? "6 4" : undefined,
});

export function SurfaceCanvas({ selected }: { selected?: string }) {
  const studio = useStudio();
  const { id, model } = studio;
  const graph = model.state.configs.surface!.current;
  const contracts = useMemo(() => contractsOf(graph), [graph]);
  // The form's findings, and a mark on each evidence binding nothing reads, which the editors leave in place rather than remove.
  const issues = useMemo(() => [...model.issues.surface, ...contracts.flatMap((c) => unreadEvidence(graph, c.iri))], [model.issues.surface, contracts, graph]);
  const picked = selected ? contractOf(graph, selected, contracts) : undefined;
  const [view, setView] = useState<"selected" | "all">("selected");
  const [focused, setFocused] = useState<string>();
  const [opened, setOpened] = useState<string>();
  const [building, setBuilding] = useState<PathPlace>();
  // The editor open on the canvas, for the expression of a derivation or for a statement of a projection (SVA-Q57 (b)).
  const [editor, setEditor] = useState<{ kind: "expression" | EditTarget["kind"]; contract: string }>();
  const [load, setLoad] = useState<SurfaceLoad>({ state: "loading" });
  const [reload, setReload] = useState(0);
  const compiledElsewhere = useCompilationEpoch();
  const [compiling, setCompiling] = useState(false);
  const [problem, setProblem] = useState<string>();

  // The ontology is the baseline and the imports and dependencies the workspace holds, as the ontology view reads it.
  const baselineGraph = model.state.baseline?.graph;
  const ontology = useMemo(
    () => ontologyOf(baselineGraph ?? Graph.empty(), [...Object.values(model.heldGraphs), ...Object.values(model.dependencyGraphs)]),
    [baselineGraph, model.heldGraphs, model.dependencyGraphs],
  );
  const terms = useMemo(() => termsOf(ontology), [ontology]);

  useEffect(() => {
    let live = true;
    readSurface(id).then(
      (next) => live && setLoad(next),
      (e: unknown) => live && setLoad({ state: "error", message: e instanceof Error ? e.message : String(e) }),
    );
    return () => {
      live = false;
    };
  }, [id, reload, compiledElsewhere]);

  const now = useMemo(() => fingerprint(graph.toTurtle(), model.state.baseline?.revision), [graph, model.state.baseline?.revision]);
  const sent = load.state === "ready" || load.state === "refused" ? readSent(id)[load.job.iri] : undefined;
  const status = load.state === "ready" ? staleMark(sent, now) : undefined;

  // The compiler reads the other parts as context, as the Build view sends them.
  const compile = async () => {
    setProblem(undefined);
    setCompiling(true);
    try {
      let body = Graph.empty();
      for (const p of PARTS) body = body.merge(model.state.configs[p]!.current);
      const job = await api.submit(id, "compile", "surface", body);
      writeCompiled(id, `urn:lattice:studio:job:${job}`, now);
      await awaitJob(job);
      setReload((n) => n + 1);
      noteCompiled();
    } catch (e) {
      setProblem(e instanceof Error ? e.message : String(e));
    } finally {
      setCompiling(false);
    }
  };

  // All contracts is an overview, the carriers, the contracts and the targets, and the contract selected in the list is drawn in full among them.
  const overview = view === "all" || !picked;
  const expanded = overview ? picked : undefined;
  const shown = overview ? contracts.map((c) => c.iri) : [picked!];
  const boxes = useMemo(
    () => (load.state === "ready" ? boxesFor(load.projections, status ?? "unknown") : boxesFor(load.state === "refused" ? "refused" : "none", "unknown")),
    [load, status],
  );
  const drawn = useMemo(() => drawContracts(graph, shown, terms, boxes, { overview, expand: expanded }), [graph, shown.join("|"), terms, boxes, overview, expanded]); // eslint-disable-line react-hooks/exhaustive-deps
  const placement = useMemo(() => placeFindings(drawn, issues), [drawn, issues]);
  const stillInList = useMemo(() => placement.unplaced.filter((i) => i.code !== "unread-evidence" && shown.some((c) => concerns(graph, c, i))), [placement, graph, shown.join("|")]); // eslint-disable-line react-hooks/exhaustive-deps

  // Path mode starts from a place that holds a path or a property, and shows the node of the configuration it writes in the form beside it.
  const begin = (place: PathPlace) => {
    setEditor(undefined);
    setBuilding(place);
    studio.open("surface", place.node);
  };
  // An editor that starts path mode, for the link property or a members path, comes back to itself when path mode is done.
  const buildFrom = (place: PathPlace) => {
    setBuilding(place);
    studio.open("surface", place.node);
  };
  // The expression editor opens from a derivation's result edge or its label, and shows the binding that states the expression in the form beside it.
  const edit = (target: { contract: string; binding?: string }) => {
    setBuilding(undefined);
    setEditor({ kind: "expression", contract: target.contract });
    studio.open("surface", target.binding ?? target.contract);
  };
  // Done goes back to the contract, which the form selects, since the statement the form showed may be gone, as when a construction is removed.
  const closeEditor = () => {
    const contract = editor?.contract;
    setEditor(undefined);
    if (contract) studio.open("surface", contract);
  };
  // A statement's editor opens from its box or the button on it, or from the toolbar, and shows the statement's node in the form beside it.
  const editStatement = (target: EditTarget) => {
    setBuilding(undefined);
    setEditor({ kind: target.kind, contract: target.contract });
    const ctx = statementContext(graph, target.contract, studio.baseline.namespace);
    const predicate = target.kind === "join" ? "joinedAs" : target.kind === "expansion" ? "expandedAs" : "constructedAs";
    studio.open("surface", (ctx.result && graph.value(ctx.result, SRF(predicate))) || ctx.result || target.contract);
  };
  const nodes = useMemo<Node[]>(
    () => drawn.nodes.map((n) => ({
      id: n.id, type: "box", position: { x: 0, y: 0 },
      data: { node: n, issues: placement.byElement.get(n.id) ?? [], selected: n.id === focused || (n.select !== undefined && n.select === selected && n.kind !== "class"), stale: n.kind === "scheme" && boxes(n.scheme!)?.stale === true, build: begin, edit: editStatement } satisfies BoxData,
    })),
    [drawn, placement, focused, selected, boxes], // eslint-disable-line react-hooks/exhaustive-deps
  );
  const edges = useMemo<Edge[]>(
    () => drawn.edges.map((e): Edge<RoutedEdgeData> => {
      const found = placement.byElement.get(e.id) ?? [];
      const level = worst(found);
      return {
        id: e.id, source: e.source, target: e.target, type: "link", markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
        style: stroke(e, level),
        data: {
          label: level && e.label ? `${level === "Violation" ? "✖" : "⚠"} ${e.label}` : level ? (level === "Violation" ? "✖" : "⚠") : e.label,
          title: [e.title, ...found.map((i) => i.message)].join("\n"), dashed: e.dashed, className: "onto-edge", labelClass: "onto-edge-label",
          onLabelClick: e.expression ? () => edit(e.expression!) : undefined,
        },
      };
    }),
    [drawn, placement], // eslint-disable-line react-hooks/exhaustive-deps
  );
  const hints = useMemo<LayoutHints>(() => Object.fromEntries(drawn.nodes.map((n) => [n.id, { ...sizeOf(n), rank: n.rank }])), [drawn]);

  const chooseEdge = (edge: Edge) => {
    const found = drawn.edges.find((e) => e.id === edge.id)?.expression;
    if (found) edit(found);
  };
  // The derivation drawn in full, which the editor opens for from the controls as from its edge.
  const derivation = drawn.contracts.find((c) => c.kind === "derivation" && (c.contract === picked) && !overview);
  // The statement the contract in full states or may state, which the toolbar edits or offers to add (SVA-Q57 (b)). A contract that states none offers the one its kind requires.
  const subject = overview ? expanded : picked;
  const statements = useMemo(() => {
    if (!subject) return [];
    const ctx = statementContext(graph, subject, studio.baseline.namespace);
    if (!ctx.result || !ctx.kind || ctx.kind === "derivation") return [];
    const states = (p: string) => graph.object(ctx.result!, SRF(p)) !== undefined;
    const t = (kind: EditTarget["kind"], name: string, add: boolean, title: string) => ({ target: { kind, contract: subject }, name, add, title });
    if (ctx.kind === "construction") {
      return states("constructedAs") ? [t("construction", "Edit construction", false, "Edit the construction this contract states")] : [t("construction", "Add a construction", true, "State the node this contract writes")];
    }
    if (ctx.kind === "join") return states("joinedAs") ? [t("join", "Edit join", false, "Edit the join this contract states")] : [t("join", "Add a join", true, "State what relates an instance to the instance it names")];
    if (!states("expandedAs")) return [t("expansion", "Add an expansion", true, "State the members this contract restates")];
    return [t("expansion", "Edit expansion", false, "Edit the expansion this contract states"), ...(states("constructedAs") ? [t("member", "Edit node for each member", false, "Edit the node made for each member")] : [])];
  }, [graph, subject, studio.baseline.namespace]);
  const choose = (node: Node) => {
    const n = (node.data as BoxData).node;
    setFocused(n.id);
    if (n.kind === "scheme") return n.scheme && boxes(n.scheme)?.state === "ready" && setOpened(n.scheme);
    if (n.kind === "contract") return n.select && studio.open("surface", n.select);
    if (n.edit) return editStatement(n.edit);
    if (n.kind === "target") return n.target?.declared && go("w", id, "baseline", n.target.iri);
    if (n.select) studio.open("surface", n.select);
  };

  const opening = opened && load.state === "ready" ? load.projections.schemes.find((s) => s.contract === opened) : undefined;
  const open = opening ? schemeOf(opening) : undefined;
  const prefixes = useMemo(() => ({ ...PREFIXES, ...baselineGraph?.prefixes, ...graph.prefixes }), [baselineGraph, graph]);
  const placed = [...placement.byElement].flatMap(([element, list]) => list.map((issue) => ({ element, issue })));
  const label = (element: string) => drawn.nodes.find((n) => n.id === element)?.title ?? drawn.edges.find((e) => e.id === element)?.title.split("\n")[0] ?? "";

  if (contracts.length === 0) {
    return (
      <div className="empty" role="region" aria-label="Surface canvas">
        <h3>No contract to draw</h3>
        <p className="small">Add a promotion, an index or a projection contract, and the canvas draws it from its carrier to what it writes.</p>
      </div>
    );
  }

  return (
    <div className="landing onto surface-canvas" role="region" aria-label="Surface canvas">
      <div className="onto-controls">
        <div className="mode-switch" role="group" aria-label="Contracts shown" style={{ margin: 0 }}>
          <button aria-pressed={view === "selected" && picked !== undefined} disabled={picked === undefined} title="The contract selected in the list" onClick={() => setView("selected")}>
            {picked ? contracts.find((c) => c.iri === picked)!.name : "Selected contract"}
          </button>
          <button aria-pressed={view === "all" || picked === undefined} onClick={() => setView("all")}>All contracts</button>
        </div>
        <span className="small muted grow">
          {load.state === "ready" && <>Lowered schemes from the compilation {ago(load.job.finishedAt ?? load.job.submittedAt)}, job <span className="mono">{jobId(load.job.iri).slice(0, 8)}</span>.</>}
          {load.state === "loading" && "Reading the latest compilation."}
          {load.state === "none" && "There is no surface compilation yet, so the lowered schemes are not shown."}
          {load.state === "refused" && "The latest compilation was refused. Its findings are in Build."}
        </span>
        {!editor && !building && statements.map((t) => (
          <button key={t.name} className="btn sm" title={t.title} onClick={() => editStatement(t.target)}>
            {t.add ? <Plus size={13} /> : <Pencil size={13} />} {t.name}
          </button>
        ))}
        {derivation && !editor && !building && (
          <button className="btn sm" title="Edit the expression this derivation states" onClick={() => edit({ contract: derivation.contract, binding: bindingsOf(graph, derivation.contract).find((b) => b.role === "result")?.iri })}>
            <Calculator size={13} /> Edit expression
          </button>
        )}
        <button className="btn sm" disabled={compiling || !graph.size} onClick={() => void compile()}>
          {compiling ? <Spinner size={12} /> : null} Compile
        </button>
      </div>
      {load.state === "error" && <p style={{ color: "var(--bad)" }}>{load.message}</p>}
      {problem && <p style={{ color: "var(--bad)" }}>{problem}</p>}
      {status === "out-of-date" && (
        <p className="landing-note" role="alert">The lowered schemes are out of date. The surface part or the baseline has changed since that compilation. Compile to read them again.</p>
      )}
      {status === "unknown" && (
        <p className="landing-note muted">That compilation was started elsewhere, so the canvas cannot tell whether the configuration has changed since. Compile here to keep track.</p>
      )}
      <div className="landing-body">
        {building ? (
          <PathMode place={building} ontology={ontology} onClose={() => setBuilding(undefined)} />
        ) : editor?.kind === "expression" ? (
          <ExpressionEditor contract={editor.contract} terms={terms} onClose={closeEditor} />
        ) : editor?.kind === "construction" || editor?.kind === "member" ? (
          <ConstructionEditor
            key={`${editor.kind}|${editor.contract}`} contract={editor.contract} member={editor.kind === "member"} ontology={ontology} terms={terms}
            onClose={closeEditor} onBuild={buildFrom} onOpen={(kind) => editStatement({ kind, contract: editor.contract })}
          />
        ) : editor?.kind === "join" ? (
          <JoinEditor key={editor.contract} contract={editor.contract} ontology={ontology} terms={terms} onClose={closeEditor} onBuild={buildFrom} />
        ) : editor?.kind === "expansion" ? (
          <ExpansionEditor key={editor.contract} contract={editor.contract} terms={terms} onClose={closeEditor} onBuild={buildFrom} onOpen={(kind) => editStatement({ kind, contract: editor.contract })} />
        ) : (
          <Canvas
            key={overview ? `all|${expanded ?? ""}` : picked}
            nodes={nodes}
            edges={edges}
            nodeTypes={NODE_TYPES}
            edgeTypes={EDGE_TYPES}
            routing
            options={LAYOUT}
            hints={hints}
            storageKey={`lattice-studio:surface-canvas:${id}:${overview ? `all|${expanded ?? ""}` : picked}`}
            height={expanded ? 900 : shown.length > 1 ? 640 : 440}
            onNodeClick={choose}
            onEdgeClick={chooseEdge}
          />
        )}
        {(placed.length > 0 || stillInList.length > 0) && (
          <aside className="surface-findings" aria-label="Findings on the canvas">
            <ul>
              {placed.map(({ element, issue }, i) => (
                <li key={i} className="row small"><SeverityIcon severity={issue.severity} size={13} /> <strong>{label(element)}</strong> {issue.message}{issue.path && <span className="muted"> ({compact(issue.path)})</span>}</li>
              ))}
            </ul>
            {stillInList.length > 0 && <p className="small muted">{stillInList.length === 1 ? "One more finding is" : `${stillInList.length} more findings are`} in the form's list, since the canvas has no element for {stillInList.length === 1 ? "it" : "them"}.</p>}
          </aside>
        )}
      </div>
      {opening && open && (
        <Modal title={`Lowered scheme ${open.scheme.label}`} subtitle={opening.lowered ? "Read only. This is the scheme the latest compilation lowered the contract to, with the review findings of its compiled form on the mappings they concern." : "Read only. The compilation held no lowered scheme, so these are the mappings as its compiled form records them, by name."} onClose={() => setOpened(undefined)} wide>
          <div role="region" aria-label="Lowered scheme">
            <MappingCanvas workspace={id} scheme={open.scheme} prefixes={prefixes} open={() => undefined} readOnly describe={open.describe} annotate={open.annotate} />
          </div>
        </Modal>
      )}
    </div>
  );
}
