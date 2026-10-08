/**
 * The suggested-key rule and value-type guess WA3's `ConstructDetector` uses in Java
 * (`platform/authoring-service/.../detection/ConstructDetector.java`), ported for the ribbon's
 * `markVariable` command (plan WA9a). Kept in exact parity (S9a-06 checks every case of
 * `contracts/authoring/fixtures/suggested-keys.json` against both).
 */
import type { ValueType } from "./types";

const MONEY_PATTERN = /(?:GBP|USD|EUR|£|\$|€)\s?\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?(?:\s?(?:million|bn|m)\b)?/u;
const PERCENTAGE_PATTERN = /\d+(?:\.\d+)?\s?(?:%|per cent\b|percent\b)/iu;
const DATE_PATTERN =
  /\b\d{1,2}(?:st|nd|rd|th)?\s(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d{4}\b|\b\d{4}-\d{2}-\d{2}\b/u;
const DURATION_PATTERN =
  /\b(?:\d{1,4}|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fourteen|fifteen|twenty|thirty|sixty|ninety)(?:\s\(\d{1,4}\))?\s(?:business\s|calendar\s|banking\s)?(?:days?|weeks?|months?|years?)\b/iu;

/** Guesses a value type from a selection's whole trimmed text: money, percentage, date, duration,
 * in that order, else `text`. */
export function guessValueType(text: string): ValueType {
  const trimmed = text.trim();
  if (MONEY_PATTERN.test(trimmed)) return "money";
  if (PERCENTAGE_PATTERN.test(trimmed)) return "percentage";
  if (DATE_PATTERN.test(trimmed)) return "date";
  if (DURATION_PATTERN.test(trimmed)) return "duration";
  return "text";
}

/** `[Agent]` → `agent`, `GBP 250` → `gbp-250`, `120 days` → `duration-120-days` (WA3's rule,
 * `ConstructDetector.suggestedKey`). */
export function suggestKey(text: string, valueType: ValueType): string {
  let key = toKey(text.toLowerCase().replace(/[^a-z0-9]+/g, "-"));
  if (key.length === 0 || /^[0-9]/.test(key)) {
    key = toKey(`${valueType}-${key}`);
  }
  return key;
}

function toKey(value: string): string {
  const trimmed = strip(value);
  return strip(trimmed.length > 40 ? trimmed.slice(0, 40) : trimmed);
}

function strip(value: string): string {
  return value.replace(/^-+|-+$/g, "");
}
