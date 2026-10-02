/**
 * Associates every command id with its handler (plan WA9a "Files"). The only module in
 * `src/commands/` that touches the real `Office` global.
 */
import { COMMAND_IDS } from "./ids";
import type { Handlers } from "./handlers";

export function registerCommands(handlers: Handlers): void {
  Office.actions.associate("showPane", (event: Office.AddinCommands.Event) => {
    Office.addin.showAsTaskpane().finally(() => event.completed());
  });

  for (const id of COMMAND_IDS) {
    if (id === "showPane") continue;
    Office.actions.associate(id, handlers[id]);
  }
}
