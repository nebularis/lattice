// SPDX-License-Identifier: MPL-2.0
// The join editor of the surface canvas (SVA-S1 part 4, SVA-Q57 (b)): the second carrier, the pairs of the key with the datatype the left value is cast to, and the two
// counts that limit what an instance writes, as the Surface README's section 6.17 gives them. A count offers `default`, which states nothing and says what the vocabulary
// means by leaving it out, beside its two choices, so an author can return it to its default. A pair is a left binding that reads the contract's own carrier and a right
// binding that reads the second, and a property picked for a side is read by a new binding of the evidence kind the statement is on. Each control is one `model.edit`
// made by a function of `surface/joinEdit.ts`, and the laws a breach of which the editor can know are never offered.

import { useMemo, useState } from "react";
import { Check, Plus, Route, Trash2 } from "lucide-react";
import { SRF, localName } from "@lattice/authoring-domain";
import type { Baseline } from "../rdf/baseline";
import type { PathPlace } from "../surface/drawing";
import {
  CARDINALITIES, DEFAULTS, WORDS, addJoin, addPair, joinChoices, joinMarks, linksOf, matchesOf, readJoin, removeJoin, removePair, setCardinality, setPairDatatype, setPairSide, setSecondCarrier,
  type Cardinality, type Side,
} from "../surface/joinEdit";
import { JOIN_DATATYPES, statementContext, xsdName, type Evidence } from "../surface/statement";
import type { Terms } from "../surface/terms";
import { Findings, Marks, TermPicker } from "./StatementKit";
import { useStudio } from "./Workspace";

/** The properties an instance of the class can have, by declared domain, and those whose domain is not stated, which any class may have. */
function propertiesFor(o: Baseline, cls: string | undefined) {
  if (!cls) return [];
  const lineage = new Set(o.ancestors(cls));
  return [...o.properties.values()].filter((p) => p.domains.length === 0 || p.domains.some((d) => lineage.has(d))).sort((a, b) => a.label.localeCompare(b.label) || a.iri.localeCompare(b.iri));
}

const sideValue = (s?: string) => (s ? `binding:${s}` : "");
const parseSide = (value: string): Side | undefined => (value.startsWith("binding:") ? { binding: value.slice("binding:".length) } : value.startsWith("property:") ? { property: value.slice("property:".length) } : undefined);

export function JoinEditor({ contract, ontology, terms, onClose, onBuild }: { contract: string; ontology: Baseline; terms: Terms; onClose: () => void; onBuild: (place: PathPlace) => void }) {
  const { model, baseline } = useStudio();
  const graph = model.state.configs.surface!.current;
  const known = model.state.baseline?.graph;
  const ctx = useMemo(() => statementContext(graph, contract, baseline.namespace, known), [graph, contract, baseline.namespace, known]);
  const j = readJoin(graph, ctx);
  const choices = useMemo(() => joinChoices(graph, ctx), [graph, ctx]);
  const marks = useMemo(() => joinMarks(graph, ctx), [graph, ctx]);
  const edit = (change: (g: typeof graph) => typeof graph) => model.edit("surface", change);
  const name = graph.value(contract, SRF("contractKey")) ?? localName(contract);
  // The second carrier is on the right bindings, so with no pair it is only chosen, and a new pair states it.
  const [pending, setPending] = useState<string>();
  const carrier = j?.secondCarrier ?? pending;
  const [left, setLeft] = useState("");
  const [right, setRight] = useState("");
  const [datatype, setDatatype] = useState("");
  const own = propertiesFor(ontology, ctx.carrier);
  const second = propertiesFor(ontology, carrier);
  const link: PathPlace | undefined = ctx.result ? { kind: "binding", node: ctx.result, contract, carrier: ctx.carrier, label: "the link property" } : undefined;
  const bindingLabel = (e: Evidence) => `${e.property ? terms.label(e.property) : "…"} (${e.role === "required" ? "required" : "candidate"})`;
  const sideOptions = (existing: Evidence[], properties: ReturnType<typeof propertiesFor>, current?: string) => (
    <>
      {current !== undefined && !existing.some((e) => e.iri === current) && <option value={sideValue(current)}>{localName(current)}</option>}
      {existing.length > 0 && (
        <optgroup label="Evidence of this contract">
          {existing.map((e) => <option key={e.iri} value={sideValue(e.iri)}>{bindingLabel(e)}</option>)}
        </optgroup>
      )}
      {properties.length > 0 && (
        <optgroup label={`A new ${choices.kind === "required" ? "required" : "candidate"} binding reading`}>
          {properties.map((p) => <option key={p.iri} value={`property:${p.iri}`}>{p.label}</option>)}
        </optgroup>
      )}
    </>
  );
  const canAdd = parseSide(left) !== undefined && parseSide(right) !== undefined && carrier !== undefined;
  const missing = j ? undefined : !ctx.result ? "This contract states no result-target binding, so it can state no join. Add the binding in the form." : ctx.kind === "join" ? undefined : "This contract is not a join, so it states no join.";

  const rule = (which: "matches" | "links") => {
    const stated = which === "matches" ? matchesOf(j!) : linksOf(j!);
    const label = which === "matches" ? "One value finds" : "One instance links";
    return (
      <div className="stmt-row" data-part={which}>
        <span className="stmt-label">{label}</span>
        <select className="select" aria-label={label} value={stated ?? "default"} onChange={(e) => edit((g) => setCardinality(g, ctx, which, e.target.value as Cardinality | "default"))}>
          <option value="default">default, {WORDS[DEFAULTS[which]]}</option>
          {(Object.keys(CARDINALITIES) as Cardinality[]).map((c) => <option key={c} value={c}>{WORDS[c]}</option>)}
        </select>
        <span className="small muted" data-rule={which}>{stated === undefined ? `States nothing, which means ${WORDS[DEFAULTS[which]]}.` : `States ${WORDS[stated]}. The default is ${WORDS[DEFAULTS[which]]}.`}</span>
        <Marks marks={marks} part={which} />
      </div>
    );
  };

  return (
    <div className="path-mode statement-editor" role="region" aria-label="Join editor">
      <div className="path-mode-head row">
        <strong className="grow">Join of {name}</strong>
        <button className="btn sm primary" onClick={onClose}><Check size={13} /> Done</button>
      </div>
      {!j ? (
        <>
          <Marks marks={marks} part={["node", "link"]} />
          <div className="expr-add row" role="group" aria-label="Add a join">
            <span className="small muted grow">{missing ?? "The result-target binding states no join. A join relates an instance to an instance of a second carrier that a value of the key names."}</span>
            {missing === undefined && <button className="btn sm primary" onClick={() => edit((g) => addJoin(g, ctx))}><Plus size={13} /> Add a join</button>}
          </div>
        </>
      ) : (
        <>
          <Marks marks={marks} part="node" />
          <Findings issues={model.issues.surface} focus={[j.node, ctx.result]} />
          <div className="stmt-row" data-part="carrier">
            <span className="stmt-label">Second carrier</span>
            <TermPicker kind="class" label="Second carrier" ontology={ontology} value={carrier} except={[ctx.carrier]} onPick={(iri) => iri && (j.pairs.length ? edit((g) => setSecondCarrier(g, ctx, iri)) : setPending(iri))} />
            {j.pairs.length === 0 && carrier !== undefined && <span className="small muted">stated by the right binding of the first pair</span>}
            <Marks marks={marks} part={["carrier", "kind"]} />
          </div>
          <div className="stmt-row stmt-pairs" data-part="pairs">
            <span className="stmt-label">Key</span>
            <ul className="stmt-list" aria-label="Pairs of the key">
              {j.pairs.map((p) => {
                const rightBinding = ctx.evidence.find((e) => e.iri === p.right);
                const stated = rightBinding ? graph.value(rightBinding.iri, SRF("bindsDatatype")) : undefined;
                return (
                  <li key={p.key} className="stmt-item" data-pair={p.key}>
                    <select className="select" aria-label="Left binding" value={sideValue(p.left)} onChange={(e) => { const side = parseSide(e.target.value); if (side) edit((g) => setPairSide(g, ctx, p.key, "left", side)); }}>
                      {sideOptions(choices.left, own, p.left)}
                    </select>
                    <span className="stmt-eq" title="The relation is equality of the two values">=</span>
                    <select className="select" aria-label="Right binding" value={sideValue(p.right)} onChange={(e) => { const side = parseSide(e.target.value); if (side) edit((g) => setPairSide(g, ctx, p.key, "right", side, carrier)); }}>
                      {sideOptions(choices.right, second, p.right)}
                    </select>
                    <select className="select" aria-label="Compared as" value={stated ?? ""} onChange={(e) => edit((g) => setPairDatatype(g, ctx, p.key, e.target.value === "" ? undefined : e.target.value))}>
                      <option value="">the same term, no datatype</option>
                      {stated !== undefined && !JOIN_DATATYPES.includes(stated) && <option value={stated}>{localName(stated)}</option>}
                      {JOIN_DATATYPES.map((d) => <option key={d} value={d}>{xsdName(d)}</option>)}
                    </select>
                    <button className="btn ghost sm" aria-label="Remove the key pair" onClick={() => edit((g) => removePair(g, ctx, p.key))}><Trash2 size={12} /> Remove</button>
                    <Marks marks={marks} part={`pair:${p.key}`} />
                  </li>
                );
              })}
              <li className="stmt-item stmt-add" role="group" aria-label="Add a key pair">
                <select className="select" aria-label="New left binding" value={left} onChange={(e) => setLeft(e.target.value)}>
                  <option value="">choose the left…</option>
                  {sideOptions(choices.left.filter((e) => !j.pairs.some((p) => p.left === e.iri)), own)}
                </select>
                <span className="stmt-eq">=</span>
                <select className="select" aria-label="New right binding" value={right} disabled={carrier === undefined} title={carrier === undefined ? "Choose the second carrier first" : undefined} onChange={(e) => setRight(e.target.value)}>
                  <option value="">choose the right…</option>
                  {sideOptions(choices.right.filter((e) => !j.pairs.some((p) => p.right === e.iri)), second)}
                </select>
                <select className="select" aria-label="New pair compared as" value={datatype} onChange={(e) => setDatatype(e.target.value)}>
                  <option value="">the same term, no datatype</option>
                  {JOIN_DATATYPES.map((d) => <option key={d} value={d}>{xsdName(d)}</option>)}
                </select>
                <button
                  className="btn sm" disabled={!canAdd}
                  onClick={() => { edit((g) => addPair(g, ctx, { left: parseSide(left)!, right: parseSide(right)!, carrier, datatype: datatype || undefined })); setLeft(""); setRight(""); setDatatype(""); }}
                ><Plus size={13} /> Add a key pair</button>
              </li>
            </ul>
            <Marks marks={marks} part="pairs" />
          </div>
          {rule("matches")}
          {rule("links")}
          <div className="stmt-row" data-part="link">
            <span className="stmt-label">Link property</span>
            <span className="stmt-value" data-link={ctx.resultProperty}>{ctx.resultProperty ? terms.label(ctx.resultProperty) : "none"}</span>
            {ctx.resultProperty !== undefined && !terms.declared("property", ctx.resultProperty) && <span className="chip warn stmt-undeclared">undeclared</span>}
            {link && <button className="btn sm" aria-label="Pick the link property on the canvas" onClick={() => onBuild(link)}><Route size={13} /> Pick on the canvas</button>}
            <span className="small muted">the property that links each instance to the instance it names</span>
            <Marks marks={marks} part="link" />
          </div>
          <div className="stmt-row">
            <button className="btn ghost sm" onClick={() => edit((g) => removeJoin(g, ctx))}><Trash2 size={12} /> Remove the join</button>
          </div>
        </>
      )}
    </div>
  );
}
