// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

/** What a confirmation says of a write (ADR-A132, STD-312). The values are the names the studio's run contract uses. */
public enum Outcome {
    APPLIED("applied"), REFUSED("refused"), LOST_RACE("lostRace");

    private final String value;

    Outcome(String value) { this.value = value; }

    /** The outcome's name, such as {@code lostRace}. */
    public String value() { return value; }
}
