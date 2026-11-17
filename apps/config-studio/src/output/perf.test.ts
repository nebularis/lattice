// SPDX-License-Identifier: MPL-2.0
// How long a large N-Triples part takes to parse and to prepare each rendering (SVA-M4). It prints the milliseconds and asserts only that
// each step finishes with the rows it should, never on time, since time depends on the machine.

import { describe, expect, it } from "vitest";
import { graphModel, parseRdf, prefixesOf, tableRows, toNTriplesText, toTurtleText } from "./rdf";

function ntriples(bytes: number): string {
  const lines: string[] = [];
  let size = 0;
  for (let i = 0; size < bytes; i++) {
    const line = `<https://example.org/data/s${Math.floor(i / 4)}> <https://example.org/lending#p${i % 4}> ${i % 2 ? `"value ${i}"` : `<https://example.org/data/s${(i * 7) % 5000}>`} .`;
    lines.push(line);
    size += line.length + 1;
  }
  return lines.join("\n") + "\n";
}

const ms = (since: number) => `${Math.round(performance.now() - since)} ms`;

describe.each([[1], [5]])("a %i MiB N-Triples part", (mebibytes) => {
  it("parses and prepares each rendering", () => {
    const text = ntriples(mebibytes * 1024 * 1024);
    const report: string[] = [];
    let t = performance.now();
    const parsed = parseRdf(text, "application/n-triples");
    report.push(`parse ${ms(t)}`);
    expect(parsed.ok).toBe(true);
    if (!parsed.ok) return;
    const prefixes = prefixesOf(parsed.prefixes);
    t = performance.now();
    const rows = tableRows(parsed.quads, prefixes);
    report.push(`table rows ${ms(t)}`);
    expect(rows.length).toBeGreaterThan(0);
    t = performance.now();
    const turtle = toTurtleText(parsed.quads, prefixes);
    report.push(`Turtle ${ms(t)}`);
    expect(turtle.length).toBeGreaterThan(0);
    t = performance.now();
    const nt = toNTriplesText(parsed.quads);
    report.push(`N-Triples ${ms(t)}`);
    expect(nt.length).toBeGreaterThan(0);
    t = performance.now();
    const model = graphModel(parsed.quads, prefixes);
    report.push(`graph model ${ms(t)}`);
    expect(model.nodes.length).toBeGreaterThan(0);
    console.log(`${mebibytes} MiB, ${parsed.quads.length} triples, ${model.nodes.length} nodes: ${report.join(", ")}`);
  }, 120_000);
});
