/** The eight ribbon/right-click command ids (plan WA9a "Commands"). */
export const COMMAND_IDS = [
  "showPane",
  "markClause",
  "markDefinition",
  "markTerm",
  "markVariable",
  "markDefinedTerm",
  "unmark",
  "analyse",
] as const;

export type CommandId = (typeof COMMAND_IDS)[number];
