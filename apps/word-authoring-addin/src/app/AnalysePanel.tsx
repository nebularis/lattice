import type { Detection, DocumentReport, ValidationResult } from "@lattice/authoring-domain";
import type { JobStatus } from "../domain/poll";

export interface AnalysePanelProps {
  canAnalyse: boolean;
  onAnalyse: () => void;
  jobStatus: JobStatus | null;
  /** The studio's report on the document as last saved, null until a save has succeeded. */
  report: DocumentReport | null;
  onAccept: (detection: Detection) => void;
}

function groupByElement(items: ValidationResult[]): Map<string, ValidationResult[]> {
  const groups = new Map<string, ValidationResult[]>();
  for (const item of items) {
    const key = item.elementId ?? "(document)";
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  return groups;
}

/** The Analyse tab: saves the document to its workspace, runs the analyse job and lists the report. */
export function AnalysePanel({ canAnalyse, onAnalyse, jobStatus, report, onAccept }: AnalysePanelProps): JSX.Element {
  return (
    <section aria-label="Analyse">
      <button type="button" disabled={!canAnalyse} onClick={onAnalyse}>
        Analyse
      </button>

      {jobStatus && <p>Job: {jobStatus}</p>}

      {report && (
        <>
          <h2>Validation</h2>
          {[...groupByElement(report.validation).entries()].map(([elementId, results]) => (
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
            {report.findings.map((finding, index) => (
              <li key={index}>
                {finding.severity}: {finding.message}
              </li>
            ))}
          </ul>

          <h2>Detections</h2>
          <ul>
            {report.detections.map((detection, index) => (
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
