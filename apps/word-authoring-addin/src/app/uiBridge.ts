/**
 * A small observable store bridging the ribbon/right-click commands (WA9a) and the task pane:
 * `App` subscribes, the Markup panel fills its forms from the drafts and shows the message, and
 * the Analyse panel runs once when `runAnalyse` is set, then it is cleared.
 */
import type { ValueType } from "../domain/types";
import type { Tab } from "./tabs";

export interface VariableDraft {
  key: string;
  label: string;
  valueType: ValueType;
}

export interface ReferenceDraft {
  text: string;
}

export interface BridgeState {
  tab: Tab | null;
  variableDraft: VariableDraft | null;
  referenceDraft: ReferenceDraft | null;
  message: string | null;
  runAnalyse: boolean;
}

export type BridgeListener = (state: BridgeState) => void;

const INITIAL_STATE: BridgeState = {
  tab: null,
  variableDraft: null,
  referenceDraft: null,
  message: null,
  runAnalyse: false,
};

export class UiBridge {
  private state: BridgeState = { ...INITIAL_STATE };
  private readonly listeners = new Set<BridgeListener>();

  getState(): BridgeState {
    return this.state;
  }

  post(partial: Partial<BridgeState>): void {
    this.state = { ...this.state, ...partial };
    for (const listener of this.listeners) {
      listener(this.state);
    }
  }

  subscribe(listener: BridgeListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }
}
