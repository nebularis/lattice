// SPDX-License-Identifier: MPL-2.0
// Read-only forms of the axioms of a class, a property or an individual of the baseline (SVA-O3,
// decision SVA-Q9). A class expression is drawn as nested structure. What the reader does not
// recognise is in a plain table, so nothing the baseline states about an element is hidden.

import { useMemo, type ReactNode } from "react";
import { PREFIXES, compact } from "@lattice/authoring-domain";
import {
  classAxioms,
  individualAxioms,
  propertyAxioms,
  type Annotation,
  type ClassExpr,
  type PropertyRef,
  type PropertyShapeRow,
  type Row,
  type TermValue,
} from "../rdf/axioms";
import type { Baseline } from "../rdf/baseline";
import { href } from "./kit";
import { useStudio } from "./Workspace";

interface Ctx {
  baseline: Baseline;
  workspace: string;
}

function useCtx(baseline: Baseline): Ctx {
  return { baseline, workspace: useStudio().id };
}

const prefixes = (baseline: Baseline) => ({ ...PREFIXES, ...baseline.graph.prefixes });

/** A named class, property or individual. A link when the baseline says something about it. */
function Ref({ iri, ctx }: { iri: string; ctx: Ctx }) {
  const shown = compact(iri, prefixes(ctx.baseline));
  if (!ctx.baseline.declares(iri)) return <span className="mono axiom-ref" title={iri}>{shown}</span>;
  return (
    <a className="axiom-ref" href={href("w", ctx.workspace, "baseline", iri)} title={iri}>
      {ctx.baseline.label(iri)} <span className="small muted mono">{shown}</span>
    </a>
  );
}

function PropRef({ p, ctx }: { p: PropertyRef; ctx: Ctx }) {
  return p.inverse ? (
    <span className="axiom-inverse">
      inverse of <Ref iri={p.iri} ctx={ctx} />
    </span>
  ) : (
    <Ref iri={p.iri} ctx={ctx} />
  );
}

function Term({ t, ctx }: { t: TermValue; ctx: Ctx }) {
  if (t.kind === "iri") return <Ref iri={t.value} ctx={ctx} />;
  if (t.kind === "literal") {
    return (
      <span className="axiom-literal">
        “{t.value}”
        {t.language && <span className="small muted"> @{t.language}</span>}
        {t.datatype && <span className="small muted mono"> {compact(t.datatype, prefixes(ctx.baseline))}</span>}
      </span>
    );
  }
  return (
    <span className="axiom-blank">
      <span className="small muted">{t.truncated ? "Anonymous node, not followed further" : "Anonymous node"}</span>
      {t.rows && t.rows.length > 0 && <Rows rows={t.rows} ctx={ctx} nested />}
    </span>
  );
}

function Rows({ rows, ctx, nested }: { rows: Row[]; ctx: Ctx; nested?: boolean }) {
  return (
    <table className={nested ? "grid axiom-rows nested" : "grid axiom-rows"}>
      <thead>
        <tr>
          <th>Predicate</th>
          <th>Object</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i}>
            <td className="small">
              <Ref iri={r.predicate} ctx={ctx} />
            </td>
            <td className="small">
              <Term t={r.object} ctx={ctx} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

const QUANTIFIER: Record<string, string> = { some: "some values from", only: "only values from", value: "has value", self: "has itself as a value" };

function Quantifier({ e }: { e: Extract<ClassExpr, { kind: "restriction" }> }) {
  if (e.cardinality === undefined) return <span className="axiom-quantifier">{QUANTIFIER[e.quantifier]}</span>;
  const word = e.quantifier === "min" ? "at least" : e.quantifier === "max" ? "at most" : "exactly";
  return <span className="axiom-quantifier">{`${word} ${e.cardinality}`}</span>;
}

/** A class expression, a restriction as a row and a compound expression as a heading over its members. */
function Expression({ e, ctx }: { e: ClassExpr; ctx: Ctx }) {
  return (
    <div className={`axiom-expr axiom-${e.kind}`}>
      <Body e={e} ctx={ctx} />
      {e.extra && e.extra.length > 0 && (
        <div className="axiom-extra">
          <div className="small muted">Also stated on this expression</div>
          <Rows rows={e.extra} ctx={ctx} nested />
        </div>
      )}
    </div>
  );
}

function Compound({ heading, children }: { heading: string; children: ReactNode }) {
  return (
    <div className="axiom-compound">
      <div className="axiom-heading">{heading}</div>
      {children}
    </div>
  );
}

function Body({ e, ctx }: { e: ClassExpr; ctx: Ctx }) {
  switch (e.kind) {
    case "named":
      return <Ref iri={e.iri} ctx={ctx} />;
    case "restriction":
      return (
        <div className="axiom-restriction">
          <span className="axiom-property">
            <PropRef p={e.property} ctx={ctx} />
          </span>
          <Quantifier e={e} />
          <span className="axiom-filler">
            {e.filler && <Expression e={e.filler} ctx={ctx} />}
            {e.value && <Term t={e.value} ctx={ctx} />}
            {!e.filler && !e.value && e.quantifier === "self" && <span className="muted small">itself</span>}
          </span>
        </div>
      );
    case "intersection":
    case "union":
      return (
        <Compound heading={e.kind === "intersection" ? "All of" : "Any of"}>
          <ul className="axiom-members">
            {e.members.map((m, i) => (
              <li key={i}>
                <Expression e={m} ctx={ctx} />
              </li>
            ))}
          </ul>
          {e.members.length === 0 && <span className="muted small">no members</span>}
        </Compound>
      );
    case "complement":
      return (
        <Compound heading="Not">
          <Expression e={e.operand} ctx={ctx} />
        </Compound>
      );
    case "oneOf":
      return (
        <Compound heading="One of">
          <ul className="axiom-members">
            {e.members.map((m, i) => (
              <li key={i}>
                <Term t={m} ctx={ctx} />
              </li>
            ))}
          </ul>
        </Compound>
      );
    case "datatypeRestriction":
      return (
        <Compound heading="Datatype restricted by facets">
          <div>
            <Ref iri={e.datatype} ctx={ctx} />
          </div>
          <ul className="axiom-members">
            {e.facets.map((f, i) => (
              <li key={i} className="axiom-facet">
                <Ref iri={f.facet} ctx={ctx} /> <Term t={f.value} ctx={ctx} />
              </li>
            ))}
          </ul>
        </Compound>
      );
    case "unknown":
      return (
        <Compound heading={e.reason === "depth" || e.reason === "cycle" ? "Not followed further" : "Not recognised"}>
          <Term t={e.term} ctx={ctx} />
        </Compound>
      );
  }
}

function Section({ name, hint, children }: { name: string; hint?: string; children: ReactNode }) {
  return (
    <section className="card section axiom-section" aria-label={name}>
      <header>
        <h3 className="grow">{name}</h3>
        {hint && <span className="set">{hint}</span>}
      </header>
      <div className="fields">{children}</div>
    </section>
  );
}

function Expressions({ items, ctx }: { items: ClassExpr[]; ctx: Ctx }) {
  return (
    <ul className="axiom-list">
      {items.map((e, i) => (
        <li key={i}>
          <Expression e={e} ctx={ctx} />
        </li>
      ))}
    </ul>
  );
}

function Annotations({ items, ctx }: { items: Annotation[]; ctx: Ctx }) {
  if (items.length === 0) return null;
  return (
    <Section name="Annotations">
      <table className="grid axiom-rows">
        <thead>
          <tr>
            <th>Annotation</th>
            <th>Language</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
          {items.map((a) => (
            <tr key={`${a.property}|${a.language}`}>
              <td className="small">
                <Ref iri={a.property} ctx={ctx} />
              </td>
              <td className="small muted">{a.language || "none"}</td>
              <td className="small">
                {a.values.map((v, i) => (
                  <div key={i}>{v.value}</div>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Section>
  );
}

function Other({ rows, ctx }: { rows: Row[]; ctx: Ctx }) {
  if (rows.length === 0) return null;
  return (
    <Section name="Other statements" hint="not recognised by a section above">
      <Rows rows={rows} ctx={ctx} />
    </Section>
  );
}

function ShapeConstraints({ row, ctx }: { row: PropertyShapeRow; ctx: Ctx }) {
  return (
    <>
      <div className="values">
        {row.constraints.map((c) => (
          <span key={c.constraint} className="chip axiom-constraint">
            <span className="muted">{c.constraint}</span>
            {c.values.map((v, i) => (
              <Term key={i} t={v} ctx={ctx} />
            ))}
          </span>
        ))}
      </div>
      {row.other.length > 0 && <Rows rows={row.other} ctx={ctx} nested />}
    </>
  );
}

export function ClassAxioms({ baseline, iri }: { baseline: Baseline; iri: string }) {
  const ctx = useCtx(baseline);
  const a = useMemo(() => classAxioms(baseline.graph, iri), [baseline, iri]);
  return (
    <div className="axioms" aria-label={`Axioms of ${baseline.label(iri)}`}>
      <Annotations items={a.annotations} ctx={ctx} />
      {a.superClasses.length > 0 && (
        <Section name="Superclasses">
          <Expressions items={a.superClasses} ctx={ctx} />
        </Section>
      )}
      {a.equivalentClasses.length > 0 && (
        <Section name="Equivalent classes">
          <Expressions items={a.equivalentClasses} ctx={ctx} />
        </Section>
      )}
      {a.disjointClasses.length > 0 && (
        <Section name="Disjoint classes">
          <Expressions items={a.disjointClasses} ctx={ctx} />
        </Section>
      )}
      {a.keys.length > 0 && (
        <Section name="Keys">
          <ul className="axiom-list">
            {a.keys.map((k, i) => (
              <li key={i} className="values">
                {k.map((p, j) => (
                  <span key={j} className="chip">
                    <PropRef p={p} ctx={ctx} />
                  </span>
                ))}
              </li>
            ))}
          </ul>
        </Section>
      )}
      {a.properties.length > 0 && (
        <Section name="Properties by domain">
          <table className="grid axiom-rows">
            <thead>
              <tr>
                <th>Property</th>
                <th>Domain declared on</th>
              </tr>
            </thead>
            <tbody>
              {a.properties.map((p) => (
                <tr key={`${p.property}|${p.from ?? ""}`}>
                  <td className="small">
                    <Ref iri={p.property} ctx={ctx} />
                  </td>
                  <td className="small">{p.from ? <>Inherited from <Ref iri={p.from} ctx={ctx} /></> : <span className="muted">This class</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}
      {a.shapes.length > 0 && (
        <Section name="Shapes that target it">
          {a.shapes.map((s, i) => (
            <div key={s.shape ?? i} className="axiom-shape">
              <div className="axiom-heading">{s.shape ? <Ref iri={s.shape} ctx={ctx} /> : "Anonymous shape"}</div>
              <table className="grid axiom-rows">
                <thead>
                  <tr>
                    <th>Path</th>
                    <th>Constraints</th>
                  </tr>
                </thead>
                <tbody>
                  {s.properties.map((p, j) => (
                    <tr key={j}>
                      <td className="small">{p.path ? <Term t={p.path} ctx={ctx} /> : <span className="muted">no path</span>}</td>
                      <td className="small">
                        <ShapeConstraints row={p} ctx={ctx} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </Section>
      )}
      {a.individuals.length > 0 && (
        <Section name="Individuals">
          <div className="values">
            {a.individuals.map((i) => (
              <span key={i} className="chip">
                <Ref iri={i} ctx={ctx} />
              </span>
            ))}
          </div>
        </Section>
      )}
      <Other rows={a.other} ctx={ctx} />
    </div>
  );
}

export function PropertyAxioms({ baseline, iri }: { baseline: Baseline; iri: string }) {
  const ctx = useCtx(baseline);
  const a = useMemo(() => propertyAxioms(baseline.graph, iri), [baseline, iri]);
  return (
    <div className="axioms" aria-label={`Axioms of ${baseline.label(iri)}`}>
      {a.kinds.length + a.characteristics.length > 0 && (
        <Section name="Characteristics">
          <div className="values">
            {a.kinds.map((k) => (
              <span key={k} className="chip baseline">
                {k} property
              </span>
            ))}
            {a.characteristics.map((c) => (
              <span key={c} className="chip">
                {c}
              </span>
            ))}
          </div>
        </Section>
      )}
      {a.domains.length > 0 && (
        <Section name="Domain">
          <Expressions items={a.domains} ctx={ctx} />
        </Section>
      )}
      {a.ranges.length > 0 && (
        <Section name="Range">
          <Expressions items={a.ranges} ctx={ctx} />
        </Section>
      )}
      {a.superProperties.length > 0 && (
        <Section name="Super-properties">
          <div className="values">
            {a.superProperties.map((p) => (
              <span key={p} className="chip">
                <Ref iri={p} ctx={ctx} />
              </span>
            ))}
          </div>
        </Section>
      )}
      {a.inverseOf.length > 0 && (
        <Section name="Inverse of">
          <div className="values">
            {a.inverseOf.map((p) => (
              <span key={p} className="chip">
                <Ref iri={p} ctx={ctx} />
              </span>
            ))}
          </div>
        </Section>
      )}
      {a.chains.length > 0 && (
        <Section name="Property chains">
          <ul className="axiom-list">
            {a.chains.map((chain, i) => (
              <li key={i} className="axiom-chain values">
                {chain.map((p, j) => (
                  <span key={j} className="chip">
                    <PropRef p={p} ctx={ctx} />
                  </span>
                ))}
              </li>
            ))}
          </ul>
        </Section>
      )}
      {a.shapes.length > 0 && (
        <Section name="Shapes that name it as a path">
          <table className="grid axiom-rows">
            <thead>
              <tr>
                <th>Node shape</th>
                <th>Target class</th>
                <th>Constraints</th>
              </tr>
            </thead>
            <tbody>
              {a.shapes.map((s, i) => (
                <tr key={i}>
                  <td className="small">{s.nodeShape ? <Ref iri={s.nodeShape} ctx={ctx} /> : <span className="muted">none</span>}</td>
                  <td className="small">
                    {s.targets.map((t) => (
                      <div key={t}>
                        <Ref iri={t} ctx={ctx} />
                      </div>
                    ))}
                  </td>
                  <td className="small">
                    <ShapeConstraints row={s.shape} ctx={ctx} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}
      <Annotations items={a.annotations} ctx={ctx} />
      <Other rows={a.other} ctx={ctx} />
    </div>
  );
}

export function IndividualAxioms({ baseline, iri }: { baseline: Baseline; iri: string }) {
  const ctx = useCtx(baseline);
  const a = useMemo(() => individualAxioms(baseline.graph, iri), [baseline, iri]);
  return (
    <div className="axioms" aria-label={`Axioms of ${baseline.label(iri)}`}>
      {a.types.length > 0 && (
        <Section name="Types">
          <div className="values">
            {a.types.map((t) => (
              <span key={t} className="chip">
                <Ref iri={t} ctx={ctx} />
              </span>
            ))}
          </div>
        </Section>
      )}
      {a.assertions.length > 0 && (
        <Section name="Assertions">
          <table className="grid axiom-rows">
            <thead>
              <tr>
                <th>Property</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {a.assertions.map((s) => (
                <tr key={s.property}>
                  <td className="small">
                    <Ref iri={s.property} ctx={ctx} />
                  </td>
                  <td className="small">
                    {s.values.map((v, i) => (
                      <div key={i}>
                        <Term t={v} ctx={ctx} />
                      </div>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Section>
      )}
      <Annotations items={a.annotations} ctx={ctx} />
    </div>
  );
}
