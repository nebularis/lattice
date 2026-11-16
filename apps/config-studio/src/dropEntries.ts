// SPDX-License-Identifier: MPL-2.0
// Walks what was dropped onto a drop area. The browser gives a drop as entries (`DataTransferItem.webkitGetAsEntry()`), each a file
// or a directory, and a directory is read in batches until a read returns nothing. Each file comes back with its path from the
// dropped root, in the form `webkitRelativePath` gives for a folder chosen through an input, so `catalog-v001.xml` entries resolve
// the same way whichever way the folder came in. The walk takes entry-like objects, so a test hands it fakes.

export interface FileEntryLike<F> {
  isFile: true;
  isDirectory: false;
  name: string;
  file(success: (file: F) => void, failure?: (error: unknown) => void): void;
}

export interface DirectoryEntryLike<F> {
  isFile: false;
  isDirectory: true;
  name: string;
  createReader(): { readEntries(success: (batch: EntryLike<F>[]) => void, failure?: (error: unknown) => void): void };
}

export type EntryLike<F> = FileEntryLike<F> | DirectoryEntryLike<F>;

export interface DroppedFile<F> {
  /** The path from the dropped root, root folder name first, with `/` between segments. A file dropped on its own is its name. */
  path: string;
  file: F;
}

/** The entries of a directory, every batch of its reader. A reader returns its entries in batches and an empty batch at the end. */
async function readAll<F>(directory: DirectoryEntryLike<F>): Promise<EntryLike<F>[]> {
  const reader = directory.createReader();
  const all: EntryLike<F>[] = [];
  for (;;) {
    const batch = await new Promise<EntryLike<F>[]>((resolve, reject) => reader.readEntries(resolve, reject));
    if (batch.length === 0) return all;
    all.push(...batch);
  }
}

async function walk<F>(entry: EntryLike<F>, prefix: string, out: DroppedFile<F>[]): Promise<void> {
  const path = prefix + entry.name;
  if (entry.isFile) {
    out.push({ path, file: await new Promise<F>((resolve, reject) => entry.file(resolve, reject)) });
    return;
  }
  for (const child of await readAll(entry)) await walk(child, `${path}/`, out);
}

/** Every file under the dropped entries, each with its path from the dropped root. An empty folder gives nothing. Rejects when a read fails. */
export async function droppedFiles<F>(entries: readonly EntryLike<F>[]): Promise<DroppedFile<F>[]> {
  const out: DroppedFile<F>[] = [];
  for (const entry of entries) await walk(entry, "", out);
  return out;
}
