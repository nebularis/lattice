// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.minting;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Typed access to parsed JSON, and trace entries. */
final class Values {
    private Values() {
    }

    @SuppressWarnings("unchecked")
    static Map<String, Object> map(Object o) {
        return (Map<String, Object>) o;
    }

    static List<?> list(Object o) {
        return (List<?>) o;
    }

    static int integer(Object o) {
        return ((Number) o).intValue();
    }

    /** An ordered map from alternating names and values. */
    static Map<String, Object> entry(Object... nameValue) {
        Map<String, Object> m = new LinkedHashMap<>();
        for (int i = 0; i < nameValue.length; i += 2) {
            m.put((String) nameValue[i], nameValue[i + 1]);
        }
        return m;
    }
}
