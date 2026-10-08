import type { AuthoringTemplate, SampleList, TemplateList } from "../domain/types";

export interface DocumentPanelProps {
  templates: TemplateList;
  samples: SampleList;
  selectedTemplate: AuthoringTemplate | null;
  onApplyTemplate: (templateId: string) => void;
  onInsertSample: (sampleId: string) => void;
  onCopyBodyOoxml: () => void;
}

/** The Document tab (plan WA9 "Panels"): template/sample catalogue, apply/insert, and the current
 * template's sections with heading, admitted term kinds and guidance. */
export function DocumentPanel({
  templates,
  samples,
  selectedTemplate,
  onApplyTemplate,
  onInsertSample,
  onCopyBodyOoxml,
}: DocumentPanelProps): JSX.Element {
  return (
    <section aria-label="Document">
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
