// SPDX-License-Identifier: MPL-2.0
// Small shared pieces: routing, modals, code views, status marks.

import { Children, createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type CSSProperties, type KeyboardEvent as ReactKeyboardEvent, type ReactNode } from "react";
import { AlertCircle, AlertTriangle, CheckCircle2, Info, Loader2, PanelLeftClose, PanelLeftOpen, PanelRightClose, PanelRightOpen } from "lucide-react";
import { DOCK, LIST, NAV_WIDTH, RAIL, clampWidth, columnKey, keyedWidth, maxWidth, readColumn, resolveWidth, writeColumn, type ColumnState, type Limits } from "./columns";
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

// --- the page's columns (SVA-U1) ------------------------------------------------------------------------------------------

/** The window's width, followed as it changes. */
export function useWindowWidth(): number {
  const [width, setWidth] = useState(() => window.innerWidth);
  useEffect(() => {
    const on = () => setWidth(window.innerWidth);
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, []);
  return width;
}

/** A column's kept state and a way to change it, written to the browser at once. The key may change, as a view's list does. */
export function useStoredColumn(key: string): [ColumnState, (patch: ColumnState) => void] {
  const [held, setHeld] = useState(() => ({ key, state: readColumn(key) }));
  const state = held.key === key ? held.state : readColumn(key);
  const update = useCallback(
    (patch: ColumnState) =>
      setHeld((prev) => {
        const next = { ...(prev.key === key ? prev.state : readColumn(key)), ...patch };
        writeColumn(key, next);
        return { key, state: next };
      }),
    [key],
  );
  return [state, update];
}

/** What a view's list column needs to know about the page: which view it is in, what the other columns hold, and where to say how wide it is. */
export interface ColumnsContextValue {
  view: string;
  navWidth: number;
  dockWidth: number;
  reportList: (width: number) => void;
}

export const ColumnsContext = createContext<ColumnsContextValue>({ view: "", navWidth: NAV_WIDTH, dockWidth: DOCK.default, reportList: () => undefined });

const ICONS = {
  nav: { close: PanelLeftClose, open: PanelLeftOpen },
  list: { close: PanelLeftClose, open: PanelLeftOpen },
  dock: { close: PanelRightClose, open: PanelRightOpen },
} as const;

/** The button in a column's head that collapses it, and in its rail that brings it back. */
export function CollapseButton(props: { column: "nav" | "list" | "dock"; noun: string; collapsed: boolean; onToggle: () => void }) {
  const Icon = ICONS[props.column][props.collapsed ? "open" : "close"];
  const label = `${props.collapsed ? "Expand" : "Collapse"} the ${props.noun}`;
  return (
    <button type="button" className="btn ghost icon sm col-toggle" aria-label={label} title={label} aria-expanded={!props.collapsed} onClick={props.onToggle}>
      <Icon size={16} />
    </button>
  );
}

/**
 * The boundary between a column and the middle. It is dragged with the pointer and moved by the arrow keys, 16 pixels at a time,
 * with Home to the column's minimum and End to its maximum. `grows` is the arrow that widens the column, so the keys follow the
 * boundary on the screen. A double click returns the column to its default.
 */
export function ResizeHandle(props: { label: string; width: number; min: number; max: number; grows: "ArrowLeft" | "ArrowRight"; onResize: (width: number) => void; onReset: () => void }) {
  const start = useRef<{ x: number; width: number } | undefined>(undefined);
  const [dragging, setDragging] = useState(false);
  const sign = props.grows === "ArrowRight" ? 1 : -1;
  const max = Math.max(props.min, props.max);
  const end = () => {
    start.current = undefined;
    setDragging(false);
  };
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={props.label}
      aria-valuenow={props.width}
      aria-valuemin={props.min}
      aria-valuemax={max}
      tabIndex={0}
      title="Drag to resize, double-click to reset"
      className={`col-handle ${props.grows === "ArrowRight" ? "after" : "before"}${dragging ? " dragging" : ""}`}
      onPointerDown={(e) => {
        if (e.button !== 0) return;
        e.currentTarget.setPointerCapture(e.pointerId);
        start.current = { x: e.clientX, width: props.width };
        setDragging(true);
      }}
      onPointerMove={(e) => {
        if (start.current) props.onResize(clampWidth(start.current.width + sign * (e.clientX - start.current.x), props.min, max));
      }}
      onPointerUp={end}
      onPointerCancel={end}
      onKeyDown={(e: ReactKeyboardEvent) => {
        const next = keyedWidth(e.key, props.width, props.min, max, props.grows);
        if (next === undefined) return;
        e.preventDefault();
        props.onResize(next);
      }}
      onDoubleClick={props.onReset}
    />
  );
}

/**
 * A view's list beside its middle. Its first child is the list and the rest are the middle, so a view gives the same two parts it
 * always did. The list collapses to a rail and is resized by the author, and its state is kept per view in this browser. A collapsed
 * list stays mounted and hidden, so what it holds, such as a filter, is there when it returns, and nothing in it takes focus.
 */
export function Split({ children, defaultWidth = LIST.default, minWidth = LIST.min }: { children: ReactNode; defaultWidth?: number; minWidth?: number }) {
  const { view, navWidth, dockWidth, reportList } = useContext(ColumnsContext);
  const windowWidth = useWindowWidth();
  const [state, update] = useStoredColumn(columnKey("list", view));
  const [list, ...middle] = Children.toArray(children);
  const collapsed = state.collapsed ?? false;
  const limits: Limits = { min: minWidth, default: defaultWidth };
  const others = navWidth + dockWidth;
  const width = resolveWidth(state.width, limits, windowWidth, others);
  const shown = collapsed ? RAIL : width;
  useEffect(() => {
    reportList(shown);
    return () => reportList(0);
  }, [shown, reportList]);
  const toggle = () => update({ collapsed: !collapsed });
  return (
    <div className="split" style={{ gridTemplateColumns: `${shown}px minmax(0, 1fr)` } as CSSProperties}>
      <div className={`col-list${collapsed ? " collapsed" : ""}`}>
        <div className={collapsed ? "rail" : "col-head"}>
          <CollapseButton column="list" noun="list" collapsed={collapsed} onToggle={toggle} />
        </div>
        <div className="col-body" hidden={collapsed}>
          {list}
        </div>
        {!collapsed && (
          <ResizeHandle label="Resize the list" width={width} min={minWidth} max={maxWidth(windowWidth, others)} grows="ArrowRight" onResize={(w) => update({ width: w })} onReset={() => update({ width: undefined })} />
        )}
      </div>
      {middle}
    </div>
  );
}
