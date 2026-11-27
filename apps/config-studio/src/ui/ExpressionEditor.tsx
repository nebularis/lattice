// SPDX-License-Identifier: MPL-2.0
// The expression editor of the surface canvas (SVA-S1 part 3, SVA-Q57 (b), SVA-Q59). It opens on the canvas for the expression the result-target binding of a
// derivation states with srf:derivedAs, and draws it as the one line of infix text the result edge carries, which is read only, or as a tree of nodes, one for
// each expression node with its operands as its children. The author chooses the rendering and the browser remembers the choice for the workspace. Both
// are drawn from the configuration, so an edit shows in both at once. Editing is structured and on the tree, and each change is one `model.edit` made by a
// function of `surface/expressionEdit.ts`, so undo works as for any edit and the form beside it reads the same graph. Each node shows the datatype it has
// under the Surface README's typing rules and marks where what the contract states disagrees (`surface/typing.ts`). Nothing is parsed from the line.

import { useMemo, useState } from "react";
import { Check, Plus, X } from "lucide-react";
import { SRF, XSD, localName, type Graph } from "@lattice/authoring-domain";
import { datatypeName, infix, readExpression } from "../surface/expression";
import {
  COMPARISONS, KINDS, addExpression, changeKind, contextOf, isNumericDatatype, operandChoices, removeAt, setComparison, setLiteral, setOperand, setResultDatatype, setScale, statedBy, validLexical,
  type ExprContext, type KindId, type OperandTo,
} from "../surface/expressionEdit";
import { NUMERIC, type Mark, type TypedNode } from "../surface/typing";
import type { Terms } from "../surface/terms";
import { SeverityIcon } from "./kit";
import { useStudio } from "./Workspace";
import { worst } from "../surface/findings";

export type Rendering = "line" | "tree";

/** The author's choice of rendering, kept in this browser for the workspace, and the line where there is none or the browser will not say. */
export const renderingKey = (workspace: string) => `lattice-studio:expression-view:${workspace}`;

export function readRendering(workspace: string): Rendering {
  try {
    return localStorage.getItem(renderingKey(workspace)) === "tree" ? "tree" : "line";
  } catch {
    return "line";
  }
}

function writeRendering(workspace: string, rendering: Rendering): void {
  try {
    localStorage.setItem(renderingKey(workspace), rendering);
  } catch {
    // The choice is lost with the page where the browser keeps nothing, and the editor works as before.
  }
}

const ROLE_WORDS: Record<string, string> = { RequiredEvidenceRole: "required evidence", CandidateEvidenceRole: "candidate evidence" };
const numeric = (datatype: string | undefined) => (datatype !== undefined && isNumericDatatype(datatype) ? datatype : undefined);

/** The slot a node of the tree sits in, which the node itself names. */
const slotOf = (t: TypedNode) => t.node.slot;
const slotKey = (t: TypedNode) => (t.node.slot ? `${t.node.slot.parent}|${t.node.slot.predicate}` : "root");

interface Actions {
  graph: Graph;
  ctx: ExprContext;
  label: (iri: string) => string;
  edit: (change: (g: Graph) => Graph) => void;
  issues: { focus?: string; severity: "Violation" | "Warning" | "Info"; message: string }[];
}

export function ExpressionEditor({ contract, terms, onClose }: { contract: string; terms: Terms; onClose: () => void }) {
  const { id, model, baseline } = useStudio();
  const graph = model.state.configs.surface!.current;
  const known = model.state.baseline?.graph;
  const [rendering, setRendering] = useState<Rendering>(() => readRendering(id));
  const choose = (next: Rendering) => {
    setRendering(next);
    writeRendering(id, next);
  };
  const ctx = useMemo(() => contextOf(graph, contract, baseline.namespace, known), [graph, contract, baseline.namespace, known]);
  const label = (iri: string) => terms.label(iri);
  const stated = useMemo(() => statedBy(graph, ctx, (iri) => terms.label(iri)), [graph, ctx, terms]);
  const edit = (change: (g: Graph) => Graph) => model.edit("surface", change);
  const act: Actions = { graph, ctx, label, edit, issues: model.issues.surface };
  const name = graph.value(contract, SRF("contractKey")) ?? localName(contract);
  const [kind, setKind] = useState<Exclude<KindId, "literal">>("sum");

  return (
    <div className="path-mode expression-editor" role="region" aria-label="Expression editor">
      <div className="path-mode-head row">
        <strong className="grow">Expression of {name}</strong>
        <div className="mode-switch" role="group" aria-label="Expression rendering" style={{ margin: 0 }}>
          <button aria-pressed={rendering === "line"} title="The expression as one line of text, read only" onClick={() => choose("line")}>Line</button>
          <button aria-pressed={rendering === "tree"} title="The expression as a tree of nodes, which is edited" onClick={() => choose("tree")}>Tree</button>
        </div>
        <button className="btn sm primary" onClick={onClose}><Check size={13} /> Done</button>
      </div>
      {ctx.binding === undefined ? (
        <p className="small muted" role="status">This contract states no result-target binding, so it can state no expression. Add the binding in the form.</p>
      ) : stated.root === undefined ? (
        <div className="expr-add row" role="group" aria-label="Add an expression">
          <span className="small muted grow">The result-target binding states no expression. An expression states its operands from the contract's own evidence.</span>
          <select className="select" aria-label="Kind of the new expression" value={kind} onChange={(e) => setKind(e.target.value as Exclude<KindId, "literal">)}>
            {KINDS.filter((k) => k.id !== "literal").map((k) => <option key={k.id} value={k.id}>{k.word}</option>)}
          </select>
          <button className="btn sm primary" onClick={() => edit((g) => addExpression(g, ctx, kind))}><Plus size={13} /> Add an expression</button>
        </div>
      ) : (
        <div className="expr-line" role="status" aria-label="Expression as a line">
          <code>{stated.line}</code>
          <span className="small muted">{rendering === "line" ? "Read only. Switch to the tree to edit it." : "Read only. It follows the tree."}</span>
        </div>
      )}
      {stated.root !== undefined && rendering === "tree" && (
        <div className="expr-tree" role="group" aria-label="Expression tree">
          <Branch t={stated.typed} act={act} />
        </div>
      )}
    </div>
  );
}

function Branch({ t, act }: { t: TypedNode; act: Actions }) {
  return (
    <div className="expr-branch">
      <NodeBox t={t} act={act} />
      {t.children.length > 0 && (
        <div className="expr-children">
          {t.children.map((c) => <Branch key={slotKey(c)} t={c} act={act} />)}
        </div>
      )}
    </div>
  );
}

/** The kind an expression node is, by its class. */
function kindIdOf(n: TypedNode["node"]): KindId | undefined {
  return n.kind === "binary" ? KINDS.find((k) => k.type === n.type)?.id : n.kind === "round" ? "round" : n.kind === "choice" ? "choice" : n.kind === "literal" ? "literal" : undefined;
}

function title(t: TypedNode): string {
  const n = t.node;
  if (n.kind === "operand") return n.label;
  if (n.kind === "missing") return "…";
  return KINDS.find((k) => k.id === kindIdOf(n))?.word ?? "Expression";
}

function NodeBox({ t, act }: { t: TypedNode; act: Actions }) {
  const n = t.node;
  const slot = slotOf(t);
  const { graph, ctx, edit } = act;
  const iri = "iri" in n ? n.iri : undefined;
  const isExpression = n.kind === "binary" || n.kind === "round" || n.kind === "literal" || n.kind === "choice";
  const found = act.issues.filter((i) => iri !== undefined && i.focus === iri);
  const level = worst(found as never);
  const stated = n.kind === "binary" || n.kind === "round" || n.kind === "choice" ? n.datatype : n.kind === "literal" ? n.statedDatatype : undefined;
  const [adding, setAdding] = useState(false);
  const at = slot ? { parent: slot.parent, predicate: slot.predicate } : undefined;
  // The expression's own slot is the result-target binding's srf:derivedAs, which takes no operand to choose, only a kind and a removal.
  const isRootSlot = at !== undefined && at.parent === ctx.binding;
  const choices = useMemo(() => (at ? operandChoices(graph, ctx, at) : { evidence: [], expressions: [] }), [graph, ctx, at?.parent, at?.predicate]); // eslint-disable-line react-hooks/exhaustive-deps
  const applyTo = (to: OperandTo) => at && edit((g) => setOperand(g, ctx, at, to));
  const tag = n.kind === "operand" ? (ROLE_WORDS[n.role ?? ""] ?? "evidence") : n.kind === "missing" ? "missing" : "expression";

  const pick = (value: string) => {
    if (value === "") return;
    if (value === "literal") return setAdding(true);
    const [what, rest] = [value.slice(0, value.indexOf(":")), value.slice(value.indexOf(":") + 1)];
    if (what === "evidence") applyTo({ kind: "evidence", iri: rest });
    else if (what === "new") applyTo({ kind: "new", expression: rest as Exclude<KindId, "literal"> });
    else if (what === "existing") applyTo({ kind: "existing", iri: rest });
  };

  return (
    <div
      className={`canvas-node expr-node ${n.kind}${t.marks.length ? " marked" : ""}${level ? ` found-${level.toLowerCase()}` : ""}`}
      data-kind={n.kind} data-iri={iri} data-slot={slot ? `${slot.parent}|${slot.predicate}` : "root"} data-datatype={t.datatype ? datatypeName(t.datatype) : undefined}
    >
      <div className="surface-tag">
        {t.role ? `${t.role}, ${tag}` : tag}
        {level && <span className="surface-finding" title={found.map((i) => i.message).join("\n")}><SeverityIcon severity={level} size={13} /> {found.length}</span>}
      </div>
      <div className="expr-head">
        <strong className="expr-title">{title(t)}</strong>
        {n.kind !== "missing" && <span className="chip expr-datatype" title="The datatype this node has under the typing rules">: {datatypeName(t.datatype)}</span>}
      </div>
      {n.kind === "missing" && <div className="small muted">{n.part}</div>}
      {n.kind === "operand" && n.datatype === undefined && <div className="small muted">states no datatype</div>}
      {t.marks.length > 0 && (
        <ul className="expr-marks" aria-label="Typing marks">
          {t.marks.map((m, i) => <MarkRow key={i} mark={m} apply={iri !== undefined && m.fix ? () => edit((g) => setResultDatatype(g, iri, m.fix!)) : undefined} />)}
        </ul>
      )}
      {isExpression && (
        <div className="expr-fields">
          <label className="expr-field">
            <span>Kind</span>
            <select className="select" aria-label="Kind" value={kindIdOf(n)} onChange={(e) => edit((g) => changeKind(g, iri!, e.target.value as KindId))}>
              {KINDS.map((k) => <option key={k.id} value={k.id}>{k.word}</option>)}
            </select>
          </label>
          {n.kind === "round" && <ScaleField node={iri!} scale={n.scale} edit={edit} />}
          {n.kind === "choice" && (
            <label className="expr-field">
              <span>Compare</span>
              <select className="select" aria-label="Comparison" value={COMPARISONS.find((c) => c.symbol === n.comparison)?.symbol ?? ""} onChange={(e) => edit((g) => setComparison(g, iri!, e.target.value))}>
                {n.comparison === undefined && <option value="">…</option>}
                {COMPARISONS.map((c) => <option key={c.symbol} value={c.symbol}>{c.symbol}</option>)}
              </select>
            </label>
          )}
          {n.kind === "literal" && <LiteralFields node={iri!} value={n.value} datatype={n.valueDatatype ?? stated} edit={edit} />}
          {n.kind !== "literal" && (
            <label className="expr-field">
              <span>Datatype</span>
              <select className="select" aria-label="Result datatype" value={stated ?? ""} onChange={(e) => edit((g) => setResultDatatype(g, iri!, e.target.value))}>
                {(stated === undefined || !numeric(stated)) && <option value="" disabled>{stated === undefined ? "none stated" : datatypeName(stated)}</option>}
                {NUMERIC.map((d) => <option key={d} value={d}>{datatypeName(d)}</option>)}
              </select>
            </label>
          )}
        </div>
      )}
      {at && !isRootSlot && (
        <div className="expr-fields">
          <label className="expr-field">
            <span>Operand</span>
            <select className="select" aria-label={`Set the ${t.role}`} value="" onChange={(e) => pick(e.target.value)}>
              <option value="">{n.kind === "missing" ? "choose…" : "replace with…"}</option>
              {choices.evidence.length > 0 && (
                <optgroup label="Evidence of this contract">
                  {choices.evidence.map((x) => <option key={x.iri} value={`evidence:${x.iri}`}>{act.label(x.property)}{x.datatype ? ` : ${datatypeName(x.datatype)}` : ""}</option>)}
                </optgroup>
              )}
              <optgroup label="A new expression">
                {KINDS.filter((k) => k.id !== "literal").map((k) => <option key={k.id} value={`new:${k.id}`}>{k.word}</option>)}
              </optgroup>
              <optgroup label="A constant">
                <option value="literal">A typed literal…</option>
              </optgroup>
              {choices.expressions.length > 0 && (
                <optgroup label="An expression already here">
                  {choices.expressions.map((e) => <option key={e} value={`existing:${e}`}>{infix(readExpression(graph, e, act.label, {}))}</option>)}
                </optgroup>
              )}
            </select>
          </label>
        </div>
      )}
      {adding && at && <NewLiteral onCancel={() => setAdding(false)} onSet={(value, datatype) => (applyTo({ kind: "literal", value, datatype }), setAdding(false))} />}
      {(isExpression || n.kind === "operand") && (
        <button className="btn ghost sm expr-remove" aria-label={`Remove ${t.role ?? "the expression"}`} title={n.kind === "operand" ? "Lets the evidence go, which stays in the contract, and leaves a placeholder" : "Removes this node and the nodes only it states, and leaves a placeholder"} onClick={() => at && edit((g) => removeAt(g, ctx, at))}>
          <X size={12} /> Remove
        </button>
      )}
    </div>
  );
}

function MarkRow({ mark, apply }: { mark: Mark; apply?: () => void }) {
  return (
    <li className="chip warn expr-mark" data-mark={mark.code}>
      <span>{mark.message}</span>
      {apply && mark.fix && <button className="btn ghost sm" aria-label={`Use ${datatypeName(mark.fix)}`} onClick={apply}>Use {datatypeName(mark.fix)}</button>}
    </li>
  );
}

/** A rounding's scale, an integer that may be negative, written when the field is left or Enter is pressed. */
function ScaleField({ node, scale, edit }: { node: string; scale?: number; edit: Actions["edit"] }) {
  const [draft, setDraft] = useState<string>();
  const shown = draft ?? (scale === undefined ? "" : String(scale));
  const bad = draft !== undefined && draft.trim() !== "" && !/^[+-]?\d+$/.test(draft.trim());
  const commit = () => {
    if (draft !== undefined && /^[+-]?\d+$/.test(draft.trim())) edit((g) => setScale(g, node, Number(draft.trim())));
    setDraft(undefined);
  };
  return (
    <label className="expr-field">
      <span>Scale</span>
      <input
        className="input" aria-label="Scale" aria-invalid={bad} inputMode="numeric" size={4} value={shown} placeholder="…"
        onChange={(e) => setDraft(e.target.value)} onBlur={commit} onKeyDown={(e) => e.key === "Enter" && commit()}
      />
      {bad && <span className="small expr-bad">a whole number</span>}
    </label>
  );
}

/** A typed literal's value and datatype, written together when the value is written as the datatype. */
function LiteralFields({ node, value, datatype, edit }: { node: string; value?: string; datatype?: string; edit: Actions["edit"] }) {
  const [draft, setDraft] = useState<string>();
  const type = numeric(datatype) ?? XSD("decimal");
  const shown = draft ?? value ?? "";
  const bad = draft !== undefined && draft !== "" && !validLexical(draft.trim(), type);
  const commit = () => {
    if (draft !== undefined && validLexical(draft.trim(), type)) edit((g) => setLiteral(g, node, draft.trim(), type));
    setDraft(undefined);
  };
  return (
    <>
      <label className="expr-field">
        <span>Value</span>
        <input className="input" aria-label="Value" aria-invalid={bad} size={8} value={shown} placeholder="…" onChange={(e) => setDraft(e.target.value)} onBlur={commit} onKeyDown={(e) => e.key === "Enter" && commit()} />
        {bad && <span className="small expr-bad">not a {datatypeName(type)}</span>}
      </label>
      <label className="expr-field">
        <span>Datatype</span>
        <select className="select" aria-label="Literal datatype" value={numeric(datatype) ?? ""} onChange={(e) => edit((g) => setResultDatatype(g, node, e.target.value))}>
          {numeric(datatype) === undefined && <option value="" disabled>{datatype ? datatypeName(datatype) : "none"}</option>}
          {NUMERIC.map((d) => <option key={d} value={d}>{datatypeName(d)}</option>)}
        </select>
      </label>
    </>
  );
}

/** The value and datatype of a literal that is to be an operand. It is made only when the value is written as the datatype. */
function NewLiteral({ onSet, onCancel }: { onSet: (value: string, datatype: string) => void; onCancel: () => void }) {
  const [value, setValue] = useState("");
  const [datatype, setDatatype] = useState<string>(XSD("decimal"));
  const ok = validLexical(value.trim(), datatype);
  return (
    <div className="expr-fields expr-new-literal" role="group" aria-label="A typed literal">
      <label className="expr-field">
        <span>Value</span>
        <input className="input" aria-label="Literal value" size={8} autoFocus value={value} onChange={(e) => setValue(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ok && onSet(value.trim(), datatype)} />
      </label>
      <label className="expr-field">
        <span>Datatype</span>
        <select className="select" aria-label="New literal datatype" value={datatype} onChange={(e) => setDatatype(e.target.value)}>
          {NUMERIC.map((d) => <option key={d} value={d}>{datatypeName(d)}</option>)}
        </select>
      </label>
      {value.trim() !== "" && !ok && <span className="small expr-bad">not a {datatypeName(datatype)}</span>}
      <button className="btn sm primary" disabled={!ok} onClick={() => onSet(value.trim(), datatype)}>Set</button>
      <button className="btn sm" onClick={onCancel}>Cancel</button>
    </div>
  );
}
