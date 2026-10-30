// SPDX-License-Identifier: MPL-2.0
// Reads the dal:, srf:, fnd: and voc: vocabularies and their SHACL shapes, as the service serves
// them, and derives every form field from them. A shape that targets a class places a property on
// it and picks the control (sh:datatype, sh:class, sh:in), and its counts say whether the field is
// single and required. Where no shape speaks, a property's rdfs:domain places it and its
// rdfs:range picks the control. The individuals of a range class are its options. Only what the
// ontology cannot say is declared here, in OVERRIDES.

import { type Constraint, merge, readShapes } from "./shapes";
import { COMMENT, DAL, ELG, Graph, LABEL, MORK, OWL, QNT, RDF, RDFS, SH, SKOS, SRF, TYPE, VOC, XSD, humanise, localName, namedNode, sentence, type Term } from "@lattice/authoring-domain";

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
  | "iri" // any IRI, typed by hand
  | "targetClass" // a class of the layers or the baseline, which a mapping writes
  | "targetProperty" // a property of the layers or the baseline, which a mapping writes
  | "targetIndividual"; // an individual of the layers, which a mapping writes

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
  /** A shape requires at least one value. */
  required?: boolean;
  range?: string;
  datatype?: string;
  lang?: string;
  options: Option[];
  /** Shown but never written in the studio, with why, as for bound meaning in the builder. */
  readOnly?: string;
}

interface Override {
  kind: FieldKind;
  single?: boolean;
  /** Offer as options the individuals that carry this property, for a range the ontology leaves open. */
  optionsWith?: string;
  /** The range, where the ontology leaves it open or the studio does not serve the property. */
  range?: string;
  datatype?: string;
  label?: string;
  /** Write a text value with this language tag. */
  lang?: string;
}

/** Properties whose range the ontology leaves open, or whose values are a baseline's terms. */
const OVERRIDES: Record<string, Override> = {
  [DAL("targetClass")]: { kind: "class", single: true },
  // MORK declares no domains and few ranges, so a mapping's fields are placed by its kinds (editors.ts) and typed here.
  [MORK("exactTBoxMatch")]: { kind: "targetClass", single: false },
  [MORK("exactRBoxMatch")]: { kind: "targetProperty", single: false },
  [MORK("inverseRBoxMatch")]: { kind: "targetProperty", single: false },
  [MORK("exactABoxMatch")]: { kind: "targetIndividual", single: false },
  [MORK("compositeBroaderMapping")]: { kind: "reference", single: true, range: MORK("DataMapping") },
  [MORK("templateMapping")]: { kind: "reference", single: true, range: MORK("DataMapping") },
  [MORK("appliesWhen")]: { kind: "reference", single: true, range: SH("NodeShape") },
  [MORK("mappingScheme")]: { kind: "reference", single: true, range: MORK("MappingScheme") },
  [MORK("mappingFor")]: { kind: "iri", single: true },
  [MORK("mappingNote")]: { kind: "text", single: true },
  [MORK("representedAs")]: { kind: "iri", single: false },
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
  // A range class with one individual in the vocabulary is still a reference to the author's nodes.
  [VOC("forContract")]: { kind: "reference", single: true },
  [ELG("constrainedByContract")]: { kind: "reference", single: true },
  [QNT("underCalendar")]: { kind: "reference", single: true },
  [QNT("numericValue")]: { kind: "number", single: true, datatype: XSD("decimal") },
  [QNT("onSpace")]: { kind: "reference", single: true, range: QNT("ValueSpace") },
  // SKOS is not among the vocabularies the studio is served.
  [SKOS("prefLabel")]: { kind: "text", single: true, label: "Preferred label", lang: "en" },
  [SKOS("definition")]: { kind: "text", single: true, label: "Definition", lang: "en" },
  [SKOS("broader")]: { kind: "reference", single: false, range: SKOS("Concept"), label: "Broader concept" },
  [SKOS("inScheme")]: { kind: "reference", single: true, range: VOC("ConceptScheme"), label: "In scheme" },
  [SKOS("notation")]: { kind: "text", single: true, label: "Notation" },
};

const NUMBERS = new Set(["integer", "long", "int", "nonNegativeInteger", "positiveInteger", "decimal"].map(XSD));
const BOOLEAN = XSD("boolean");
/** RDF's own vocabularies, never a mapping's target term by choice. */
const META = [RDF(""), RDFS(""), OWL(""), XSD("")];
const TEXT = new Set([XSD("string"), XSD("anyURI"), XSD("dateTime"), RDFS("Literal")]);

export class Vocabulary {
  private readonly superClasses = new Map<string, string[]>();
  private readonly byDomain = new Map<string, string[]>();
  private readonly shapes: Map<string, Map<string, Constraint>>;
  private readonly fieldCache = new Map<string, Field>();
  private readonly targetCache = new Map<string, Option[]>();

  constructor(readonly graph: Graph) {
    this.shapes = readShapes(graph);
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

  /** The properties a class takes: those a shape of the class or one of its ancestors names, and those whose rdfs:domain is one of them. */
  propertiesOf(classIri: string): string[] {
    const seen = new Set<string>();
    for (const c of this.ancestors(classIri)) {
      for (const p of this.byDomain.get(c) ?? []) seen.add(p);
      for (const p of this.shapes.get(c)?.keys() ?? []) if (this.isProperty(p)) seen.add(p);
    }
    return [...seen].sort((a, b) => this.label(a).localeCompare(this.label(b)));
  }

  isProperty(iri: string): boolean {
    const types = this.graph.types(iri);
    return types.includes(OWL("ObjectProperty")) || types.includes(OWL("DatatypeProperty")) || types.includes(RDF("Property"));
  }

  /** The terms a mapping may write, by kind: every class, property or individual the staged layers declare, MORK's own
   * and RDF's own left out, sorted by label. */
  targets(kind: "class" | "property" | "individual"): Option[] {
    const cached = this.targetCache.get(kind);
    if (cached) return cached;
    const g = this.graph;
    const own = (iri: string) => !iri.startsWith(MORK("")) && !iri.startsWith(SH("")) && !META.some((m) => iri.startsWith(m));
    const isClass = (iri: string) => g.types(iri).some((t) => t === OWL("Class") || t === RDFS("Class"));
    const subjects = [...new Set(g.quads(null, TYPE).filter((q) => q.subject.termType === "NamedNode").map((q) => q.subject.value))].filter(own);
    const picked = subjects.filter((s) =>
      kind === "class" ? isClass(s) : kind === "property" ? this.isProperty(s) : !isClass(s) && !this.isProperty(s) && g.types(s).some((t) => own(t) && isClass(t)),
    );
    const options = this.options(picked.map((s) => namedNode(s)));
    this.targetCache.set(kind, options);
    return options;
  }

  individuals(classIri: string): Option[] {
    return this.options(this.graph.subjects(TYPE, classIri));
  }

  /** What the shapes of a class and its ancestors say of a property, the nearest class first. */
  constraint(classIri: string, property: string): Constraint | undefined {
    let out: Constraint | undefined;
    for (const c of this.ancestors(classIri)) {
      const own = this.shapes.get(c)?.get(property);
      if (own) out = merge(out, own);
    }
    return out;
  }

  /** The field for a property, as a node of the class takes it. Without a class, or where no shape names the property, only the property's own declarations speak. */
  field(property: string, classIri?: string): Field {
    const shape = classIri ? this.constraint(classIri, property) : undefined;
    const key = shape ? `${classIri}|${property}` : property;
    const cached = this.fieldCache.get(key);
    if (cached) return cached;
    const g = this.graph;
    const override = OVERRIDES[property];
    const range = override?.range ?? shape?.datatype ?? shape?.cls ?? g.value(property, RDFS("range"));
    // srf:, voc:, qnt: and elg: declare owl:FunctionalProperty on every single-valued property. dal:
    // declares none, and the persistence compiler reads every dal: property it compiles as
    // single-valued, so there one value is the default and OVERRIDES names the exceptions.
    // A shape's sh:maxCount decides first, and only where a shape gives none do these rules apply.
    const functional = shape?.maxCount !== undefined ? shape.maxCount === 1 : g.types(property).includes(OWL("FunctionalProperty")) || property.startsWith(DAL(""));
    const base = {
      property,
      label: override?.label ?? (g.value(property, LABEL) || shape?.name || this.label(property)),
      lang: override?.lang,
      comment: this.comment(property) || shape?.description || "",
      required: (shape?.minCount ?? 0) >= 1,
      range,
      options: [] as Option[],
    };
    let field: Field;
    if (override) {
      const options = override.optionsWith ? this.options(g.subjects(override.optionsWith)) : [];
      field = { ...base, kind: override.kind, single: override.single ?? functional, options, datatype: override.datatype };
    } else if (range === BOOLEAN) {
      field = { ...base, kind: "boolean", single: true, datatype: range };
    } else if (range && NUMBERS.has(range)) {
      field = { ...base, kind: "number", single: true, datatype: range };
    } else if (shape?.in) {
      field = { ...base, kind: "choice", single: functional, options: this.options(shape.in) };
    } else if (shape?.datatype || (range && TEXT.has(range)) || g.types(property).includes(OWL("DatatypeProperty"))) {
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
    this.fieldCache.set(key, field);
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
