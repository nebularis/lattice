// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

/**
 * A validated IRI reference (ADR-A132 decision 2, ADR-A79 point 4). An IRI holding a delimiter, a space, a control, a zero-width or a
 * bidirectional-override character is refused rather than escaped. {@link #toString()} is the angle-bracketed form.
 */
public record Iri(String value) implements Term, Comparable<Iri> {
    private static final String FORBIDDEN = "<>\"{}|\\^`";

    public Iri {
        if (value == null || value.isEmpty()) throw new SparqlTermException("IRI must be a non-empty string, got " + Text.repr(value));
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (c <= 0x20 || FORBIDDEN.indexOf(c) >= 0) {
                throw new SparqlTermException("IRI '" + value + "' contains the disallowed character U+" + String.format("%04X", (int) c) + ", refused rather than percent-escaped");
            }
            if (c == 0x200B || c == 0x200C || c == 0x200D || c == 0x2060 || c == 0xFEFF
                || (c >= 0x202A && c <= 0x202E) || (c >= 0x2066 && c <= 0x2069)) {
                throw new SparqlTermException("IRI '" + value + "' contains a zero-width or bidirectional-override character (U+" + String.format("%04X", (int) c) + "), refused");
            }
        }
    }

    /** The IRI for {@code value}, or {@link SparqlTermException}. */
    public static Iri of(String value) {
        return new Iri(value);
    }

    @Override public String nt() { return toString(); }

    @Override public String sparql() { return toString(); }

    @Override public String toString() { return "<" + value + ">"; }

    @Override public int compareTo(Iri other) { return Text.compare(value, other.value); }
}
