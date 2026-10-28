/**
 * The studio's own templates and the document markup samples, read from the contracts, for tests
 * that need a real template and a real document.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { readMarkup, type AuthoringTemplate, type DocumentSnapshot } from "@lattice/authoring-domain";
import { parseTemplates } from "../../api/client";

const REPO_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../../..");

export function readRepoFile(relativePath: string): string {
  return readFileSync(path.join(REPO_ROOT, relativePath), "utf-8");
}

export const TEMPLATES: AuthoringTemplate[] = parseTemplates(readRepoFile("contracts/config-studio/document-templates.ttl"));

export function loadSample(sampleId: string): DocumentSnapshot {
  return readMarkup(readRepoFile(`contracts/document/samples/${sampleId}.xml`));
}

export function loadTemplate(templateId: string): AuthoringTemplate {
  const template = TEMPLATES.find((candidate) => candidate.templateId === templateId);
  if (!template) throw new Error(`no template ${templateId}`);
  return template;
}
