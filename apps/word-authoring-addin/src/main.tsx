/**
 * The real Word task pane entry point (plan WA9 "Files"): checks the `WordApi 1.4` requirement
 * set before rendering, since the add-in's content control and custom XML part calls need it.
 */
import { createRoot } from "react-dom/client";
import { HttpApiClient } from "./api/client";
import { App } from "./app/App";
import "./app/app.css";
import { OfficeWordPort } from "./word/officePort";

export function isWordApiSupported(): boolean {
  return Office.context.requirements.isSetSupported("WordApi", "1.4");
}

export function render(container: HTMLElement): void {
  const root = createRoot(container);
  if (!isWordApiSupported()) {
    root.render(<p>This add-in requires a newer version of Word.</p>);
    return;
  }
  root.render(<App port={new OfficeWordPort()} api={new HttpApiClient("/api")} />);
}

Office.onReady(() => {
  const container = document.getElementById("root");
  if (container) {
    render(container);
  }
});
