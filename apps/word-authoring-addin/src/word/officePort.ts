/**
 * A `DocumentPort` over Office.js's real Word API (plan WA9 section "Office port rules"). Never
 * exercised under test (no real Word host is available here); only `tsc --noEmit` checks it,
 * against the real `Word`/`OfficeExtension` ambient types `@types/office-js` declares.
 */
import { decode, encode, title, TAG_APPEARANCE, TAG_COLOUR } from "../domain/tags";
import { fromXml, METADATA_NAMESPACE, toXml } from "../domain/metadata";
import type { AuthoringMetadata, DocumentPort, InlineMark, MarkResult } from "./port";

function parentKind(tag: string | null): "clause" | "definition" | "section" | "variable" | "reference" | "term" | null {
  if (!tag) return null;
  const decoded = decode(tag);
  return decoded ? decoded.kind : null;
}

export class OfficeWordPort implements DocumentPort {
  async readBodyOoxml(): Promise<string> {
    return Word.run(async (context) => {
      const result = context.document.body.getOoxml();
      await context.sync();
      return result.value;
    });
  }

  async readMetadata(): Promise<AuthoringMetadata | null> {
    return Word.run(async (context) => {
      const parts = context.document.customXmlParts.getByNamespace(METADATA_NAMESPACE);
      parts.load("items");
      await context.sync();
      if (parts.items.length === 0) {
        return null;
      }
      const xml = parts.items[0].getXml();
      await context.sync();
      return fromXml(xml.value);
    });
  }

  async writeMetadata(metadata: AuthoringMetadata): Promise<void> {
    await Word.run(async (context) => {
      const parts = context.document.customXmlParts.getByNamespace(METADATA_NAMESPACE);
      parts.load("items");
      await context.sync();
      for (const part of parts.items) {
        part.delete();
      }
      context.document.customXmlParts.add(toXml(metadata));
      await context.sync();
    });
  }

  async insertOoxml(packageXml: string): Promise<void> {
    await Word.run(async (context) => {
      context.document.body.insertOoxml(packageXml, Word.InsertLocation.end);
      await context.sync();
    });
  }

  async readSelection(): Promise<{ text: string; elementId: string | null }> {
    return Word.run(async (context) => {
      const range = context.document.getSelection();
      range.load("text");
      const parent = range.parentContentControlOrNullObject;
      parent.load(["isNullObject", "tag"]);
      await context.sync();
      const elementId = this.elementIdOf(parent);
      return { text: range.text, elementId };
    });
  }

  private elementIdOf(control: Word.ContentControl): string | null {
    if (control.isNullObject) return null;
    const kind = parentKind(control.tag);
    if (kind !== "clause" && kind !== "definition") return null;
    const decoded = decode(control.tag);
    return decoded?.value ?? null;
  }

  async wrapSelectionAsElement(kind: "clause" | "definition", elementId: string): Promise<MarkResult> {
    return Word.run(async (context) => {
      const selection = context.document.getSelection();
      selection.load("text");
      await context.sync();
      if (selection.text.length === 0) {
        return { ok: false, reason: "no-selection" };
      }

      const first = selection.paragraphs.getFirst().getRange();
      const last = selection.paragraphs.getLast().getRange();
      const range = first.expandTo(last);
      const parent = range.parentContentControlOrNullObject;
      parent.load(["isNullObject", "tag"]);
      await context.sync();
      if (parent.isNullObject || parentKind(parent.tag) !== "section") {
        return { ok: false, reason: "outside-section" };
      }

      const control = range.insertContentControl();
      control.tag = encode(kind, elementId);
      control.title = title(kind);
      control.appearance =
        TAG_APPEARANCE[kind] === "BoundingBox" ? Word.ContentControlAppearance.boundingBox : Word.ContentControlAppearance.tags;
      control.color = TAG_COLOUR[kind];
      await context.sync();
      return { ok: true };
    });
  }

  async markSelection(mark: InlineMark): Promise<MarkResult> {
    return Word.run(async (context) => {
      const range = context.document.getSelection();
      range.load("text");
      const parent = range.parentContentControlOrNullObject;
      parent.load(["isNullObject", "tag"]);
      await context.sync();
      return this.applyMark(context, range, mark);
    });
  }

  async markOccurrence(elementId: string, text: string, occurrence: number, mark: InlineMark): Promise<boolean> {
    return Word.run(async (context) => {
      let controls: Word.ContentControlCollection | null = null;
      for (const kind of ["clause", "definition"] as const) {
        const candidate = context.document.contentControls.getByTag(encode(kind, elementId));
        candidate.load("items");
        await context.sync();
        if (candidate.items.length > 0) {
          controls = candidate;
          break;
        }
      }
      if (!controls) return false;

      const elementRange = controls.items[0].getRange();
      const found = elementRange.search(text, { matchCase: true });
      found.load("items");
      await context.sync();
      if (occurrence >= found.items.length) return false;

      const target = found.items[occurrence];
      target.load("text");
      const parent = target.parentContentControlOrNullObject;
      parent.load(["isNullObject", "tag"]);
      await context.sync();
      const result = await this.applyMark(context, target, mark);
      return result.ok;
    });
  }

  private async applyMark(context: Word.RequestContext, range: Word.Range, mark: InlineMark): Promise<MarkResult> {
    if (range.text.length === 0) {
      return { ok: false, reason: "no-selection" };
    }
    const parent = range.parentContentControlOrNullObject;
    if (parent.isNullObject) {
      return { ok: false, reason: "outside-element" };
    }
    const kind = parentKind(parent.tag);
    if (kind !== "clause" && kind !== "definition") {
      return kind === null ? { ok: false, reason: "outside-element" } : { ok: false, reason: "already-marked" };
    }

    const control = range.insertContentControl();
    const value = mark.kind === "variable" ? mark.variableKey : mark.kind === "reference" ? mark.targetElementId : undefined;
    const text = mark.kind === "variable" ? mark.label : mark.kind === "reference" ? mark.term : undefined;
    control.tag = encode(mark.kind, value);
    control.title = title(mark.kind, text);
    control.appearance =
      TAG_APPEARANCE[mark.kind] === "BoundingBox" ? Word.ContentControlAppearance.boundingBox : Word.ContentControlAppearance.tags;
    control.color = TAG_COLOUR[mark.kind];
    await context.sync();
    return { ok: true };
  }

  async unmarkSelection(): Promise<MarkResult> {
    return Word.run(async (context) => {
      const range = context.document.getSelection();
      const parent = range.parentContentControlOrNullObject;
      parent.load(["isNullObject", "tag"]);
      await context.sync();

      if (parent.isNullObject) {
        return { ok: false, reason: "outside-element" };
      }
      const kind = parentKind(parent.tag);
      if (kind !== "variable" && kind !== "reference" && kind !== "term") {
        return { ok: false, reason: "outside-element" };
      }
      parent.delete(true);
      await context.sync();
      return { ok: true };
    });
  }
}
