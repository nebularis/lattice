// SPDX-License-Identifier: MPL-2.0
// The workspace list, and the dialog that makes a workspace from a sample, uploaded Turtle or an exported workspace.

import { useEffect, useState } from "react";
import { Download, FilePlus2, FolderOpen, Layers, Trash2, Upload } from "lucide-react";
import { api, type Sample, type WorkspaceSummary } from "../api";
import { Baseline } from "../rdf/baseline";
import { Graph, TurtleError } from "@lattice/authoring-domain";
import { CONFIG_PARTS, split } from "../rdf/split";
import { Modal, Spinner, ago, go, readFiles } from "./kit";

export function Home() {
  const [workspaces, setWorkspaces] = useState<WorkspaceSummary[]>();
  const [error, setError] = useState<string>();
  const [creating, setCreating] = useState(false);

  const load = () =>
    api
      .workspaces()
      .then(setWorkspaces)
      .catch((e: Error) => setError(e.message));
  useEffect(() => void load(), []);

  const remove = async (w: WorkspaceSummary) => {
    if (!window.confirm(`Delete the workspace "${w.label}" and its configuration? This cannot be undone.`)) return;
    await api.deleteWorkspace(w.id);
    void load();
  };

  return (
    <div className="home">
      <div className="hero">
        <div className="grow">
          <div className="brand">
            <span className="mark">
              <Layers size={16} />
            </span>
            LATTICE Configuration Studio
          </div>
          <h1 style={{ marginTop: 18 }}>Configure how your ontology is stored and surfaced</h1>
          <p>
            Open a baseline, author its persistence profiles and surface contracts with forms read from the LATTICE ontologies, see every violation where it
            arises, and compile to the profile and SPARQL your application runs.
          </p>
        </div>
        <button className="btn primary" onClick={() => setCreating(true)}>
          <FilePlus2 size={16} /> New workspace
        </button>
      </div>

      {error && <div className="card" style={{ padding: 16, color: "var(--bad)" }}>The service did not answer: {error}</div>}
      {!workspaces && !error && (
        <div className="empty">
          <Spinner size={20} />
        </div>
      )}
      {workspaces && (
        <div className="ws-grid">
          {workspaces.map((w) => (
            <div
              key={w.id}
              className="card ws-card"
              role="link"
              tabIndex={0}
              onClick={() => go("w", w.id)}
              onKeyDown={(e) => e.key === "Enter" && go("w", w.id)}
            >
              <div className="row">
                <FolderOpen size={18} color="var(--accent)" />
                <h3 className="grow ellipsis">{w.label}</h3>
                <a
                  className="btn ghost icon sm"
                  aria-label={`Export ${w.label}`}
                  title="Export as a TriG file"
                  href={api.exportUrl(w.id)}
                  download
                  onClick={(e) => e.stopPropagation()}
                >
                  <Download size={14} />
                </a>
                <button
                  className="btn ghost icon sm"
                  aria-label={`Delete ${w.label}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    void remove(w);
                  }}
                >
                  <Trash2 size={14} />
                </button>
              </div>
              <div className="row small muted">Changed {ago(w.modifiedAt)}</div>
              <div className="row" style={{ flexWrap: "wrap" }}>
                {w.sample && <span className="chip">from sample {w.sample}</span>}
                <span className="chip baseline">baseline r{w.revisions.baseline}</span>
                {CONFIG_PARTS.filter((p) => w.revisions[p] > 0).map((p) => (
                  <span key={p} className="chip">
                    {p} r{w.revisions[p]}
                  </span>
                ))}
              </div>
            </div>
          ))}
          <button className="card ws-card new" onClick={() => setCreating(true)}>
            <span className="row">
              <FilePlus2 size={18} /> New workspace
            </span>
          </button>
        </div>
      )}
      {creating && <NewWorkspace onClose={() => setCreating(false)} />}
    </div>
  );
}

function NewWorkspace({ onClose }: { onClose: () => void }) {
  const [samples, setSamples] = useState<Sample[]>([]);
  const [source, setSource] = useState<string>("upload");
  const [label, setLabel] = useState("");
  const [files, setFiles] = useState<{ name: string; text: string }[]>([]);
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();

  useEffect(() => {
    api
      .samples()
      .then((s) => {
        setSamples(s);
        if (s.length) {
          setSource(s[0].id);
          setLabel(s[0].label);
        }
      })
      .catch(() => undefined);
  }, []);

  const parsed = (): Graph => {
    let graph = Graph.empty();
    for (const f of files) {
      try {
        graph = graph.merge(Graph.parse(f.text));
      } catch (e) {
        throw new TurtleError(`${f.name}: ${e instanceof Error ? e.message : String(e)}`);
      }
    }
    return graph;
  };

  let preview: string | undefined;
  const fromFiles = source === "upload" || source === "import";
  if (source === "upload" && files.length) {
    try {
      const parts = split(parsed());
      const b = new Baseline(parts.baseline);
      preview = `${b.classes.size} classes and ${b.properties.size} properties in the baseline. ${CONFIG_PARTS.map((p) => `${parts[p].size} ${p}`).join(", ")} triples.`;
    } catch (e) {
      preview = e instanceof Error ? e.message : String(e);
    }
  }

  const createIt = async () => {
    setBusy(true);
    setError(undefined);
    try {
      if (source === "import") {
        go("w", await api.importWorkspace(files[0].text, label.trim() || undefined));
        return;
      }
      const graph = source === "upload" ? parsed() : await api.sample(source);
      const parts = split(graph);
      const id = await api.createWorkspace(label.trim() || "Untitled workspace", parts.baseline, source === "upload" ? undefined : source);
      for (const part of CONFIG_PARTS) {
        if (parts[part].size) await api.save(id, part, parts[part], '"0"');
      }
      go("w", id);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setBusy(false);
    }
  };

  return (
    <Modal
      title="New workspace"
      subtitle="A workspace holds one baseline and the persistence and surface configuration authored against it."
      onClose={onClose}
      footer={
        <>
          {error && <span className="grow small" style={{ color: "var(--bad)" }}>{error}</span>}
          <button className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn primary" disabled={busy || (fromFiles && !files.length)} onClick={() => void createIt()}>
            {busy && <Spinner />} Create workspace
          </button>
        </>
      }
    >
      <label className="field-label" htmlFor="ws-name">
        Name
      </label>
      <input id="ws-name" className="input" value={label} placeholder="Lending platform" onChange={(e) => setLabel(e.target.value)} autoFocus />

      <div className="field-label" style={{ marginTop: 18 }}>
        Start from
      </div>
      <div className="choice-grid">
        {samples.map((s) => (
          <button
            key={s.id}
            className="choice-card"
            aria-pressed={source === s.id}
            onClick={() => {
              setSource(s.id);
              setLabel(s.label);
            }}
          >
            <span className="title">{s.label}</span>
            <span className="desc">{s.comment}</span>
          </button>
        ))}
        <button
          className="choice-card"
          aria-pressed={source === "upload"}
          onClick={() => {
            setSource("upload");
            setFiles([]);
          }}
        >
          <span className="title">Your own Turtle</span>
          <span className="desc">Upload a baseline, and any configuration you already have. Each subject is sorted into the baseline or a configuration by its terms.</span>
        </button>
        <button
          className="choice-card"
          aria-pressed={source === "import"}
          onClick={() => {
            setSource("import");
            setFiles([]);
            setLabel("");
          }}
        >
          <span className="title">An exported workspace</span>
          <span className="desc">A .trig file a workspace was exported to, here or on another machine. It comes back with its revisions, as a new workspace.</span>
        </button>
      </div>

      {fromFiles && (
        <div style={{ marginTop: 14 }}>
          <label
            className={`dropzone${over ? " over" : ""}`}
            style={{ display: "block" }}
            onDragOver={(e) => {
              e.preventDefault();
              setOver(true);
            }}
            onDragLeave={() => setOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setOver(false);
              void readFiles(e.dataTransfer.files).then(setFiles);
            }}
          >
            <Upload size={20} />
            <div style={{ marginTop: 6 }}>
              {files.length ? files.map((f) => f.name).join(", ") : source === "import" ? "Drop a .trig file here, or click to choose" : "Drop .ttl files here, or click to choose"}
            </div>
            <input
              type="file"
              accept={source === "import" ? ".trig,application/trig" : ".ttl,text/turtle"}
              multiple={source === "upload"}
              hidden
              onChange={(e) => e.target.files && void readFiles(e.target.files).then(setFiles)}
            />
          </label>
          {preview && <p className="small muted">{preview}</p>}
        </div>
      )}
    </Modal>
  );
}
