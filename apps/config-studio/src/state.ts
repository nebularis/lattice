// SPDX-License-Identifier: MPL-2.0
// A workspace's state in the browser: the baseline, and per configuration the saved graph, the
// edited graph with its undo history, its revision and its latest validation. Edits never reach
// the service until saved. Validation runs on the edited graph, 600 ms after the last edit, with
// at most one job in flight per configuration, and a result for an older graph is discarded.

import { useCallback, useEffect, useMemo, useReducer, useRef } from "react";
import { ApiError, Conflict, api, awaitJob, type Target, type WorkspaceSummary } from "./api";
import { Baseline } from "./rdf/baseline";
import { checkReferences } from "./rdf/editors";
import { Graph } from "./rdf/graph";
import { bySeverity, type Issue } from "./rdf/report";
import type { Vocabulary } from "./rdf/vocabulary";

export type Part = Target;
export const PARTS: Part[] = ["persistence", "surface"];

export interface Validation {
  state: "idle" | "running" | "done" | "failed";
  issues: Issue[];
  /** The graph the issues are for. */
  of?: Graph;
  message?: string;
}

export interface Config {
  saved: Graph;
  current: Graph;
  revision: string;
  past: Graph[];
  future: Graph[];
  validation: Validation;
  saving: boolean;
}

export interface Conflicted {
  part: Part;
  theirs: Graph;
  revision: string;
}

interface State {
  summary?: WorkspaceSummary;
  baseline?: { graph: Graph; index: Baseline; revision: string };
  configs: Partial<Record<Part, Config>>;
  conflict?: Conflicted;
  error?: string;
}

type Action =
  | { type: "loaded"; summary: WorkspaceSummary; baseline: Graph; baselineRevision: string; configs: Record<Part, { graph: Graph; revision: string }> }
  | { type: "edit"; part: Part; graph: Graph }
  | { type: "undo" | "redo"; part: Part }
  | { type: "validation"; part: Part; validation: Validation }
  | { type: "saving"; part: Part; saving: boolean }
  | { type: "saved"; part: Part; graph: Graph; revision: string }
  | { type: "conflict"; conflict?: Conflicted }
  | { type: "baseline"; graph: Graph; revision: string }
  | { type: "error"; error?: string };

const HISTORY = 200;

function update(state: State, part: Part, change: (c: Config) => Config): State {
  const c = state.configs[part];
  return c ? { ...state, configs: { ...state.configs, [part]: change(c) } } : state;
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "loaded": {
      const configs: State["configs"] = {};
      for (const part of PARTS) {
        const { graph, revision } = action.configs[part];
        configs[part] = { saved: graph, current: graph, revision, past: [], future: [], validation: { state: "idle", issues: [] }, saving: false };
      }
      return {
        summary: action.summary,
        baseline: { graph: action.baseline, index: new Baseline(action.baseline), revision: action.baselineRevision },
        configs,
      };
    }
    case "edit":
      return update(state, action.part, (c) =>
        c.current === action.graph ? c : { ...c, current: action.graph, past: [...c.past, c.current].slice(-HISTORY), future: [] },
      );
    case "undo":
      return update(state, action.part, (c) =>
        c.past.length ? { ...c, current: c.past[c.past.length - 1], past: c.past.slice(0, -1), future: [c.current, ...c.future] } : c,
      );
    case "redo":
      return update(state, action.part, (c) =>
        c.future.length ? { ...c, current: c.future[0], future: c.future.slice(1), past: [...c.past, c.current] } : c,
      );
    case "validation":
      return update(state, action.part, (c) => ({ ...c, validation: action.validation }));
    case "saving":
      return update(state, action.part, (c) => ({ ...c, saving: action.saving }));
    case "saved":
      return update(state, action.part, (c) => ({ ...c, saved: action.graph, revision: action.revision, saving: false }));
    case "conflict":
      return { ...state, conflict: action.conflict };
    case "baseline":
      return { ...state, baseline: { graph: action.graph, index: new Baseline(action.graph), revision: action.revision } };
    case "error":
      return { ...state, error: action.error };
  }
}

export function isDirty(c?: Config): boolean {
  return !!c && c.current !== c.saved && c.current.toTurtle() !== c.saved.toTurtle();
}

export function useWorkspace(id: string, vocab: Vocabulary) {
  const [state, dispatch] = useReducer(reducer, { configs: {} });
  const latest = useRef(state);
  latest.current = state;

  const load = useCallback(async () => {
    try {
      const [summary, baseline, persistence, surface] = await Promise.all([
        api.workspace(id),
        api.graph(id, "baseline"),
        api.graph(id, "persistence"),
        api.graph(id, "surface"),
      ]);
      dispatch({ type: "loaded", summary, baseline: baseline.graph, baselineRevision: baseline.revision, configs: { persistence, surface } });
    } catch (error) {
      dispatch({ type: "error", error: error instanceof Error ? error.message : String(error) });
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  const edit = useCallback((part: Part, change: (g: Graph) => Graph) => {
    const c = latest.current.configs[part];
    if (c) dispatch({ type: "edit", part, graph: change(c.current) });
  }, []);

  const save = useCallback(
    async (part: Part, force?: { revision: string }) => {
      const c = latest.current.configs[part];
      if (!c) return;
      dispatch({ type: "saving", part, saving: true });
      const graph = c.current;
      try {
        const revision = await api.save(id, part, graph, force?.revision ?? c.revision);
        dispatch({ type: "saved", part, graph, revision });
      } catch (error) {
        dispatch({ type: "saving", part, saving: false });
        if (error instanceof Conflict) {
          const theirs = await api.graph(id, part);
          dispatch({ type: "conflict", conflict: { part, theirs: theirs.graph, revision: theirs.revision } });
        } else {
          dispatch({ type: "error", error: error instanceof ApiError ? `Saving failed: ${error.message}` : String(error) });
        }
      }
    },
    [id],
  );

  /** Settle a conflict: keep mine overwrites theirs, take theirs drops my unsaved edits. */
  const resolve = useCallback(
    async (keep: "mine" | "theirs") => {
      const conflict = latest.current.conflict;
      if (!conflict) return;
      dispatch({ type: "conflict" });
      if (keep === "mine") {
        await save(conflict.part, { revision: conflict.revision });
      } else {
        dispatch({ type: "edit", part: conflict.part, graph: conflict.theirs });
        dispatch({ type: "saved", part: conflict.part, graph: conflict.theirs, revision: conflict.revision });
      }
    },
    [save],
  );

  const replaceBaseline = useCallback(
    async (graph: Graph) => {
      const b = latest.current.baseline;
      if (!b) return;
      const revision = await api.save(id, "baseline", graph, b.revision);
      dispatch({ type: "baseline", graph, revision });
    },
    [id],
  );

  useValidation(id, "persistence", state, dispatch, vocab);
  useValidation(id, "surface", state, dispatch, vocab);

  const issues = useMemo(() => {
    const out: Record<Part, Issue[]> = { persistence: [], surface: [] };
    for (const part of PARTS) {
      const c = state.configs[part];
      if (!c || !state.baseline) continue;
      out[part] = [...c.validation.issues, ...checkReferences(c.current, state.baseline.index, vocab)].sort(bySeverity);
    }
    return out;
  }, [state.configs, state.baseline, vocab]);

  return {
    state,
    issues,
    edit,
    save,
    resolve,
    replaceBaseline,
    reload: load,
    undo: (part: Part) => dispatch({ type: "undo", part }),
    redo: (part: Part) => dispatch({ type: "redo", part }),
    dismissError: () => dispatch({ type: "error" }),
  };
}

export type WorkspaceModel = ReturnType<typeof useWorkspace>;

function useValidation(id: string, part: Part, state: State, dispatch: (a: Action) => void, vocab: Vocabulary) {
  const current = state.configs[part]?.current;
  const baselineRevision = state.baseline?.revision;
  const inFlight = useRef(false);
  const queued = useRef<Graph | undefined>(undefined);

  useEffect(() => {
    if (!current || !baselineRevision) return;
    const run = async (graph: Graph): Promise<void> => {
      // An empty configuration conforms by definition, and the store holds no graph for it.
      if (graph.size === 0) {
        dispatch({ type: "validation", part, validation: { state: "done", issues: [], of: graph } });
        return;
      }
      if (inFlight.current) {
        queued.current = graph;
        return;
      }
      inFlight.current = true;
      dispatch({ type: "validation", part, validation: { state: "running", issues: [], of: graph } });
      try {
        const jobId = await api.submit(id, "validate", part, graph);
        const job = await awaitJob(jobId);
        void api.deleteJob(jobId).catch(() => undefined);
        const validation: Validation =
          job.status === "Failed"
            ? { state: "failed", issues: [], of: graph, message: job.failure ?? "The validation job failed." }
            : { state: "done", issues: job.issues, of: graph };
        if (!queued.current) dispatch({ type: "validation", part, validation });
      } catch (error) {
        if (!queued.current) {
          dispatch({ type: "validation", part, validation: { state: "failed", issues: [], of: graph, message: error instanceof Error ? error.message : String(error) } });
        }
      } finally {
        inFlight.current = false;
        const next = queued.current;
        queued.current = undefined;
        if (next) void run(next);
      }
    };
    const timer = setTimeout(() => void run(current), 600);
    return () => clearTimeout(timer);
  }, [id, part, current, baselineRevision, dispatch, vocab]);
}
