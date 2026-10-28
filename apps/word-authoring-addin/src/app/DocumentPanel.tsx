import { useState } from "react";
import type { AuthoringTemplate, SampleSummary } from "@lattice/authoring-domain";
import type { Workspace } from "../api/client";

export interface DocumentPanelProps {
  workspaces: Workspace[];
  workspaceId: string | null;
  onSelectWorkspace: (workspaceId: string) => void;
  onCreateWorkspace: (label: string) => void;
  templates: AuthoringTemplate[];
  samples: SampleSummary[];
  selectedTemplate: AuthoringTemplate | null;
  onApplyTemplate: (templateId: string) => void;
  onInsertSample: (sampleId: string) => void;
  onCopyBodyOoxml: () => void;
}

/** The Document tab (plan WA9 "Panels"): template/sample catalogue, apply/insert, and the current
 * template's sections with heading, admitted term kinds and guidance. */
export function DocumentPanel({
  workspaces,
  workspaceId,
  onSelectWorkspace,
  onCreateWorkspace,
  templates,
  samples,
  selectedTemplate,
  onApplyTemplate,
  onInsertSample,
  onCopyBodyOoxml,
}: DocumentPanelProps): JSX.Element {
  const [newLabel, setNewLabel] = useState("");
  return (
    <section aria-label="Document">
      <h2>Workspace</h2>
      <select aria-label="Workspace" value={workspaceId ?? ""} onChange={(event) => onSelectWorkspace(event.target.value)}>
        <option value="" disabled>
          Pick a workspace
        </option>
        {workspaces.map((workspace) => (
          <option key={workspace.id} value={workspace.id}>
            {workspace.label || workspace.id}
          </option>
        ))}
      </select>
      <input aria-label="New workspace" value={newLabel} onChange={(event) => setNewLabel(event.target.value)} />
      <button
        type="button"
        disabled={newLabel.trim() === ""}
        onClick={() => {
          onCreateWorkspace(newLabel.trim());
          setNewLabel("");
        }}
      >
        Create workspace
      </button>

      <h2>Templates</h2>
      <ul>
        {templates.map((template) => (
          <li key={template.templateId}>
            {template.title}
            <button type="button" onClick={() => onApplyTemplate(template.templateId)}>
              Apply template
            </button>
          </li>
        ))}
      </ul>

      <h2>Samples</h2>
      <ul>
        {samples.map((sample) => (
          <li key={sample.sampleId}>
            {sample.title}
            <button type="button" onClick={() => onInsertSample(sample.sampleId)}>
              Insert sample
            </button>
          </li>
        ))}
      </ul>

      {selectedTemplate && (
        <>
          <h2>Sections</h2>
          <ul>
            {selectedTemplate.sections.map((section) => (
              <li key={section.sectionKey}>
                <strong>{section.heading}</strong> ({section.allowedTermKinds.join(", ") || "no term kinds"})
                <p>{section.guidance}</p>
              </li>
            ))}
          </ul>
        </>
      )}

      <button type="button" onClick={onCopyBodyOoxml}>
        Copy body OOXML
      </button>
    </section>
  );
}
