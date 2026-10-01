/**
 * The real Word task pane entry point (plan WA9 "Files"): checks the `WordApi 1.4` requirement
 * set before rendering, since the add-in's content control and custom XML part calls need it.
 * Registers the ribbon/right-click commands (plan WA9a) before rendering, sharing one bridge and
 * port with `App`.
 */
import { createRoot } from "react-dom/client";
import { HttpApiClient } from "./api/client";
import { App } from "./app/App";
import "./app/app.css";
import { UiBridge } from "./app/uiBridge";
import { createHandlers } from "./commands/handlers";
import { registerCommands } from "./commands/register";
import { newUuid } from "./domain/uuid";
import { OfficeWordPort } from "./word/officePort";

export function isWordApiSupported(): boolean {
  return Office.context.requirements.isSetSupported("WordApi", "1.4");
}

const port = new OfficeWordPort();
const bridge = new UiBridge();

export function render(container: HTMLElement): void {
  const root = createRoot(container);
  if (!isWordApiSupported()) {
    root.render(<p>This add-in requires a newer version of Word.</p>);
    return;
  }
  root.render(<App port={port} api={new HttpApiClient("/api")} bridge={bridge} />);
}

Office.onReady(() => {
  registerCommands(
    createHandlers({
      port,
      bridge,
      showPane: () => {
        Office.addin.showAsTaskpane();
      },
      newUuid,
    }),
  );

  const container = document.getElementById("root");
  if (container) {
    render(container);
  }
});

