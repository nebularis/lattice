// SPDX-License-Identifier: MPL-2.0
// Publishing (ADR-A149): every unit of the workspace's saved parts, the version each was last published as, and a button
// that publishes it. Nothing is published until someone presses it.

import { useEffect, useMemo, useState } from "react";
import { Link2, Pin, Send, Upload, X } from "lucide-react";
import { CST, Graph, LABEL, SKOS, TYPE, localName } from "@lattice/authoring-domain";
import { api, awaitJob, type WorkspaceSummary } from "../api";
import { CONFIG_PARTS, type ConfigPart } from "../rdf/split";
import { Spinner } from "./kit";
import { useStudio } from "./Workspace";

interface Unit {
  root: string;
  label: string;
  kind: string;
  /** Where it is authored: a part, or a held import named by its digest. */
  part: ConfigPart | "import";
  importDigest?: string;
}

/** The roots of the units table's classes in each part as saved, or, given `imported`, in that import whatever its part. */
export function unitsIn(table: Graph, saved: Partial<Record<ConfigPart, Graph>>, imported?: { graph: Graph; digest: string }): Unit[] {
  const out: Unit[] = [];
  for (const unit of table.ofType(CST("PublicationUnit"))) {
    const authored = table.value(unit.value, CST("authoredIn")) as ConfigPart | undefined;
    const part = imported ? "import" : authored;
    const graph = imported ? imported.graph : authored && saved[authored];
    if (!graph || !part) continue;
    const roots = new Set(table.objects(unit.value, CST("rootClass")).flatMap((c) => graph.subjects(TYPE, c.value).map((r) => r.value)));
    for (const root of roots) {
      if (root.startsWith("_:")) continue;
      out.push({ root, part, importDigest: imported?.digest, kind: table.value(unit.value, LABEL) ?? localName(unit.value), label: graph.value(root, LABEL) ?? graph.value(root, SKOS("prefLabel")) ?? localName(root) });
    }
  }
  return out.sort((a, b) => a.part.localeCompare(b.part) || a.label.localeCompare(b.label));
}

type Row = { state: "idle" | "publishing" } | { state: "failed"; message: string } | { state: "published"; version: string };

export function PublishView() {
  const studio = useStudio();
  const configs = studio.model.state.configs;
  const [table, setTable] = useState<Graph>();
  const [current, setCurrent] = useState<Record<string, string | null>>({});
  const [rows, setRows] = useState<Record<string, Row>>({});
  const [error, setError] = useState<string>();
  useEffect(() => void api.publicationUnits().then(setTable, (e: Error) => setError(e.message)), []);
  const saved = useMemo(() => Object.fromEntries(CONFIG_PARTS.map((p) => [p, configs[p]?.saved])) as Partial<Record<ConfigPart, Graph>>, [configs]);
  const [imported, setImported] = useState<Record<string, Graph>>({});
  const held = studio.model.state.summary!.imports;
  useEffect(() => {
    for (const i of held) if (!imported[i.digest]) void api.importGraph(studio.id, i.digest).then((g) => setImported((m) => ({ ...m, [i.digest]: g })), () => undefined);
  }, [held]); // eslint-disable-line react-hooks/exhaustive-deps
  const units = useMemo(
    () => (table ? [...unitsIn(table, saved), ...held.flatMap((i) => (imported[i.digest] ? unitsIn(table, {}, { graph: imported[i.digest], digest: i.digest }) : []))] : []),
    [table, saved, held, imported],
  );
  useEffect(() => {
    for (const u of units) {
      void api.lineage(u.root).then((g) => setCurrent((c) => ({ ...c, [u.root]: g?.value(u.root, CST("current")) ?? null })), () => undefined);
    }
  }, [units]);

  const publish = async (u: Unit) => {
    setRows((r) => ({ ...r, [u.root]: { state: "publishing" } }));
    try {
      const id = await api.preparePublication(studio.id, u.part, u.root, u.importDigest);
      const job = await awaitJob(id);
      if (job.status === "Failed") throw new Error(job.failure ?? "The publish job failed.");
      const lineage = await api.publish(studio.id, id);
      void api.deleteJob(id).catch(() => undefined);
      const version = lineage.value(u.root, CST("current")) ?? "";
      setCurrent((c) => ({ ...c, [u.root]: version }));
      setRows((r) => ({ ...r, [u.root]: { state: "published", version } }));
    } catch (e) {
      setRows((r) => ({ ...r, [u.root]: { state: "failed", message: e instanceof Error ? e.message : String(e) } }));
    }
  };

  const summary = studio.model.state.summary!;
  if (error) return <div className="empty">{error}</div>;
  if (!table) return <div className="empty"><Spinner size={20} /></div>;
  return (
    <div className="view">
      <h2>Publish</h2>
      <p className="muted">
        Publishing a unit makes the part as saved a version that never changes, which any workspace may depend on and a deployment may fetch. Publishing
        content that is unchanged names the version it already has.
      </p>
      {units.length === 0 && <div className="empty small">No part of this workspace holds a unit to publish yet.</div>}
      <table className="table">
        <thead>
          <tr>
            <th>Unit</th>
            <th>Kind</th>
            <th>Part</th>
            <th>Current version</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {units.map((u) => {
            const row = rows[u.root] ?? { state: "idle" };
            const unsaved = u.part !== "import" && configs[u.part] && configs[u.part]!.current !== configs[u.part]!.saved;
            const version = current[u.root];
            return (
              <tr key={u.root}>
                <td title={u.root}>{u.label}</td>
                <td>{u.kind}</td>
                <td>{u.part}</td>
                <td className="small" title={version ?? undefined}>
                  {version === undefined ? <Spinner size={12} /> : version ? version.slice(version.lastIndexOf("/rev/") + 5) : "not published"}
                  {row.state === "failed" && <div className="error small">{row.message}</div>}
                </td>
                <td>
                  <button className="btn sm" disabled={row.state === "publishing"} title={unsaved ? "Publishes the part as saved, not your unsaved edits" : undefined} onClick={() => void publish(u)}>
                    {row.state === "publishing" ? <Spinner size={12} /> : <Send size={14} />} Publish
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <Imports summary={summary} onChange={studio.model.setSummary} />
      <Dependencies summary={summary} onChange={studio.model.setSummary} />
    </div>
  );
}

/** The imports the workspace holds, read only, and a way to add one from a file (ADR-A149 decision 6). */
function Imports({ summary, onChange }: { summary: WorkspaceSummary; onChange: (s: WorkspaceSummary) => void }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string>();
  const add = async (file: File) => {
    setBusy(true);
    try {
      const xml = /\.(rdf|owl|xml)$/i.test(file.name);
      onChange(await api.fenceImport(summary.id, await file.text(), xml ? "application/rdf+xml" : "text/turtle", file.name));
      setMessage(undefined);
    } catch (e) {
      setMessage(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  const release = (digest: string) =>
    void api.releaseImport(summary.id, digest).then(
      () => onChange({ ...summary, imports: summary.imports.filter((i) => i.digest !== digest) }),
      (e: Error) => setMessage(e.message),
    );
  return (
    <>
      <h3 style={{ marginTop: 24 }}>Imports</h3>
      <p className="muted">
        An import is kept as it was read, stored once whichever workspaces hold it, and never edited. The workspace reads it, and its units can be published.
      </p>
      {message && <div className="error small">{message}</div>}
      <ul className="list">
        {summary.imports.map((i) => (
          <li key={i.digest} title={i.graph}>
            {i.label} <span className="muted small">{i.digest.slice(0, 16)}</span>
            <button className="btn ghost icon" aria-label={`Release ${i.label}`} onClick={() => release(i.digest)}>
              <X size={14} />
            </button>
          </li>
        ))}
      </ul>
      <label className="btn sm">
        {busy ? <Spinner size={12} /> : <Upload size={14} />} Import a Turtle or RDF/XML file
        <input type="file" accept=".ttl,.rdf,.owl,.xml" hidden disabled={busy} onChange={(e) => e.target.files?.[0] && void add(e.target.files[0])} />
      </label>
    </>
  );
}

const shortVersion = (v: string) => v.slice(v.lastIndexOf("/rev/") + 5);
const lineageOf = (v: string) => (v.includes("/rev/1-") ? v.slice(0, v.lastIndexOf("/rev/1-")) : v);

/** What the workspace depends on, and the registry to choose from (ADR-A149 decisions 5 and 7). */
function Dependencies({ summary, onChange }: { summary: WorkspaceSummary; onChange: (s: WorkspaceSummary) => void }) {
  const [registry, setRegistry] = useState<{ lineage: string; current: string }[]>();
  const [message, setMessage] = useState<string>();
  useEffect(() => void api.registry().then(setRegistry, (e: Error) => setMessage(e.message)), []);
  const set = (iris: string[]) =>
    void api.setDependencies(summary.id, iris).then(
      (s) => {
        setMessage(undefined);
        onChange(s);
      },
      (e: Error) => setMessage(e.message),
    );
  const held = new Set(summary.dependsOn.map(lineageOf));
  return (
    <>
      <h3 style={{ marginTop: 24 }}>Depends on</h3>
      <p className="muted">
        A workspace reads what it depends on without copying it. Following a lineage reads its current version, and publishing pins it. Pinning a version
        keeps it whatever is published later.
      </p>
      {message && <div className="error small">{message}</div>}
      {summary.dependsOn.length === 0 && <div className="empty small">Nothing yet.</div>}
      <ul className="list">
        {summary.dependsOn.map((d) => (
          <li key={d} title={d}>
            {d.includes("/rev/1-") ? <Pin size={14} /> : <Link2 size={14} />} {lineageOf(d)}
            {d.includes("/rev/1-") ? `, pinned to ${shortVersion(d)}` : ", following"}
            <button className="btn ghost icon" aria-label={`Stop depending on ${d}`} onClick={() => set(summary.dependsOn.filter((x) => x !== d))}>
              <X size={14} />
            </button>
          </li>
        ))}
      </ul>
      <h4>Published</h4>
      {!registry ? (
        <Spinner size={14} />
      ) : (
        <ul className="list">
          {registry
            .filter((r) => !held.has(r.lineage))
            .map((r) => (
              <li key={r.lineage} title={r.lineage}>
                {r.lineage} <span className="muted small">{shortVersion(r.current)}</span>
                <button className="btn sm" onClick={() => set([...summary.dependsOn, r.lineage])}>
                  <Link2 size={14} /> Follow
                </button>
                <button className="btn sm" onClick={() => set([...summary.dependsOn, r.current])}>
                  <Pin size={14} /> Pin {shortVersion(r.current)}
                </button>
              </li>
            ))}
        </ul>
      )}
    </>
  );
}
