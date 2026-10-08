import { useEffect, useState } from "react";
import type { DocumentElement, ValueType } from "../domain/types";
import type { ReferenceDraft, VariableDraft } from "./uiBridge";

const VALUE_TYPES: ValueType[] = ["money", "percentage", "date", "duration", "number", "text", "party"];

export interface MarkupPanelProps {
  markMessage: string | null;
  definitions: DocumentElement[];
  existingVariableKeys: string[];
  variableDraft: VariableDraft | null;
  referenceDraft: ReferenceDraft | null;
  onMarkClause: () => void;
  onMarkDefinition: () => void;
  onMarkTerm: () => void;
  onMarkVariable: (variableKey: string, label: string, valueType: ValueType) => void;
  onMarkDefinedTerm: (targetElementId: string, term: string) => void;
  onUnmark: () => void;
}

/** The Markup tab (plan WA9 "Panels"), with the ribbon commands' drafts (plan WA9a) filling its
 * forms. */
export function MarkupPanel({
  markMessage,
  definitions,
  existingVariableKeys,
  variableDraft,
  referenceDraft,
  onMarkClause,
  onMarkDefinition,
  onMarkTerm,
  onMarkVariable,
  onMarkDefinedTerm,
  onUnmark,
}: MarkupPanelProps): JSX.Element {
  const [variableKey, setVariableKey] = useState("");
  const [variableLabel, setVariableLabel] = useState("");
  const [valueType, setValueType] = useState<ValueType>("text");

  useEffect(() => {
    if (variableDraft) {
      setVariableKey(variableDraft.key);
      setVariableLabel(variableDraft.label);
      setValueType(variableDraft.valueType);
    }
  }, [variableDraft]);

  return (
    <section aria-label="Markup">
      <div className="button-row">
        <button type="button" onClick={onMarkClause}>
          Clause
        </button>
        <button type="button" onClick={onMarkDefinition}>
          Definition
        </button>
        <button type="button" onClick={onMarkTerm}>
          Term
        </button>
        <button type="button" onClick={onUnmark}>
          Unmark
        </button>
      </div>

      <h2>Mark variable</h2>
      <label>
        Key
        <input
          value={variableKey}
          list="existing-variable-keys"
          onChange={(event) => setVariableKey(event.target.value)}
        />
      </label>
      <datalist id="existing-variable-keys">
        {existingVariableKeys.map((key) => (
          <option key={key} value={key} />
        ))}
      </datalist>
      <label>
        Label
        <input value={variableLabel} onChange={(event) => setVariableLabel(event.target.value)} />
      </label>
      <label>
        Value type
        <select value={valueType} onChange={(event) => setValueType(event.target.value as ValueType)}>
          {VALUE_TYPES.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
      </label>
      <button type="button" onClick={() => onMarkVariable(variableKey, variableLabel, valueType)}>
        Mark variable
      </button>

      <h2>Mark defined term</h2>
      <ul>
        {definitions.map((definition) => (
          <li key={definition.elementId}>
            {definition.definedTerm ?? definition.elementId}
            <button
              type="button"
              onClick={() => onMarkDefinedTerm(definition.elementId, definition.definedTerm ?? "")}
            >
              Mark defined term
            </button>
          </li>
        ))}
      </ul>

      {referenceDraft && (
        <p>
          No single definition matched &quot;{referenceDraft.text}&quot;. Pick one above, or mark the selection as a
          variable instead.
        </p>
      )}

      {markMessage && <p role="status">{markMessage}</p>}
    </section>
  );
}
