/**
 * Helpers that translate a model text offset into what Office.js's `Range.search` needs (plan
 * WA8 section "Files under `src/`"). JavaScript strings already count UTF-16 code units, the same
 * unit plan §2.5 uses for every `start`/`end`, so no conversion is needed here, unlike the Python
 * worker's `offsets.py`.
 */

/**
 * The 0-based index, among all (possibly overlapping) occurrences of `text` within
 * `elementText`, of the one that begins at `start`. Matches the index Office.js's
 * `RangeCollection.items[occurrence]` expects after a `search(text)` call. Throws if `text` does
 * not occur at `start`.
 */
export function occurrenceIndex(elementText: string, start: number, text: string): number {
  if (text.length === 0) {
    throw new Error("cannot locate the occurrence of an empty search string");
  }
  let occurrence = 0;
  let searchFrom = 0;
  while (true) {
    const found = elementText.indexOf(text, searchFrom);
    if (found === -1 || found > start) {
      break;
    }
    if (found === start) {
      return occurrence;
    }
    occurrence += 1;
    searchFrom = found + 1;
  }
  throw new Error(`"${text}" does not occur at offset ${start} in the element text`);
}

/** Escapes `^`, the one character Word's search API treats specially, as `^^`. */
export function escapeWordSearch(text: string): string {
  return text.replace(/\^/g, "^^");
}
