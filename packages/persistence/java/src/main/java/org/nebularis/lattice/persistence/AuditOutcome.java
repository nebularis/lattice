// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

/** What an audit reports (ADR-A132 decision 2). The values are the individuals of {@code dal:AuditOutcome}. */
public enum AuditOutcome {
    CLEAN("Clean"), FAILED("Failed"), NOTHING_EXAMINED("NothingExamined");

    private final String value;

    AuditOutcome(String value) { this.value = value; }

    /** The individual's name, such as {@code NothingExamined}. */
    public String value() { return value; }
}
