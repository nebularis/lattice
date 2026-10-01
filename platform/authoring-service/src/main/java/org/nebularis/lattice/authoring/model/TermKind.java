// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.model;

/** The relation classes a clause may be read as. Not produced by WA2, used from WA3 onward. */
public enum TermKind {
    OBLIGATION("Obligation"),
    PROHIBITION("Prohibition"),
    PERMISSION("Permission"),
    EXCLUSION("Exclusion"),
    POWER("Power"),
    DEFINITION("Definition"),
    DEEMING("Deeming");

    private final String jsonValue;

    TermKind(String jsonValue) {
        this.jsonValue = jsonValue;
    }

    public String jsonValue() {
        return jsonValue;
    }

    public static TermKind fromJson(String value) {
        for (TermKind kind : values()) {
            if (kind.jsonValue.equals(value)) {
                return kind;
            }
        }
        throw new IllegalArgumentException("unknown TermKind: " + value);
    }
}
