// SPDX-License-Identifier: MPL-2.0
import { describe, expect, it } from "vitest";
import { droppedFiles, type DirectoryEntryLike, type EntryLike, type FileEntryLike } from "./dropEntries";

const file = (name: string, content = name): FileEntryLike<string> => ({ isFile: true, isDirectory: false, name, file: (ok) => ok(content) });

/** A directory whose reader returns `batches` in order, then an empty batch, as the browser's does. */
function directory(name: string, batches: EntryLike<string>[][]): DirectoryEntryLike<string> & { reads: () => number } {
  let reads = 0;
  return {
    isFile: false,
    isDirectory: true,
    name,
    createReader: () => {
      let next = 0;
      return {
        readEntries: (ok) => {
          reads++;
          ok(batches[next++] ?? []);
        },
      };
    },
    reads: () => reads,
  };
}

describe("droppedFiles", () => {
  it("gives a file dropped on its own its name", async () => {
    expect(await droppedFiles([file("a.ttl")])).toEqual([{ path: "a.ttl", file: "a.ttl" }]);
  });

  it("gives each file of a nested folder its path from the dropped root, the root first", async () => {
    const root = directory("onts", [[file("catalog-v001.xml"), directory("core", [[file("base.ttl"), directory("deep", [[file("x.owl")]])]])]]);
    const paths = (await droppedFiles([root])).map((f) => f.path).sort();
    expect(paths).toEqual(["onts/catalog-v001.xml", "onts/core/base.ttl", "onts/core/deep/x.owl"]);
  });

  it("reads a directory until a read returns nothing, so entries past the first batch are kept", async () => {
    const root = directory("big", [[file("a.ttl"), file("b.ttl")], [file("c.ttl")], [file("d.ttl")]]);
    const found = await droppedFiles([root]);
    expect(found.map((f) => f.path)).toEqual(["big/a.ttl", "big/b.ttl", "big/c.ttl", "big/d.ttl"]);
    expect(root.reads()).toBe(4);
  });

  it("gives nothing for an empty folder", async () => {
    expect(await droppedFiles([directory("empty", [])])).toEqual([]);
  });

  it("keeps files dropped beside a folder, each under its own name", async () => {
    const found = await droppedFiles([file("loose.ttl"), directory("folder", [[file("in.ttl")]]), file("other.rdf")]);
    expect(found.map((f) => f.path)).toEqual(["loose.ttl", "folder/in.ttl", "other.rdf"]);
  });

  it("hands over the file the entry gave", async () => {
    expect(await droppedFiles([directory("d", [[file("a.ttl", "content of a")]])])).toEqual([{ path: "d/a.ttl", file: "content of a" }]);
  });

  it("rejects when a read fails", async () => {
    const broken: DirectoryEntryLike<string> = { isFile: false, isDirectory: true, name: "bad", createReader: () => ({ readEntries: (_ok, fail) => fail?.(new Error("denied")) }) };
    await expect(droppedFiles([broken])).rejects.toThrow("denied");
  });
});
