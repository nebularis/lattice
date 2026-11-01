// SPDX-License-Identifier: MPL-2.0
// Line diff and syntax colouring for the read-only Turtle and SPARQL views.

export type DiffLine = { op: " " | "+" | "-"; text: string };

/** A line diff by longest common subsequence. Quadratic in lines, fine for a configuration. */
export function diffLines(before: string, after: string): DiffLine[] {
  const a = before.split("\n");
  const b = after.split("\n");
  const lcs: number[][] = Array.from({ length: a.length + 1 }, () => new Array<number>(b.length + 1).fill(0));
  for (let i = a.length - 1; i >= 0; i--) {
    for (let j = b.length - 1; j >= 0; j--) {
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }
  const out: DiffLine[] = [];
  let i = 0;
  let j = 0;
  while (i < a.length || j < b.length) {
    if (i < a.length && j < b.length && a[i] === b[j]) {
      out.push({ op: " ", text: a[i++] });
      j++;
    } else if (j < b.length && (i === a.length || lcs[i][j + 1] >= lcs[i + 1][j])) {
      out.push({ op: "+", text: b[j++] });
    } else {
      out.push({ op: "-", text: a[i++] });
    }
  }
  return out;
}

export type TokenKind = "comment" | "string" | "iri" | "keyword" | "prefixed" | "variable" | "number" | "punct" | "text";
export type Token = { kind: TokenKind; text: string };

const RULES: [TokenKind, RegExp][] = [
  ["comment", /#[^\n]*/y],
  ["string", /"""[\s\S]*?"""|"(?:[^"\\\n]|\\.)*"(?:@[a-zA-Z-]+|\^\^)?/y],
  ["iri", /<[^>\s]*>/y],
  ["variable", /[?$][A-Za-z_][\w]*/y],
  ["keyword", /@?\b(?:prefix|base|PREFIX|BASE|SELECT|CONSTRUCT|ASK|DESCRIBE|WHERE|INSERT|DELETE|DATA|GRAPH|FILTER|OPTIONAL|UNION|BIND|VALUES|NOT|EXISTS|MINUS|LIMIT|ORDER|BY|GROUP|HAVING|AS|DISTINCT|WITH|USING|a|true|false|IN|IF|COALESCE|STR|IRI|BOUND|CONCAT|ENCODE_FOR_URI|SHA256|COUNT|MAX|MIN|SUM)\b/y],
  ["prefixed", /[A-Za-z][\w-]*:[\w.-]*[\w-]|[A-Za-z][\w-]*:/y],
  ["number", /[+-]?\d+(?:\.\d+)?/y],
  ["punct", /[{}()[\];,.^]+/y],
];

/** Tokens for Turtle and SPARQL. A token never spans a newline except a long string. */
export function tokenise(source: string): Token[] {
  const out: Token[] = [];
  let pos = 0;
  let text = "";
  const flush = () => {
    if (text) out.push({ kind: "text", text });
    text = "";
  };
  outer: while (pos < source.length) {
    for (const [kind, rule] of RULES) {
      rule.lastIndex = pos;
      const m = rule.exec(source);
      if (m && m[0].length > 0) {
        flush();
        out.push({ kind, text: m[0] });
        pos += m[0].length;
        continue outer;
      }
    }
    text += source[pos++];
  }
  flush();
  return out;
}
