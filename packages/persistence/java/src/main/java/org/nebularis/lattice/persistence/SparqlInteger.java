// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

/** A bare integer literal, for example a shard count (ADR-A132 decision 2). */
public record SparqlInteger(long value) {
    @Override public String toString() { return Long.toString(value); }
}
