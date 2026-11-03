// SPDX-License-Identifier: MPL-2.0
// What a save changed, as a patch the service applies to the part it holds (DR-Q5 (c), DR-Q7 (b)).

import { DataFactory, Writer } from "n3";
import type { Graph, Quad } from "@lattice/authoring-domain";

/** The service's names for the two graphs of a patch, `Command.PATCH_ADD` and `Command.PATCH_DEL`. */
export const PATCH_ADD = "urn:lattice:studio:patch:add";
export const PATCH_DEL = "urn:lattice:studio:patch:del";

export interface Patch {
  add: Quad[];
  del: Quad[];
}

/** What `current` adds to `saved` and removes from it, or undefined when either holds a blank node, which a patch cannot name. */
export function patchOf(saved: Graph, current: Graph): Patch | undefined {
  const add = current.quads().filter((q) => !saved.store.has(q));
  const del = saved.quads().filter((q) => !current.store.has(q));
  const blank = (q: Quad) => q.subject.termType === "BlankNode" || q.object.termType === "BlankNode";
  return add.some(blank) || del.some(blank) ? undefined : { add, del };
}

/** The patch as TriG, its two graphs named as the service expects. */
export function patchTrig(patch: Patch, prefixes: Record<string, string> = {}): string {
  const { namedNode, quad } = DataFactory;
  const writer = new Writer({ format: "application/trig", prefixes });
  const into = (graph: string) => (q: Quad) => writer.addQuad(quad(q.subject, q.predicate, q.object, namedNode(graph)));
  patch.add.forEach(into(PATCH_ADD));
  patch.del.forEach(into(PATCH_DEL));
  let text = "";
  writer.end((error, result) => {
    if (error) throw error;
    text = result ?? "";
  });
  // an empty side is still named, so the service sees both graphs
  for (const graph of [PATCH_ADD, PATCH_DEL]) if (!text.includes(`<${graph}>`)) text += `\n<${graph}> {}\n`;
  return text;
}
