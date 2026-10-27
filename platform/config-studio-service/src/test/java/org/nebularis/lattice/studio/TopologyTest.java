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
    }
}
