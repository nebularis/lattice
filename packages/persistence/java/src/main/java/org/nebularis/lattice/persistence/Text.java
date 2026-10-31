// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Comparator;
import java.util.List;
import java.util.TreeSet;

/** String helpers shared by the library. Order is by code point, which is the order of the UTF-8 bytes. */
final class Text {
    private Text() {}

    static final Comparator<String> ORDER = Text::compare;

    static int compare(String a, String b) {
        int i = 0, j = 0;
        while (i < a.length() && j < b.length()) {
            int x = a.codePointAt(i), y = b.codePointAt(j);
            if (x != y) return Integer.compare(x, y);
            i += Character.charCount(x);
            j += Character.charCount(y);
        }
        return Integer.compare(a.length() - i, b.length() - j);
    }

    static List<String> sortedUnique(Collection<String> values) {
        TreeSet<String> set = new TreeSet<>(ORDER);
        set.addAll(values);
        return new ArrayList<>(set);
    }

    static byte[] utf8(String s) {
        return s.getBytes(StandardCharsets.UTF_8);
    }

    static String repr(Object o) {
        return o instanceof String s ? "'" + s + "'" : String.valueOf(o);
    }

    static String local(String iri) {
        return iri.substring(iri.lastIndexOf('#') + 1);
    }
}
