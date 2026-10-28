import type { Finding } from "@lattice/authoring-domain";
import type { JobStatus } from "../domain/poll";

export interface AnalysePanelProps {
  canAnalyse: boolean;
  onAnalyse: () => void;
  jobStatus: JobStatus | null;
  /** The template findings of the analysis, null until an analysis has succeeded. */
  findings: Finding[] | null;
}

/** The Analyse tab: saves the document to its workspace, runs the analyse job and lists its findings. */
export function AnalysePanel({ canAnalyse, onAnalyse, jobStatus, findings }: AnalysePanelProps): JSX.Element {
  return (
    <section aria-label="Analyse">
      <button type="button" disabled={!canAnalyse} onClick={onAnalyse}>
        Analyse
      </button>

      {jobStatus && <p>Job: {jobStatus}</p>}

      {findings && (
        <>
          <h2>Template findings</h2>
          <ul>
            {findings.map((finding, index) => (
              <li key={index}>
                {finding.severity}: {finding.message}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
