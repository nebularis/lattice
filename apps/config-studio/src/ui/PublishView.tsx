// SPDX-License-Identifier: MPL-2.0
// Publishing (ADR-A149): every unit of the workspace's saved parts, the version each was last published as, and a button
// that publishes it. Nothing is published until someone presses it.

import { useEffect, useMemo, useState } from "react";
import { Send } from "lucide-react";
import { CST, Graph, LABEL, SKOS, TYPE, localName } from "@lattice/authoring-domain";
import { api, awaitJob } from "../api";
import { CONFIG_PARTS, type ConfigPart } from "../rdf/split";
import { Spinner } from "./kit";
import { useStudio } from "./Workspace";

interface Unit {
  root: string;
  label: string;
  kind: string;
  part: ConfigPart;
}

/** The roots of the units table's classes in each part as saved. */
export function unitsIn(table: Graph, saved: Partial<Record<ConfigPart, Graph>>): Unit[] {
  const out: Unit[] = [];
  for (const unit of table.ofType(CST("PublicationUnit"))) {
    const part = table.value(unit.value, CST("authoredIn")) as ConfigPart | undefined;
    const graph = part && saved[part];
    if (!graph) continue;
    const roots = new Set(table.objects(unit.value, CST("rootClass")).flatMap((c) => graph.subjects(TYPE, c.value).map((r) => r.value)));
    for (const root of roots) {
      if (root.startsWith("_:")) continue;
      out.push({ root, part, kind: table.value(unit.value, LABEL) ?? localName(unit.value), label: graph.value(root, LABEL) ?? graph.value(root, SKOS("prefLabel")) ?? localName(root) });
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
  const units = useMemo(() => (table ? unitsIn(table, saved) : []), [table, saved]);
  useEffect(() => {
    for (const u of units) {
      void api.lineage(u.root).then((g) => setCurrent((c) => ({ ...c, [u.root]: g?.value(u.root, CST("current")) ?? null })), () => undefined);
    }
  }, [units]);

  const publish = async (u: Unit) => {
    setRows((r) => ({ ...r, [u.root]: { state: "publishing" } }));
    try {
      const id = await api.preparePublication(studio.id, u.part, u.root);
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
            const unsaved = configs[u.part] && configs[u.part]!.current !== configs[u.part]!.saved;
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
    </div>
  );
}
