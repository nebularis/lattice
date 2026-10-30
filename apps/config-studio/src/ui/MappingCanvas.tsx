// SPDX-License-Identifier: MPL-2.0
// Mapping mode's canvas, an editor for a scheme drawn with React Flow: each mapping a node, each source concept a node on the
// left, and links for each mapping's parent, its template and the concept it maps for. Dragging a link from a mapping to a
// mapping makes the first the second's parent, and from a source concept to a mapping says what the mapping maps for. A
// right click offers what fits where it lands. Positions are the author's, kept in this browser for the scheme, and never in
// the graph, since where a node sits on a canvas says nothing about what it maps.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  applyNodeChanges,
  type Connection,
  type Edge,
  type Node,
  type NodeChange,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { compact, type Graph } from "@lattice/authoring-domain";
import { setParent, setSource, unlink, written, type MappingNode, type Scheme } from "../rdf/mapping";

const COLUMN = 280;
const ROW = 64;
const DECISION: Record<string, string> = { Accepted: "var(--ok)", Corrected: "var(--warn)", Rejected: "var(--bad)", Deferred: "var(--text-3)" };

type MappingData = { mapping: MappingNode; terms: string; selected: boolean; count?: number };
type SourceData = { label: string; path: string };

function MappingBox({ data }: NodeProps<Node<MappingData>>) {
  const m = data.mapping;
  return (
    <div className="canvas-node" style={{ borderColor: data.selected ? "var(--accent)" : undefined, borderStyle: m.isTemplate ? "dashed" : undefined }}>
      <Handle type="target" position={Position.Left} />
      {m.review && <span className="canvas-review" style={{ background: DECISION[m.review.decision] }} title={m.review.decision} />}
      <div className="row" style={{ gap: 6 }}>
        <strong className="grow" style={{ fontWeight: m.kind === "Datum" ? 650 : 500 }}>{m.label}</strong>
        {data.count !== undefined && <span className="small" style={{ color: data.count ? "var(--accent)" : "var(--text-3)" }}>{data.count}</span>}
      </div>
      <div className="small muted canvas-terms">{data.terms || (m.template ? "through its template" : "writes nothing")}</div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

function SourceBox({ data }: NodeProps<Node<SourceData>>) {
  return (
    <div className="canvas-node canvas-source">
      <strong>{data.label}</strong>
      <div className="small muted mono canvas-terms">{data.path}</div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const NODE_TYPES = { mapping: MappingBox, source: SourceBox };

interface Menu {
  x: number;
  y: number;
  items: { label: string; run: () => void; danger?: boolean }[];
}

export function MappingCanvas(props: {
  workspace: string;
  scheme: Scheme;
  graph: Graph;
  prefixes: Record<string, string>;
  selected?: string;
  open: (node: string) => void;
  add: (type: "Datum" | "DataMapping", parent?: string) => void;
  edit: (change: (g: Graph) => Graph) => void;
  counts?: (mapping: string) => number | undefined;
}) {
  const { scheme, prefixes, selected } = props;
  const key = `lattice-studio:mapping-canvas:${props.workspace}:${scheme.iri}`;
  const [saved, setSaved] = useState<Record<string, { x: number; y: number }>>(() => {
    try {
      return JSON.parse(localStorage.getItem(key) ?? "{}");
    } catch {
      return {};
    }
  });
  const [menu, setMenu] = useState<Menu>();

  const laid = useMemo<Node[]>(() => {
    const at = (id: string, x: number, y: number) => saved[id] ?? { x, y };
    const sources: Node[] = scheme.sources.map((s, n) => ({
      id: s.iri, type: "source", position: at(s.iri, -COLUMN - 40, n * ROW), data: { label: s.label, path: s.path ?? s.representedAs.map((r) => compact(r, prefixes)).join(", ") },
    }));
    const mappings: Node[] = scheme.mappings.map((m) => ({
      id: m.iri, type: "mapping", position: at(m.iri, m.depth * COLUMN, m.row * ROW),
      data: { mapping: m, terms: written(m, prefixes).map((w) => `${w.box} ${w.term}`).join("  "), selected: m.iri === selected, count: props.counts?.(m.iri) },
    }));
    return [...sources, ...mappings];
  }, [scheme, prefixes, selected, saved, props.counts]); // eslint-disable-line react-hooks/exhaustive-deps
  const [nodes, setNodes] = useState<Node[]>(laid);
  // An edit keeps every node where it is, so a link dropped where a node was still lands on it. Only a new node is laid out.
  const relayout = useRef(false);
  useEffect(() => setNodes((prev) => {
    const at = new Map(relayout.current ? [] : prev.map((n) => [n.id, n.position]));
    relayout.current = false;
    return laid.map((n) => ({ ...n, position: at.get(n.id) ?? n.position }));
  }), [laid]);

  const edges = useMemo<Edge[]>(() => {
    const ids = new Set(scheme.mappings.map((m) => m.iri));
    const out: Edge[] = [];
    for (const m of scheme.mappings) {
      if (m.parent && ids.has(m.parent)) out.push({ id: `parent|${m.iri}`, source: m.parent, target: m.iri, markerEnd: { type: MarkerType.ArrowClosed } });
      if (m.template && ids.has(m.template)) out.push({ id: `template|${m.iri}`, source: m.template, target: m.iri, label: "template", style: { strokeDasharray: "5 4" } });
      if (m.source && scheme.sources.some((s) => s.iri === m.source)) out.push({ id: `source|${m.iri}`, source: m.source, target: m.iri, style: { strokeDasharray: "2 3" }, animated: false });
    }
    return out;
  }, [scheme]);

  const keep = useCallback((next: Node[]) => {
    const positions = Object.fromEntries(next.map((n) => [n.id, n.position]));
    setSaved(positions);
    try {
      localStorage.setItem(key, JSON.stringify(positions));
    } catch {
      // A browser that keeps nothing lays the scheme out afresh on the next visit.
    }
  }, [key]);

  /** A link from a mapping makes it the target's parent, and one from a source concept says what the target maps for. */
  const connect = (c: Connection) => {
    if (!c.source || !c.target) return;
    const isSource = scheme.sources.some((s) => s.iri === c.source);
    props.edit((g) => (isSource ? setSource(g, c.target!, c.source!) : setParent(g, c.target!, c.source!) ?? g));
  };

  const removeLink = (edge: Edge) => {
    const [kind, node] = edge.id.split("|") as ["parent" | "template" | "source", string];
    props.edit((g) => unlink(g, kind, node));
  };

  const nodeMenu = (event: React.MouseEvent, node: Node) => {
    event.preventDefault();
    if (node.type !== "mapping") return;
    const m = (node.data as MappingData).mapping;
    setMenu({
      x: event.clientX, y: event.clientY,
      items: [
        { label: "Open in the editor", run: () => props.open(m.iri) },
        { label: "Add a child datum", run: () => props.add("Datum", m.iri) },
        { label: "Add a child data mapping", run: () => props.add("DataMapping", m.iri) },
        ...(m.parent ? [{ label: "Detach from its parent", run: () => removeLink({ id: `parent|${m.iri}`, source: m.parent!, target: m.iri }) }] : []),
        {
          label: "Delete the mapping", danger: true,
          run: () => window.confirm(`Delete ${m.label}? Links to it are removed too. You can undo this.`) && props.edit((g) => g.edit((e) => e.remove(m.iri))),
        },
      ],
    });
  };

  return (
    <div style={{ height: Math.max(420, Math.min(900, (scheme.mappings.length + 2) * 28)), position: "relative" }} onClick={() => setMenu(undefined)}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        onNodesChange={(changes: NodeChange[]) => setNodes((ns) => applyNodeChanges(changes, ns))}
        onNodeDragStop={() => setNodes((ns) => (keep(ns), ns))}
        onConnect={connect}
        onNodeClick={(_, n) => n.type === "mapping" && props.open(n.id)}
        onNodeContextMenu={nodeMenu}
        onEdgeContextMenu={(event, edge) => {
          event.preventDefault();
          setMenu({ x: event.clientX, y: event.clientY, items: [{ label: `Remove the ${edge.id.split("|")[0]} link`, run: () => removeLink(edge), danger: true }] });
        }}
        onPaneContextMenu={(event) => {
          event.preventDefault();
          setMenu({ x: event.clientX, y: event.clientY, items: [
            { label: "Add a root datum", run: () => props.add("Datum") },
            { label: "Lay the scheme out again", run: () => ((relayout.current = true), keep([])) },
          ] });
        }}
        deleteKeyCode={null}
        // A small scheme fits the view, and a large one opens readable at its top left, its source concepts in sight.
        fitView={laid.length <= 30}
        defaultViewport={{ x: COLUMN + 60, y: 16, zoom: 0.85 }}
        minZoom={0.2}
        proOptions={{ hideAttribution: true }}
      >
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
      {menu && (
        <div className="menu" role="menu" style={{ position: "fixed", left: menu.x, top: menu.y }} onClick={(e) => e.stopPropagation()}>
          {menu.items.map((item) => (
            <button key={item.label} role="menuitem" style={item.danger ? { color: "var(--bad)" } : undefined} onClick={() => (setMenu(undefined), item.run())}>
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
