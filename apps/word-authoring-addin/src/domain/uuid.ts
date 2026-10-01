/** A dependency-free UUID v4 generator (plan WA8/WA9), not cryptographically strong, which is
 * fine for a proof of concept: avoids relying on a global `crypto.randomUUID` whose availability
 * varies across the Node/jsdom/Office.js runtimes this code runs under. */
export function newUuid(): string {
  const hex = (): string => Math.floor(Math.random() * 16).toString(16);
  const digits = Array.from({ length: 32 }, hex);
  digits[12] = "4";
  digits[16] = ["8", "9", "a", "b"][Math.floor(Math.random() * 4)];
  const s = digits.join("");
  return `${s.slice(0, 8)}-${s.slice(8, 12)}-${s.slice(12, 16)}-${s.slice(16, 20)}-${s.slice(20, 32)}`;
}
