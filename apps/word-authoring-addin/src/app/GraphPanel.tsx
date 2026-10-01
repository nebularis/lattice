import { useEffect, useState } from "react";
import mermaid from "mermaid";
import { toMermaid } from "../domain/mermaid";
import type { Analysis } from "../domain/types";

mermaid.initialize({ securityLevel: "strict", startOnLoad: false });

export interface GraphPanelProps {
  analysis: Analysis | null;
  turtle: string | null;
  onShowTurtle: () => void;
}

/** The Graph tab (plan WA9 "Panels"). The SVG is Mermaid's own sanitized output
 * (`securityLevel: "strict"` escapes node labels), a deliberately different, safer code path from
 * the Logical English tab's plain element text, which never goes through `dangerouslySetInnerHTML`. */
export function GraphPanel({ analysis, turtle, onShowTurtle }: GraphPanelProps): JSX.Element {
  const [svg, setSvg] = useState<string>("");

  useEffect(() => {
    if (!analysis) {
      setSvg("");
      return;
    }
    let cancelled = false;
    mermaid.render("wap-graph", toMermaid(analysis.graphView)).then((result) => {
      if (!cancelled) setSvg(result.svg);
    });
    return () => {
      cancelled = true;
    };
  }, [analysis]);

  return (
    <section aria-label="Graph">
      {analysis ? (
        <div className="graph-diagram" dangerouslySetInnerHTML={{ __html: svg }} />
      ) : (
        <p>No analysis yet.</p>
      )}
      <button type="button" onClick={onShowTurtle} disabled={!analysis}>
        Turtle
      </button>
      {turtle && <pre>{turtle}</pre>}
    </section>
  );
}
