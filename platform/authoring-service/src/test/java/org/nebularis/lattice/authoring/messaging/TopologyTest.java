// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.messaging;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.fasterxml.jackson.databind.JsonNode;
import java.io.IOException;
import java.io.UncheckedIOException;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.authoring.RepoPaths;
import org.nebularis.lattice.authoring.json.Json;

class TopologyTest {

    /** S5-08: the Java constants equal `contracts/authoring/amqp-topology.json`. */
    @Test
    void matchesTheCommittedTopologyFile() throws IOException {
        JsonNode topology = Json.MAPPER.readTree(
            RepoPaths.contracts().resolve("authoring/amqp-topology.json").toFile());

        assertEquals(Topology.EXCHANGE, topology.get("exchange").asText());
        assertEquals(Topology.DEAD_LETTER_EXCHANGE, topology.get("deadLetterExchange").asText());

        JsonNode queues = topology.get("queues");
        assertEquals(3, queues.size());
        assertQueue(queues, Topology.REQUESTED_QUEUE, Topology.REQUESTED_ROUTING_KEY, true);
        assertQueue(queues, Topology.COMPLETED_QUEUE, Topology.COMPLETED_ROUTING_KEY, true);
        assertQueue(queues, Topology.DEAD_QUEUE, Topology.DEAD_ROUTING_KEY, false);
    }

    private static void assertQueue(JsonNode queues, String name, String routingKey, boolean deadLetter) {
        for (JsonNode queue : queues) {
            if (queue.get("name").asText().equals(name)) {
                assertEquals(routingKey, queue.get("routingKey").asText());
                assertEquals(deadLetter, queue.get("deadLetter").asBoolean());
                return;
            }
        }
        throw new AssertionError("no queue named " + name + " in " + queues);
    }
}
