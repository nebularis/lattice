// SPDX-License-Identifier: MPL-2.0
// The persistence canvas's exploded view (SVA-P1, SVA-P1b), read only. For the target, profile or scope node the author picks, it draws one
// root with the closure of its boundary and every place its data lands when written. It draws `compiled-profile.ttl`, the artefact the
// latest finished persistence compilation of the workspace holds, which states the places itself. Nothing is drawn from the browser's own
// reading of the configuration, and the picture says when the persistence part or the baseline has changed since the compilation it
// shows. Edits on the canvas are SVA-P2.

import { useEffect, useMemo, useState } from "react";
import { Handle, MarkerType, Position, type Edge, type Node, type NodeProps } from "@xyflow/react";
import { Graph } from "@lattice/authoring-domain";
import { api, awaitJob, jobId } from "../api";
import { useSim } from "../persistence/simulatorStore";
import { isLit } from "../persistence/simulator";
import { read, noteCompiled, useCompilationEpoch, type Load } from "../persistence/compilation";
import { Canvas, RoutedEdge, type LayoutHints, type LayoutOptions, type RoutedEdgeData } from "../canvas/kit";
import {
  LENSES, choices, drawing, fingerprint, freshness, localName, readCompiled, targetLabel, writeCompiled,
  type CanvasNode, type Lens, type LandingPlaces, type LandingTarget, type Place,
} from "../persistence/landing";
import { PARTS } from "../state";
import { Spinner, ago } from "./kit";
import { useStudio } from "./Workspace";

/** Left to right, the boundary, the root and its places. The ranks are kept by the layout, and the gaps leave room for an edge's label. */
const LAYOUT: LayoutOptions = { direction: "LR", columnGap: 160, rowGap: 14 };
const EDGE_TYPES = { link: RoutedEdge };

type BoxData = { node: CanvasNode; selected: boolean; lit: boolean };

const KIND_WORDS: Record<string, string> = {
  root: "Root", owned: "Owned", reference: "Referenced", target: "Target", place: "",
};

function Box({ data }: NodeProps<Node<BoxData>>) {
  const n = data.node;
  return (
    <div
      className={`canvas-node landing-node ${n.kind}${data.selected ? " selected" : ""}${data.lit ? " lit" : ""}`}
      data-lit={n.kind === "place" ? String(data.lit) : undefined}
      title={n.kind === "place" ? `${n.label}, written to ${n.sub}${data.lit ? ". The last step of the simulator wrote it." : ""}` : `${n.label}, ${n.sub}`}
    >
      <Handle type="target" position={Position.Left} />
      <div className="landing-kind">{n.kind === "place" ? n.place!.kind : KIND_WORDS[n.kind]}{data.lit && <span className="landing-lit"> · written by the last step</span>}</div>
      <strong className="landing-label">{n.label}</strong>
      <div className={n.kind === "place" ? "landing-graph" : "small muted landing-sub"}>{n.sub}</div>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

const NODE_TYPES = { box: Box };

const SIZES: Record<CanvasNode["kind"], { width: number; height: number }> = {
  root: { width: 200, height: 56 },
  owned: { width: 200, height: 56 },
  reference: { width: 200, height: 56 },
  target: { width: 200, height: 56 },
  place: { width: 260, height: 88 },
};

export function PersistenceCanvas() {
  const studio = useStudio();
  const { id, model } = studio;
  const [lens, setLens] = useState<Lens>("aggregate");
  const [picked, setPicked] = useState<Partial<Record<Lens, string>>>({});
  const [selected, setSelected] = useState<string>();
  const [load, setLoad] = useState<Load>({ state: "loading" });
  const [reload, setReload] = useState(0);
  const compiledElsewhere = useCompilationEpoch();
  const lit = useSim(id).lit;
  const [compiling, setCompiling] = useState(false);
  const [problem, setProblem] = useState<string>();

  useEffect(() => {
    let live = true;
    read(id).then(
      (next) => live && setLoad(next),
      (e: unknown) => live && setLoad({ state: "error", message: e instanceof Error ? e.message : String(e) }),
    );
    return () => {
      live = false;
    };
  }, [id, reload, compiledElsewhere]);

  // What the persistence part and the baseline hold now, to compare with what the compilation was sent.
  const persistence = model.state.configs.persistence?.current;
  const now = useMemo(() => fingerprint(persistence?.toTurtle() ?? "", model.state.baseline?.revision), [persistence, model.state.baseline?.revision]);

  // The compiler reads the other parts as context, as the Build view sends them.
  const compile = async () => {
    setProblem(undefined);
    setCompiling(true);
    try {
      let body = Graph.empty();
      for (const p of PARTS) body = body.merge(model.state.configs[p]!.current);
      const job = await api.submit(id, "compile", "persistence", body);
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

  const doc = load.state === "ready" ? load.doc : undefined;
  const options = useMemo(() => (doc ? choices(doc, lens) : []), [doc, lens]);
  const choice = options.find((c) => c.id === picked[lens])?.id ?? options[0]?.id;
  const drawn = useMemo(() => (doc && choice !== undefined ? drawing(doc, lens, choice) : undefined), [doc, lens, choice]);

  const nodes = useMemo<Node[]>(
    () => (drawn?.nodes ?? []).map((n) => ({ id: n.id, type: "box", position: { x: 0, y: 0 }, data: { node: n, selected: n.id === selected, lit: n.kind === "place" && n.place !== undefined && isLit(n.place, lit) } satisfies BoxData })),
    [drawn, selected, lit],
  );
  const edges = useMemo<Edge[]>(
    () =>
      (drawn?.edges ?? []).map((e): Edge<RoutedEdgeData> => ({
        id: e.id, source: e.source, target: e.target, type: "link",
        markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18 },
        style: e.kind === "lands" ? { stroke: "var(--persist)", strokeWidth: 1.8 } : e.kind === "owned" ? { stroke: "var(--accent)", strokeWidth: 1.8 } : { stroke: "var(--text-3)", strokeDasharray: "6 4" },
        data: { label: e.label, title: e.title, dashed: e.dashed, className: "onto-edge", labelClass: "onto-edge-label" },
      })),
    [drawn],
  );
  const hints = useMemo<LayoutHints>(
    () => Object.fromEntries((drawn?.nodes ?? []).map((n) => [n.id, { ...SIZES[n.kind], rank: n.rank }])),
    [drawn],
  );

  const status = load.state === "ready" ? freshness(readCompiled(id)[load.job.iri], now) : undefined;
  const shown = nodes.find((n) => n.id === selected)?.data.node as CanvasNode | undefined;

  const compileButton = (
    <button className="btn sm primary" disabled={compiling || !persistence?.size} onClick={() => void compile()}>
      {compiling ? <Spinner size={12} /> : null} Compile
    </button>
  );

  return (
    <div className="landing onto" role="region" aria-label="Persistence canvas">
      {load.state === "loading" && <p className="muted small">Reading the latest compilation.</p>}
      {load.state === "error" && <p style={{ color: "var(--bad)" }}>{load.message}</p>}
      {problem && <p style={{ color: "var(--bad)" }}>{problem}</p>}
      {(load.state === "none" || load.state === "refused" || load.state === "old") && (
        <div className="empty">
          <h3>{load.state === "none" ? "No persistence compilation yet" : load.state === "refused" ? "The latest compilation was refused" : "The latest compilation predates the landing places"}</h3>
          <p className="small">
            {load.state === "none"
              ? "The canvas draws where each class's data lands as the compiler says it, so it needs a compilation of the persistence configuration."
              : load.state === "refused"
                ? "There is nothing to draw from a refused compilation. Its findings are in Build. Compile again once they are resolved."
                : "That compilation did not describe where data lands. Compile again."}
          </p>
          {compileButton}
        </div>
      )}
      {doc && drawn && load.state === "ready" && (
        <>
          <div className="onto-controls">
            <div className="mode-switch" role="group" aria-label="Lens" style={{ margin: 0 }}>
              {LENSES.map((l) => (
                <button key={l.lens} aria-pressed={lens === l.lens} title={l.what} onClick={() => (setLens(l.lens), setSelected(undefined))}>
                  {l.title}
                </button>
              ))}
            </div>
            <label className="row small" style={{ gap: 6 }}>
              {LENSES.find((l) => l.lens === lens)!.picker}
              <select
                className="select"
                aria-label={LENSES.find((l) => l.lens === lens)!.picker}
                value={choice ?? ""}
                disabled={options.length === 0}
                onChange={(e) => (setPicked({ ...picked, [lens]: e.target.value }), setSelected(undefined))}
              >
                {options.map((c) => (
                  <option key={c.id} value={c.id}>{c.label}</option>
                ))}
              </select>
            </label>
            <span className="small muted grow">
              Drawn from the compilation {ago(load.job.finishedAt ?? load.job.submittedAt)}, job <span className="mono">{jobId(load.job.iri).slice(0, 8)}</span>.
            </span>
            {compileButton}
          </div>
          {status === "out-of-date" && (
            <p className="landing-note" role="alert">This picture is out of date. The persistence part or the baseline has changed since that compilation. Compile to draw it again.</p>
          )}
          {status === "unknown" && (
            <p className="landing-note muted">That compilation was started elsewhere, so the canvas cannot tell whether the configuration has changed since. Compile here to keep track.</p>
          )}
          <div className="landing-body">
            {drawn.nodes.length === 0 ? (
              <div className="empty"><p>The compilation holds nothing to draw for this choice.</p></div>
            ) : (
              <Canvas
                key={`${lens}|${choice}|${drawn.nodes.length}|${drawn.edges.length}`}
                nodes={nodes}
                edges={edges}
                nodeTypes={NODE_TYPES}
                edgeTypes={EDGE_TYPES}
                routing
                options={LAYOUT}
                hints={hints}
                storageKey={`lattice-studio:persistence-canvas:${id}:${lens}:${choice}`}
                height={700}
                onNodeClick={(n) => setSelected(n.id)}
              />
            )}
            <Details doc={doc} node={shown} />
          </div>
        </>
      )}
    </div>
  );
}

/** A target's place that is the same as `place`, since a shared place is drawn once and each target keeps its own operations. */
function placeOf(target: LandingTarget, place: Place): Place | undefined {
  return target.places.find((p) => p.kind === place.kind && p.graph === place.graph && p.label === place.label);
}

function Details({ doc, node }: { doc: LandingPlaces; node?: CanvasNode }) {
  if (!node) {
    return (
      <aside className="landing-details" aria-label="Selected node">
        <p className="small muted">Select a node to see what it is and which operations write it. The canvas is read only. Edit the configuration in the node list.</p>
      </aside>
    );
  }
  const targets = doc.targets.filter((t) => (node.targets ?? []).includes(t.id));
  return (
    <aside className="landing-details" aria-label="Selected node">
      {node.kind === "place" && node.place && (
        <>
          <span className="chip persist">{node.place.kind}</span>
          <h3>{node.place.label}</h3>
          <div className="field-label">Graph or naming rule</div>
          <div className="mono landing-rule">{node.place.graph}</div>
          <div className="field-label">Written by</div>
          {targets.map((t) => {
            const mine = placeOf(t, node.place!);
            return (
              <div key={t.id} className="landing-ops">
                <div className="small muted">{targetLabel(t)}</div>
                <ul>
                  {(mine?.operations ?? []).map((name) => {
                    const op = t.operations.find((o) => o.operation === name);
                    return (
                      <li key={name}>
                        <strong>{name}</strong>
                        {op && (
                          <>
                            <div className="small muted">{op.templateId}</div>
                            <div className="small mono landing-path">{op.path}</div>
                          </>
                        )}
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
          <p className="small muted">The SPARQL of each is in Build, under the compilation's artefacts, at the path shown.</p>
        </>
      )}
      {(node.kind === "root" || node.kind === "target") && node.target && (
        <>
          <span className="chip persist">{node.kind === "root" ? "Root" : "Target"}</span>
          <h3>{targetLabel(node.target)}</h3>
          <div className="iri">{node.target.class}</div>
          <div className="field-label">Aggregate boundary</div>
          <p className="small">{node.target.aggregate.strategy ?? "None"}{node.target.aggregate.rootShape ? `, shape ${localName(node.target.aggregate.rootShape)}` : ""}</p>
          <div className="field-label">Profiles it resolved from</div>
          <ul className="landing-list">{node.target.profiles.map((p) => <li key={p} className="mono small">{localName(p)}</li>)}</ul>
          <div className="field-label">Scope nodes</div>
          <ul className="landing-list">{node.target.scopes.map((p) => <li key={p} className="mono small">{localName(p)}</li>)}</ul>
          <p className="small muted">{node.target.places.length} places and {node.target.operations.length} operations.</p>
        </>
      )}
      {(node.kind === "owned" || node.kind === "reference") && node.edge && (
        <>
          <span className="chip persist">{node.kind === "owned" ? "Owned" : "Referenced"}</span>
          <h3>{node.label}</h3>
          <div className="field-label">Property</div>
          <div className="iri">{node.edge.inverse ? "inverse of " : ""}{node.edge.property}</div>
          <p className="small">
            {node.kind === "owned"
              ? "Inside the boundary, so one write covers it."
              : node.edge.ownership === "Vocabulary"
                ? "A vocabulary node, outside the boundary."
                : node.edge.mode === "Pinned"
                  ? "Outside the boundary, pinned to a version of the node."
                  : "Outside the boundary, referenced by identity."}
          </p>
        </>
      )}
    </aside>
  );
}
