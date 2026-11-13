// SPDX-License-Identifier: MPL-2.0
// The ontology drawn on the canvas kit (SVA-O2), read only. One view draws the classes with an edge for each object property
// between them, and another draws the class hierarchy. Both are derived in the browser from the baseline graph and never stored,
// and the author's positions are kept in this browser by the kit, never in a graph. A class selected in the baseline limits the
// drawing to its neighbourhood, and clicking a class selects it there by the route the axiom forms use. A whole ontology of
// many classes is drawn only when the author asks for it, so the page never stops by surprise.

import { useMemo, useState } from "react";
import { Handle, MarkerType, Position, type Edge, type Node, type NodeProps } from "@xyflow/react";
import { PREFIXES, compact } from "@lattice/authoring-domain";
import { Canvas, RoutedEdge, type LayoutOptions, type RoutedEdgeData } from "../canvas/kit";
import type { Baseline } from "../rdf/baseline";
import { DEFAULT_HOPS, classGraph, counts, hierarchyGraph, type ClassEdge, type ClassGraph, type HierarchyGraph } from "../rdf/ontologyGraph";
import { go } from "./kit";

/** More classes than this are drawn only when the author asks. */
export const DRAW_AT_ONCE = 150;

type View = "classes" | "hierarchy";
type Hops = "1" | "2" | "3" | "all";

export const LAYOUTS: Record<View, LayoutOptions> = {
  classes: { direction: "LR", columnGap: 420, rowGap: 84 },
  hierarchy: { direction: "TB", columnGap: 110, rowGap: 280 },
};

type ClassData = { label: string; short: string; selected: boolean; direction: "LR" | "TB" };

function ClassBox({ data }: NodeProps<Node<ClassData>>) {
  const lr = data.direction === "LR";
  return (
    <div className="canvas-node" style={{ borderColor: data.selected ? "var(--accent)" : undefined }} title={data.short}>
      <Handle type="target" position={lr ? Position.Left : Position.Top} />
      <strong className="ellipsis" style={{ display: "block" }}>{data.label}</strong>
      <div className="small muted mono canvas-terms">{data.short}</div>
      <Handle type="source" position={lr ? Position.Right : Position.Bottom} />
    </div>
  );
}

/** The edge classes the stylesheet knows, around what an edge says. */
const ROUTED = (data: RoutedEdgeData): RoutedEdgeData => ({ ...data, className: "onto-edge", labelClass: "onto-edge-label" });

const NODE_TYPES = { cls: ClassBox };
const EDGE_TYPES = { link: RoutedEdge };

export function OntologyCanvas({ workspace, baseline, selected }: { workspace: string; baseline: Baseline; selected?: string }) {
  const [view, setView] = useState<View>("classes");
  const [shapes, setShapes] = useState(false);
  const [hops, setHops] = useState<Hops>("2");
  const [whole, setWhole] = useState(false);
  const focus = selected && baseline.classes.has(selected) ? selected : undefined;
  const prefixes = useMemo(() => ({ ...PREFIXES, ...baseline.graph.prefixes }), [baseline]);
  const label = (iri: string) => baseline.classes.get(iri)?.label ?? compact(iri, prefixes);

  const reach = hops === "all" ? Infinity : Number(hops);
  const drawn = useMemo<ClassGraph | HierarchyGraph>(() => {
    const options = { focus, hops: focus ? reach : DEFAULT_HOPS, shapes: view === "classes" && shapes };
    return view === "classes" ? classGraph(baseline.graph, options) : hierarchyGraph(baseline.graph, options);
  }, [baseline, view, shapes, focus, reach]);
  const held = counts(drawn);
  // Nothing is drawn of a large ontology until the author asks, unless a class limits it to its neighbourhood.
  const deferred = !focus && !whole && baseline.classes.size > DRAW_AT_ONCE;

  const nodes = useMemo<Node[]>(
    () => (deferred ? [] : drawn.nodes.map((n) => ({ id: n.iri, type: "cls", position: { x: 0, y: 0 }, data: { label: n.label, short: compact(n.iri, prefixes), selected: n.iri === focus, direction: LAYOUTS[view].direction } }))),
    [drawn, deferred, prefixes, focus, view],
  );
  const edges = useMemo<Edge[]>(() => {
    if (deferred) return [];
    if (view === "hierarchy") {
      // The layout puts a superclass above its subclasses, so the edge runs down and its arrow points back up at the superclass.
      return (drawn as HierarchyGraph).edges.map((e) => ({
        id: e.id, source: e.target, target: e.source, type: "link", markerStart: { type: MarkerType.ArrowClosed, width: 18, height: 18 },
        style: { stroke: "var(--accent)", strokeWidth: 1.6 }, data: ROUTED({ title: `${label(e.source)} is a subclass of ${label(e.target)}` }),
      }));
    }
    return (drawn as ClassGraph).edges.map((e: ClassEdge) => {
      const property = compact(e.property, prefixes);
      const stated = e.shapes?.map((s) => compact(s, prefixes)).join(", ");
      const title = `${property}, from ${label(e.source)} to ${label(e.target)}${e.byShape ? `, stated by ${stated || "a shape"}` : ""}`;
      return {
        id: e.id, source: e.source, target: e.target, type: "link", markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18 },
        style: e.origin === "shape" ? { strokeDasharray: "6 4" } : undefined, data: ROUTED({ label: property, title, dashed: e.origin === "shape" }),
      };
    });
  }, [drawn, deferred, view, prefixes]); // eslint-disable-line react-hooks/exhaustive-deps

  const storageKey = `lattice-studio:ontology-canvas:${workspace}:${view}:${focus ? "focus" : "all"}`;
  const summary = `${held.classes} ${held.classes === 1 ? "class" : "classes"} and ${held.links} ${held.links === 1 ? "link" : "links"}${view === "classes" && shapes ? `, ${held.byShape} stated by shapes` : ""}`;

  return (
    <div className="onto" role="region" aria-label="Ontology diagram">
      <div className="onto-controls">
        <div className="mode-switch" role="group" aria-label="Ontology view" style={{ margin: 0 }}>
          <button aria-pressed={view === "classes"} onClick={() => setView("classes")}>Classes and properties</button>
          <button aria-pressed={view === "hierarchy"} onClick={() => setView("hierarchy")}>Class hierarchy</button>
        </div>
        {view === "classes" && (
          <label className="row small" style={{ gap: 6 }}>
            <input type="checkbox" checked={shapes} onChange={(e) => setShapes(e.target.checked)} /> Include shapes
          </label>
        )}
        <label className="row small" style={{ gap: 6 }}>
          Hops
          <select className="select" aria-label="Hops around the selected class" value={hops} disabled={!focus} onChange={(e) => setHops(e.target.value as Hops)}>
            <option value="1">1</option>
            <option value="2">2</option>
            <option value="3">3</option>
            <option value="all">All</option>
          </select>
        </label>
        <span className="small muted grow" role="status">
          {deferred ? `The ontology holds ${held.classes} classes and ${held.links} links.` : `${summary} drawn${focus ? `, around ${label(focus)}` : ""}.`}
        </span>
      </div>
      {deferred ? (
        <div className="empty">
          <p>That is a lot to draw at once. Pick a class to draw its neighbourhood, or draw them all.</p>
          <button className="btn" onClick={() => setWhole(true)}>Draw the whole ontology</button>
        </div>
      ) : nodes.length === 0 ? (
        <div className="empty"><p>The baseline declares no class to draw.</p></div>
      ) : (
        <>
          {view === "classes" && <p className="small muted" style={{ margin: "6px 0" }}>An arrow runs from a property's domain to its range.{shapes && " A dashed arrow is stated only by a shape."}</p>}
          <Canvas
            key={`${view}|${focus ?? ""}|${hops}`}
            nodes={nodes}
            edges={edges}
            nodeTypes={NODE_TYPES}
            edgeTypes={EDGE_TYPES}
            routing
            options={LAYOUTS[view]}
            storageKey={storageKey}
            height={560}
            fitViewUpTo={60}
            onNodeClick={(n) => go("w", workspace, "baseline", n.id)}
          />
        </>
      )}
    </div>
  );
}
