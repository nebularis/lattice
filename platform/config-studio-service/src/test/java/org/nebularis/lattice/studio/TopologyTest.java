// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.jobs.Topology;

class TopologyTest {
    @Test
    void theConstantsEqualTheContractFile() throws IOException {
        Path file = Path.of("..", "..", "contracts", "config-studio", "amqp-topology.json");
        String json = Files.readString(file);
        for (String[] pair : new String[][] {
            {"exchange", Topology.EXCHANGE}, {"deadLetterExchange", Topology.DEAD_LETTER_EXCHANGE},
            {"name", Topology.JOBS_QUEUE}, {"routingKey", Topology.JOBS_ROUTING_KEY},
            {"name", Topology.DEAD_QUEUE}, {"routingKey", Topology.DEAD_ROUTING_KEY}}) {
            assertTrue(json.contains("\"" + pair[0] + "\": \"" + pair[1] + "\""), pair[0] + " " + pair[1]);
        }
        String jobs = json.substring(json.indexOf("\"lattice.studio.jobs\""), json.indexOf("\"lattice.studio.dead\""));
        assertTrue(jobs.contains("\"deadLetter\": true"));
        assertTrue(json.substring(json.indexOf("\"lattice.studio.dead\"")).contains("\"deadLetter\": false"));
        assertTrue(json.contains("\"superStream\": \"" + Topology.WRITES + "\""));
        assertTrue(json.contains("\"partitions\": " + Topology.PARTITIONS));
        assertTrue(json.contains("\"x-max-age\": \"" + Topology.PARTITION_ARGUMENTS.get("x-max-age") + "\""));
        assertTrue(json.contains("\"x-max-length-bytes\": " + Topology.PARTITION_ARGUMENTS.get("x-max-length-bytes")));
        assertTrue(json.contains("\"consumerGroup\": \"lattice.studio.writers\""));
    }

    @Test
    void aWorkspaceRoutesByItsIdsFirst32Bits() {
        org.junit.jupiter.api.Assertions.assertEquals("7", Topology.routingKey("ffffffff-0000-4000-8000-000000000000"));
        org.junit.jupiter.api.Assertions.assertEquals("0", Topology.routingKey("00000000-ffff-4000-8000-000000000000"));
        org.junit.jupiter.api.Assertions.assertEquals("5", Topology.routingKey("0000000d-0000-4000-8000-000000000000"));
    }
}
