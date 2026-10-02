import type { MarkResultReason } from "../word/port";

/** Plain-words rendering of a `MarkResult`'s reason, for the Markup panel (plan WA9). */
export function markResultMessage(reason: MarkResultReason): string {
  switch (reason) {
    case "no-selection":
      return "Select some text first.";
    case "outside-element":
      return "Select text inside a clause or definition.";
    case "outside-section":
      return "Select text inside a section.";
    case "already-marked":
      return "That text is already marked.";
    case "spans-parts":
      return "The selection crosses an existing mark. Select within one part.";
  }
}
