import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { validate } from "./schemas";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "../../../..");
const VALID_DIR = path.join(REPO_ROOT, "contracts/authoring/fixtures/valid");
const INVALID_DIR = path.join(REPO_ROOT, "contracts/authoring/fixtures/invalid");
const SAMPLES_DIR = path.join(REPO_ROOT, "contracts/authoring/samples");
const TEMPLATES_DIR = path.join(REPO_ROOT, "contracts/authoring/templates");

function load(file: string): unknown {
  return JSON.parse(readFileSync(file, "utf-8"));
}

function schemaNameFor(fileName: string): string {
  const stem = fileName.replace(/\.json$/, "");
  return stem.split("--")[0];
}

describe("schemas.validate against the WA1 fixtures (S8-07, same outcomes as AC-05 to AC-07)", () => {
  it("validates every valid fixture with no errors", () => {
    for (const fileName of readdirSync(VALID_DIR)) {
      const name = schemaNameFor(fileName);
      const errors = validate(name, load(path.join(VALID_DIR, fileName)));
      expect(errors, `${fileName}: ${errors.join("; ")}`).toEqual([]);
    }
  });

  it("rejects every invalid fixture with at least one error", () => {
    for (const fileName of readdirSync(INVALID_DIR)) {
      const name = schemaNameFor(fileName);
      const errors = validate(name, load(path.join(INVALID_DIR, fileName)));
      expect(errors.length).toBeGreaterThan(0);
    }
  });

  it("validates every WA1 sample as a document-snapshot", () => {
    for (const fileName of readdirSync(SAMPLES_DIR)) {
      const errors = validate("document-snapshot", load(path.join(SAMPLES_DIR, fileName)));
      expect(errors, `${fileName}: ${errors.join("; ")}`).toEqual([]);
    }
  });

  it("validates every WA1 template as an authoring-template", () => {
    for (const fileName of readdirSync(TEMPLATES_DIR)) {
      const errors = validate("authoring-template", load(path.join(TEMPLATES_DIR, fileName)));
      expect(errors, `${fileName}: ${errors.join("; ")}`).toEqual([]);
    }
  });

  it("throws for an unknown schema name", () => {
    expect(() => validate("no-such-schema", {})).toThrow();
  });
});
