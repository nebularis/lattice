// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.List;
import java.util.Map;

/** The adopter's SPARQL client, behind the one method the library asks of it (ADR-A132 decision 3). The library defines it and does not implement it. */
public interface SelectClient {
    /** Run a SELECT. Each row maps a variable name to its value, as text or a number. */
    List<Map<String, Object>> select(String query);
}
