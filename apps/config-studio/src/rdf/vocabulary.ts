// SPDX-License-Identifier: MPL-2.0
// Reads the dal:, srf:, fnd: and voc: vocabularies the service serves and derives every form field
// from them: a property's rdfs:domain places it, its rdfs:range picks the control, and the
// individuals of a range class are its options. Only what the ontology cannot say is declared
// here, in OVERRIDES.

import { Graph, type Term } from "./graph";
import { COMMENT, DAL, LABEL, OWL, RDF, RDFS, SRF, TYPE, XSD, humanise, localName, sentence } from "./ns";

export type FieldKind =
  | "text"
  | "number"
  | "boolean"
  | "choice" // one or more individuals of the range class
  | "reference" // a node of the range class, authored in the configuration
  | "class" // a class of the baseline
  | "property" // a property of the baseline
  | "propertyList" // an rdf:List of baseline properties
  | "textList" // an rdf:List of strings
  | "iri"; // any IRI, typed by hand

export interface Option {
  iri: string;
  label: string;
  comment: string;
}

export interface Field {
  property: string;
  label: string;
  comment: string;
  kind: FieldKind;
  /** Only one value. Not functional means several values, shown as chips. */
  single: boolean;
  range?: string;
  datatype?: string;
  options: Option[];
}

interface Override {
  kind: FieldKind;
  single?: boolean;
  /** Offer as options the individuals that carry this property, for a range the ontology leaves open. */
  optionsWith?: string;
}

/** Properties whose range the ontology leaves open, or whose values are a baseline's terms. */
const OVERRIDES: Record<string, Override> = {
  [DAL("targetClass")]: { kind: "class", single: true },
  [DAL("coversClass")]: { kind: "class", single: false },
  [DAL("keyProperty")]: { kind: "propertyList", single: true },
  [DAL("scopeProperty")]: { kind: "property", single: false },
  [DAL("mergeRelation")]: { kind: "property", single: true },
  [DAL("valueGuardProperty")]: { kind: "property", single: false },
  [DAL("normalizePipeline")]: { kind: "choice", single: true, optionsWith: DAL("unicodeVersion") },
  [DAL("tuplePrefix")]: { kind: "textList", single: true },
  [DAL("dataGraph")]: { kind: "iri", single: true },
  [DAL("boundaryShape")]: { kind: "iri", single: true },
  [DAL("appliesTo")]: { kind: "reference", single: true },
  [DAL("priority")]: { kind: "number", single: true },
  [SRF("hasPopulationMember")]: { kind: "iri", single: false },
};

const NUMBERS = new Set(["integer", "long", "int", "nonNegativeInteger", "positiveInteger", "decimal"].map(XSD));
const BOOLEAN = XSD("boolean");
const TEXT = new Set([XSD("string"), XSD("anyURI"), XSD("dateTime"), RDFS("Literal")]);

export class Vocabulary {
  private readonly superClasses = new Map<string, string[]>();
  private readonly byDomain = new Map<string, string[]>();
  private readonly fieldCache = new Map<string, Field>();

  constructor(readonly graph: Graph) {
    for (const q of graph.quads(null, RDFS("subClassOf"))) {
      if (q.object.termType !== "NamedNode") continue;
      const list = this.superClasses.get(q.subject.value) ?? [];
      list.push(q.object.value);
      this.superClasses.set(q.subject.value, list);
    }
    for (const q of graph.quads(null, RDFS("domain"))) {
      for (const domain of this.members(q.object)) {
        const list = this.byDomain.get(domain) ?? [];
        list.push(q.subject.value);
        this.byDomain.set(domain, list);
      }
    }
  }

  static parse(turtle: string): Vocabulary {
    return new Vocabulary(Graph.parse(turtle));
  }

  label(iri: string): string {
    return this.graph.value(iri, LABEL) ?? sentence(humanise(localName(iri)));
  }

  comment(iri: string): string {
    return this.graph.value(iri, COMMENT) ?? "";
  }

  /** A class and every class it is asserted to be a subclass of. */
  ancestors(iri: string): string[] {
    const out = [iri];
    for (let i = 0; i < out.length; i++) {
      for (const parent of this.superClasses.get(out[i]) ?? []) if (!out.includes(parent)) out.push(parent);
    }
    return out;
  }

  /** The properties a class takes: those whose rdfs:domain is the class or one of its ancestors. */
  propertiesOf(classIri: string): string[] {
    const seen = new Set<string>();
    for (const c of this.ancestors(classIri)) for (const p of this.byDomain.get(c) ?? []) seen.add(p);
    return [...seen].sort((a, b) => this.label(a).localeCompare(this.label(b)));
  }

  isProperty(iri: string): boolean {
    const types = this.graph.types(iri);
    return types.includes(OWL("ObjectProperty")) || types.includes(OWL("DatatypeProperty")) || types.includes(RDF("Property"));
  }

  individuals(classIri: string): Option[] {
    return this.options(this.graph.subjects(TYPE, classIri));
  }

  field(property: string): Field {
    const cached = this.fieldCache.get(property);
    if (cached) return cached;
    const g = this.graph;
    const override = OVERRIDES[property];
    const range = g.value(property, RDFS("range"));
    // srf: declares owl:FunctionalProperty on every single-valued property. The persistence compiler
    // reads every dal: property it compiles as single-valued, so elsewhere one value is the default
    // and OVERRIDES names the exceptions.
    const functional = g.types(property).includes(OWL("FunctionalProperty")) || !property.startsWith(SRF(""));
    const base = {
      property,
      label: this.label(property),
      comment: this.comment(property),
      range,
      options: [] as Option[],
    };
    let field: Field;
    if (override) {
      const options = override.optionsWith ? this.options(g.subjects(override.optionsWith)) : [];
      field = { ...base, kind: override.kind, single: override.single ?? functional, options };
    } else if (range === BOOLEAN) {
      field = { ...base, kind: "boolean", single: true, datatype: range };
    } else if (range && NUMBERS.has(range)) {
      field = { ...base, kind: "number", single: true, datatype: range };
    } else if (range && (TEXT.has(range) || g.types(property).includes(OWL("DatatypeProperty")))) {
      field = { ...base, kind: "text", single: true, datatype: range };
    } else if (range === RDFS("Class") || range === OWL("Class")) {
      field = { ...base, kind: "class", single: functional };
    } else if (range === RDF("Property")) {
      field = { ...base, kind: "property", single: functional };
    } else if (range && this.individuals(range).length > 0) {
      field = { ...base, kind: "choice", single: functional, options: this.individuals(range) };
    } else if (range) {
      field = { ...base, kind: "reference", single: functional };
    } else {
      field = { ...base, kind: "iri", single: functional };
    }
    this.fieldCache.set(property, field);
    return field;
  }

  private options(terms: Term[]): Option[] {
    return terms
      .filter((t) => t.termType === "NamedNode")
      .map((t) => ({ iri: t.value, label: this.label(t.value), comment: this.comment(t.value) }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }

  /** A domain is a class, or an owl:unionOf of classes. */
  private members(domain: Term): string[] {
    if (domain.termType === "NamedNode") return [domain.value];
    const union = this.graph.object(domain, OWL("unionOf"));
    return union ? (this.graph.list(union) ?? []).map((t) => t.value) : [];
  }
}
