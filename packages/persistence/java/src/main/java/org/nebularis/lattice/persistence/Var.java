// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.regex.Pattern;

/** A validated SPARQL variable reference, for example {@code ?entity} (ADR-A132 decision 2). */
public record Var(String name) {
    private static final Pattern NAME = Pattern.compile("[A-Za-z_][A-Za-z0-9_]*");

    public Var {
        if (name == null || !NAME.matcher(name).matches()) throw new SparqlTermException("invalid SPARQL variable name " + Text.repr(name));
    }

    @Override public String toString() { return "?" + name; }
}
