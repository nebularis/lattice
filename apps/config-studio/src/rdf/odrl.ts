// SPDX-License-Identifier: MPL-2.0
// The browser half of the ODRL import (contracts/config-studio/README.md, "Importing an ODRL policy"): the document a job
// carries, and the job's artefacts added to the configurations they belong to.

import { CST, Graph, TYPE, iri, literal } from "@lattice/authoring-domain";
import { mergeProposals } from "./meaning";
import type { Artefact } from "./report";
import { CONFIG_PARTS, type ConfigPart } from "./split";

export const ODRL_PROFILE = "http://www.w3.org/ns/odrl/2/";
const CONFORMS_TO = "http://purl.org/dc/terms/conformsTo";

/** The media type a file is read as, from how the author supplied it and never from its content (STD-292). */
export function mediaTypeOf(filename: string): string | undefined {
  const ext = filename.toLowerCase().match(/\.([a-z]+)$/)?.[1];
  return ext === "jsonld" || ext === "json" ? "application/ld+json" : ext === "ttl" ? "text/turtle" : ext === "nt" ? "application/n-triples" : undefined;
}

/** The one `cst:ImportDocument` of an odrl job's body, minted under the workspace. `confirmed` is the author's confirmation
 * that the file is an ODRL 2.2 policy. */
export function importDocument(workspace: string, content: string, mediaType: string, confirmed: boolean, into?: string): Graph {
  const node = `urn:lattice:studio:ws:${workspace}:import/1`;
  return Graph.empty().edit((e) => {
    e.add(node, TYPE, iri(CST("ImportDocument")));
    e.add(node, CST("documentContent"), literal(content));
    e.add(node, CST("documentMediaType"), literal(mediaType));
    if (confirmed) e.add(node, CONFORMS_TO, iri(ODRL_PROFILE));
    if (into) e.add(node, CST("importInto"), iri(into));
  });
}

export interface Applied {
  /** The graph each configuration is to be edited to. */
  edits: Partial<Record<ConfigPart, Graph>>;
  added: number;
  /** Artefacts for a group that cannot be an unsaved edit, such as the baseline, whose roles the author adds there. */
  unapplied: Artefact[];
}

/** Adds each artefact to the configuration its group names. Review goes through `mergeProposals`, the rest merge. */
export function applyArtefacts(artefacts: Artefact[], current: Partial<Record<ConfigPart, Graph>>): Applied {
  const out: Applied = { edits: {}, added: 0, unapplied: [] };
  for (const a of artefacts) {
    const part = a.group as ConfigPart;
    if (!(CONFIG_PARTS as string[]).includes(part)) {
      out.unapplied.push(a);
      continue;
    }
    const base = out.edits[part] ?? current[part] ?? Graph.empty();
    if (part === "review") {
      const merged = mergeProposals(base, Graph.parse(a.content));
      out.edits[part] = merged.review;
      out.added += merged.added;
    } else {
      out.edits[part] = base.merge(Graph.parse(a.content));
    }
  }
  return out;
}
