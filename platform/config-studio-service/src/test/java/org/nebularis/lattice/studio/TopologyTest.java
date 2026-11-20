// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
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
            {"name", Topology.JOBS_LONG_QUEUE}, {"routingKey", Topology.JOBS_LONG_ROUTING_KEY},
            {"name", Topology.TRANSFORMS_QUEUE}, {"routingKey", Topology.TRANSFORMS_ROUTING_KEY},
            {"name", Topology.RUNS_INTERACTIVE_QUEUE}, {"routingKey", Topology.RUNS_INTERACTIVE_ROUTING_KEY},
            {"name", Topology.RUNS_QUEUE}, {"routingKey", Topology.RUNS_ROUTING_KEY},
            {"name", Topology.RUNS_RDF_QUEUE}, {"routingKey", Topology.RUNS_RDF_ROUTING_KEY},
            {"name", Topology.DEAD_QUEUE}, {"routingKey", Topology.DEAD_ROUTING_KEY}}) {
            assertTrue(json.contains("\"" + pair[0] + "\": \"" + pair[1] + "\""), pair[0] + " " + pair[1]);
        }
        String jobs = json.substring(json.indexOf("\"lattice.studio.jobs\""), json.indexOf("\"lattice.studio.dead\""));
        assertTrue(jobs.contains("\"deadLetter\": true"));
        String longJobs = json.substring(json.indexOf("\"lattice.studio.jobs.long\""), json.indexOf("\"lattice.studio.transforms\""));
        assertTrue(longJobs.contains("\"deadLetter\": true"));
        assertTrue(json.substring(json.indexOf("\"lattice.studio.dead\"")).contains("\"deadLetter\": false"));
        String transforms = json.substring(json.indexOf("\"lattice.studio.transforms\""), json.indexOf("\"lattice.studio.dead\""));
        assertTrue(transforms.contains("\"deadLetter\": false"));
        String runs = json.substring(json.indexOf("\"lattice.studio.runs.interactive\""), json.indexOf("\"lattice.studio.dead\""));
        assertEquals(3, runs.split("\"deadLetter\": false", -1).length - 1, "the three run queues are not dead-lettered");
        assertTrue(runs.indexOf("\"lattice.studio.runs\"") > 0);
        assertTrue(json.contains("\"superStream\": \"" + Topology.WRITES + "\""));
        assertTrue(json.contains("\"partitions\": " + Topology.PARTITIONS));
        assertTrue(json.contains("\"x-max-age\": \"" + Topology.PARTITION_ARGUMENTS.get("x-max-age") + "\""));
        assertTrue(json.contains("\"x-max-length-bytes\": " + Topology.PARTITION_ARGUMENTS.get("x-max-length-bytes")));
        assertTrue(json.contains("\"consumerGroup\": \"lattice.studio.writers\""));
    }

    @Test
    void theRunQueuesAreDeclaredLikeTheTransformsQueueAndNeitherIsDeadLettered() throws IOException {
        java.util.Map<String, java.util.Map<String, Object>> declared = new java.util.LinkedHashMap<>();
        java.util.List<String[]> bound = new java.util.ArrayList<>();
        com.rabbitmq.client.Channel channel = (com.rabbitmq.client.Channel) java.lang.reflect.Proxy.newProxyInstance(
            getClass().getClassLoader(), new Class<?>[] {com.rabbitmq.client.Channel.class}, (self, method, args) -> {
                if (method.getName().equals("queueDeclare") && args.length == 5) {
                    @SuppressWarnings("unchecked") java.util.Map<String, Object> arguments = (java.util.Map<String, Object>) args[4];
                    declared.put((String) args[0], arguments);
                    assertEquals(java.util.List.of(true, false, false), java.util.List.of(args[1], args[2], args[3]), (String) args[0]);
                } else if (method.getName().equals("queueBind") && args.length == 3) {
                    bound.add(new String[] {(String) args[0], (String) args[1], (String) args[2]});
                }
                return null;
            });
        Topology.declare(channel);
        for (String queue : new String[] {Topology.RUNS_INTERACTIVE_QUEUE, Topology.RUNS_QUEUE, Topology.RUNS_RDF_QUEUE}) {
            assertEquals(declared.get(Topology.TRANSFORMS_QUEUE), declared.get(queue), queue);
            assertTrue(declared.get(queue).isEmpty(), queue);
            assertTrue(bound.stream().anyMatch(b -> b[0].equals(queue) && b[1].equals(Topology.EXCHANGE) && b[2].equals(queue)), queue);
        }
    }

    @Test
    void aWorkspaceRoutesByItsIdsFirst32Bits() {
        org.junit.jupiter.api.Assertions.assertEquals("7", Topology.routingKey("ffffffff-0000-4000-8000-000000000000"));
        org.junit.jupiter.api.Assertions.assertEquals("0", Topology.routingKey("00000000-ffff-4000-8000-000000000000"));
        org.junit.jupiter.api.Assertions.assertEquals("5", Topology.routingKey("0000000d-0000-4000-8000-000000000000"));
    }
}
