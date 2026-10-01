/**
 * Reads and writes the document's `AuthoringMetadata` as the custom XML part Word stores it in
 * (plan WA8 section "`DocumentPort`"), namespace `urn:nebularis:lattice:authoring:1`.
 */
import type { AuthoringMetadata } from "../word/port";
import type { ValueType } from "./types";
import { childrenByNameNs, escapeXml, firstChildByNameNs, parseXmlDocument } from "./xml";

export const METADATA_NAMESPACE = "urn:nebularis:lattice:authoring:1";

export function toXml(metadata: AuthoringMetadata): string {
  const revisionXml = metadata.revision === null ? "" : `<revision>${metadata.revision}</revision>`;
  const variablesXml = metadata.variables
    .map(
      (variable) =>
        `<variable key="${escapeXml(variable.variableKey)}" label="${escapeXml(variable.label)}" valueType="${escapeXml(
          variable.valueType,
        )}"/>`,
    )
    .join("");
  return (
    `<authoring xmlns="${METADATA_NAMESPACE}">` +
    `<documentId>${escapeXml(metadata.documentId)}</documentId>` +
    `<templateId>${escapeXml(metadata.templateId)}</templateId>` +
    `<title>${escapeXml(metadata.title)}</title>` +
    revisionXml +
    `<variables>${variablesXml}</variables>` +
    `</authoring>`
  );
}

export function fromXml(xml: string): AuthoringMetadata {
  const doc = parseXmlDocument(xml);
  const root = doc.documentElement;
  const text = (name: string) => firstChildByNameNs(root, METADATA_NAMESPACE, name)?.textContent ?? "";
  const revisionEl = firstChildByNameNs(root, METADATA_NAMESPACE, "revision");
  const variablesEl = firstChildByNameNs(root, METADATA_NAMESPACE, "variables");
  const variables = variablesEl
    ? childrenByNameNs(variablesEl, METADATA_NAMESPACE, "variable").map((el) => ({
        variableKey: el.getAttribute("key") ?? "",
        label: el.getAttribute("label") ?? "",
        valueType: (el.getAttribute("valueType") ?? "text") as ValueType,
      }))
    : [];
  return {
    documentId: text("documentId"),
    templateId: text("templateId"),
    title: text("title"),
    revision: revisionEl ? Number(revisionEl.textContent) : null,
    variables,
  };
}
