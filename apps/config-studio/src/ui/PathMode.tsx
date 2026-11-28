// SPDX-License-Identifier: MPL-2.0
// Path mode of the surface canvas (SVA-S1 part 2, SVA-Q60 (a)). It builds a read path, a binding's property or an expansion's members path by clicking
// along the properties the ontology declares. The canvas shows the class at the end of the path so far with the properties a next hop may be, the
// outgoing ones to its right for a forward hop and the incoming ones to its left for an inverse hop, so the direction is plain, and a click on one
// adds the hop and moves to the class it reaches. A datatype property ends the path. Each click edits the surface part by the writer the form's
// hop-by-hop control uses (`writePath` for a read path), so the form and the canvas read one graph and neither keeps a path of its own. The class graph
// is the ontology view's, read through `Baseline`. Leaving keeps what was written.

import { useMemo, useState } from "react";
import { Handle, MarkerType, Position, type Edge, type Node, type NodeProps } from "@xyflow/react";
import { compact, localName, type Graph } from "@lattice/authoring-domain";
import { Check, Replace, Undo2 } from "lucide-react";
import { Canvas, RoutedEdge, type LayoutHints, type LayoutOptions, type RoutedEdgeData } from "../canvas/kit";
import type { Baseline } from "../rdf/baseline";
import type { PathPlace } from "../surface/drawing";
import type { Closure } from "../surface/paths";
import { addHop, optionsAt, reachedAfter, readPlace, replaceNamedSource, setClosure, undoHop, type PathOption } from "../surface/pathmode";
import { useStudio } from "./Workspace";

/** Incoming properties on the left, the class reached in the middle and outgoing properties on the right. */
const LAYOUT: LayoutOptions = { direction: "LR", columnGap: 120, rowGap: 12 };
const EDGE_TYPES = { link: RoutedEdge };
const SIZE = { width: 232, height: 76 };
/** More properties than this each way are drawn only where the author asks, so a class with many leaves the canvas readable. */
const LIMIT = 12;

type Data = { option?: PathOption; title: string; lines: string[]; current: boolean; given?: boolean };

function Box({ data }: NodeProps<Node<Data>>) {
  const o = data.option;
  return (
    <div
      className={`canvas-node surface-node path-option${o ? ` ${o.inverse ? "inverse" : "forward"}` : " reached"}${o?.group === "any" ? " any" : ""}${data.current ? " current" : ""}${data.given ? " given" : ""}`}
      data-direction={o ? (o.inverse ? "inverse" : "forward") : "class"}
      data-property={o?.property}
      data-title={data.title}
      title={o ? `Takes ${o.label} ${o.inverse ? "inversely" : "forward"}` : undefined}
      style={{ width: SIZE.width }}
    >
      <Handle type="target" position={Position.Left} />
      <div className="surface-tag">
        {o ? (o.inverse ? "Incoming" : "Outgoing") : "Reached"}
        {data.given && <span className="chip surface-mark">given by the name</span>}
        {o?.group === "any" && !o.unknownClass && <span className="chip warn surface-mark">any class</span>}
        {o?.unknownClass && <span className="chip warn surface-mark">class unknown</span>}
        {o?.leads.kind === "value" && <span className="chip surface-mark">ends the path</span>}
      </div>
      <strong className="surface-title">{data.title}</strong>
      {data.lines.map((l, i) => <div key={i} className="small muted surface-line">{l}</div>)}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const NODE_TYPES = { box: Box };

export function PathMode({ place, ontology, onClose }: { place: PathPlace; ontology: Baseline; onClose: () => void }) {
  const { id, model } = useStudio();
  const graph = model.state.configs.surface!.current;
  const { hops, readable, source } = readPlace(graph, place);
  const edit = (change: (g: Graph) => Graph) => model.edit("surface", change);
  // Named as the drawing names them, by the ontology's label and else by the term's own name.
  const classLabel = (c?: string) => (c ? (ontology.classes.get(c)?.label ?? localName(c)) : "unknown class");
  const propertyLabel = (p: string) => ontology.properties.get(p)?.label ?? localName(p);

  // A binding binds one property of the class it reads, so its options are always those of the carrier.
  const asHops = place.kind === "binding" ? [] : hops;
  const { at, value } = reachedAfter(ontology, place.carrier, asHops);
  const trail = useMemo(() => {
    const out: { label: string; inverse: boolean; closure?: Closure; reaches: string; value: boolean }[] = [];
    let from = place.carrier;
    for (const h of hops) {
      const reached = reachedAfter(ontology, from, [h]);
      out.push({ label: propertyLabel(h.property), inverse: h.inverse, closure: h.closure, reaches: reached.value ? "a value" : classLabel(reached.at), value: reached.value });
      from = reached.at;
    }
    return out;
  }, [hops, ontology, place.carrier]); // eslint-disable-line react-hooks/exhaustive-deps

  const [query, setQuery] = useState("");
  const [everything, setEverything] = useState(false);
  // A property the laws forbid the place is not offered, as the one an expansion expands from is not offered for the property it writes (srf:P21).
  const every = useMemo(() => {
    if (value) return { forward: [], inverse: [] };
    const all = optionsAt(ontology, at);
    const barred = new Set(place.except ?? []);
    return barred.size === 0 ? all : { forward: all.forward.filter((o) => !barred.has(o.property)), inverse: all.inverse.filter((o) => !barred.has(o.property)) };
  }, [ontology, at, value, place.except]);
  // A filter on the names, for a class with many properties or one that is not known, which offers them all.
  const offered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const keep = (o: PathOption) => !q || o.label.toLowerCase().includes(q) || localName(o.property).toLowerCase().includes(q);
    const cap = <T,>(list: T[]) => (everything ? list : list.slice(0, LIMIT));
    return { forward: cap(every.forward.filter(keep)), inverse: cap(every.inverse.filter(keep)) };
  }, [every, query, everything]);
  const matching = (list: PathOption[]) => list.filter((o) => !query.trim() || o.label.toLowerCase().includes(query.trim().toLowerCase()) || localName(o.property).toLowerCase().includes(query.trim().toLowerCase())).length;
  const total = every.forward.length + (place.kind === "binding" ? 0 : every.inverse.length);
  const found = matching(every.forward) + (place.kind === "binding" ? 0 : matching(every.inverse));
  const shown = offered.forward.length + (place.kind === "binding" ? 0 : offered.inverse.length);
  // A path given by a named source is drawn as the chain of classes it stands for, with nothing to click, since path mode edits none of it.
  const named = place.kind === "members" && source !== undefined;
  const chain = useMemo(() => {
    const classes: Node[] = [{ id: "c|0", type: "box", position: { x: 0, y: 0 }, data: { title: classLabel(place.carrier), lines: ["the carrier"], current: false, given: false } satisfies Data }];
    const links: Edge<RoutedEdgeData>[] = [];
    trail.forEach((h, i) => {
      classes.push({ id: `c|${i + 1}`, type: "box", position: { x: 0, y: 0 }, data: { title: h.reaches, lines: [], current: false, given: true } satisfies Data });
      links.push({
        id: `h|${i}`, source: `c|${i}`, target: `c|${i + 1}`, type: "link", markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 }, style: { stroke: "var(--accent)", strokeWidth: 1.6, strokeDasharray: "6 4" },
        data: { label: `${h.inverse ? "← " : ""}${h.label}${h.closure ? ` ${h.closure}` : ""}`, title: `${h.label} is given by ${source ? compact(source) : "the name"}`, dashed: true, className: "onto-edge", labelClass: "onto-edge-label" },
      });
    });
    return { nodes: classes, edges: links };
  }, [trail, place.carrier, source]); // eslint-disable-line react-hooks/exhaustive-deps
  const nodes = useMemo<Node[]>(() => {
    if (named) return chain.nodes;
    const centre: Node = {
      id: "class", type: "box", position: { x: 0, y: 0 },
      data: { title: value ? "A value" : classLabel(at), lines: [value ? "the path ends here" : at === undefined ? "no class is declared here, so every property is offered" : "the class reached so far"], current: false } satisfies Data,
    };
    const forward = place.kind === "binding" ? hops[0]?.property : undefined;
    const box = (o: PathOption): Node => ({
      id: `${o.inverse ? "inv" : "fwd"}|${o.property}`, type: "box", position: { x: 0, y: 0 },
      data: {
        option: o, title: `${o.inverse ? "← " : ""}${o.label}${o.inverse ? "" : " →"}`, current: !o.inverse && o.property === forward,
        lines: [o.leads.kind === "class" ? `${o.inverse ? "from" : "to"} ${classLabel(o.leads.iri)}` : o.leads.kind === "value" ? `a value${o.leads.datatype ? `, ${compact(o.leads.datatype)}` : ""}` : "class not declared"],
      } satisfies Data,
    });
    return [centre, ...offered.inverse.filter(() => place.kind !== "binding").map(box), ...offered.forward.map(box)];
  }, [offered, at, value, place.kind, hops, named, chain]); // eslint-disable-line react-hooks/exhaustive-deps
  const edges = useMemo<Edge[]>(() => named ? chain.edges : [
    ...offered.inverse.filter(() => place.kind !== "binding").map((o): Edge<RoutedEdgeData> => ({
      id: `inv|${o.property}`, source: `inv|${o.property}`, target: "class", type: "link", markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
      style: { stroke: "var(--surface-c)", strokeWidth: 1.4 }, data: { title: `${o.label} points into ${classLabel(at)}`, className: "onto-edge", labelClass: "onto-edge-label" },
    })),
    ...offered.forward.map((o): Edge<RoutedEdgeData> => ({
      id: `fwd|${o.property}`, source: "class", target: `fwd|${o.property}`, type: "link", markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16 },
      style: { stroke: "var(--accent)", strokeWidth: 1.4 }, data: { title: `${classLabel(at)} has ${o.label}`, className: "onto-edge", labelClass: "onto-edge-label" },
    })),
  ], [offered, at, place.kind, named, chain]); // eslint-disable-line react-hooks/exhaustive-deps
  const hints = useMemo<LayoutHints>(
    () => Object.fromEntries(nodes.map((n) => [n.id, { ...SIZE, rank: n.id.startsWith("c|") ? Number(n.id.slice(2)) : n.id === "class" ? 1 : n.id.startsWith("inv|") ? 0 : 2 }])),
    [nodes],
  );

  const click = (n: Node) => {
    const option = (n.data as Data).option;
    if (option && !named) edit((g) => addHop(g, place, place.carrier, ontology, option));
  };

  const members = place.kind === "members";
  return (
    <div className="path-mode" role="region" aria-label="Path mode">
      <div className="path-mode-head row">
        <strong className="grow">Building {place.label}</strong>
        {named && (
          <button className="btn sm" disabled={hops.length === 0} title={hops.length ? "Removes srf:expansionSource and writes this path as srf:membersPath, which can then be edited" : "The name stands for no path, since the binding it expands from binds no property"} onClick={() => edit((g) => replaceNamedSource(g, place))}>
            <Replace size={13} /> Replace the named source with a path
          </button>
        )}
        <button className="btn sm" aria-label="Undo the last hop" disabled={hops.length === 0 || named} onClick={() => edit((g) => undoHop(g, place))}><Undo2 size={13} /> Undo</button>
        <button className="btn sm primary" onClick={onClose}><Check size={13} /> Done</button>
      </div>
      <ol className="path-trail" aria-label="Path so far">
        <li className="path-trail-class">{classLabel(place.carrier)}</li>
        {trail.map((h, i) => (
          <li key={i} className="path-trail-hop" data-hop={i}>
            <span className="arrow">{h.inverse ? "←" : "→"}</span> <span className="hop-name">{h.label}{h.closure ? ` ${h.closure}` : ""}</span>
            {members && !named && (
              <span className="path-closure" role="group" aria-label={`Closure of ${h.label}`}>
                {(["+", "*"] as const).map((c) => (
                  <button
                    key={c} className="btn ghost sm" aria-pressed={h.closure === c}
                    aria-label={`${c === "+" ? "One or more" : "Zero or more"} times: ${h.label}`}
                    title={c === "+" ? "One or more times, sh:oneOrMorePath" : "Zero or more times, sh:zeroOrMorePath"}
                    onClick={() => edit((g) => setClosure(g, place, i, h.closure === c ? undefined : c))}
                  >
                    {c}
                  </button>
                ))}
              </span>
            )}
            <span className="path-trail-class">{h.reaches}</span>
          </li>
        ))}
      </ol>
      <p className="small muted path-mode-note" role="status">
        {place.kind === "binding" && "A binding binds one property, so a click replaces it. It is written as srf:bindsProperty."}
        {place.kind === "read" && (hops.length === 1 && !hops[0].inverse ? "One forward hop is written as srf:readProperty." : hops.length ? `${hops.length} hops are written as srf:PathStep nodes.` : "No read path yet. Click a property to start it.")}
        {members && !readable && "The members path is stated in a form the canvas does not read, so the first hop replaces it. "}
        {named && `The expansion names ${compact(source!)}, and the path drawn is the one the name stands for, as the vocabulary defines it. Path mode edits nothing while the name is stated. Replace the named source with a path to write it out as srf:membersPath, drop the name and edit the path. `}
        {members && readable && !named && (hops.length ? "The path is written as srf:membersPath, a list for a sequence, sh:inversePath for an inverse hop." : "No members path yet. Click a property to start it.")}
        {value && " The path has ended in a value."}
        {!value && at === undefined && place.kind !== "binding" && hops.length > 0 && " The last hop declares no range, so the class is unknown and every property is offered."}
      </p>
      {total > 8 && !named && (
        <label className="row small path-filter">
          Filter the properties
          <input className="input" type="search" aria-label="Filter the properties" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="a part of a name" />
          <span className="muted">{found === total ? `${total} properties` : `${found} of ${total} properties match`}{shown < found ? `, ${shown} drawn` : ""}</span>
          {shown < found && <button className="btn sm" onClick={() => setEverything(true)}>Draw them all</button>}
        </label>
      )}
      <Canvas
        key={`${place.node}|${at ?? "?"}|${value}|${hops.length}|${query}|${named}`}
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        edgeTypes={EDGE_TYPES}
        routing
        options={LAYOUT}
        hints={hints}
        storageKey={`lattice-studio:surface-path:${id}:${place.node}:${at ?? "unknown"}:${value}${named ? ":named" : ""}`}
        height={460}
        onNodeClick={click}
      />
    </div>
  );
}
