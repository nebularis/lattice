// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

/** The logical kind of an operation (ADR-A123). A caller and a model compare operations by kind, not by the SPARQL a builder writes. */
public enum OperationKind {
    CREATE("Create"), BOOTSTRAP("Bootstrap"), REPLACE("Replace"), TOMBSTONE("Tombstone"), APPEND("Append"), APPEND_VERSION("AppendVersion"),
    UNCONDITIONAL_WRITE("UnconditionalWrite"), VALUE_GUARDED_REPLACE("ValueGuardedReplace"), KEY_CLAIM_WRITE("KeyClaimWrite"),
    KEY_CLAIM_WRITE_DUAL("KeyClaimWriteDual"), KEY_CLAIM_RETIRE("KeyClaimRetire"), QUARANTINE("Quarantine"), MERGE_REWRITE("MergeRewrite"),
    AUDIT("Audit"), MEMBERS_READ("MembersRead"), PAYLOAD_CHECK("PayloadCheck");

    private final String value;

    OperationKind(String value) { this.value = value; }

    /** The name the profile gives the kind, such as {@code Replace}. */
    public String value() { return value; }

    /** The kind with this profile name. */
    public static OperationKind of(String value) {
        for (OperationKind k : values()) if (k.value.equals(value)) return k;
        throw new ProfileException("'" + value + "' is not an operation kind");
    }
}
