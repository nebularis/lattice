// SPDX-License-Identifier: MPL-2.0
// The construction editor of the surface canvas (SVA-S1 part 4, SVA-Q57 (b)), for the constructed node of a graph construction and for the node an expansion makes for
// each member, which is the same statement beside an expansion statement. It opens on the canvas from the box that draws the statement or from a button on it, edits
// what the Surface README's section 6.16 states and nothing it does not, and marks a breach of the laws the node is held to, computed by the rules the shapes state,
// beside the findings of the form. Each control is one `model.edit` made by a function of `surface/constructionEdit.ts`, so undo works as for any edit.

import { useMemo, useState } from "react";
import { Check, Plus, Route, Trash2 } from "lucide-react";
import { SRF, localName } from "@lattice/authoring-domain";
import type { Baseline } from "../rdf/baseline";
import type { PathPlace } from "../surface/drawing";
import {
  addConstruction, addKeyBinding, addMemberNode, addWrite, constructionChoices, constructionMarks, readConstruction, removeConstruction, removeKeyBinding, removeWrite, setConstructedClass,
  setIdentity, setKeyMember, setMemberName, setWriteFrom, setWriteProperty, type Identity, type WriteFrom,
} from "../surface/constructionEdit";
import { readExpansion } from "../surface/expansionEdit";
import { statementContext, type Evidence } from "../surface/statement";
import type { Terms } from "../surface/terms";
import { Findings, Marks, TermPicker } from "./StatementKit";
import { useStudio } from "./Workspace";

const IDENTITY_WORDS: Record<Identity, string> = { PerInstance: "For each instance", ByKey: "By a key", MemberNode: "The member itself" };
const PER_INSTANCE_UNDER_EXPANSION = "For each instance and member";

const sourceValue = (from: WriteFrom | undefined) => (from === undefined ? "" : "member" in from ? "member" : `binding:${from.binding}`);
const parseSource = (value: string): WriteFrom | undefined => (value === "member" ? { member: true } : value.startsWith("binding:") ? { binding: value.slice("binding:".length) } : undefined);

export function ConstructionEditor({ contract, member, ontology, terms, onClose, onBuild, onOpen }: {
  contract: string;
  member: boolean;
  ontology: Baseline;
  terms: Terms;
  onClose: () => void;
  onBuild: (place: PathPlace) => void;
  onOpen: (kind: "expansion") => void;
}) {
  const { model, baseline } = useStudio();
  const graph = model.state.configs.surface!.current;
  const known = model.state.baseline?.graph;
  const ctx = useMemo(() => statementContext(graph, contract, baseline.namespace, known), [graph, contract, baseline.namespace, known]);
  const c = readConstruction(graph, ctx);
  const choices = useMemo(() => constructionChoices(graph, ctx), [graph, ctx]);
  const marks = useMemo(() => constructionMarks(graph, ctx), [graph, ctx]);
  const edit = (change: (g: typeof graph) => typeof graph) => model.edit("surface", change);
  const name = graph.value(contract, SRF("contractKey")) ?? localName(contract);
  const word = member ? "node for each member" : "construction";
  const [property, setProperty] = useState<string>();
  const [source, setSource] = useState("");
  const expansion = readExpansion(graph, ctx);

  const evidenceLabel = (e: Evidence) => `${e.property ? terms.label(e.property) : "…"} (${e.role === "required" ? "required" : "candidate"})`;
  const keyList = c ? [...new Set([...ctx.evidence.filter((e) => e.role === "required" && e.property !== undefined).map((e) => e.iri), ...c.keyBindings])] : [];
  const bindingLabel = (iri: string) => {
    const e = ctx.evidence.find((x) => x.iri === iri);
    return e ? evidenceLabel(e) : localName(iri);
  };
  const link = ctx.result ? ({ kind: "binding", node: ctx.result, contract, carrier: ctx.carrier, label: "the link property" } satisfies PathPlace) : undefined;
  const addable = property !== undefined && parseSource(source) !== undefined;

  // What this contract may state, which decides what the editor says where it states none.
  const missing = (() => {
    if (c) return undefined;
    if (!ctx.result) return `This contract states no result-target binding, so it can state no ${word}. Add the binding in the form.`;
    if (member) return expansion ? undefined : "This contract states no expansion statement, which a node for each member is stated beside. Add the expansion first.";
    return ctx.kind === "construction" ? undefined : "This contract is not a graph construction, so it states no construction.";
  })();

  return (
    <div className="path-mode statement-editor" role="region" aria-label={member ? "Node for each member editor" : "Construction editor"}>
      <div className="path-mode-head row">
        <strong className="grow">{member ? "Node for each member of" : "Construction of"} {name}</strong>
        {member && <button className="btn sm" onClick={() => onOpen("expansion")}>Edit the expansion</button>}
        <button className="btn sm primary" onClick={onClose}><Check size={13} /> Done</button>
      </div>
      {!c && <Marks marks={marks} part={["node", "link"]} />}
      {!c ? (
        <div className="expr-add row" role="group" aria-label={member ? "Add a node for each member" : "Add a construction"}>
          <span className="small muted grow">{missing ?? `The result-target binding states no ${word}. ${member ? "It is made for each member the expansion reaches." : "It writes a node of a class, linked from each instance."}`}</span>
          {missing === undefined && (
            <button className="btn sm primary" onClick={() => edit((g) => (member ? addMemberNode(g, ctx) : addConstruction(g, ctx)))}>
              <Plus size={13} /> {member ? "Add a node for each member" : "Add a construction"}
            </button>
          )}
        </div>
      ) : (
        <>
          <Marks marks={marks} part="node" />
          <Findings issues={model.issues.surface} focus={[c.node, ctx.result]} />
          <div className="stmt-row" data-part="class">
            <span className="stmt-label">Class</span>
            <TermPicker kind="class" label="Class" ontology={ontology} value={c.class} onPick={(iri) => edit((g) => setConstructedClass(g, ctx, iri))} />
            <Marks marks={marks} part="class" />
          </div>
          <div className="stmt-row" data-part="identity">
            <span className="stmt-label">Identity</span>
            <div role="radiogroup" aria-label="Identity" className="stmt-choices">
              {choices.identities.map((identity) => (
                <label key={identity} className="stmt-choice">
                  <input type="radio" name={`identity-${contract}`} checked={c.identity === identity} onChange={() => edit((g) => setIdentity(g, ctx, identity))} />
                  {identity === "PerInstance" && member ? PER_INSTANCE_UNDER_EXPANSION : IDENTITY_WORDS[identity]}
                </label>
              ))}
            </div>
            <Marks marks={marks} part="identity" />
          </div>
          {c.identity === "ByKey" && (
            <div className="stmt-row" data-part="key">
              <span className="stmt-label">Key</span>
              <div role="group" aria-label="Key" className="stmt-choices">
                {keyList.map((b) => (
                  <label key={b} className="stmt-choice">
                    <input
                      type="checkbox" checked={c.keyBindings.includes(b)} aria-label={`Key part ${bindingLabel(b)}`}
                      onChange={(e) => edit((g) => (e.target.checked ? addKeyBinding(g, ctx, b) : removeKeyBinding(g, ctx, b)))}
                    />
                    {bindingLabel(b)}
                  </label>
                ))}
                {keyList.length === 0 && <span className="small muted">The contract holds no required evidence to key by.</span>}
                {(choices.member.key || c.keyMember) && (
                  <label className="stmt-choice">
                    <input type="checkbox" checked={c.keyMember} aria-label="Key part the member" onChange={(e) => edit((g) => setKeyMember(g, ctx, e.target.checked))} />
                    The member
                  </label>
                )}
              </div>
              <Marks marks={marks} part="key" />
            </div>
          )}
          {c.identity !== "ByKey" && <Marks marks={marks} part="key" />}
          {(choices.member.name || c.memberNames.length > 0) && (
            <div className="stmt-row" data-part="name">
              <span className="stmt-label">Stable name</span>
              <TermPicker kind="property" label="Member name" none="no name" ontology={ontology} value={c.memberName} onPick={(iri) => edit((g) => setMemberName(g, ctx, iri))} />
              <span className="small muted">a property of the members that names each one</span>
              <Marks marks={marks} part="name" />
            </div>
          )}
          <div className="stmt-row stmt-writes" data-part="writes">
            <span className="stmt-label">Writes</span>
            <ul className="stmt-list" aria-label="Values it writes">
              {c.writes.map((w) => (
                <li key={w.key} className="stmt-item" data-write={w.key} data-property={w.property}>
                  <TermPicker kind="property" label="Property written" ontology={ontology} value={w.property} onPick={(iri) => iri && edit((g) => setWriteProperty(g, ctx, w.key, iri))} />
                  <span className="arrow">←</span>
                  <select
                    className="select" aria-label="Read from" value={sourceValue(w.member ? { member: true } : w.binding ? { binding: w.binding } : undefined)}
                    onChange={(e) => { const from = parseSource(e.target.value); if (from) edit((g) => setWriteFrom(g, ctx, w.key, from)); }}
                  >
                    {w.binding === undefined && !w.member && <option value="">choose…</option>}
                    {w.binding !== undefined && !choices.from.some((e) => e.iri === w.binding) && <option value={`binding:${w.binding}`}>{bindingLabel(w.binding)}</option>}
                    {choices.from.map((e) => <option key={e.iri} value={`binding:${e.iri}`}>{evidenceLabel(e)}</option>)}
                    {choices.member.value && <option value="member">the member</option>}
                  </select>
                  <button className="btn ghost sm" aria-label={`Remove the value ${w.property ? terms.label(w.property) : ""}`.trim()} onClick={() => edit((g) => removeWrite(g, ctx, w.key))}><Trash2 size={12} /> Remove</button>
                  <Marks marks={marks} part={`write:${w.key}`} />
                </li>
              ))}
              <li className="stmt-item stmt-add" role="group" aria-label="Add a value">
                <TermPicker kind="property" label="New property" ontology={ontology} value={property} onPick={setProperty} />
                <span className="arrow">←</span>
                <select className="select" aria-label="New value read from" value={source} onChange={(e) => setSource(e.target.value)}>
                  <option value="">choose…</option>
                  {choices.from.map((e) => <option key={e.iri} value={`binding:${e.iri}`}>{evidenceLabel(e)}</option>)}
                  {choices.member.value && <option value="member">the member</option>}
                </select>
                <button
                  className="btn sm" disabled={!addable} onClick={() => { const from = parseSource(source)!; edit((g) => addWrite(g, ctx, property!, from)); setProperty(undefined); setSource(""); }}
                ><Plus size={13} /> Add a value</button>
              </li>
            </ul>
            <Marks marks={marks} part="writes" />
          </div>
          <div className="stmt-row" data-part="link">
            <span className="stmt-label">Link property</span>
            <span className="stmt-value" data-link={ctx.resultProperty}>{ctx.resultProperty ? terms.label(ctx.resultProperty) : "none"}</span>
            {ctx.resultProperty !== undefined && !terms.declared("property", ctx.resultProperty) && <span className="chip warn stmt-undeclared">undeclared</span>}
            {link && <button className="btn sm" aria-label="Pick the link property on the canvas" onClick={() => onBuild(link)}><Route size={13} /> Pick on the canvas</button>}
            <span className="small muted">the property that links each {member ? "instance to each node" : "instance to the node"}</span>
            <Marks marks={marks} part="link" />
          </div>
          <div className="stmt-row">
            <button className="btn ghost sm" onClick={() => edit((g) => removeConstruction(g, ctx))}><Trash2 size={12} /> Remove the {word}</button>
          </div>
        </>
      )}
    </div>
  );
}
