import type { Detection, SnapshotAccepted, ValidationResult } from "../domain/types";
import type { JobView } from "../domain/types";

export interface AnalysePanelProps {
  canAnalyse: boolean;
  onAnalyse: () => void;
  snapshotAccepted: SnapshotAccepted | null;
  job: JobView | null;
  onAccept: (detection: Detection) => void;
}

function groupByElement<T extends { elementId: string | null }>(items: T[]): Map<string, T[]> {
  const groups = new Map<string, T[]>();
  for (const item of items) {
    const key = item.elementId ?? "(document)";
    const group = groups.get(key) ?? [];
    group.push(item);
    groups.set(key, group);
  }
  return groups;
}

/** The Analyse tab (plan WA9 "Panels"). */
export function AnalysePanel({ canAnalyse, onAnalyse, snapshotAccepted, job, onAccept }: AnalysePanelProps): JSX.Element {
  const validationGroups: Map<string, ValidationResult[]> = snapshotAccepted
    ? groupByElement(snapshotAccepted.validation.results)
    : new Map();

  return (
    <section aria-label="Analyse">
      <button type="button" disabled={!canAnalyse} onClick={onAnalyse}>
        Analyse
      </button>

      {job && <p>Job: {job.status}</p>}

      {snapshotAccepted && (
        <>
          <h2>Validation</h2>
          {[...validationGroups.entries()].map(([elementId, results]) => (
            <div key={elementId}>
              <h3>{elementId}</h3>
              <ul>
                {results.map((result, index) => (
                  <li key={index}>
                    {result.severity}: {result.message}
                  </li>
                ))}
              </ul>
            </div>
          ))}

          <h2>Template findings</h2>
          <ul>
            {snapshotAccepted.templateFindings.map((finding, index) => (
              <li key={index}>
                {finding.severity}: {finding.message}
              </li>
            ))}
          </ul>

          <h2>Detections</h2>
          <ul>
            {snapshotAccepted.detections.map((detection, index) => (
              <li key={index}>
                {detection.text} ({detection.kind})
                {detection.suggestion.action !== "none" && (
                  <button type="button" onClick={() => onAccept(detection)}>
                    Accept
                  </button>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
