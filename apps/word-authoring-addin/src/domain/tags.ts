/**
 * The content-control tag codec of plan WA8 section "Tag codec": the mapping between a kind of
 * marked text and the Word content control `tag`/`title`/appearance/colour it gets written with.
 */

export type TagKind = "section" | "clause" | "definition" | "term" | "variable" | "reference";

export interface DecodedTag {
  kind: TagKind;
  value: string | null;
}

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const KEY_PATTERN = /^[a-z][a-z0-9-]{0,39}$/;
const SECTION_KEY_PATTERN = /^[a-z][a-z0-9-]{0,31}$/;

const MAX_TAG_LENGTH = 64;
const MAX_TITLE_LENGTH = 64;

const PREFIX: Record<Exclude<TagKind, "term">, string> = {
  section: "lat:s:",
  clause: "lat:e:",
  definition: "lat:d:",
  variable: "lat:v:",
  reference: "lat:r:",
};

const VALUE_PATTERN: Record<Exclude<TagKind, "term">, RegExp> = {
  section: SECTION_KEY_PATTERN,
  clause: UUID_PATTERN,
  definition: UUID_PATTERN,
  variable: KEY_PATTERN,
  reference: UUID_PATTERN,
};

export const TAG_APPEARANCE: Record<TagKind, "BoundingBox" | "Tags"> = {
  section: "BoundingBox",
  clause: "BoundingBox",
  definition: "BoundingBox",
  term: "Tags",
  variable: "Tags",
  reference: "Tags",
};

export const TAG_COLOUR: Record<TagKind, string> = {
  section: "#5B6B7F",
  clause: "#1F6FB2",
  definition: "#6A3FB5",
  term: "#6A3FB5",
  variable: "#C46A00",
  reference: "#2E7D32",
};

/** Builds the content control `tag`. Throws when `value` fails its §2.4 pattern, or the whole tag
 * would exceed Word's 64-character content control tag limit. `term` takes no value. */
export function encode(kind: TagKind, value?: string): string {
  if (kind === "term") {
    return "lat:term";
  }
  if (value === undefined || !VALUE_PATTERN[kind].test(value)) {
    throw new Error(`${kind} tag value ${JSON.stringify(value)} does not match the expected pattern`);
  }
  const tag = `${PREFIX[kind]}${value}`;
  if (tag.length > MAX_TAG_LENGTH) {
    throw new Error(`tag exceeds ${MAX_TAG_LENGTH} characters: ${tag}`);
  }
  return tag;
}

/** The inverse of `encode`. Returns `null` for anything not a well-formed LATTICE tag. */
export function decode(tag: string): DecodedTag | null {
  if (tag === "lat:term") {
    return { kind: "term", value: null };
  }
  for (const kind of Object.keys(PREFIX) as Array<Exclude<TagKind, "term">>) {
    const prefix = PREFIX[kind];
    if (tag.startsWith(prefix)) {
      const value = tag.slice(prefix.length);
      return VALUE_PATTERN[kind].test(value) ? { kind, value } : null;
    }
  }
  return null;
}

/** The content control `title`, cut to 64 characters. The appearance shows the title, so colour
 * is never the only cue (plan WA8). `text` is the section heading, variable label or defined
 * term, as the table requires; ignored for `clause`, `definition` and `term`. */
export function title(kind: TagKind, text?: string): string {
  let raw: string;
  switch (kind) {
    case "section":
      raw = `Section: ${text ?? ""}`;
      break;
    case "variable":
      raw = `Variable: ${text ?? ""}`;
      break;
    case "reference":
      raw = `Defined term: ${text ?? ""}`;
      break;
    case "clause":
      raw = "Clause";
      break;
    case "definition":
      raw = "Definition";
      break;
    case "term":
      raw = "Term";
      break;
  }
  return raw.length > MAX_TITLE_LENGTH ? raw.slice(0, MAX_TITLE_LENGTH) : raw;
}
