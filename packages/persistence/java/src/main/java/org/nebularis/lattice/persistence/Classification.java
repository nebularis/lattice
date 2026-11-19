// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

/**
 * The classification of a write (ADR-A132, STD-312, the confirmation section of {@code contracts/persistence/README.md}). For a lost race it is the
 * cause, and each cause answers one guard of the generated operations.
 */
public enum Classification {
    APPLIED("Applied", Outcome.APPLIED), IDEMPOTENCY_KEY_REUSE("IdempotencyKeyReuse", Outcome.REFUSED),
    EPOCH_CHANGED("EpochChanged", Outcome.LOST_RACE), GONE("Gone", Outcome.LOST_RACE), PRECONDITION_FAILED("PreconditionFailed", Outcome.LOST_RACE),
    ALREADY_EXISTS("AlreadyExists", Outcome.LOST_RACE), KEY_CLAIM_HELD("KeyClaimHeld", Outcome.LOST_RACE), NOT_APPLIED("NotApplied", Outcome.LOST_RACE);

    private final String value;
    private final Outcome outcome;

    Classification(String value, Outcome outcome) {
        this.value = value;
        this.outcome = outcome;
    }

    /** The classification's name, such as {@code PreconditionFailed}. */
    public String value() { return value; }

    /** The outcome this classification gives. */
    public Outcome outcome() { return outcome; }
}
