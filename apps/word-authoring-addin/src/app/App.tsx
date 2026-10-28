/**
 * The task pane's root component (plan WA9): tabs Document, Markup, Analyse, Logical English,
 * Graph, and an error banner. Holds all shared state; each panel is a plain function of props.
 */
import { useEffect, useRef, useState } from "react";
import type { StudioClient, Workspace } from "../api/client";
import { ApiError } from "../api/client";
import { buildSnapshot } from "../domain/snapshot";
import { parseBody, writePackage, writeSections, writeTemplate, type WritableSection } from "../domain/ooxml";
import type { JobStatus } from "../domain/poll";
import type {
  AnalysisView,
  AuthoringTemplate,
  SampleSummary,
  Section,
  ValueType,
} from "@lattice/authoring-domain";
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
  api: StudioClient;
  bridge: UiBridge;
  options?: AppOptions;
}

export function App({ port, api, bridge, options }: AppProps): JSX.Element {
  const [activeTab, setActiveTab] = useState<Tab>("document");
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState<boolean | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [templates, setTemplates] = useState<AuthoringTemplate[]>([]);
  const [samples, setSamples] = useState<SampleSummary[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<AuthoringTemplate | null>(null);
  const [metadata, setMetadata] = useState<AuthoringMetadata | null>(null);
  const [sections, setSections] = useState<Section[]>([]);
  const [markMessage, setMarkMessage] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisView | null>(null);
  const [proposals, setProposals] = useState<string | null>(null);
  const [graphTurtle, setGraphTurtle] = useState<string | null>(null);
  const [variableDraft, setVariableDraft] = useState<VariableDraft | null>(null);
  const [referenceDraft, setReferenceDraft] = useState<ReferenceDraft | null>(null);
  const handleAnalyseRef = useRef(handleAnalyse);

  useEffect(() => {
    handleAnalyseRef.current = handleAnalyse;
  });

  useEffect(() => {
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

  async function loadCatalog(): Promise<void> {
    try {
      const [loadedWorkspaces, loadedTemplates, loadedSamples] = await Promise.all([
        api.listWorkspaces(),
        api.listTemplates(),
        api.listSamples(),
      ]);
      setConnected(true);
      setWorkspaces(loadedWorkspaces);
      setWorkspaceId((current) => current ?? loadedWorkspaces[0]?.id ?? null);
      setTemplates(loadedTemplates);
      setSamples(loadedSamples);
    } catch (e) {
      setConnected(false);
      setError(messageOf(e));
    }
  }

  async function handleCreateWorkspace(label: string): Promise<void> {
    try {
      const created = await api.createWorkspace(label);
      setWorkspaces((current) => [...current, created]);
      setWorkspaceId(created.id);
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
      const template = templates.find((candidate) => candidate.templateId === templateId);
      if (!template) throw new Error(`No template ${templateId}.`);
      const nextMetadata: AuthoringMetadata = {
        documentId: newUuid(),
        templateId: template.templateId,
        title: template.title,
        ...(workspaceId ? { workspaceId } : {}),
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
      const sample = await api.getSample(sampleId);
      const template = templates.find((candidate) => candidate.templateId === sample.templateId);
      if (!template) throw new Error(`No template ${sample.templateId}.`);
      const headingBySectionKey = new Map(template.sections.map((section) => [section.sectionKey, section.heading]));
      const nextMetadata: AuthoringMetadata = {
        documentId: newUuid(),
        templateId: sample.templateId,
        title: sample.title,
        ...(workspaceId ? { workspaceId } : {}),
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
    if (!workspaceId) {
      setError("Pick or create a workspace first.");
      return;
    }
    try {
      const ooxml = await port.readBodyOoxml();
      const parsed = parseBody(ooxml);
      setSections(parsed.sections);
      const { snapshot } = buildSnapshot(parsed, metadata);

      // A document saved in another workspace is a new document in this one.
      const revision = metadata.workspaceId === workspaceId ? metadata.revision : null;
      const saved = await api.saveDocument(workspaceId, snapshot, revision);
      const nextMetadata: AuthoringMetadata = { ...metadata, workspaceId, revision: saved };
      await port.writeMetadata(nextMetadata);
      setMetadata(nextMetadata);
      setJobStatus("queued");
      setAnalysis(null);
      setProposals(null);

      try {
        const result = await api.analyse(workspaceId, metadata.documentId, { timeoutMs: options?.pollTimeoutMs });
        setJobStatus("succeeded");
        setAnalysis(result.view);
        setProposals(result.proposals);
      } catch (e) {
        setJobStatus("failed");
        throw e;
      }
    } catch (e) {
      setError(messageOf(e));
    }
  }

  async function handleShowTurtle(): Promise<void> {
    if (!metadata || !metadata.workspaceId || metadata.revision === null) return;
    try {
      setGraphTurtle(await api.getDocumentGraph(metadata.workspaceId, metadata.documentId));
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
          workspaces={workspaces}
          workspaceId={workspaceId}
          onSelectWorkspace={setWorkspaceId}
          onCreateWorkspace={handleCreateWorkspace}
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
          jobStatus={jobStatus}
          findings={analysis?.conformance ?? null}
        />
      )}

      {activeTab === "le" && <LogicalEnglishPanel analysis={analysis?.analysis ?? null} />}

      {activeTab === "graph" && (
        <GraphPanel
          analysis={analysis?.analysis ?? null}
          documentTurtle={graphTurtle}
          proposalsTurtle={proposals}
          onShowTurtle={handleShowTurtle}
        />
      )}
    </div>
  );
}

function messageOf(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return String(e);
}
