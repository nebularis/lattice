// SPDX-License-Identifier: MPL-2.0
// Small shared pieces: routing, modals, code views, status marks.

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { AlertCircle, AlertTriangle, CheckCircle2, Info, Loader2 } from "lucide-react";
import { diffLines, tokenise } from "../lib/text";
import type { Severity } from "../rdf/report";

/** The route is the location hash, "#/w/<id>/persistence/<node>", split on "/". */
export function useRoute(): string[] {
  const read = () =>
    window.location.hash
      .replace(/^#\/?/, "")
      .split("/")
      .filter(Boolean)
      .map(decodeURIComponent);
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const on = () => setRoute(read());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return route;
}

export function href(...parts: string[]): string {
  return "#/" + parts.map(encodeURIComponent).join("/");
}

export function go(...parts: string[]): void {
  window.location.hash = href(...parts);
}

export function Modal(props: { title: string; subtitle?: ReactNode; onClose: () => void; children: ReactNode; footer?: ReactNode; wide?: boolean }) {
  useEffect(() => {
    const key = (e: KeyboardEvent) => e.key === "Escape" && props.onClose();
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  }, [props]);
  return (
    <div className="backdrop" onMouseDown={(e) => e.target === e.currentTarget && props.onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={props.title} style={props.wide ? { width: "min(980px, calc(100vw - 32px))" } : undefined}>
        <header>
          <h3>{props.title}</h3>
          {props.subtitle && <p>{props.subtitle}</p>}
        </header>
        <div className="body">{props.children}</div>
        {props.footer && <footer>{props.footer}</footer>}
      </div>
    </div>
  );
}

export function Code({ text, maxHeight }: { text: string; maxHeight?: number }) {
  const tokens = useMemo(() => tokenise(text), [text]);
  return (
    <pre className="code" style={maxHeight ? { maxHeight } : undefined}>
      {tokens.map((t, i) => (t.kind === "text" ? t.text : <span key={i} className={t.kind}>{t.text}</span>))}
    </pre>
  );
}

export function Diff({ before, after }: { before: string; after: string }) {
  const lines = useMemo(() => diffLines(before, after), [before, after]);
  if (before === after) return <p className="muted">No differences.</p>;
  return (
    <pre className="diff" aria-label="Differences">
      {lines.map((l, i) => (
        <div key={i} className={l.op === "+" ? "add" : l.op === "-" ? "del" : undefined}>
          {l.op} {l.text}
        </div>
      ))}
    </pre>
  );
}

export function SeverityIcon({ severity, size = 15 }: { severity: Severity; size?: number }) {
  if (severity === "Violation") return <AlertCircle size={size} color="var(--bad)" aria-label="Violation" />;
  if (severity === "Warning") return <AlertTriangle size={size} color="var(--warn)" aria-label="Warning" />;
  return <Info size={size} color="var(--text-3)" aria-label="Information" />;
}

export function Spinner({ size = 14 }: { size?: number }) {
  return <Loader2 size={size} className="spin" aria-label="Working" />;
}

export function Conforms({ ok, size = 15 }: { ok: boolean; size?: number }) {
  return ok ? <CheckCircle2 size={size} color="var(--ok)" aria-label="Conforms" /> : <AlertCircle size={size} color="var(--bad)" aria-label="Does not conform" />;
}

/** Close a popover on an outside click or Escape. */
export function useDismiss(open: boolean, close: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const click = (e: MouseEvent) => ref.current && !ref.current.contains(e.target as Node) && close();
    const key = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("mousedown", click);
    window.addEventListener("keydown", key);
    return () => {
      window.removeEventListener("mousedown", click);
      window.removeEventListener("keydown", key);
    };
  }, [open, close]);
  return ref;
}

export function readFiles(files: FileList | File[]): Promise<{ name: string; text: string }[]> {
  return Promise.all([...files].map(async (f) => ({ name: f.name, text: await f.text() })));
}

export function download(name: string, text: string, type = "text/turtle"): void {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function ago(iso?: string): string {
  if (!iso) return "";
  const seconds = (Date.now() - Date.parse(iso)) / 1000;
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
  return new Date(iso).toLocaleDateString();
}
