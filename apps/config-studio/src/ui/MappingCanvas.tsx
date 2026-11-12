// SPDX-License-Identifier: MPL-2.0
// Mapping mode's canvas, an editor for a scheme drawn with React Flow: each mapping a node, each source concept a node on the
// left, and links for each mapping's parent, its template and the concept it maps for. Dragging a link from a mapping to a
// mapping makes the first the second's parent, and from a source concept to a mapping says what the mapping maps for. A
// right click offers what fits where it lands. The canvas kit (src/canvas) draws it, lays it out and keeps the author's
// positions in this browser for the scheme, never in the graph, since where a node sits says nothing about what it maps.
// Each mapping's depth and row are its rank and order, and the source concepts are the rank before the first, as they always were.

import { useCallback, useMemo } from "react";
import { Handle, MarkerType, Position, type Connection, type Edge, type Node, type NodeProps } from "@xyflow/react";
import { compact, type Graph } from "@lattice/authoring-domain";
import { Canvas, type LayoutHints, type LayoutOptions, type MenuItem, type Point } from "../canvas/kit";
import { setParent, setSource, unlink, written, type MappingNode, type Scheme } from "../rdf/mapping";

const COLUMN = 280;
const ROW = 64;
const SOURCE_GAP = 40;
const LAYOUT: LayoutOptions = { direction: "LR", columnGap: COLUMN, rowGap: ROW };
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
  const storageKey = `lattice-studio:mapping-canvas:${props.workspace}:${scheme.iri}`;

  const nodes = useMemo<Node[]>(() => {
    const at = { x: 0, y: 0 };
    const sources: Node[] = scheme.sources.map((s) => ({
      id: s.iri, type: "source", position: at, data: { label: s.label, path: s.path ?? s.representedAs.map((r) => compact(r, prefixes)).join(", ") },
    }));
    const mappings: Node[] = scheme.mappings.map((m) => ({
      id: m.iri, type: "mapping", position: at,
      data: { mapping: m, terms: written(m, prefixes).map((w) => `${w.box} ${w.term}`).join("  "), selected: m.iri === selected, count: props.counts?.(m.iri) },
    }));
    return [...sources, ...mappings];
  }, [scheme, prefixes, selected, props.counts]); // eslint-disable-line react-hooks/exhaustive-deps

  // The source concepts are the rank before the first, in the order the scheme lists them, and a mapping's rank is its depth and its order its row.
  const hints = useMemo<LayoutHints>(() => ({
    ...Object.fromEntries(scheme.sources.map((s, n) => [s.iri, { rank: -1, order: n }])),
    ...Object.fromEntries(scheme.mappings.map((m) => [m.iri, { rank: m.depth, order: m.row }])),
  }), [scheme]);
  // A source concept sits a little further left than a column, which leaves room for its links.
  const sourceIris = useMemo(() => new Set(scheme.sources.map((s) => s.iri)), [scheme]);
  const afterLayout = useCallback((positions: Map<string, Point>) => new Map([...positions].map(([id, p]) => [id, sourceIris.has(id) ? { x: p.x - SOURCE_GAP, y: p.y } : p])), [sourceIris]);

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

  const nodeMenu = (node: Node): MenuItem[] | undefined => {
    if (node.type !== "mapping") return;
    const m = (node.data as MappingData).mapping;
    return [
      { label: "Open in the editor", run: () => props.open(m.iri) },
      { label: "Add a child datum", run: () => props.add("Datum", m.iri) },
      { label: "Add a child data mapping", run: () => props.add("DataMapping", m.iri) },
      ...(m.parent ? [{ label: "Detach from its parent", run: () => removeLink({ id: `parent|${m.iri}`, source: m.parent!, target: m.iri }) }] : []),
      {
        label: "Delete the mapping", danger: true,
        run: () => window.confirm(`Delete ${m.label}? Links to it are removed too. You can undo this.`) && props.edit((g) => g.edit((e) => e.remove(m.iri))),
      },
    ];
  };

  return (
    <Canvas
      nodes={nodes}
      edges={edges}
      nodeTypes={NODE_TYPES}
      hints={hints}
      options={LAYOUT}
      afterLayout={afterLayout}
      storageKey={storageKey}
      height={Math.max(420, Math.min(900, (scheme.mappings.length + 2) * 28))}
      defaultViewport={{ x: COLUMN + 60, y: 16, zoom: 0.85 }}
      onConnect={connect}
      onNodeClick={(n) => n.type === "mapping" && props.open(n.id)}
      nodeMenu={nodeMenu}
      edgeMenu={(edge) => [{ label: `Remove the ${edge.id.split("|")[0]} link`, run: () => removeLink(edge), danger: true }]}
      paneMenu={({ layOutAgain }) => [
        { label: "Add a root datum", run: () => props.add("Datum") },
        { label: "Lay the scheme out again", run: layOutAgain },
      ]}
    />
  );
}
