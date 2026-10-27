// SPDX-License-Identifier: MPL-2.0
// Compile jobs: submit the edited configuration, follow the job through its states, and read what
// the compiler produced: the compiled profile, the SPARQL per operation, the surfaces, its
// findings and the gaps between what is declared and what the SPARQL implements.

import { useCallback, useEffect, useMemo, useState } from "react";
import { Check, Copy, Database, Download, FileText, Hammer, Sparkles } from "lucide-react";
import { api, jobId } from "../api";
import { nodeFor } from "../rdf/editors";
import type { Issue, Job } from "../rdf/report";
import type { Part } from "../state";
import { Code, Conforms, SeverityIcon, Spinner, ago, download } from "./kit";
import { useStudio } from "./Workspace";

const STEPS = ["Queued", "Running", "Finished"] as const;

export function BuildView() {
  const { id, model, open } = useStudio();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selected, setSelected] = useState<string>();
  const [detail, setDetail] = useState<Job>();
  const [error, setError] = useState<string>();

  const refresh = useCallback(() => api.compileJobs(id).then(setJobs).catch((e: Error) => setError(e.message)), [id]);
  useEffect(() => void refresh(), [refresh]);

  // Follow the selected job until it finishes.
  useEffect(() => {
    if (!selected) return;
    let live = true;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const job = await api.job(jobId(selected));
        if (!live) return;
        setDetail(job);
        if (job.status === "Queued" || job.status === "Running") timer = setTimeout(poll, 500);
        else void refresh();
      } catch (e) {
        if (live) setError(e instanceof Error ? e.message : String(e));
      }
    };
    void poll();
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [selected, refresh]);

  useEffect(() => {
    if (!selected && jobs[0]) setSelected(jobs[0].iri);
  }, [jobs, selected]);

  const compile = async (part: Part) => {
    setError(undefined);
    try {
      const job = await api.submit(id, "compile", part, model.state.configs[part]!.current);
      setDetail(undefined);
      setSelected(`urn:lattice:studio:job:${job}`);
      void refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="page" style={{ maxWidth: 1400 }}>
      <div className="page-head">
        <div className="grow">
          <h1>Build</h1>
          <p>Compile the configuration as it stands in the editor, saved or not. The persistence compiler gives the compiled profile and its SPARQL, the surface compiler the generated surfaces.</p>
        </div>
        <button className="btn" disabled={!model.state.configs.persistence!.current.size} onClick={() => void compile("persistence")}>
          <Database size={15} /> Compile persistence
        </button>
        <button className="btn primary" disabled={!model.state.configs.surface!.current.size} onClick={() => void compile("surface")}>
          <Sparkles size={15} /> Compile surface
        </button>
      </div>
      {error && <p style={{ color: "var(--bad)" }}>{error}</p>}
      <div className="build-grid">
        <div className="card" style={{ overflow: "hidden" }}>
          <div className="list-head" style={{ padding: "10px 14px", borderBottom: "1px solid var(--border)", fontWeight: 600 }}>
            History
          </div>
          {jobs.length === 0 && <div className="empty small">No compile yet.</div>}
          {jobs.map((j) => (
            <div key={j.iri} className="list-item" aria-selected={j.iri === selected} onClick={() => setSelected(j.iri)}>
              {j.target === "Persistence" ? <Database size={15} color="var(--persist)" /> : <Sparkles size={15} color="var(--surface-c)" />}
              <div className="grow">
                <div className="name">{j.target}</div>
                <div className="detail">{ago(j.submittedAt)}</div>
              </div>
              <StatusMark job={j} />
            </div>
          ))}
        </div>
        <div>{detail ? <JobDetail
              job={detail}
              onIssue={(issue) => {
                const part = detail.target === "Persistence" ? "persistence" : "surface";
                const node = nodeFor(model.state.configs[part]!.current, issue);
                if (node) open(part, node, issue.path);
              }}
            /> : selected ? <Spinner /> : <EmptyBuild />}</div>
      </div>
    </div>
  );
}

function EmptyBuild() {
  return (
    <div className="card empty">
      <Hammer size={28} />
      <h3>Nothing compiled yet</h3>
      <p>Compile a configuration to see what your application would run.</p>
    </div>
  );
}

function StatusMark({ job }: { job: Job }) {
  if (job.status === "Queued" || job.status === "Running") return <Spinner />;
  if (job.status === "Failed") return <span className="chip bad">failed</span>;
  return job.conforms === undefined ? null : <Conforms ok={job.conforms} />;
}

function JobDetail({ job, onIssue }: { job: Job; onIssue: (issue: Issue) => void }) {
  const reached = job.status === "Queued" ? 0 : job.status === "Running" ? 1 : 2;
  const groups = useMemo(() => {
    const out = new Map<string, Job["artefacts"]>();
    for (const a of job.artefacts) out.set(a.group, [...(out.get(a.group) ?? []), a]);
    return [...out.entries()];
  }, [job.artefacts]);
  const [file, setFile] = useState<string>();
  const artefact = job.artefacts.find((a) => a.path === file) ?? job.artefacts[0];
  const [copied, setCopied] = useState(false);

  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div className="card" style={{ padding: 16 }}>
        <div className="row" style={{ flexWrap: "wrap", gap: 16 }}>
          <div className="timeline" aria-label="Job state">
            {STEPS.map((s, i) => (
              <span key={s} className="row" style={{ gap: 0 }}>
                {i > 0 && <span className={`bar${i <= reached ? " on" : ""}`} />}
                <span className={`step${i <= reached ? " on" : ""}`}>
                  {i === reached && reached < 2 ? <Spinner size={12} /> : i < reached || reached === 2 ? <Check size={13} /> : null}
                  {s === "Finished" && reached === 2 ? job.status : s}
                </span>
              </span>
            ))}
          </div>
          <span className="spacer" />
          {job.status === "Succeeded" && (
            <span className={`status`} style={{ color: job.conforms ? "var(--ok)" : "var(--bad)" }}>
              <Conforms ok={!!job.conforms} /> {job.conforms ? "Compiled" : "Refused"}
            </span>
          )}
          <span className="small muted mono">{job.iri.replace("urn:lattice:studio:job:", "").slice(0, 8)}</span>
        </div>
        {job.failure && (
          <p style={{ color: "var(--bad)", marginBottom: 0 }}>
            The job could not run: {job.failure}
          </p>
        )}
      </div>

      {job.issues.length > 0 && (
        <div className="card" style={{ padding: "6px 0" }}>
          {job.issues.map((i, n) => (
            <div key={n} className="issue" onClick={() => onIssue(i)}>
              <span className="sev">
                <SeverityIcon severity={i.severity} />
              </span>
              <span className="grow">
                {i.message}
                <div className="where">{[i.code, i.focus].filter(Boolean).join(" · ")}</div>
              </span>
            </div>
          ))}
        </div>
      )}

      {job.artefacts.length > 0 && (
        <div className="card" style={{ display: "grid", gridTemplateColumns: "260px 1fr", overflow: "hidden" }}>
          <div className="file-list" style={{ borderRight: "1px solid var(--border)", maxHeight: 640, overflow: "auto" }} role="listbox" aria-label="Artefacts">
            {groups.map(([group, files]) => (
              <div key={group}>
                <div className="grp">{group || "output"}</div>
                {files.map((a) => (
                  <button key={a.path} role="option" aria-selected={a === artefact} onClick={() => setFile(a.path)} title={a.path}>
                    <FileText size={13} /> <span className="ellipsis">{a.path.split("/").pop()}</span>
                  </button>
                ))}
              </div>
            ))}
          </div>
          {artefact && (
            <div style={{ minWidth: 0, padding: 12 }}>
              <div className="row" style={{ marginBottom: 8 }}>
                <strong className="grow mono ellipsis">{artefact.path}</strong>
                <span className="chip">{artefact.mediaType}</span>
                <button
                  className="btn sm"
                  onClick={() => {
                    void navigator.clipboard.writeText(artefact.content);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 1200);
                  }}
                >
                  {copied ? <Check size={13} /> : <Copy size={13} />} Copy
                </button>
                <button className="btn sm" onClick={() => download(artefact.path.split("/").pop() ?? "artefact", artefact.content, artefact.mediaType)}>
                  <Download size={13} /> Download
                </button>
              </div>
              <Code text={artefact.content} maxHeight={600} />
            </div>
          )}
        </div>
      )}

      {job.gaps.length > 0 && (
        <div className="card" style={{ overflow: "hidden" }}>
          <table className="grid">
            <thead>
              <tr>
                <th>Gap: declared, not implemented by the SPARQL</th>
                <th style={{ width: 140 }}>Obligation of</th>
              </tr>
            </thead>
            <tbody>
              {job.gaps.map((g, i) => (
                <tr key={i}>
                  <td>
                    {g.message}
                    <div className="small muted mono">{g.group}</div>
                  </td>
                  <td>
                    <span className={`chip ${g.obligation === "caller" ? "accent" : g.obligation === "unimplemented" ? "warn" : ""}`}>{g.obligation}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
