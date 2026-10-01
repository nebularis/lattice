/**
 * Renders a `GraphView` (plan WA6/WA8) as Mermaid `flowchart` text, for the Graph tab (WA9).
 * Deterministic: node aliases are assigned `n0`, `n1`, ... in the graph view's own (already
 * sorted) node order, so the same `GraphView` always renders identical text.
 */
import type { GraphNodeKind, GraphView } from "./types";

const NODE_SHAPE: Record<GraphNodeKind, { open: string; close: string }> = {
  relation: { open: "[", close: "]" },
  element: { open: "(", close: ")" },
  role: { open: "{{", close: "}}" },
  variable: { open: "[[", close: "]]" },
};

/** Mermaid reserves `"` inside a quoted label; escaped as `#quot;` per Mermaid's own entity table. */
function escapeLabel(text: string): string {
  return text.replace(/"/g, "#quot;");
}

export function toMermaid(graphView: GraphView): string {
  const alias = new Map<string, string>();
  graphView.nodes.forEach((node, index) => alias.set(node.id, `n${index}`));

  const lines: string[] = ["flowchart LR"];
  for (const node of graphView.nodes) {
    const shape = NODE_SHAPE[node.kind];
    lines.push(`  ${alias.get(node.id)}${shape.open}"${escapeLabel(node.label)}"${shape.close}`);
  }
  for (const edge of graphView.edges) {
    const from = alias.get(edge.from);
    const to = alias.get(edge.to);
    if (from === undefined || to === undefined) {
      throw new Error(`edge references a node outside the graph view: ${edge.from} -> ${edge.to}`);
    }
    lines.push(`  ${from} -->|${escapeLabel(edge.label)}| ${to}`);
  }
  return lines.join("\n");
}
