// SPDX-License-Identifier: MPL-2.0
// The canvas kit, what every canvas of the studio shares. A canvas gives its nodes, its edges and what each does, and the kit
// draws them with React Flow, lays out the nodes it has no position for, keeps the author's positions in this browser and offers
// a right-click menu. A canvas's picture is a function of its nodes and edges and the author's stored positions, the layout is
// one function that another can replace (layout.ts), and a position never enters a graph. A canvas may also have its edges routed
// and their labels placed (edges.ts), from the nodes where they are now.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  BaseEdge,
  Controls,
  EdgeLabelRenderer,
  ReactFlow,
  applyNodeChanges,
  getBezierPath,
  type Connection,
  type Edge,
  type EdgeProps,
  type EdgeTypes,
  type Node,
  type NodeChange,
  type NodeTypes,
  type Viewport,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { DEFAULT_NODE_SIZE, routeEdges, type EdgeRoute, type RouteOptions } from "./edges";
import { layered, type Layout, type LayoutNode, type LayoutOptions } from "./layout";
import { clearPositions, readPositions, resolvePositions, writePositions, type Point, type Positions } from "./positions";

export type { Layout, LayoutEdge, LayoutNode, LayoutOptions } from "./layout";
export type { Point, Positions } from "./positions";
export { DEFAULT_NODE_SIZE, DEFAULT_ROUTE_OPTIONS, LABEL_CANDIDATES, chooseSides, curvePoint, routeEdges } from "./edges";
export type { Box, EdgeRoute, RouteEdge, RouteOptions, Side } from "./edges";

export interface MenuItem {
  label: string;
  run: () => void;
  danger?: boolean;
}

export interface Menu {
  x: number;
  y: number;
  items: MenuItem[];
}

/** A menu opened by a right click, closed by a click anywhere or by choosing an item. */
export function ContextMenu({ menu, close }: { menu: Menu; close: () => void }) {
  return (
    <div className="menu" role="menu" style={{ position: "fixed", left: menu.x, top: menu.y }} onClick={(e) => e.stopPropagation()}>
      {menu.items.map((item) => (
        <button key={item.label} role="menuitem" style={item.danger ? { color: "var(--bad)" } : undefined} onClick={() => (close(), item.run())}>
          {item.label}
        </button>
      ))}
    </div>
  );
}

/**
 * The route of every edge, from the nodes where they are now, so while a node is dragged its edges and their labels follow it. A node
 * is as large as React Flow measured it, or else as large as `DEFAULT_NODE_SIZE`. An edge's label is its `data.label` where that is
 * a string. Nothing is routed where `options` is not given.
 */
export function useEdgeRoutes(nodes: readonly Node[], edges: readonly Edge[], options?: Partial<RouteOptions>): Map<string, EdgeRoute> {
  const on = options !== undefined;
  const { direction, labelCharWidth, labelHeight, labelPadding } = options ?? {};
  return useMemo(() => {
    if (!on) return new Map();
    const boxes = new Map(
      nodes.map((n) => [n.id, { x: n.position.x, y: n.position.y, width: n.measured?.width ?? n.width ?? DEFAULT_NODE_SIZE.width, height: n.measured?.height ?? n.height ?? DEFAULT_NODE_SIZE.height }]),
    );
    const routed = routeEdges(
      boxes,
      edges.map((e) => ({ id: e.id, source: e.source, target: e.target, label: typeof e.data?.label === "string" ? e.data.label : undefined })),
      { direction, labelCharWidth, labelHeight, labelPadding },
    );
    return new Map(routed.map((r) => [r.id, r]));
  }, [on, nodes, edges, direction, labelCharWidth, labelHeight, labelPadding]);
}

export type RoutedEdgeData = {
  /** Set by a canvas given `routing`. An edge with none is drawn as React Flow draws a Bezier edge. */
  route?: EdgeRoute;
  label?: string;
  /** Names the edge for a screen reader and a pointer, as its title. */
  title: string;
  dashed?: boolean;
  /** The class of the edge's group, and of its label, which takes " dashed" when the edge is. */
  className?: string;
  labelClass?: string;
};

/**
 * An edge that draws the path the kit routed and puts its label, in HTML, where the kit placed it. It draws from the node boxes
 * and ignores where React Flow would attach it, so a node still needs a handle for React Flow to accept the edge and the handle can
 * be hidden. Give it in `edgeTypes` and give the canvas `routing`.
 */
export function RoutedEdge(props: EdgeProps<Edge<RoutedEdgeData>>) {
  const data = props.data!;
  const [fallback, fx, fy] = getBezierPath(props);
  const path = data.route?.path ?? fallback;
  const box = data.route?.label;
  const x = box ? box.x + box.width / 2 : fx;
  const y = box ? box.y + box.height / 2 : fy;
  const labelClass = data.labelClass ?? "canvas-edge-label";
  return (
    <g className={data.className}>
      <title>{data.title}</title>
      <BaseEdge id={props.id} path={path} markerStart={props.markerStart} markerEnd={props.markerEnd} style={props.style} interactionWidth={14} />
      {data.label && (
        <EdgeLabelRenderer>
          <div className={data.dashed ? `${labelClass} dashed` : labelClass} title={data.title} style={{ transform: `translate(-50%, -50%) translate(${x}px, ${y}px)` }}>
            {data.label}
          </div>
        </EdgeLabelRenderer>
      )}
    </g>
  );
}

export const DEFAULT_LAYOUT_OPTIONS: LayoutOptions = { direction: "LR", columnGap: 280, rowGap: 64 };

/** What a node tells the layout besides its id. A node with no entry is left to the layout. */
export type LayoutHints = Record<string, Omit<LayoutNode, "id">>;

export interface CanvasProps {
  /** Their positions are the kit's to set, so give any. Memoise the array, since the kit lays out again when it changes. */
  nodes: Node[];
  /** Memoised like the nodes. */
  edges: Edge[];
  /** A constant, since React Flow redraws every node when it changes. */
  nodeTypes: NodeTypes;
  /** A constant like the node types. A canvas that draws its own edges gives them here. */
  edgeTypes?: EdgeTypes;
  /** Routes the edges and places their labels from the nodes' places now, and gives each edge its route as `data.route`. */
  routing?: true | Partial<Omit<RouteOptions, "direction">>;
  hints?: LayoutHints;
  layout?: Layout;
  options?: LayoutOptions;
  /** Where the layout puts nodes, changed afterwards. Memoise it. The author's positions are not changed by it. */
  afterLayout?: (positions: Map<string, Point>) => Map<string, Point>;
  /** The key the author's positions are kept under in this browser. */
  storageKey: string;
  height: number;
  /** Where the view opens on a graph too large to fit it. */
  defaultViewport?: Viewport;
  /** A graph of this many nodes or fewer fits the view. */
  fitViewUpTo?: number;
  onConnect?: (connection: Connection) => void;
  onNodeClick?: (node: Node) => void;
  /** A menu provider returns nothing where there is no menu. A right click is still taken from the browser. */
  nodeMenu?: (node: Node) => MenuItem[] | undefined;
  edgeMenu?: (edge: Edge) => MenuItem[] | undefined;
  paneMenu?: (context: { layOutAgain: () => void }) => MenuItem[] | undefined;
}

export function Canvas(props: CanvasProps) {
  const { nodes: given, edges, storageKey, layout = layered, options = DEFAULT_LAYOUT_OPTIONS, hints, afterLayout } = props;
  const [stored, setStored] = useState<{ key: string; positions: Positions }>(() => ({ key: storageKey, positions: readPositions(storageKey) }));
  // A canvas that is given another key, such as another scheme, reads the positions kept under it.
  const saved = stored.key === storageKey ? stored.positions : readPositions(storageKey);
  if (stored.key !== storageKey) setStored({ key: storageKey, positions: saved });
  const setSaved = (positions: Positions) => setStored({ key: storageKey, positions });
  const [menu, setMenu] = useState<Menu>();

  // The layout depends on the nodes' ids and hints and on the edges, and a new array with the same content does not lay out again.
  const shape = useMemo(
    () => JSON.stringify([given.map((n) => [n.id, hints?.[n.id] ?? null]), edges.map((e) => [e.source, e.target])]),
    [given, edges, hints],
  );
  const { direction, columnGap, rowGap } = options;
  const computed = useMemo(() => {
    const [ns, es] = JSON.parse(shape) as [[string, Omit<LayoutNode, "id"> | null][], [string, string][]];
    const laidOut = layout(ns.map(([id, h]) => ({ id, ...h })), es.map(([source, target]) => ({ source, target })), { direction, columnGap, rowGap });
    return afterLayout ? afterLayout(laidOut) : laidOut;
  }, [shape, layout, direction, columnGap, rowGap, afterLayout]);

  const ids = useMemo(() => given.map((n) => n.id), [given]);
  const laid = useMemo<Node[]>(() => {
    const at = resolvePositions(ids, computed, saved);
    return given.map((n) => ({ ...n, position: at.get(n.id)! }));
  }, [given, ids, computed, saved]);
  const [nodes, setNodes] = useState<Node[]>(laid);
  // An edit keeps every node where it is, so a link dropped where a node was still lands on it. Only a new node is laid out.
  const relayout = useRef(false);
  useEffect(() => {
    const again = relayout.current;
    relayout.current = false;
    setNodes((prev) => {
      const at = resolvePositions(ids, computed, saved, again ? undefined : new Map(prev.map((n) => [n.id, n.position])));
      return laid.map((n) => ({ ...n, position: at.get(n.id)! }));
    });
  }, [laid]); // eslint-disable-line react-hooks/exhaustive-deps

  const routes = useEdgeRoutes(nodes, edges, props.routing ? { ...(props.routing === true ? {} : props.routing), direction: options.direction } : undefined);
  const shown = useMemo(() => (props.routing ? edges.map((e) => ({ ...e, data: { ...e.data, route: routes.get(e.id) } })) : edges), [edges, routes, props.routing]);

  const keep = useCallback((next: Node[]) => {
    const positions: Positions = Object.fromEntries(next.map((n) => [n.id, n.position]));
    setStored({ key: storageKey, positions });
    writePositions(storageKey, positions);
  }, [storageKey]);

  const layOutAgain = () => {
    relayout.current = true;
    clearPositions(storageKey);
    setSaved({});
  };

  const open = (event: Pick<MouseEvent, "preventDefault" | "clientX" | "clientY">, items: MenuItem[] | undefined) => {
    event.preventDefault();
    if (items?.length) setMenu({ x: event.clientX, y: event.clientY, items });
  };

  return (
    <div style={{ height: props.height, position: "relative" }} onClick={() => setMenu(undefined)}>
      <ReactFlow
        nodes={nodes}
        edges={shown}
        nodeTypes={props.nodeTypes}
        edgeTypes={props.edgeTypes}
        onNodesChange={(changes: NodeChange[]) => setNodes((ns) => applyNodeChanges(changes, ns))}
        onNodeDragStop={() => setNodes((ns) => (keep(ns), ns))}
        onConnect={props.onConnect}
        onNodeClick={props.onNodeClick && ((_, n) => props.onNodeClick!(n))}
        onNodeContextMenu={(event, node) => open(event, props.nodeMenu?.(node))}
        onEdgeContextMenu={(event, edge) => open(event, props.edgeMenu?.(edge))}
        onPaneContextMenu={(event) => open(event, props.paneMenu?.({ layOutAgain }))}
        deleteKeyCode={null}
        // A small graph fits the view, and a large one opens readable at its top left.
        fitView={laid.length <= (props.fitViewUpTo ?? 30)}
        defaultViewport={props.defaultViewport ?? { x: 16, y: 16, zoom: 0.85 }}
        minZoom={0.2}
        proOptions={{ hideAttribution: true }}
      >
        <Background />
        <Controls showInteractive={false} />
      </ReactFlow>
      {menu && <ContextMenu menu={menu} close={() => setMenu(undefined)} />}
    </div>
  );
}
