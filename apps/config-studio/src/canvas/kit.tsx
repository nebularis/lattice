// SPDX-License-Identifier: MPL-2.0
// The canvas kit, what every canvas of the studio shares. A canvas gives its nodes, its edges and what each does, and the kit
// draws them with React Flow, lays out the nodes it has no position for, keeps the author's positions in this browser and offers
// a right-click menu. A canvas's picture is a function of its nodes and edges and the author's stored positions, the layout is
// one function that another can replace (layout.ts), and a position never enters a graph.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Background,
  Controls,
  ReactFlow,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeTypes,
  type Node,
  type NodeChange,
  type NodeTypes,
  type Viewport,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { layered, type Layout, type LayoutNode, type LayoutOptions } from "./layout";
import { clearPositions, readPositions, resolvePositions, writePositions, type Point, type Positions } from "./positions";

export type { Layout, LayoutEdge, LayoutNode, LayoutOptions } from "./layout";
export type { Point, Positions } from "./positions";

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
        edges={edges}
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
