// SPDX-License-Identifier: MPL-2.0
// The output explorer (SVA-M4): one part of a run's result, shown in each rendering its media type allows. RDF is a text (Turtle by
// default, N-Triples offered), a table or a graph on the canvas kit. JSON and XML are a collapsible tree or a text. Anything else is a
// text. The author's choice for each media type is kept in this browser (output/media.ts). A part is parsed only after the page has been
// drawn and only once, so a large part never holds the page up, a table draws a page of rows at a time, and a graph of many nodes is
// drawn only when asked. A part that does not parse in its media type is said so, with the parser's message, and shown as text.

import { memo, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { Handle, MarkerType, Position, type Edge, type Node, type NodeProps } from "@xyflow/react";
import { Check, Copy, Download } from "lucide-react";
import { Canvas, RoutedEdge, type LayoutHints, type LayoutOptions, type RoutedEdgeData } from "../canvas/kit";
import { NO_CHOICES, RENDERING_LABEL, familyOf, formatOf, readChoices, renderingOf, renderingsFor, withFormat, withRendering, writeChoices, type Choices, type Rendering, type TextFormat } from "../output/media";
import { declaredPrefixes, filterRows, graphModel, parseRdf, prefixesOf, tableRows, toNTriplesText, toTurtleText, type GraphModel, type Parsed, type Row } from "../output/rdf";
import { parseJsonTree, parseXmlTree, prettyJson, type ParsedTree, type TreeNode } from "../output/tree";
import { DRAW_AT_ONCE } from "./OntologyCanvas";
import { download } from "./kit";

/** What the explorer reads of a run's part. */
export interface ExplorerPart {
  mediaType: string;
  text: string;
  role?: string;
  path?: string;
  group?: string;
  step?: number;
}

// The author's choices are read when first needed and shared by every part, so changing a media type's rendering changes it for each part of that type.
let kept: Choices | undefined;
const listeners = new Set<() => void>();
const currentChoices = () => (kept ??= readChoices());
function keep(next: Choices): void {
  kept = next;
  writeChoices(next);
  listeners.forEach((l) => l());
}
function useChoices(): Choices {
  return useSyncExternalStore(
    (listener) => (listeners.add(listener), () => void listeners.delete(listener)),
    currentChoices,
    () => NO_CHOICES,
  );
}

/**
 * The value of `compute` for `key`, computed after the page has been drawn and kept while the key stays. Nothing is computed while
 * `compute` is undefined, which is how a rendering that is not shown asks for nothing. Until it is there the value is undefined.
 */
function useLater<T>(key: unknown, compute: (() => T) | undefined): T | undefined {
  const [done, setDone] = useState<{ key: unknown; value: T }>();
  const latest = useRef(compute);
  latest.current = compute;
  const have = useRef(done);
  have.current = done;
  const needed = compute !== undefined;
  useEffect(() => {
    if (!needed) return;
    let live = true;
    const handle = setTimeout(() => {
      if (live && have.current?.key !== key) setDone({ key, value: latest.current!() });
    }, 0);
    return () => {
      live = false;
      clearTimeout(handle);
    };
  }, [key, needed]);
  return done && done.key === key ? done.value : undefined;
}

function Problem({ part, message }: { part: ExplorerPart; message: string }) {
  return (
    <p className="output-problem">
      This part is {part.mediaType} and does not parse as that. {message.replace(/\s+$/, "")} Its text is shown as received.
    </p>
  );
}

function fileName(part: ExplorerPart, extension?: string): string {
  const base = (part.path ?? `${part.role ?? "output"}`).split("/").pop() || "output";
  if (!extension) return base;
  return `${base.replace(/\.[A-Za-z0-9]+$/, "")}${extension}`;
}

function TextBlock({ part, text, type, extension }: { part: ExplorerPart; text: string; type: string; extension?: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // A browser that refuses the clipboard leaves the text selectable.
    }
  };
  return (
    <div className="output-text">
      <div className="output-text-actions">
        <button className="btn sm" onClick={() => void copy()}>
          {copied ? <Check size={13} /> : <Copy size={13} />} Copy
        </button>
        <button className="btn sm" onClick={() => download(fileName(part, extension), text, type)}>
          <Download size={13} /> Download
        </button>
      </div>
      <pre className="run-part-text" tabIndex={0} aria-label="Output text">{text}</pre>
    </div>
  );
}

// --- RDF ---

type TermData = { label: string; types: string[]; rows: { predicate: string; value: string }[]; blank: boolean };
const MAX_NODE_ROWS = 8;

function TermNode({ data }: NodeProps<Node<TermData>>) {
  const shown = data.rows.slice(0, MAX_NODE_ROWS);
  return (
    <div className={`canvas-node term-node${data.blank ? " blank" : ""}`} title={data.label}>
      <Handle type="target" position={Position.Left} />
      <strong className="ellipsis term-label">{data.label}</strong>
      {data.types.length > 0 && <div className="small muted mono canvas-terms">{data.types.join(", ")}</div>}
      {shown.map((r, i) => (
        <div key={i} className="term-row small" title={`${r.predicate} ${r.value}`}>
          <span className="muted mono">{r.predicate}</span> <span className="mono">{r.value}</span>
        </div>
      ))}
      {data.rows.length > shown.length && <div className="small muted">and {data.rows.length - shown.length} more</div>}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const NODE_TYPES = { term: TermNode };
const EDGE_TYPES = { link: RoutedEdge };
const GRAPH_LAYOUT: LayoutOptions = { direction: "LR", columnGap: 150, rowGap: 28 };
const ROUTED = (data: RoutedEdgeData): RoutedEdgeData => ({ ...data, className: "onto-edge", labelClass: "onto-edge-label" });

function GraphView({ model, storageKey }: { model: GraphModel; storageKey: string }) {
  const [whole, setWhole] = useState(false);
  const deferred = model.nodes.length > DRAW_AT_ONCE && !whole;
  const nodes = useMemo<Node[]>(
    () => (deferred ? [] : model.nodes.map((n) => ({ id: n.id, type: "term", position: { x: 0, y: 0 }, data: { label: n.label, types: n.types, rows: n.rows, blank: n.blank } satisfies TermData }))),
    [model, deferred],
  );
  const edges = useMemo<Edge[]>(
    () =>
      deferred
        ? []
        : model.edges.map((e) => ({
            id: e.id,
            source: e.source,
            target: e.target,
            type: "link",
            markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18 },
            style: { stroke: "var(--accent)", strokeWidth: 1.6 },
            data: ROUTED({ label: e.label, title: `${e.label}, from ${e.source} to ${e.target}` }),
          })),
    [model, deferred],
  );
  const hints = useMemo<LayoutHints>(
    () => Object.fromEntries(model.nodes.map((n) => [n.id, { width: 240, height: 30 + (n.types.length ? 17 : 0) + 17 * Math.min(n.rows.length, MAX_NODE_ROWS) + (n.rows.length > MAX_NODE_ROWS ? 17 : 0) }])),
    [model],
  );
  const counts = `${model.nodes.length} ${model.nodes.length === 1 ? "node" : "nodes"} and ${model.edges.length} ${model.edges.length === 1 ? "link" : "links"}`;
  if (model.nodes.length === 0) return <p className="small muted">The part holds no triples to draw.</p>;
  if (deferred) {
    return (
      <div className="empty output-deferred">
        <p>The graph holds {counts}. That is a lot to draw at once.</p>
        <button className="btn" onClick={() => setWhole(true)}>Draw the whole graph</button>
      </div>
    );
  }
  return (
    <div className="output-graph">
      <p className="small muted output-count">{counts}. An arrow runs from a triple's subject to its object, a literal is a row inside its subject, and the graphs of a dataset are merged.</p>
      <Canvas key={`${model.nodes.length}|${model.edges.length}|${model.nodes[0].id}`} nodes={nodes} edges={edges} nodeTypes={NODE_TYPES} edgeTypes={EDGE_TYPES} routing options={GRAPH_LAYOUT} hints={hints} storageKey={storageKey} height={Math.min(440, Math.max(220, 80 + 56 * model.nodes.length))} />
    </div>
  );
}

const PAGE = 200;

function TableView({ rows, held }: { rows: readonly Row[]; held: number }) {
  const [filter, setFilter] = useState("");
  const [pages, setPages] = useState(1);
  const matching = useMemo(() => filterRows(rows, filter), [rows, filter]);
  const shown = matching.slice(0, PAGE * pages);
  const graphs = useMemo(() => rows.some((r) => r.graph !== ""), [rows]);
  return (
    <div className="output-table-wrap">
      <div className="output-table-tools">
        <input className="input" type="search" aria-label="Filter rows" placeholder="Filter rows" value={filter} onChange={(e) => (setFilter(e.target.value), setPages(1))} />
        <span className="small muted" aria-live="polite">
          {filter.trim() ? `Showing ${shown.length.toLocaleString()} of ${matching.length.toLocaleString()} matching rows, ${held.toLocaleString()} held.` : `Showing ${shown.length.toLocaleString()} of ${held.toLocaleString()} rows.`}
        </span>
      </div>
      <div className="output-table-scroll">
        <table className="output-table" aria-label="Triples">
          <thead>
            <tr>
              <th>Subject</th>
              <th>Predicate</th>
              <th>Object</th>
              {graphs && <th>Graph</th>}
            </tr>
          </thead>
          <tbody>
            {shown.map((r, i) => (
              <tr key={i}>
                <td>{r.subject}</td>
                <td>{r.predicate}</td>
                <td>{r.object}</td>
                {graphs && <td>{r.graph}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {shown.length < matching.length && (
        <button className="btn sm" onClick={() => setPages((p) => p + 1)}>
          Show more
        </button>
      )}
      {matching.length === 0 && <p className="small muted">No row holds that text.</p>}
    </div>
  );
}

function RdfView({ part, rendering, choices, prefixes }: { part: ExplorerPart; rendering: Rendering; choices: Choices; prefixes?: Record<string, string> }) {
  const source = useMemo(() => ({ text: part.text, mediaType: part.mediaType }), [part.text, part.mediaType]);
  const parsed = useLater<Parsed>(source, () => parseRdf(part.text, part.mediaType));
  const format = formatOf(part.mediaType, choices);
  // The Turtle is written first where it, a table or a graph is shown, so each of them compacts IRIs with the prefixes the writer chose.
  const own = useMemo(() => (parsed?.ok ? prefixesOf(parsed.prefixes, prefixes) : undefined), [parsed, prefixes]);
  const turtle = useLater(parsed, parsed?.ok && own && (rendering !== "text" || format === "turtle") ? () => toTurtleText(parsed.quads, own) : undefined);
  const all = useMemo(() => (turtle !== undefined && own ? { ...own, ...declaredPrefixes(turtle) } : undefined), [turtle, own]);
  const textKey = useMemo(() => ({ parsed, format }), [parsed, format]);
  const ntriples = useLater(textKey, rendering === "text" && format === "ntriples" && parsed?.ok ? () => toNTriplesText(parsed.quads) : undefined);
  const text = format === "turtle" ? turtle : ntriples;
  const rows = useLater(all, rendering === "table" && parsed?.ok && all ? () => tableRows(parsed.quads, all) : undefined);
  const model = useLater(all, rendering === "graph" && parsed?.ok && all ? () => graphModel(parsed.quads, all) : undefined);
  if (parsed && !parsed.ok) {
    return (
      <>
        <Problem part={part} message={parsed.message} />
        <TextBlock part={part} text={part.text} type={part.mediaType} />
      </>
    );
  }
  if (rendering === "table") return rows ? <TableView rows={rows} held={rows.length} /> : <p className="small muted">Reading the rows.</p>;
  if (rendering === "graph") return model ? <GraphView model={model} storageKey={`lattice-studio:output-canvas:${part.group ?? ""}:${part.path ?? part.role ?? ""}`} /> : <p className="small muted">Reading the graph.</p>;
  // Until the Turtle is written the text is shown as received, so the part is never blank.
  return text !== undefined ? (
    <TextBlock part={part} text={text} type={format === "turtle" ? "text/turtle" : "application/n-triples"} extension={format === "turtle" ? ".ttl" : ".nt"} />
  ) : (
    <TextBlock part={part} text={part.text} type={part.mediaType} />
  );
}

// --- JSON and XML ---

const CHILD_PAGE = 100;

const TreeRow = memo(function TreeRow({ node, depth }: { node: TreeNode; depth: number }) {
  const [open, setOpen] = useState(depth < 2);
  const [limit, setLimit] = useState(CHILD_PAGE);
  const container = node.children.length > 0;
  const name = node.label !== undefined && (
    <span className={node.kind === "attribute" ? "tree-attr" : "tree-key"}>{node.kind === "element" ? `<${node.label}>` : node.label}</span>
  );
  const value = node.value !== undefined && <span className={`tree-value ${node.kind}`}>{node.value}</span>;
  const summary = node.summary !== undefined && <span className="muted small"> {node.summary}</span>;
  return (
    <li role="treeitem" aria-expanded={container ? open : undefined}>
      {container ? (
        <button className="tree-toggle" aria-label={`${open ? "Collapse" : "Expand"} ${node.label ?? node.kind}`} aria-expanded={open} onClick={() => setOpen(!open)}>
          <span aria-hidden="true">{open ? "\u25BE" : "\u25B8"}</span> {name} {summary}
        </button>
      ) : (
        <span className="tree-leaf">
          {name} {value}
          {summary}
        </span>
      )}
      {container && open && (
        <ul role="group">
          {node.children.slice(0, limit).map((child) => (
            <TreeRow key={child.id} node={child} depth={depth + 1} />
          ))}
          {node.children.length > limit && (
            <li role="none">
              <button className="btn sm" onClick={() => setLimit(limit + CHILD_PAGE)}>
                Show more ({node.children.length - limit} not shown)
              </button>
            </li>
          )}
        </ul>
      )}
    </li>
  );
});

function TreeView({ tree }: { tree: ParsedTree }) {
  if (!tree.ok) return null;
  return (
    <ul className="output-tree" role="tree" aria-label="Output tree">
      <TreeRow node={tree.root} depth={0} />
    </ul>
  );
}

function StructuredView({ part, rendering, family }: { part: ExplorerPart; rendering: Rendering; family: "json" | "xml" }) {
  const source = useMemo(() => ({ text: part.text, mediaType: part.mediaType }), [part.text, part.mediaType]);
  const tree = useLater<ParsedTree>(source, family === "json" ? () => parseJsonTree(part.text) : () => parseXmlTree(part.text));
  const pretty = useLater(source, family === "json" && rendering === "text" ? () => prettyJson(part.text) : undefined);
  if (tree && !tree.ok) {
    return (
      <>
        <Problem part={part} message={tree.message} />
        <TextBlock part={part} text={part.text} type={part.mediaType} />
      </>
    );
  }
  if (rendering === "tree") return tree ? <TreeView tree={tree} /> : <p className="small muted">Reading the {family === "json" ? "JSON" : "XML"}.</p>;
  if (family === "json" && pretty?.ok) return <TextBlock part={part} text={pretty.text} type="application/json" extension=".json" />;
  return <TextBlock part={part} text={part.text} type={part.mediaType} />;
}

// --- The explorer ---

export function OutputExplorer({ part, prefixes }: { part: ExplorerPart; prefixes?: Record<string, string> }) {
  const choices = useChoices();
  const family = familyOf(part.mediaType);
  const offered = renderingsFor(part.mediaType);
  const rendering = renderingOf(part.mediaType, choices);
  return (
    <div className="output-explorer">
      {(offered.length > 1 || (family === "rdf" && rendering === "text")) && (
        <div className="output-tools">
          {offered.length > 1 && (
            <div className="mode-switch output-switch" role="group" aria-label="Rendering">
              {offered.map((r) => (
                <button key={r} aria-pressed={rendering === r} onClick={() => keep(withRendering(currentChoices(), part.mediaType, r))}>
                  {RENDERING_LABEL[r]}
                </button>
              ))}
            </div>
          )}
          {family === "rdf" && rendering === "text" && (
            <div className="mode-switch output-switch" role="group" aria-label="Text format">
              {(["turtle", "ntriples"] as TextFormat[]).map((f) => (
                <button key={f} aria-pressed={formatOf(part.mediaType, choices) === f} onClick={() => keep(withFormat(currentChoices(), part.mediaType, f))}>
                  {f === "turtle" ? "Turtle" : "N-Triples"}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      {family === "rdf" ? (
        <RdfView part={part} rendering={rendering} choices={choices} prefixes={prefixes} />
      ) : family === "json" || family === "xml" ? (
        <StructuredView part={part} rendering={rendering} family={family} />
      ) : (
        <TextBlock part={part} text={part.text} type={part.mediaType} />
      )}
    </div>
  );
}
