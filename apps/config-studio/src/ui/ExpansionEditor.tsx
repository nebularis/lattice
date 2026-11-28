// SPDX-License-Identifier: MPL-2.0
// The expansion editor of the surface canvas (SVA-S1 part 4, SVA-Q57 (b)): the evidence binding an expansion expands from, and how its members are reached, a named
// source or a members path, as the Surface README's section 6.18 gives them. A named source is drawn as the path the name stands for, which path mode edits nothing of
// (part 3), and one action replaces it with that path so that the statement states exactly one of the two (srf:P20). The path itself and the property each member is
// written as are built in path mode (part 2). Each control is one `model.edit` made by a function of `surface/expansionEdit.ts`.

import { useMemo } from "react";
import { Check, Plus, Replace, Route, Trash2 } from "lucide-react";
import { SRF, compact, localName } from "@lattice/authoring-domain";
import type { PathPlace } from "../surface/drawing";
import {
  SOURCES, SOURCE_WORDS, addExpansion, expansionChoices, expansionMarks, readExpansion, removeExpansion, setExpandsFrom, useNamedSource, type Source,
} from "../surface/expansionEdit";
import { addMemberNode, readConstruction } from "../surface/constructionEdit";
import { readPlace, replaceNamedSource } from "../surface/pathmode";
import { statementContext } from "../surface/statement";
import type { Terms } from "../surface/terms";
import { Findings, Marks } from "./StatementKit";
import { useStudio } from "./Workspace";

export function ExpansionEditor({ contract, terms, onClose, onBuild, onOpen }: { contract: string; terms: Terms; onClose: () => void; onBuild: (place: PathPlace) => void; onOpen: (kind: "member") => void }) {
  const { model, baseline } = useStudio();
  const graph = model.state.configs.surface!.current;
  const known = model.state.baseline?.graph;
  const ctx = useMemo(() => statementContext(graph, contract, baseline.namespace, known), [graph, contract, baseline.namespace, known]);
  const x = readExpansion(graph, ctx);
  const choices = useMemo(() => expansionChoices(graph, ctx), [graph, ctx]);
  const marks = useMemo(() => expansionMarks(graph, ctx), [graph, ctx]);
  const edit = (change: (g: typeof graph) => typeof graph) => model.edit("surface", change);
  const name = graph.value(contract, SRF("contractKey")) ?? localName(contract);
  const construction = readConstruction(graph, ctx);

  const fromBinding = x && x.from.length === 1 ? ctx.evidence.find((e) => e.iri === x.from[0].value) : undefined;
  const members: PathPlace | undefined = x?.named ? { kind: "members", node: x.node, contract, carrier: ctx.carrier, label: "the members path" } : undefined;
  const state = members ? readPlace(graph, members) : undefined;
  const link: PathPlace | undefined = ctx.result ? { kind: "binding", node: ctx.result, contract, carrier: ctx.carrier, label: "the property each member is written as", except: fromBinding?.property ? [fromBinding.property] : undefined } : undefined;
  const label = (iri: string) => terms.label(iri);
  const trail = (state?.hops ?? []).map((h) => `${h.inverse ? "← " : ""}${[h.property, ...(h.alternatives ?? [])].map(label).join(" | ")}${h.closure ?? ""}`);
  const evidenceLabel = (e: { property?: string; role: string }) => `${e.property ? label(e.property) : "…"} (${e.role === "required" ? "required" : "candidate"})`;
  const stated = x?.paths.length ? "path" : x?.sources.length ? "source" : undefined;
  const missing = x ? undefined : !ctx.result ? "This contract states no result-target binding, so it can state no expansion. Add the binding in the form." : ctx.kind === "expansion" ? undefined : "This contract is not an expansion, so it states no expansion.";

  return (
    <div className="path-mode statement-editor" role="region" aria-label="Expansion editor">
      <div className="path-mode-head row">
        <strong className="grow">Expansion of {name}</strong>
        <button className="btn sm primary" onClick={onClose}><Check size={13} /> Done</button>
      </div>
      {!x ? (
        <>
          <Marks marks={marks} part={["node", "link"]} />
          <div className="expr-add row" role="group" aria-label="Add an expansion">
            <span className="small muted grow">{missing ?? "The result-target binding states no expansion. An expansion restates one relation of an instance as a statement for each node it reaches."}</span>
            {missing === undefined && <button className="btn sm primary" onClick={() => edit((g) => addExpansion(g, ctx))}><Plus size={13} /> Add an expansion</button>}
          </div>
        </>
      ) : (
        <>
          <Marks marks={marks} part="node" />
          <Findings issues={model.issues.surface} focus={[x.node, ctx.result]} />
          <div className="stmt-row" data-part="from">
            <span className="stmt-label">Expands from</span>
            <select
              className="select" aria-label="Expands from" value={fromBinding?.iri ?? ""}
              onChange={(e) => e.target.value !== "" && edit((g) => setExpandsFrom(g, ctx, e.target.value))}
            >
              {fromBinding === undefined && <option value="">choose…</option>}
              {fromBinding !== undefined && !choices.from.some((e) => e.iri === fromBinding.iri) && <option value={fromBinding.iri}>{evidenceLabel(fromBinding)}</option>}
              {choices.from.map((e) => <option key={e.iri} value={e.iri}>{evidenceLabel(e)}</option>)}
            </select>
            <span className="small muted">{stated === "path" ? "A members path is stated, so only evidence the path reads is offered. Use a named source to change the property." : "an evidence binding of this contract's own carrier"}</span>
            <Marks marks={marks} part="from" />
          </div>
          <div className="stmt-row" data-part="members">
            <span className="stmt-label">Members</span>
            {stated === "path" ? (
              <>
                <span className="stmt-value" data-members="path">a members path</span>
                <ol className="path-trail" aria-label="Members path so far">
                  <li className="path-trail-class">{ctx.carrier ? label(ctx.carrier) : "the carrier"}</li>
                  {trail.map((t, i) => <li key={i} className="path-trail-hop"><span className="arrow">→</span> <span className="hop-name">{t}</span></li>)}
                </ol>
                {members && <button className="btn sm" onClick={() => onBuild(members)}><Route size={13} /> Build the members path</button>}
                <select className="select" aria-label="Use a named source" value="" onChange={(e) => e.target.value && edit((g) => useNamedSource(g, ctx, e.target.value as Source))}>
                  <option value="">use a named source…</option>
                  {(Object.keys(SOURCES) as Source[]).map((s) => <option key={s} value={s}>{compact(SOURCES[s])}, {SOURCE_WORDS[s]}</option>)}
                </select>
              </>
            ) : (
              <>
                <span className="stmt-value" data-members="source">{x.source ? `the named source ${compact(SOURCES[x.source])}` : "no members stated"}</span>
                <select className="select" aria-label="Named source" value={x.source ?? ""} onChange={(e) => e.target.value && edit((g) => useNamedSource(g, ctx, e.target.value as Source))}>
                  {x.source === undefined && <option value="">choose…</option>}
                  {(Object.keys(SOURCES) as Source[]).map((s) => <option key={s} value={s}>{compact(SOURCES[s])}, {SOURCE_WORDS[s]}</option>)}
                </select>
                {x.source !== undefined && trail.length > 0 && (
                  <ol className="path-trail" aria-label="The path the name stands for">
                    <li className="path-trail-class">{ctx.carrier ? label(ctx.carrier) : "the carrier"}</li>
                    {trail.map((t, i) => <li key={i} className="path-trail-hop given"><span className="arrow">→</span> <span className="hop-name">{t}</span></li>)}
                  </ol>
                )}
                {members && x.source !== undefined && (
                  <button className="btn sm" disabled={(state?.hops.length ?? 0) === 0} onClick={() => edit((g) => replaceNamedSource(g, members))}><Replace size={13} /> Replace the named source with a path</button>
                )}
                {members && x.source === undefined && <button className="btn sm" onClick={() => onBuild(members)}><Route size={13} /> Build a members path</button>}
              </>
            )}
            <Marks marks={marks} part={["source", "path"]} />
          </div>
          <div className="stmt-row" data-part="link">
            <span className="stmt-label">Written as</span>
            <span className="stmt-value" data-link={ctx.resultProperty}>{ctx.resultProperty ? label(ctx.resultProperty) : "none"}</span>
            {ctx.resultProperty !== undefined && !terms.declared("property", ctx.resultProperty) && <span className="chip warn stmt-undeclared">undeclared</span>}
            {link && <button className="btn sm" aria-label="Pick the property each member is written as on the canvas" onClick={() => onBuild(link)}><Route size={13} /> Pick on the canvas</button>}
            <span className="small muted">the property each member is written as, which the members never read</span>
            <Marks marks={marks} part="link" />
          </div>
          <div className="stmt-row" data-part="node">
            {construction ? (
              <>
                <span className="small muted grow">A node is made for each member, stated beside this expansion.</span>
                <button className="btn sm" onClick={() => onOpen("member")}>Edit the node for each member</button>
              </>
            ) : (
              <>
                <span className="small muted grow">The members are written as statements on the instance. A node for each member makes a node of its own for each.</span>
                <button className="btn sm" onClick={() => { edit((g) => addMemberNode(g, ctx)); onOpen("member"); }}><Plus size={13} /> Add a node for each member</button>
              </>
            )}
          </div>
          <div className="stmt-row">
            <button className="btn ghost sm" disabled={construction !== undefined} title={construction ? "Remove the node for each member first, which no other kind of statement may be stated beside" : undefined} onClick={() => edit((g) => removeExpansion(g, ctx))}>
              <Trash2 size={12} /> Remove the expansion
            </button>
          </div>
        </>
      )}
    </div>
  );
}
