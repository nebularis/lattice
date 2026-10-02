import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { guessValueType, suggestKey } from "./keys";
import type { ValueType } from "./types";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../../../..");
const FIXTURE = path.join(REPO_ROOT, "contracts/authoring/fixtures/suggested-keys.json");

interface Case {
  text: string;
  valueType: ValueType;
  suggestedKey: string;
}

describe("suggestKey and guessValueType against suggested-keys.json (S9a-06)", () => {
  const cases: Case[] = JSON.parse(readFileSync(FIXTURE, "utf-8"));

  it.each(cases)("$text -> $valueType / $suggestedKey", (testCase) => {
    expect(guessValueType(testCase.text)).toBe(testCase.valueType);
    expect(suggestKey(testCase.text, testCase.valueType)).toBe(testCase.suggestedKey);
  });
});
