// SPDX-License-Identifier: MPL-2.0
// What the output explorer (SVA-M4) offers for a media type, and the choice the author keeps for each. A part is shown in every
// rendering its media type allows, and the rendering the author picks for a media type is kept in this browser, never in a graph
// and never sent to the service. A browser that keeps nothing shows each media type's default, and the explorer still works.

export type Family = "rdf" | "json" | "xml" | "other";
export type Rendering = "text" | "table" | "graph" | "tree";

const RDF_TYPES = ["text/turtle", "application/n-triples", "application/n-quads", "application/trig"];
const JSON_TYPES = ["application/json", "application/ld+json"];
const XML_TYPES = ["application/xml", "text/xml", "application/xslt+xml"];

/** The media type without its parameters, in lower case, as a stored choice is keyed. */
export function baseType(mediaType: string): string {
  return mediaType.split(";")[0].trim().toLowerCase();
}

export function familyOf(mediaType: string): Family {
  const type = baseType(mediaType);
  if (RDF_TYPES.includes(type)) return "rdf";
  if (JSON_TYPES.includes(type)) return "json";
  if (XML_TYPES.includes(type)) return "xml";
  return "other";
}

/** The renderings offered for a media type, the default first. */
export function renderingsFor(mediaType: string): Rendering[] {
  switch (familyOf(mediaType)) {
    case "rdf":
      return ["text", "table", "graph"];
    case "json":
    case "xml":
      return ["tree", "text"];
    default:
      return ["text"];
  }
}

export const RENDERING_LABEL: Record<Rendering, string> = { text: "Text", table: "Table", graph: "Graph", tree: "Tree" };

/** The rendering a part opens in: the author's choice for its media type where it is still offered, else the default. */
export function renderingOf(mediaType: string, choices: Choices): Rendering {
  const offered = renderingsFor(mediaType);
  const kept = choices.renderings[baseType(mediaType)];
  return kept && offered.includes(kept) ? kept : offered[0];
}

export type TextFormat = "turtle" | "ntriples";

export interface Choices {
  renderings: Record<string, Rendering>;
  formats: Record<string, TextFormat>;
}

export const NO_CHOICES: Choices = { renderings: {}, formats: {} };
export const CHOICES_KEY = "lattice-studio:output-explorer";

export type ChoiceStore = Pick<Storage, "getItem" | "setItem">;

function browserStore(): ChoiceStore | undefined {
  try {
    return typeof localStorage === "undefined" ? undefined : localStorage;
  } catch {
    return undefined;
  }
}

const RENDERINGS: readonly string[] = ["text", "table", "graph", "tree"];
const FORMATS: readonly string[] = ["turtle", "ntriples"];

function onlyValid<T extends string>(value: unknown, valid: readonly string[]): Record<string, T> {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return {};
  return Object.fromEntries(Object.entries(value).filter(([, v]) => typeof v === "string" && valid.includes(v))) as Record<string, T>;
}

/** What the browser kept, read part by part, so a value that is not what was written is ignored and the rest still holds. */
export function readChoices(store: ChoiceStore | undefined = browserStore()): Choices {
  try {
    const parsed: unknown = JSON.parse(store?.getItem(CHOICES_KEY) ?? "{}");
    if (typeof parsed !== "object" || parsed === null) return NO_CHOICES;
    const { renderings, formats } = parsed as Record<string, unknown>;
    return { renderings: onlyValid<Rendering>(renderings, RENDERINGS), formats: onlyValid<TextFormat>(formats, FORMATS) };
  } catch {
    return NO_CHOICES;
  }
}

export function writeChoices(choices: Choices, store: ChoiceStore | undefined = browserStore()): void {
  try {
    store?.setItem(CHOICES_KEY, JSON.stringify(choices));
  } catch {
    // A browser that keeps nothing shows the defaults on the next visit.
  }
}

export function withRendering(choices: Choices, mediaType: string, rendering: Rendering): Choices {
  return { ...choices, renderings: { ...choices.renderings, [baseType(mediaType)]: rendering } };
}

export function withFormat(choices: Choices, mediaType: string, format: TextFormat): Choices {
  return { ...choices, formats: { ...choices.formats, [baseType(mediaType)]: format } };
}

export function formatOf(mediaType: string, choices: Choices): TextFormat {
  return choices.formats[baseType(mediaType)] ?? "turtle";
}
