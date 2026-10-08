import { describe, expect, it, vi } from "vitest";
import { registerCommands } from "./register";
import { COMMAND_IDS } from "./ids";
import type { Handlers } from "./handlers";
import type { CommandEvent } from "./handlers";

describe("registerCommands (S9a-02)", () => {
  it("associates each command id exactly once", () => {
    const associateCalls: string[] = [];
    (globalThis as { Office?: unknown }).Office = {
      actions: {
        associate: (id: string) => {
          associateCalls.push(id);
        },
      },
      addin: {
        showAsTaskpane: () => Promise.resolve(),
      },
    };

    const noop = vi.fn(async (event: CommandEvent) => event.completed());
    const handlers: Handlers = {
      markClause: noop,
      markDefinition: noop,
      markTerm: noop,
      markVariable: noop,
      markDefinedTerm: noop,
      unmark: noop,
      analyse: noop,
    };

    registerCommands(handlers);

    expect([...associateCalls].sort()).toEqual([...COMMAND_IDS].sort());
    expect(new Set(associateCalls).size).toBe(associateCalls.length);

    delete (globalThis as { Office?: unknown }).Office;
  });
});
