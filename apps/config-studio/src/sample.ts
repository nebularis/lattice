// SPDX-License-Identifier: MPL-2.0
// The sample pane's model (sketch 10.3, ADR-A154): which compiled forms a scheme has and whether a runtime exists for each, and the session that
// keeps the sample, the last compilation and the last run. Nothing runs until `run()` is called, which compiles when the mapping part or the other
// parts have changed since the last compilation and then starts a `sample` run through the run controller. An edit, a new sample or a new format
// never starts one. The counts a run gave are kept with what they were counted from, so the session can say they are out of date.

import { CST, MORK, SKOS, localName, type Graph } from "@lattice/authoring-domain";
import { SAMPLE_FORMATS, sampleFormat, type SampleFormat } from "./rdf/mapping";
import type { Artefact } from "./rdf/report";
import type { RunController, RunPart, RunState } from "./runs";

export type FormKind = "construct" | "xslt" | "jolt" | "rml";

/** One form a compilation wrote for a scheme. */
export interface Form {
  kind: FormKind;
  label: string;
  /** The sample format the form reads, none for a form no runtime reads. */
  reads?: SampleFormat;
  /** Whether a runtime of the studio runs the form. */
  runtime: boolean;
  path: string;
  mediaType: string;
  content: string;
}

/** The forms of each source and whether a runtime exists for each (sketch 10.3). RDF is run by `mork_rdf` in the Python worker, XML and JSON by the Java run worker. */
export const FORM_TABLE: Record<FormKind, { label: string; reads?: SampleFormat; runtime: boolean }> = {
  construct: { label: "SPARQL CONSTRUCT", reads: "text/turtle", runtime: true },
  xslt: { label: "XSLT 3.0", reads: "application/xml", runtime: true },
  jolt: { label: "JOLT", reads: "application/json", runtime: true },
  rml: { label: "RML", runtime: false },
};

/** What the pane says of a form no runtime runs. */
export const WAITS = "Waits on an RML runtime. The scheme is written as RML, and nothing in the studio runs it yet.";

const formatName = (f: SampleFormat) => SAMPLE_FORMATS.find(([m]) => m === f)![1];

/**
 * The source formats a scheme's mappings read, as `mork:format` names them for the representation scheme of each source concept. A concept that is
 * an `mork:Entity`, or is represented as one, is read from RDF, which needs no description of its structure.
 */
export function sourceFormats(graph: Graph, scheme: string): Set<string> {
  const formats = new Set<string>();
  const entity = (term: string) => graph.types(term).includes(MORK("Entity"));
  for (const mapping of graph.subjects(MORK("mappingScheme"), scheme)) {
    for (const concept of graph.objects(mapping, MORK("mappingFor"))) {
      let named = false;
      for (const rs of graph.objects(concept, SKOS("inScheme"))) {
        const format = graph.value(rs, MORK("format"));
        if (format) {
          formats.add(localName(format));
          named = true;
        }
      }
      if (!named && (entity(concept.value) || graph.objects(concept, MORK("representedAs")).some((r) => entity(r.value)))) formats.add("RDF");
    }
  }
  return formats;
}

/** The mapping scheme whose mappings read a representation scheme, which is how an example source finds the scheme it belongs to. */
export function schemeReading(graph: Graph, source: string): string | undefined {
  for (const concept of graph.subjects(SKOS("inScheme"), source)) {
    for (const mapping of graph.subjects(MORK("mappingFor"), concept)) {
      const scheme = graph.value(mapping, MORK("mappingScheme"));
      if (scheme) return scheme;
    }
  }
  return undefined;
}

/** The forms of a scheme that a compilation's artefacts hold, in the order the table lists them. */
export function formsOf(artefacts: readonly Artefact[], scheme: string, formats: ReadonlySet<string>): Form[] {
  const forms: Form[] = [];
  for (const a of artefacts.filter((x) => x.group === scheme)) {
    const kind: FormKind | undefined =
      a.path.endsWith(".compiled.ttl") && formats.has("RDF") ? "construct" : a.mediaType === "application/xslt+xml" ? "xslt" : a.path.endsWith(".jolt.json") ? "jolt" : a.path.endsWith(".rml.ttl") ? "rml" : undefined;
    if (kind) forms.push({ kind, ...FORM_TABLE[kind], path: a.path, mediaType: a.mediaType, content: a.content });
  }
  const order = Object.keys(FORM_TABLE);
  return forms.sort((a, b) => order.indexOf(a.kind) - order.indexOf(b.kind) || a.path.localeCompare(b.path));
}

/** The template libraries a scheme instantiates from. Libraries arrive with a later slice, so a scheme names none yet. */
export function librariesOf(_graph: Graph, _scheme: string): string[] {
  return [];
}

/** What a run wrote, by mapping and stratum, from the artefact parts of its frames. */
export interface RunResult {
  /** Each mapping's output lines, by the stratum that wrote them. */
  lines: Map<string, { stratum: number; lines: string[] }[]>;
  /** The first stratum each mapping ran in. */
  ran: Map<string, number>;
  strata: number;
}

export function runResult(parts: readonly RunPart[]): RunResult {
  const lines = new Map<string, { stratum: number; lines: string[] }[]>();
  const ran = new Map<string, number>();
  let strata = 0;
  for (const p of parts) {
    if (p.role !== "artefact" || p.group === undefined) continue;
    const stratum = p.step ?? 0;
    strata = Math.max(strata, stratum + 1);
    lines.set(p.group, [...(lines.get(p.group) ?? []), { stratum, lines: p.text.split("\n").filter(Boolean) }]);
    ran.set(p.group, Math.min(ran.get(p.group) ?? stratum, stratum));
  }
  return { lines, ran, strata };
}

/** The engine a run's report names with `cst:engine`, where it names one. */
export function engineOf(parts: readonly RunPart[], parse: (text: string) => Graph): string | undefined {
  const report = parts.find((p) => p.role === "report");
  if (!report) return undefined;
  try {
    return parse(report.text).quads(null, CST("engine"))[0]?.object.value;
  } catch {
    return undefined;
  }
}

// --- the session ---

/** A compilation of the mapping part, with what it was made from. `graph` and `context` are unknown for one the pane found and did not make. */
export interface Compilation {
  job: string;
  artefacts: Artefact[];
  graph?: Graph;
  context?: string;
  /** Whether the pane made it, and so may remove it when it makes another. */
  owned: boolean;
}

/** The last run that completed, with what it ran over. */
export interface LastRun {
  job: string;
  parts: RunPart[];
  graph: Graph;
  context: string;
  sample: string;
  format: SampleFormat;
}

export interface SampleState {
  scheme?: string;
  sample?: string;
  format: SampleFormat;
  /** The mapping part the pane lists forms and examples of. */
  graph?: Graph;
  libraries: string[];
  compilation?: Compilation;
  /** Whether the compilation is of the mapping part and the other parts as they are now. False where it predates an edit or is not known to be current. */
  compilationCurrent: boolean;
  forms: Form[];
  /** The form that runs, the author's choice or the one the sample's format reads. */
  form?: Form;
  /** Why Run is off, in words, where it is. */
  blocked?: string;
  /** What the author should know where Run is on, such as that no form of the scheme reads the sample, so the run covers the other schemes of the part. */
  note?: string;
  canRun: boolean;
  preparing: boolean;
  problem?: string;
  run: RunState;
  last?: LastRun;
  /** Whether the scheme, another part or the sample has changed since the last run, so that its counts are out of date. */
  stale: boolean;
}

export interface Compiled {
  job: string;
  artefacts: Artefact[];
}

export interface SampleDeps {
  workspace: string;
  /** Compiles the mapping part as given and gives the finished job, or throws with why it failed. */
  compile(graph: Graph): Promise<Compiled>;
  /** The latest finished compilation of the mapping part the workspace holds, which lists the forms before this pane has compiled one. */
  latest(): Promise<Compiled | undefined>;
  /** Removes a compilation this pane made and has replaced. */
  forget(job: string): void;
  controller: RunController;
  storage: { get(key: string): string | undefined; set(key: string, value?: string): void };
}

export interface SampleInputs {
  graph: Graph;
  /** The revisions of the parts a compilation reads beside the mapping part, which say when it is out of date (ADR-A149). */
  context: string;
}

export interface SampleSession {
  getState(): SampleState;
  subscribe(listener: () => void): () => void;
  /** The mapping part and the revisions of the other parts, as the workspace holds them now. Changing them starts no run. */
  setInputs(inputs: SampleInputs): void;
  /** The scheme the pane lists the forms of, which the view picks. */
  setScheme(scheme?: string): void;
  setSample(text?: string, filename?: string): void;
  setFormat(format: SampleFormat): void;
  chooseForm(kind?: FormKind): void;
  /** Reads the latest compilation the workspace holds, once, so that its forms are listed before this pane compiles one. */
  refresh(): Promise<void>;
  /** Compiles when the parts have changed since the last compilation, then runs the form over the sample. The only way a run starts. */
  run(): Promise<void>;
  dispose(): void;
}

const IDLE: RunState = { phase: "idle" };

/** One session a workspace. The sample and its format are kept in the browser's storage for the workspace, as they always were. */
export function createSampleSession(deps: SampleDeps): SampleSession {
  const { controller, storage } = deps;
  const key = `lattice-studio:mapping-sample:${deps.workspace}`;
  const listeners = new Set<() => void>();
  let inputs: SampleInputs | undefined;
  let scheme: string | undefined;
  let sample = storage.get(key);
  let format = (storage.get(`${key}:format`) as SampleFormat | undefined) ?? sampleFormat(sample ?? "");
  let chosen: FormKind | undefined;
  let compilation: Compilation | undefined;
  let inflight: { graph: Graph; context: string; promise: Promise<Compilation> } | undefined;
  let preparing = false;
  let problem: string | undefined;
  let last: LastRun | undefined;
  let pending: { number: number; ran: Omit<LastRun, "parts"> } | undefined;
  let cached: SampleState | undefined;
  let disposed = false;
  let refreshed = false;

  const change = () => {
    cached = undefined;
    for (const l of [...listeners]) l();
  };

  const current = (c: Compilation | undefined) => !!c && !!inputs && c.graph === inputs.graph && c.context === inputs.context;

  const build = (): SampleState => {
    const forms = compilation && scheme && inputs ? formsOf(compilation.artefacts, scheme, sourceFormats(inputs.graph, scheme)) : [];
    const explicit = forms.find((f) => f.kind === chosen);
    const form = explicit ?? forms.find((f) => f.reads === format) ?? forms.find((f) => f.runtime) ?? forms[0];
    const run = controller.getState();
    const busy = preparing || run.phase === "running" || run.phase === "queued";
    let blocked: string | undefined;
    let note: string | undefined;
    if (!sample?.trim()) blocked = "Give a sample to run.";
    else if (form) {
      // A run covers every scheme of the mapping part that reads the sample's format, so a form the author did not choose never stops it, and one the author chose does where it cannot run the sample.
      if (!form.runtime) blocked = WAITS;
      else if (explicit && explicit.reads !== format) blocked = `${explicit.label} reads ${formatName(explicit.reads!)}, and this sample is ${formatName(format)}. Change the sample's format or pick another form.`;
      else if (!explicit && form.reads !== format) note = `No form of this scheme reads a ${formatName(format)} sample. The run covers the schemes of the mapping part that do.`;
    }
    return {
      scheme,
      sample,
      format,
      graph: inputs?.graph,
      libraries: inputs && scheme ? librariesOf(inputs.graph, scheme) : [],
      compilation,
      compilationCurrent: current(compilation),
      forms,
      form,
      blocked,
      note,
      canRun: !blocked && !busy,
      preparing,
      problem,
      run,
      last,
      stale: !!last && (!inputs || last.graph !== inputs.graph || last.context !== inputs.context || last.sample !== sample || last.format !== format),
    };
  };

  /** A run that completed is the last run, with what it ran over. Any other end leaves the last run as it was. */
  const settle = () => {
    const state = controller.getState();
    if (pending && "number" in state && state.number === pending.number) {
      if (state.phase === "complete") {
        last = { ...pending.ran, parts: state.parts };
        pending = undefined;
      } else if (state.phase === "failed" || state.phase === "incomplete" || state.phase === "refused") pending = undefined;
    }
    change();
  };
  const stop = controller.subscribe(settle);

  const ensureCompiled = (): Promise<Compilation> => {
    const now = inputs!;
    if (compilation && current(compilation)) return Promise.resolve(compilation);
    if (inflight && inflight.graph === now.graph && inflight.context === now.context) return inflight.promise;
    const promise = (async () => {
      const done = await deps.compile(now.graph);
      const replaced = compilation;
      compilation = { job: done.job, artefacts: done.artefacts, graph: now.graph, context: now.context, owned: true };
      if (replaced?.owned) deps.forget(replaced.job);
      return compilation;
    })();
    const entry = { graph: now.graph, context: now.context, promise };
    inflight = entry;
    const clear = () => {
      if (inflight === entry) inflight = undefined;
    };
    promise.then(clear, clear);
    return promise;
  };

  return {
    getState: () => (cached ??= build()),
    subscribe(listener) {
      listeners.add(listener);
      return () => void listeners.delete(listener);
    },
    setInputs(next) {
      if (inputs && inputs.graph === next.graph && inputs.context === next.context) return;
      inputs = next;
      change();
    },
    setScheme(next) {
      if (scheme === next) return;
      scheme = next;
      chosen = undefined;
      change();
    },
    setSample(text, filename) {
      const before = sample;
      sample = text;
      storage.set(key, text);
      chosen = undefined;
      // The format is read from a sample the first time it has text, from a file's name, and again when an edit makes it another kind of document, so that typing in a sample never undoes the format the author set.
      if (text && (filename !== undefined || !before?.trim() || sampleFormat(text) !== sampleFormat(before))) {
        format = sampleFormat(text, filename);
        storage.set(`${key}:format`, format);
      }
      change();
    },
    setFormat(next) {
      format = next;
      chosen = undefined;
      storage.set(`${key}:format`, next);
      change();
    },
    chooseForm(kind) {
      chosen = kind;
      change();
    },
    async refresh() {
      if (refreshed || disposed) return;
      refreshed = true;
      try {
        const found = await deps.latest();
        if (found && !compilation && !disposed) {
          compilation = { job: found.job, artefacts: found.artefacts, owned: false };
          change();
        }
      } catch {
        // The forms are listed once the pane compiles.
      }
    },
    async run() {
      const before = build();
      if (!before.canRun || !inputs || disposed) return;
      problem = undefined;
      preparing = true;
      change();
      try {
        const compiled = await ensureCompiled();
        if (disposed) return;
        const body = sample!;
        controller.start({ workspace: deps.workspace, kind: "sample", target: "mapping", job: compiled.job, body, mediaType: format });
        const started = controller.getState();
        pending = { number: "number" in started ? started.number : 0, ran: { job: compiled.job, graph: compiled.graph!, context: compiled.context!, sample: body, format } };
      } catch (error) {
        problem = error instanceof Error ? error.message : String(error);
      } finally {
        preparing = false;
        change();
      }
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      stop();
      controller.dispose();
      listeners.clear();
    },
  };
}

export const IDLE_SAMPLE: SampleState = { format: "text/turtle", libraries: [], compilationCurrent: false, forms: [], canRun: false, preparing: false, run: IDLE, stale: false };
