// SPDX-License-Identifier: MPL-2.0
// Where a finding is drawn on the surface canvas (SVA-Q61 (a)). The findings are the ones the form shows, from the same source, so a finding is
// never invented here and never hidden. Each is placed by its focus node and path on the element that claims them, a binding, an edge or a box.
// A finding whose focus is the contract goes on the contract's carrier. One that cannot be placed stays in the form's list alone.

import type { Issue } from "../rdf/report";
import type { Claim, Drawing } from "./drawing";

export interface Placement {
  /** The findings of each node and edge of the drawing, by its id. */
  byElement: Map<string, Issue[]>;
  /** The findings no element claims. They stay in the form's list. */
  unplaced: Issue[];
}

/** How well a claim answers a finding, 3 where it names the finding's path, 2 where it is the element's general claim, 1 where it names other paths of the same node. */
function tier(claim: Claim, issue: Issue): number {
  if (claim.focus !== issue.focus) return 0;
  if (claim.paths === undefined) return 2;
  return issue.path !== undefined && claim.paths.includes(issue.path) ? 3 : 1;
}

export function placeFindings(drawing: Pick<Drawing, "nodes" | "edges">, issues: readonly Issue[]): Placement {
  const elements = [...drawing.nodes.map((n) => ({ id: n.id, claims: n.claims })), ...drawing.edges.map((e) => ({ id: e.id, claims: e.claims }))];
  const byElement = new Map<string, Issue[]>();
  const unplaced: Issue[] = [];
  for (const issue of issues) {
    if (issue.focus === undefined) {
      unplaced.push(issue);
      continue;
    }
    const scored = elements.map((e) => ({ id: e.id, tier: Math.max(0, ...e.claims.map((c) => tier(c, issue))) })).filter((e) => e.tier > 0);
    const best = Math.max(0, ...scored.map((e) => e.tier));
    if (best === 0) {
      unplaced.push(issue);
      continue;
    }
    // Where an element names the path, or states the node generally, each such element shows it. Elements that only name another path of the node
    // are a last resort, and the first of them shows it.
    const chosen = best >= 2 ? scored.filter((e) => e.tier === best) : scored.slice(0, 1);
    for (const e of chosen) byElement.set(e.id, [...(byElement.get(e.id) ?? []), issue]);
  }
  return { byElement, unplaced };
}

/** The worst severity of a list of findings, for the mark an element carries. */
export function worst(issues: readonly Issue[] | undefined): Issue["severity"] | undefined {
  if (!issues?.length) return undefined;
  return issues.some((i) => i.severity === "Violation") ? "Violation" : issues.some((i) => i.severity === "Warning") ? "Warning" : "Info";
}
