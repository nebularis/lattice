/**
 * The ribbon/right-click command handlers (plan WA9a "Commands"). No Office global is touched
 * here, so these run under Vitest and in the harness; `register.ts` is the only module that talks
 * to `Office.actions` directly.
 */
import { guessValueType, suggestKey } from "../domain/keys";
import { parseBody } from "../domain/ooxml";
import type { DocumentPort, MarkResult } from "../word/port";
import type { CommandId } from "./ids";
import { markResultMessage } from "../app/markMessages";
import type { UiBridge } from "../app/uiBridge";

export interface CommandEvent {
  completed(): void;
}

export interface HandlerDeps {
  port: DocumentPort;
  bridge: UiBridge;
  showPane: () => void;
  newUuid: () => string;
}

export type CommandHandler = (event: CommandEvent) => Promise<void>;

/** `WITHOUT_SHOW_PANE`: `showPane` is registered separately, directly against
 * `Office.addin.showAsTaskpane` (`register.ts`), since it needs no handler logic at all. */
export type Handlers = Record<Exclude<CommandId, "showPane">, CommandHandler>;

const FINAL_SUFFIXES = ["'s", "\u2019s", "s"];

function withoutFinalSuffix(text: string): string {
  for (const suffix of FINAL_SUFFIXES) {
    if (text.endsWith(suffix)) {
      return text.slice(0, text.length - suffix.length);
    }
  }
  return text;
}

export function createHandlers(deps: HandlerDeps): Handlers {
  const { port, bridge, showPane, newUuid } = deps;

  function reportResult(result: MarkResult): void {
    if (!result.ok) {
      bridge.post({ tab: "markup", message: markResultMessage(result.reason) });
      showPane();
    }
  }

  function reportError(error: unknown): void {
    bridge.post({ tab: "markup", message: error instanceof Error ? error.message : String(error) });
    showPane();
  }

  async function run(action: () => Promise<void>, event: CommandEvent): Promise<void> {
    try {
      await action();
    } catch (error) {
      reportError(error);
    } finally {
      event.completed();
    }
  }

  const markClause: CommandHandler = (event) =>
    run(async () => reportResult(await port.wrapSelectionAsElement("clause", newUuid())), event);

  const markDefinition: CommandHandler = (event) =>
    run(async () => reportResult(await port.wrapSelectionAsElement("definition", newUuid())), event);

  const markTerm: CommandHandler = (event) => run(async () => reportResult(await port.markSelection({ kind: "term" })), event);

  const unmark: CommandHandler = (event) => run(async () => reportResult(await port.unmarkSelection()), event);

  const markVariable: CommandHandler = (event) =>
    run(async () => {
      const selection = await port.readSelection();
      if (selection.text.length === 0) {
        bridge.post({ tab: "markup", message: markResultMessage("no-selection") });
        showPane();
        return;
      }
      const valueType = guessValueType(selection.text);
      bridge.post({
        tab: "markup",
        message: null,
        variableDraft: {
          key: suggestKey(selection.text, valueType),
          label: selection.text.trim().slice(0, 100),
          valueType,
        },
      });
      showPane();
    }, event);

  const markDefinedTerm: CommandHandler = (event) =>
    run(async () => {
      const selection = await port.readSelection();
      if (selection.text.length === 0) {
        bridge.post({ tab: "markup", message: markResultMessage("no-selection") });
        showPane();
        return;
      }
      const text = selection.text.trim();
      const ooxml = await port.readBodyOoxml();
      const parsed = parseBody(ooxml);
      const definitions = parsed.sections.flatMap((section) => section.elements).filter((element) => element.kind === "definition");
      const stripped = withoutFinalSuffix(text);
      const matches = definitions.filter((definition) => definition.definedTerm === text || definition.definedTerm === stripped);

      if (matches.length === 1) {
        const target = matches[0];
        reportResult(await port.markSelection({ kind: "reference", targetElementId: target.elementId, term: target.definedTerm ?? text }));
        return;
      }

      bridge.post({ tab: "markup", message: null, referenceDraft: { text } });
      showPane();
    }, event);

  const analyse: CommandHandler = (event) =>
    run(async () => {
      bridge.post({ tab: "analyse", runAnalyse: true });
      showPane();
    }, event);

  return { markClause, markDefinition, markTerm, markVariable, markDefinedTerm, unmark, analyse };
}
