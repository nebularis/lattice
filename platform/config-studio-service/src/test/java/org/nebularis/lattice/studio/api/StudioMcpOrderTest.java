// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.api;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/** The MCP server lists clauses in reading order, numbers compared as numbers. */
class StudioMcpOrderTest {
    @Test
    void objectIdsSortInReadingOrder() {
        List<String> ids = new ArrayList<>(List.of("12.1", "5.3", "5.2B", "9.1", "5.2A", "5.10"));
        ids.sort(StudioMcp::byNumber);
        assertEquals(List.of("5.2A", "5.2B", "5.3", "5.10", "9.1", "12.1"), ids);
    }
}
