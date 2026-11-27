// SPDX-License-Identifier: MPL-2.0
// The pure part of path mode (SVA-S1 part 2, SVA-Q60). A path is built on the canvas by clicking from class to class along the properties the
// ontology declares, and each click is an edit of the configuration made by the writer the form uses, so the form and the canvas read one graph.
// This file reads where a path stands, which class it has reached and which properties a next hop may be, and writes a hop, an undo and a closure.
// It draws nothing. The three places a path is built are a contract's read path, which is `writePath`, the one property a role binding binds, and an
// expansion's members path, a SHACL property path.

import { Graph, RDF, RDFS, SRF, XSD, type Term } from "@lattice/authoring-domain";
import { readPath, writeBindingProperty, writeMembersPath, writePath } from "../rdf/path";
import { readExpression, type ClassExpr } from "../rdf/axioms";
import type { Baseline } from "../rdf/baseline";
import type { PathPlace } from "./drawing";
import { membersPath, sourceHops, type Closure, type Hop } from "./paths";

/** Where a hop leads. A datatype property leads to a value, and a path ends there. A property with no declared range leads nowhere known. */
export type Leads = { kind: "class"; iri: string } | { kind: "value"; datatype?: string } | { kind: "unknown" };

export interface PathOption {
  property: string;
  label: string;
  /** An inverse hop is taken from the class a property's range is, to its domain. */
  inverse: boolean;
  leads: Leads;
  /** Whether the ontology declares the property of this class, or states no domain (forward) or range (inverse) and so offers it of any class. */
  group: "class" | "any";
  /** Where the class reached so far is unknown, so every property is offered. */
  unknownClass: boolean;
}

const named = (e: ClassExpr): string[] => (e.kind === "named" ? [e.iri] : e.kind === "union" ? e.members.flatMap(named) : []);

/** The named classes a property's domains or ranges state, a union by its members, and whether the property states any at all. */
function ends(graph: Graph, property: string, predicate: string): { classes: string[]; stated: boolean } {
  const terms: Term[] = graph.objects(property, predicate);
  return { classes: [...new Set(terms.flatMap((t) => named(readExpression(graph, t))))].sort(), stated: terms.length > 0 };
}

const DATATYPES = [XSD(""), RDF("langString"), RDFS("Literal"), RDF("PlainLiteral")];
const isDatatype = (iri: string) => DATATYPES.some((d) => (d.endsWith("#") ? iri.startsWith(d) : iri === d));

interface Shape {
  domains: string[];
  domainStated: boolean;
  ranges: string[];
  rangeStated: boolean;
  /** A datatype property, or one whose range is a datatype. */
  value: boolean;
  datatype?: string;
}

function shapeOf(o: Baseline, property: string): Shape {
  const p = o.properties.get(property);
  const d = ends(o.graph, property, RDFS("domain"));
  const r = ends(o.graph, property, RDFS("range"));
  const datatype = r.classes.find(isDatatype);
  return { domains: d.classes, domainStated: d.stated, ranges: r.classes.filter((c) => !isDatatype(c)), rangeStated: r.stated, value: p?.datatype === true || datatype !== undefined, datatype };
}

const leadsForward = (s: Shape): Leads => (s.value ? { kind: "value", datatype: s.datatype } : s.ranges[0] ? { kind: "class", iri: s.ranges[0] } : { kind: "unknown" });

/**
 * Where a path stands after `hops` from `start`, the class it has reached, or none where that is unknown, and whether it has ended in a value.
 * A forward hop reaches the first declared range of its property and an inverse hop the first declared domain, as `PathBuilder` reads it. A
 * property the ontology does not declare, or declares with no range, reaches no known class.
 */
export function reachedAfter(o: Baseline, start: string | undefined, hops: readonly Hop[]): { at?: string; value: boolean } {
  let at = start;
  let value = false;
  for (const h of hops) {
    const s = shapeOf(o, h.property);
    value = false;
    if (!h.inverse && s.value) {
      at = undefined;
      value = true;
    } else at = h.inverse ? s.domains[0] : s.ranges[0];
  }
  return { at, value };
}

/**
 * The properties a next hop may be from the class `at`, outgoing for a forward hop and incoming for an inverse hop. A property of the class or of a
 * class above it is offered of the class. One with no declared domain (a forward hop) or range (an inverse hop) is offered of any class. Where the
 * class is unknown every property is offered, marked so. An inverse hop is never offered a datatype property, which no class is the value of.
 */
export function optionsAt(o: Baseline, at: string | undefined): { forward: PathOption[]; inverse: PathOption[] } {
  const above = at ? o.ancestors(at) : [];
  const forward: PathOption[] = [];
  const inverse: PathOption[] = [];
  for (const [property, p] of o.properties) {
    const s = shapeOf(o, property);
    const known = at !== undefined;
    const fits = (declared: string[], stated: boolean) => (!known ? "any" : !stated ? "any" : declared.some((c) => above.includes(c)) ? "class" : undefined);
    const out = fits(s.domains, s.domainStated);
    if (out) forward.push({ property, label: p.label, inverse: false, leads: leadsForward(s), group: out, unknownClass: !known });
    if (!s.value) {
      const into = fits(s.ranges, s.rangeStated);
      if (into) inverse.push({ property, label: p.label, inverse: true, leads: s.domains[0] ? { kind: "class", iri: s.domains[0] } : { kind: "unknown" }, group: into, unknownClass: !known });
    }
  }
  const order = (a: PathOption, b: PathOption) => Number(a.group === "any") - Number(b.group === "any") || a.label.localeCompare(b.label) || a.property.localeCompare(b.property);
  return { forward: forward.sort(order), inverse: inverse.sort(order) };
}

/** What a place states now. A members path in a form the canvas does not read has no hops and is not readable, and the first hop replaces it. */
export function readPlace(g: Graph, place: PathPlace): { hops: Hop[]; readable: boolean; source?: string } {
  if (place.kind === "read") return { hops: readPath(g, place.node).map((s) => ({ property: s.property, inverse: s.inverse })), readable: true };
  if (place.kind === "binding") {
    const property = g.value(place.node, SRF("bindsProperty"));
    return { hops: property ? [{ property, inverse: false }] : [], readable: true };
  }
  if (g.object(place.node, SRF("membersPath"))) {
    const hops = membersPath(g, place.node);
    return { hops: hops ?? [], readable: hops !== undefined };
  }
  // A named source stands for a path, which is written out as the path on the first edit.
  const source = g.value(place.node, SRF("expansionSource"));
  const property = g.value(g.value(place.node, SRF("expandsFrom")) ?? "", SRF("bindsProperty"));
  return { hops: (property ? sourceHops(source, property) : undefined) ?? [], readable: true, source };
}

/** Writes `hops` as the place states them. A binding takes at most one forward hop. */
export function writeHops(g: Graph, place: PathPlace, hops: readonly Hop[]): Graph {
  if (place.kind === "read") return writePath(g, place.node, hops.map((h) => ({ property: h.property, inverse: h.inverse })));
  if (place.kind === "binding") return writeBindingProperty(g, place.node, hops[0]?.property);
  return writeMembersPath(g, place.node, hops.map((h) => ({ ...h })));
}

/** A click on a property of the class reached: adds the hop, and for a binding replaces the one property. A path that has ended in a value takes none. */
export function addHop(g: Graph, place: PathPlace, start: string | undefined, o: Baseline, option: Pick<PathOption, "property" | "inverse">): Graph {
  const { hops } = readPlace(g, place);
  if (place.kind === "binding") return option.inverse ? g : writeHops(g, place, [{ property: option.property, inverse: false }]);
  if (reachedAfter(o, start, hops).value) return g;
  return writeHops(g, place, [...hops, { property: option.property, inverse: option.inverse }]);
}

/** Removes the last hop. */
export function undoHop(g: Graph, place: PathPlace): Graph {
  return writeHops(g, place, readPlace(g, place).hops.slice(0, -1));
}

/** Sets the closure of one hop of a members path, one or more or zero or more, or none. Only a members path has one. */
export function setClosure(g: Graph, place: PathPlace, index: number, closure: Closure | undefined): Graph {
  if (place.kind !== "members") return g;
  const { hops } = readPlace(g, place);
  if (!hops[index]) return g;
  return writeHops(g, place, hops.map((h, i) => (i === index ? { ...h, closure } : h)));
}
