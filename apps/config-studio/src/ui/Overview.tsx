// SPDX-License-Identifier: MPL-2.0
// What of the baseline is configured: each class with the persistence nodes declared at its class
// scope and the surface contracts it carries. Resolution across scopes and priorities is the
// compiler's, shown on the Build view, so this view says "declared for", never "resolved to".

import { Plus } from "lucide-react";
import { KINDS, create, type Kind } from "../rdf/editors";
import type { Graph } from "../rdf/graph";
import { DAL, SRF, compact } from "../rdf/ns";
import type { Part } from "../state";
import { go } from "./kit";
import { useStudio, type Studio } from "./Workspace";

const kind = (type: string) => KINDS.find((k) => k.type === type)!;

/** Persistence nodes whose dal:appliesTo is a class scope matching the class: the class itself, or
 * an ancestor with dal:includeSubclasses true. */
export function declaredFor(graph: Graph, classIri: string, ancestors: string[]): string[] {
  const scopes = graph.ofType(DAL("ClassScope")).filter((s) => {
    const target = graph.value(s, DAL("targetClass"));
    return target === classIri || (target !== undefined && ancestors.includes(target) && graph.value(s, DAL("includeSubclasses")) === "true");
  });
  return scopes.flatMap((s) => graph.subjects(DAL("appliesTo"), s).map((n) => n.value));
}

export function addFor(studio: Studio, part: Part, k: Kind, classIri: string): void {
  const label = studio.baseline.classes.get(classIri)?.label ?? compact(classIri);
  let made = "";
  studio.model.edit(part, (g) => {
    const created = create(g, k, `${label} ${k.title}`, studio.baseline.namespace, classIri);
    made = created.iri;
    return created.graph;
  });
  studio.open(part, made);
}

export function Overview() {
  const studio = useStudio();
  const { baseline, model, vocab } = studio;
  const persistence = model.state.configs.persistence!.current;
  const surface = model.state.configs.surface!.current;
  const contracts = [...surface.ofType(SRF("PromotionContract")), ...surface.ofType(SRF("IndexContract"))];
  const issues = [...model.issues.persistence, ...model.issues.surface];
  const classes = [...baseline.classes.values()].sort((a, b) => a.label.localeCompare(b.label));
  const configured = classes.filter(
    (c) => declaredFor(persistence, c.iri, baseline.ancestors(c.iri)).length || contracts.some((k) => surface.value(k, SRF("carrier")) === c.iri),
  ).length;

  const chip = (part: Part, graph: Graph, node: string) => {
    const types = graph.types(node);
    const k = KINDS.find((x) => types.includes(x.type));
    const strategy = graph.value(node, DAL("strategy"));
    const concurrency = graph.value(node, DAL("concurrencyProfile"));
    const extra = [strategy, concurrency].filter(Boolean).map((v) => vocab.label(v!)).join(" · ");
    return (
      <button key={node} className={`chip ${part === "persistence" ? "persist" : "surface"}`} style={{ cursor: "pointer" }} onClick={() => studio.open(part, node)} title={node}>
        {k?.title ?? compact(node)}
        {extra && `: ${extra}`}
      </button>
    );
  };

  return (
    <div className="page">
      <div className="page-head">
        <div className="grow">
          <h1>Overview</h1>
          <p>Every class of the baseline, with the persistence configuration declared at its class scope and the surface contracts it carries. Add either from its row.</p>
        </div>
      </div>
      <div className="stats">
        <Stat n={baseline.classes.size} l="classes in the baseline" />
        <Stat n={`${configured}/${baseline.classes.size}`} l="classes configured" />
        <Stat n={studio.items.persistence.length} l="persistence nodes" />
        <Stat n={contracts.length} l="surface contracts" />
        <Stat n={issues.filter((i) => i.severity === "Violation").length} l="violations" tone={issues.some((i) => i.severity === "Violation") ? "bad" : "ok"} />
      </div>
      <div className="card" style={{ overflow: "hidden" }}>
        <table className="grid">
          <thead>
            <tr>
              <th style={{ width: "24%" }}>Class</th>
              <th>Persistence</th>
              <th>Surface</th>
            </tr>
          </thead>
          <tbody>
            {classes.length === 0 && (
              <tr>
                <td colSpan={3} className="muted">
                  The baseline declares no classes. Replace it from the Baseline view.
                </td>
              </tr>
            )}
            {classes.map((c) => {
              const declared = declaredFor(persistence, c.iri, baseline.ancestors(c.iri));
              const carried = contracts.filter((k) => surface.value(k, SRF("carrier")) === c.iri).map((k) => k.value);
              return (
                <tr key={c.iri}>
                  <td>
                    <a href={`#/w/${studio.id}/baseline/${encodeURIComponent(c.iri)}`} style={{ fontWeight: 600, textDecoration: "none" }}>
                      {c.label}
                    </a>
                    <div className="small muted mono ellipsis">{compact(c.iri, { ...baseline.graph.prefixes })}</div>
                  </td>
                  <td>
                    <div className="cell-actions">
                      {declared.map((n) => chip("persistence", persistence, n))}
                      {!declared.some((n) => persistence.types(n).includes(DAL("DataAccessProfile"))) && (
                        <button className="add-link" onClick={() => addFor(studio, "persistence", kind(DAL("DataAccessProfile")), c.iri)}>
                          <Plus size={12} /> Profile
                        </button>
                      )}
                      <button className="add-link" onClick={() => addFor(studio, "persistence", kind(DAL("UniquenessConstraint")), c.iri)}>
                        <Plus size={12} /> Key
                      </button>
                    </div>
                  </td>
                  <td>
                    <div className="cell-actions">
                      {carried.map((n) => chip("surface", surface, n))}
                      <button className="add-link" onClick={() => addFor(studio, "surface", kind(SRF("PromotionContract")), c.iri)}>
                        <Plus size={12} /> Promotion
                      </button>
                      <button className="add-link" onClick={() => addFor(studio, "surface", kind(SRF("IndexContract")), c.iri)}>
                        <Plus size={12} /> Index
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="small muted" style={{ marginTop: 12 }}>
        Nodes declared at a namespace or graph pattern scope are not shown here. The <a href={`#/w/${studio.id}/build`} onClick={() => go("w", studio.id, "build")}>build</a> shows which
        profile the compiler resolved for each target.
      </p>
    </div>
  );
}

function Stat({ n, l, tone }: { n: number | string; l: string; tone?: "ok" | "bad" }) {
  return (
    <div className="card stat">
      <div className="n" style={tone ? { color: `var(--${tone})` } : undefined}>
        {n}
      </div>
      <div className="l">{l}</div>
    </div>
  );
}
