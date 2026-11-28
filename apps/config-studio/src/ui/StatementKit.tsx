// SPDX-License-Identifier: MPL-2.0
// What the construction, join and expansion editors of the surface canvas share (SVA-S1 part 4, SVA-Q57 (b)): the marks of the laws a statement is held to,
// shown beside the part they concern with the findings of the form on the same nodes, and a picker for a class or a property of the ontology the workspace holds,
// which also takes an IRI typed by the author and marks it undeclared. Each control makes one edit of the surface part through the function it is given.

import { useState } from "react";
import { localName } from "@lattice/authoring-domain";
import type { Baseline } from "../rdf/baseline";
import type { Issue } from "../rdf/report";
import { worst } from "../surface/findings";
import { validIri, type LawMark } from "../surface/statement";
import { SeverityIcon } from "./kit";

/** The marks of the laws that concern a part of a statement, as one list, each with the law and the rule it breaches. A part given as a prefix takes every part under it. */
export function Marks({ marks, part, label = "Law marks" }: { marks: readonly LawMark[]; part: string | string[]; label?: string }) {
  const parts = Array.isArray(part) ? part : [part];
  const shown = marks.filter((m) => parts.some((p) => m.part === p || m.part.startsWith(`${p}:`)));
  if (shown.length === 0) return null;
  return (
    <ul className="stmt-marks" aria-label={label}>
      {shown.map((m, i) => (
        <li key={i} className="chip warn stmt-mark" data-law={m.law} data-mark={m.code} data-part={m.part}>
          <strong>{m.law}</strong> <span>{m.message}</span>
        </li>
      ))}
    </ul>
  );
}

/** The findings of the form on the nodes a part of the statement is, which the form's list shows and the canvas places here as part 1 places them. */
export function Findings({ issues, focus }: { issues: readonly Issue[]; focus: readonly (string | undefined)[] }) {
  const found = issues.filter((i) => i.focus !== undefined && focus.includes(i.focus));
  if (found.length === 0) return null;
  const level = worst(found);
  return (
    <ul className="stmt-findings" aria-label="Findings of the form" data-level={level?.toLowerCase()}>
      {found.map((i, k) => (
        <li key={k} className="small row"><SeverityIcon severity={i.severity} size={13} /> <span>{i.message}</span></li>
      ))}
    </ul>
  );
}

/** A class or a property of the ontology, picked from the list or typed as an IRI, and marked where the ontology does not declare it. */
export function TermPicker({ kind, ontology, value, onPick, label, none, except }: { kind: "class" | "property"; ontology: Baseline; value?: string; onPick: (iri: string | undefined) => void; label: string; none?: string; except?: readonly (string | undefined)[] }) {
  const map = kind === "class" ? ontology.classes : ontology.properties;
  const declared = value !== undefined && map.has(value);
  const [typed, setTyped] = useState("");
  const [open, setOpen] = useState(false);
  // A term the laws forbid here is not offered. The one that stands is kept in the list so the select shows it.
  const options = [...map.values()].filter((o) => !except?.includes(o.iri) || o.iri === value).sort((a, b) => a.label.localeCompare(b.label) || a.iri.localeCompare(b.iri));
  const ok = validIri(typed.trim());
  return (
    <span className="stmt-picker">
      <select className="select" aria-label={label} value={value ?? ""} onChange={(e) => onPick(e.target.value === "" ? undefined : e.target.value)}>
        {value === undefined ? <option value="">{none ?? "choose…"}</option> : none ? <option value="">{none}</option> : null}
        {value !== undefined && !declared && <option value={value}>{localName(value)} (undeclared)</option>}
        {options.map((o) => <option key={o.iri} value={o.iri}>{o.label}</option>)}
      </select>
      {value !== undefined && !declared && <span className="chip warn stmt-undeclared" title="The ontology does not declare it, so the contract names a term of its own">undeclared</span>}
      {open ? (
        <>
          <input className="input" aria-label={`${label} IRI`} aria-invalid={typed.trim() !== "" && !ok} size={26} autoFocus placeholder="an absolute IRI" value={typed} onChange={(e) => setTyped(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ok && (onPick(typed.trim()), setTyped(""), setOpen(false))} />
          <button className="btn sm" disabled={!ok} aria-label={`Use the ${label} IRI`} onClick={() => (onPick(typed.trim()), setTyped(""), setOpen(false))}>Use</button>
          <button className="btn ghost sm" onClick={() => (setTyped(""), setOpen(false))}>Cancel</button>
        </>
      ) : (
        <button className="btn ghost sm" aria-label={`Type the ${label} as an IRI`} title="Names a term the ontology does not declare, which is marked undeclared" onClick={() => setOpen(true)}>Type an IRI</button>
      )}
    </span>
  );
}
