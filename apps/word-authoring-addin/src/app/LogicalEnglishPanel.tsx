import type { Analysis, ElementAnalysis, Span } from "../domain/types";

export interface LogicalEnglishPanelProps {
  analysis: Analysis | null;
}

const ROLE_LEGEND: Span["role"][] = [
  "fixed",
  "ignorable",
  "slot-variable",
  "slot-constant",
  "slot-text",
  "modal",
  "connective",
  "unmatched",
];

function renderSpans(text: string, spans: Span[]): JSX.Element[] {
  const pieces: JSX.Element[] = [];
  let cursor = 0;
  spans.forEach((span, index) => {
    if (span.start > cursor) {
      pieces.push(<span key={`gap-${index}`}>{text.slice(cursor, span.start)}</span>);
    }
    pieces.push(
      <span key={index} className={`role-${span.role}`}>
        {text.slice(span.start, span.end)}
      </span>,
    );
    cursor = span.end;
  });
  if (cursor < text.length) {
    pieces.push(<span key="tail">{text.slice(cursor)}</span>);
  }
  return pieces;
}

function ElementRow({ element }: { element: ElementAnalysis }): JSX.Element {
  return (
    <li>
      <strong>{element.objectId}</strong> {element.relationClass ?? "unmatched"} ({element.basis}
      {element.formId ? `, ${element.formId}` : ""})
      <p>{renderSpans(element.text, element.spans)}</p>
    </li>
  );
}

/** The Logical English tab (plan WA9 "Panels"). Every piece of document or API text is rendered
 * as React text (never `dangerouslySetInnerHTML`), per the plan's explicit anti-pattern. */
export function LogicalEnglishPanel({ analysis }: LogicalEnglishPanelProps): JSX.Element {
  if (!analysis) {
    return <section aria-label="Logical English">No analysis yet.</section>;
  }

  return (
    <section aria-label="Logical English">
      <h2>Legend</h2>
      <ul className="legend">
        {ROLE_LEGEND.map((role) => (
          <li key={role} className={`role-${role}`}>
            {role}
          </li>
        ))}
      </ul>

      <h2>Elements</h2>
      <ul>
        {analysis.elements.map((element) => (
          <ElementRow key={element.elementId} element={element} />
        ))}
      </ul>

      <h2>LE program</h2>
      <pre>{analysis.leProgram}</pre>
      <button type="button" onClick={() => navigator.clipboard.writeText(analysis.leProgram)}>
        Copy
      </button>
    </section>
  );
}
