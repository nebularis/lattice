// SPDX-License-Identifier: MPL-2.0
// The surface canvas (SVA-S1, part 1). It draws a contract of the surface part, a promotion, an index or a projection of any kind, from the
// carrier class to what is read from it to what is written, in one grammar for every kind (SVA-Q59). It is drawn from the configuration as the
// author states it, so an edit in the form shows at once, and the browser never computes what a contract lowers to (SVA-Q58 (a)). The targets a
// contract writes are drawn as types from the ontology the workspace holds (SVA-Q62), and a small box for each projection reads the lowered
// scheme from the latest finished surface compilation, marked out of date when the surface part or the baseline has changed since. A finding the
// form shows is drawn on the element it concerns (SVA-Q61). The canvas edits nothing. Selecting a node selects the matching node in the form.

import { useEffect, useMemo, useState } from "react";
import { Handle, MarkerType, Position, type Edge, type Node, type NodeProps } from "@xyflow/react";
import { Graph, compact } from "@lattice/authoring-domain";
import { api, awaitJob, jobId } from "../api";
import { Canvas, RoutedEdge, type LayoutHints, type LayoutOptions, type RoutedEdgeData } from "../canvas/kit";
import { concerns } from "../rdf/editors";
import type { Issue } from "../rdf/report";
import { fingerprint, readCompiled as readSent, writeCompiled } from "../persistence/landing";
import { noteCompiled, useCompilationEpoch } from "../persistence/compilation";
import { readSurface, type SurfaceLoad } from "../surface/compilation";
import { contractOf, contractsOf, drawContracts, type DrawEdge, type DrawNode } from "../surface/drawing";
import { placeFindings, worst } from "../surface/findings";
import { boxesFor, schemeOf, staleMark } from "../surface/scheme";
import { ontologyOf, termsOf } from "../surface/terms";
import { MappingCanvas } from "./MappingCanvas";
import { Modal, SeverityIcon, Spinner, ago, go } from "./kit";
import { useStudio } from "./Workspace";
import { PARTS } from "../state";

/** Left to right, the carrier, what is read, what is written and the lowered scheme. Each gap leaves room for an edge's label. */
const LAYOUT: LayoutOptions = { direction: "LR", columnGap: 130, rowGap: 30 };
const EDGE_TYPES = { link: RoutedEdge };

type BoxData = { node: DrawNode; issues: Issue[]; selected: boolean; stale: boolean };

const WIDTH = 224;
/** The size the layout reserves, counting the rows a long line wraps to. */
const sizeOf = (n: DrawNode) => {
  const width = n.kind === "statement" || n.kind === "entries" ? 252 : WIDTH;
  const rows = n.lines.reduce((sum, l) => sum + Math.max(1, Math.ceil(l.length / (width / 6.3))), 0) + Math.max(0, Math.ceil(n.title.length / (width / 7.5)) - 1);
  return { width, height: 46 + 17 * rows };
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
  const issues = model.issues.surface;
  const contracts = useMemo(() => contractsOf(graph), [graph]);
  const picked = selected ? contractOf(graph, selected, contracts) : undefined;
  const [view, setView] = useState<"selected" | "all">("selected");
  const [focused, setFocused] = useState<string>();
  const [opened, setOpened] = useState<string>();
  const [load, setLoad] = useState<SurfaceLoad>({ state: "loading" });
  const [reload, setReload] = useState(0);
  const compiledElsewhere = useCompilationEpoch();
  const [compiling, setCompiling] = useState(false);
  const [problem, setProblem] = useState<string>();

  // The ontology is the baseline and the imports and dependencies the workspace holds, as the ontology view reads it.
  const baselineGraph = model.state.baseline?.graph;
  const terms = useMemo(
    () => termsOf(ontologyOf(baselineGraph ?? Graph.empty(), [...Object.values(model.heldGraphs), ...Object.values(model.dependencyGraphs)])),
    [baselineGraph, model.heldGraphs, model.dependencyGraphs],
  );

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

  const shown = view === "all" || !picked ? contracts.map((c) => c.iri) : [picked];
  const boxes = useMemo(
    () => (load.state === "ready" ? boxesFor(load.projections, status ?? "unknown") : boxesFor(load.state === "refused" ? "refused" : "none", "unknown")),
    [load, status],
  );
  const drawn = useMemo(() => drawContracts(graph, shown, terms, boxes), [graph, shown.join("|"), terms, boxes]); // eslint-disable-line react-hooks/exhaustive-deps
  const placement = useMemo(() => placeFindings(drawn, issues), [drawn, issues]);
  const stillInList = useMemo(() => placement.unplaced.filter((i) => shown.some((c) => concerns(graph, c, i))), [placement, graph, shown.join("|")]); // eslint-disable-line react-hooks/exhaustive-deps

  const nodes = useMemo<Node[]>(
    () => drawn.nodes.map((n) => ({
      id: n.id, type: "box", position: { x: 0, y: 0 },
      data: { node: n, issues: placement.byElement.get(n.id) ?? [], selected: n.id === focused || (n.select !== undefined && n.select === selected && n.kind !== "class"), stale: n.kind === "scheme" && boxes(n.scheme!)?.stale === true } satisfies BoxData,
    })),
    [drawn, placement, focused, selected, boxes],
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
        },
      };
    }),
    [drawn, placement],
  );
  const hints = useMemo<LayoutHints>(() => Object.fromEntries(drawn.nodes.map((n) => [n.id, { ...sizeOf(n), rank: n.rank }])), [drawn]);

  const choose = (node: Node) => {
    const n = (node.data as BoxData).node;
    setFocused(n.id);
    if (n.kind === "scheme") return n.scheme && boxes(n.scheme)?.state === "ready" && setOpened(n.scheme);
    if (n.kind === "target") return n.target?.declared && go("w", id, "baseline", n.target.iri);
    if (n.select) studio.open("surface", n.select);
  };

  const opening = opened && load.state === "ready" ? load.projections.schemes.find((s) => s.contract === opened) : undefined;
  const open = opening ? schemeOf(opening) : undefined;
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
        <Canvas
          key={view === "all" || !picked ? "all" : picked}
          nodes={nodes}
          edges={edges}
          nodeTypes={NODE_TYPES}
          edgeTypes={EDGE_TYPES}
          routing
          options={LAYOUT}
          hints={hints}
          storageKey={`lattice-studio:surface-canvas:${id}:${view === "all" || !picked ? "all" : picked}`}
          height={shown.length > 1 ? 900 : 440}
          onNodeClick={choose}
        />
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
        <Modal title={`Lowered scheme ${open.scheme.label}`} subtitle="Read only. This is the scheme the latest compilation made from the contract, as its compiled form records it." onClose={() => setOpened(undefined)} wide>
          <div role="region" aria-label="Lowered scheme">
            <MappingCanvas workspace={id} scheme={open.scheme} prefixes={{}} open={() => undefined} readOnly describe={open.describe} />
          </div>
        </Modal>
      )}
    </div>
  );
}
