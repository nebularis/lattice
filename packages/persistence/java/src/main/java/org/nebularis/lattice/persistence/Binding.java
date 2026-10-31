// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

/** A compile-time binding of an operation, such as {@code graphPrefix}, with its text as the compile encoded it. */
public record Binding(String name, String text) implements Comparable<Binding> {
    @Override public int compareTo(Binding o) {
        int c = Text.compare(name, o.name);
        return c != 0 ? c : Text.compare(text, o.text);
    }
}
