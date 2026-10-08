/**
 * The task pane's root component (plan WA9): tabs Document, Markup, Analyse, Logical English,
 * Graph, and an error banner. Holds all shared state; each panel is a plain function of props.
 */
import { useEffect, useRef, useState } from "react";
import type { ApiClient } from "../api/client";
import { ApiError } from "../api/client";
import { buildSnapshot } from "../domain/snapshot";
import { occurrenceIndex } from "../domain/offsets";
import { parseBody, writePackage, writeSections, writeTemplate, type WritableSection } from "../domain/ooxml";
import { pollJob } from "../domain/poll";
import type {
  AnalysisView,
  AuthoringTemplate,
  Detection,
  DocumentSnapshot,
  Health,
  JobView,
  SampleList,
  Section,
  SnapshotAccepted,
  TemplateList,
  ValueType,
} from "../domain/types";
import { newUuid } from "../domain/uuid";
import type { AuthoringMetadata, DocumentPort, InlineMark, MarkResult } from "../word/port";
import { AnalysePanel } from "./AnalysePanel";
import { DocumentPanel } from "./DocumentPanel";
import { GraphPanel } from "./GraphPanel";
import { LogicalEnglishPanel } from "./LogicalEnglishPanel";
import { MarkupPanel } from "./MarkupPanel";
import { markResultMessage } from "./markMessages";
import type { Tab } from "./tabs";
import type { UiBridge, VariableDraft, ReferenceDraft } from "./uiBridge";

export interface AppOptions {
  pollTimeoutMs?: number;
}

export interface AppProps {
  port: DocumentPort;
  api: ApiClient;
  bridge: UiBridge;
  options?: AppOptions;
}

export function App({ port, api, bridge, options }: AppProps): JSX.Element {
  const [activeTab, setActiveTab] = useState<Tab>("document");
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState<boolean | null>(null);
  const [templates, setTemplates] = useState<TemplateList>([]);
  const [samples, setSamples] = useState<SampleList>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<AuthoringTemplate | null>(null);
  const [metadata, setMetadata] = useState<AuthoringMetadata | null>(null);
  const [sections, setSections] = useState<Section[]>([]);
  const [markMessage, setMarkMessage] = useState<string | null>(null);
  const [snapshotAccepted, setSnapshotAccepted] = useState<SnapshotAccepted | null>(null);
  const [job, setJob] = useState<JobView | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisView | null>(null);
  const [graphTurtle, setGraphTurtle] = useState<string | null>(null);
  const [variableDraft, setVariableDraft] = useState<VariableDraft | null>(null);
  const [referenceDraft, setReferenceDraft] = useState<ReferenceDraft | null>(null);
  const handleAnalyseRef = useRef(handleAnalyse);

  useEffect(() => {
    handleAnalyseRef.current = handleAnalyse;
  });

  useEffect(() => {
    void refreshHealth();
    void loadCatalog();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const unsubscribe = bridge.subscribe((state) => {
      if (state.tab) setActiveTab(state.tab);
      if (state.message !== null) setMarkMessage(state.message);
      if (state.variableDraft) setVariableDraft(state.variableDraft);
      if (state.referenceDraft) setReferenceDraft(state.referenceDraft);
      if (state.runAnalyse) {
        void handleAnalyseRef.current().finally(() => bridge.post({ runAnalyse: false }));
      }
    });
    return unsubscribe;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bridge]);

  async function refreshHealth(): Promise<void> {
    try {
      const health: Health = await api.health();
      setConnected(health.status === "ok" && health.fuseki === "up" && health.amqp === "up");
    } catch {
      setConnected(false);
    }
  }

  async function loadCatalog(): Promise<void> {
    try {
      const [loadedTemplates, loadedSamples] = await Promise.all([api.listTemplates(), api.listSamples()]);
      setTemplates(loadedTemplates);
      setSamples(loadedSamples);
    } catch (e) {
      setError(messageOf(e));
    }
  }

  async function refreshModel(): Promise<Section[]> {
    const ooxml = await port.readBodyOoxml();
    const parsed = parseBody(ooxml);
    setSections(parsed.sections);
    return parsed.sections;
  }

  function markOutcome(result: MarkResult): void {
    setMarkMessage(result.ok ? null : markResultMessage(result.reason));
  }

  async function handleApplyTemplate(templateId: string): Promise<void> {
    try {
      const template = await api.getTemplate(templateId);
      const nextMetadata: AuthoringMetadata = {
        documentId: newUuid(),
        templateId: template.templateId,
        title: template.title,
        revision: null,
        variables: template.variables,
      };
      await port.writeMetadata(nextMetadata);
      await port.insertOoxml(writePackage(writeTemplate(template)));
      setSelectedTemplate(template);
      setMetadata(nextMetadata);
      await refreshModel();
    } catch (e) {
      setError(messageOf(e));
    }
  }

  async function handleInsertSample(sampleId: string): Promise<void> {
    try {
      const sample: DocumentSnapshot = await api.getSample(sampleId);
      const template = await api.getTemplate(sample.templateId);
      const headingBySectionKey = new Map(template.sections.map((section) => [section.sectionKey, section.heading]));
      const nextMetadata: AuthoringMetadata = {
        documentId: newUuid(),
        templateId: sample.templateId,
        title: sample.title,
        revision: null,
        variables: sample.variables,
      };
      await port.writeMetadata(nextMetadata);
      const writable: WritableSection[] = sample.sections.map((section) => ({
        sectionKey: section.sectionKey,
        heading: headingBySectionKey.get(section.sectionKey) ?? section.sectionKey,
        elements: section.elements,
      }));
      await port.insertOoxml(writePackage(writeSections(writable)));
      setSelectedTemplate(template);
      setMetadata(nextMetadata);
      await refreshModel();
    } catch (e) {
      setError(messageOf(e));
    }
  }

  async function handleMark(mark: InlineMark, valueType?: ValueType): Promise<void> {
    try {
      const result = await port.markSelection(mark);
      markOutcome(result);
      if (result.ok) {
        await declareVariableIfNeeded(mark, valueType ?? "text");
        await refreshModel();
      }
    } catch (e) {
      setError(messageOf(e));
    }
  }

  async function handleWrap(kind: "clause" | "definition"): Promise<void> {
    try {
      const result = await port.wrapSelectionAsElement(kind, newUuid());
      markOutcome(result);
      if (result.ok) {
        await refreshModel();
      }
    } catch (e) {
      setError(messageOf(e));
    }
  }

  async function handleUnmark(): Promise<void> {
    try {
      const result = await port.unmarkSelection();
      markOutcome(result);
      if (result.ok) {
        await refreshModel();
      }
    } catch (e) {
      setError(messageOf(e));
    }
  }

  async function declareVariableIfNeeded(mark: InlineMark, valueType: ValueType): Promise<void> {
    if (mark.kind !== "variable" || !metadata) return;
    if (metadata.variables.some((variable) => variable.variableKey === mark.variableKey)) return;
    const nextMetadata: AuthoringMetadata = {
      ...metadata,
      variables: [...metadata.variables, { variableKey: mark.variableKey, label: mark.label, valueType }],
    };
    await port.writeMetadata(nextMetadata);
    setMetadata(nextMetadata);
  }

  async function handleAnalyse(): Promise<void> {
    if (!metadata) {
      setError("Apply a template or insert a sample first.");
      return;
    }
    try {
      const ooxml = await port.readBodyOoxml();
      const parsed = parseBody(ooxml);
      setSections(parsed.sections);
      const { snapshot } = buildSnapshot(parsed, metadata);

      const accepted = await api.submitSnapshot(metadata.documentId, { baseRevision: metadata.revision, snapshot });
      const nextMetadata: AuthoringMetadata = { ...metadata, revision: accepted.revision };
      await port.writeMetadata(nextMetadata);
      setMetadata(nextMetadata);
      setSnapshotAccepted(accepted);
      setJob(null);
      setAnalysis(null);

      const finalJob = await pollJob(api, accepted.job.jobId, { timeoutMs: options?.pollTimeoutMs });
      setJob(finalJob);
      if (finalJob.status === "completed") {
        const view = await api.getAnalysis(metadata.documentId, accepted.revision);
        setAnalysis(view);
      }
    } catch (e) {
      setError(messageOf(e));
    }
  }

  async function handleAccept(detection: Detection): Promise<void> {
    if (!metadata) return;
    try {
      const element = sections.flatMap((section) => section.elements).find((candidate) => candidate.elementId === detection.elementId);
      if (!element) return;
      const elementText = element.parts.map((part) => part.text).join("");
      const occurrence = occurrenceIndex(elementText, detection.start, detection.text);

      if (detection.suggestion.action === "mark-variable" && detection.suggestion.suggestedKey && detection.suggestion.valueType) {
        const variableKey = detection.suggestion.suggestedKey;
        const valueType = detection.suggestion.valueType;
        if (!metadata.variables.some((variable) => variable.variableKey === variableKey)) {
          const nextMetadata: AuthoringMetadata = {
            ...metadata,
            variables: [...metadata.variables, { variableKey, label: detection.text, valueType }],
          };
          await port.writeMetadata(nextMetadata);
          setMetadata(nextMetadata);
        }
        await port.markOccurrence(detection.elementId, detection.text, occurrence, {
          kind: "variable",
          variableKey,
          label: detection.text,
        });
      } else if (detection.suggestion.action === "mark-reference" && detection.suggestion.targetElementId) {
        await port.markOccurrence(detection.elementId, detection.text, occurrence, {
          kind: "reference",
          targetElementId: detection.suggestion.targetElementId,
          term: detection.text,
        });
      }
      await refreshModel();
    } catch (e) {
      setError(messageOf(e));
    }
  }

  async function handleShowTurtle(): Promise<void> {
    if (!metadata || metadata.revision === null) return;
    try {
      const text = await api.getGraph(metadata.documentId, metadata.revision, "proposal");
      setGraphTurtle(text);
    } catch (e) {
      setError(messageOf(e));
    }
  }

  const definitions = sections.flatMap((section) => section.elements).filter((element) => element.kind === "definition");

  return (
    <div className="addin-pane">
      <header className="addin-header">
        <span className={connected ? "status-connected" : "status-disconnected"}>
          {connected === null ? "Checking..." : connected ? "Connected" : "Disconnected"}
        </span>
      </header>

      {error && (
        <div className="error-banner" role="alert">
          {error}
          <button type="button" onClick={() => setError(null)}>
            Dismiss
          </button>
        </div>
      )}

      <nav className="tab-bar">
        {(
          [
            ["document", "Document"],
            ["markup", "Markup"],
            ["analyse", "Analyse"],
            ["le", "Logical English"],
            ["graph", "Graph"],
          ] as [Tab, string][]
        ).map(([tab, label]) => (
          <button
            key={tab}
            type="button"
            className={activeTab === tab ? "tab active" : "tab"}
            onClick={() => setActiveTab(tab)}
          >
            {label}
          </button>
        ))}
      </nav>

      {activeTab === "document" && (
        <DocumentPanel
          templates={templates}
          samples={samples}
          selectedTemplate={selectedTemplate}
          onApplyTemplate={handleApplyTemplate}
          onInsertSample={handleInsertSample}
          onCopyBodyOoxml={async () => {
            const ooxml = await port.readBodyOoxml();
            await navigator.clipboard.writeText(ooxml);
          }}
        />
      )}

      {activeTab === "markup" && (
        <MarkupPanel
          markMessage={markMessage}
          definitions={definitions}
          existingVariableKeys={metadata?.variables.map((variable) => variable.variableKey) ?? []}
          variableDraft={variableDraft}
          referenceDraft={referenceDraft}
          onMarkClause={() => handleWrap("clause")}
          onMarkDefinition={() => handleWrap("definition")}
          onMarkTerm={() => handleMark({ kind: "term" })}
          onMarkVariable={(variableKey, label, valueType) => handleMark({ kind: "variable", variableKey, label }, valueType)}
          onMarkDefinedTerm={(targetElementId, term) => handleMark({ kind: "reference", targetElementId, term })}
          onUnmark={handleUnmark}
        />
      )}

      {activeTab === "analyse" && (
        <AnalysePanel
          canAnalyse={metadata !== null}
          onAnalyse={handleAnalyse}
          snapshotAccepted={snapshotAccepted}
          job={job}
          onAccept={handleAccept}
        />
      )}

      {activeTab === "le" && <LogicalEnglishPanel analysis={analysis?.analysis ?? null} />}

      {activeTab === "graph" && (
        <GraphPanel analysis={analysis?.analysis ?? null} turtle={graphTurtle} onShowTurtle={handleShowTurtle} />
      )}
    </div>
  );
}

function messageOf(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return String(e);
}
