// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.rabbitmq.client.Channel;
import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Proxy;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.jobs.Topology;

class TopologyTest {
    private static JsonObject contract() throws IOException {
        try (InputStream in = Files.newInputStream(Path.of("..", "..", "contracts", "config-studio", "amqp-topology.json"))) {
            return JSON.parse(in);
        }
    }

    @Test
    void theConstantsEqualTheContractFile() throws IOException {
        JsonObject json = contract();
        assertEquals(Topology.EXCHANGE, json.getString("exchange"));
        assertEquals(Topology.DEAD_LETTER_EXCHANGE, json.getString("deadLetterExchange"));
        List<String> names = new ArrayList<>();
        List<String> keys = new ArrayList<>();
        json.get("queues").getAsArray().forEach(q -> {
            names.add(q.getAsObject().getString("name"));
            keys.add(q.getAsObject().getString("routingKey"));
        });
        assertEquals(List.of(Topology.JOBS_QUEUE, Topology.JOBS_LONG_QUEUE, Topology.TRANSFORMS_QUEUE, Topology.DEAD_QUEUE), names);
        assertEquals(List.of(Topology.JOBS_ROUTING_KEY, Topology.JOBS_LONG_ROUTING_KEY, Topology.TRANSFORMS_ROUTING_KEY,
            Topology.DEAD_ROUTING_KEY), keys);
        JsonObject writes = json.get("writes").getAsObject();
        assertEquals(Topology.WRITES, writes.getString("superStream"));
        assertEquals(Topology.PARTITIONS, writes.get("partitions").getAsNumber().value().intValue());
        JsonObject partition = writes.get("partitionArguments").getAsObject();
        assertEquals(Topology.PARTITION_ARGUMENTS.get("x-max-age"), partition.getString("x-max-age"));
        assertEquals(Topology.PARTITION_ARGUMENTS.get("x-max-length-bytes"), partition.get("x-max-length-bytes").getAsNumber().value().longValue());
        assertEquals("lattice.studio.writers", writes.getString("consumerGroup"));
    }

    /**
     * MSA-F4, MSAI12-01. What the service declares, recorded on a channel, is the operator guide's table, which the worker's
     * {@code test_the_worker_declares_each_queue_where_the_contract_binds_it} holds the worker to as well.
     */
    @Test
    void theServiceDeclaresEachQueueWhereTheContractBindsIt() throws IOException {
        List<List<Object>> calls = new ArrayList<>();
        Channel channel = (Channel) Proxy.newProxyInstance(Channel.class.getClassLoader(), new Class<?>[] {Channel.class},
            (self, method, args) -> {
                switch (method.getName()) {
                    case "exchangeDeclare" -> calls.add(List.of("exchange", args[0], args[1], args[2], args.length > 4 ? args[4] : Map.of()));
                    case "queueDeclare" -> calls.add(List.of("queue", args[0], args[1], args[4]));
                    case "queueBind" -> calls.add(List.of("bind", args[0], args[1], args[2], args.length > 3 ? args[3] : Map.of()));
                    default -> {
                    }
                }
                return null;
            });
        Topology.declare(channel);
        assertEquals(List.of(
            List.of("exchange", "lattice.studio", "topic", true, Map.of()),
            List.of("exchange", "lattice.studio.dlx", "topic", true, Map.of()),
            List.of("queue", "lattice.studio.jobs", true, Map.of("x-dead-letter-exchange", "lattice.studio.dlx")),
            List.of("bind", "lattice.studio.jobs", "lattice.studio", "lattice.studio.jobs", Map.of()),
            List.of("queue", "lattice.studio.jobs.long", true, Map.of("x-dead-letter-exchange", "lattice.studio.dlx")),
            List.of("bind", "lattice.studio.jobs.long", "lattice.studio", "lattice.studio.jobs.long", Map.of()),
            List.of("queue", "lattice.studio.transforms", true, Map.of()),
            List.of("bind", "lattice.studio.transforms", "lattice.studio", "lattice.studio.transforms", Map.of()),
            List.of("queue", "lattice.studio.dead", true, Map.of()),
            List.of("bind", "lattice.studio.dead", "lattice.studio.dlx", "#", Map.of())), calls.subList(0, 10));
    }

    @Test
    void aWorkspaceRoutesByItsIdsFirst32Bits() {
        assertEquals("7", Topology.routingKey("ffffffff-0000-4000-8000-000000000000"));
        assertEquals("0", Topology.routingKey("00000000-ffff-4000-8000-000000000000"));
        assertEquals("5", Topology.routingKey("0000000d-0000-4000-8000-000000000000"));
    }
}
