// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.probes.msa;

import com.rabbitmq.stream.Consumer;
import com.rabbitmq.stream.Environment;
import com.rabbitmq.stream.NoOffsetException;
import com.rabbitmq.stream.OffsetSpecification;
import java.util.List;

/**
 * Reads the offset the broker holds for the writers group on each partition, with a consumer of the same name that is not part
 * of a single active consumer group and does not store anything. The value is what the next active consumer is told to resume
 * after.
 */
final class Offsets {
    private Offsets() {
    }

    static void main(Main.Args a) throws Exception {
        String superStream = a.str("super", "lattice.studio.writes");
        int partitions = a.num("partitions", 8);
        List<String> uris = a.list("uris", "rabbitmq-stream://guest:guest@msa-i9-rmq1:5552");
        var eb = Environment.builder();
        if (uris.size() == 1) {
            eb.uri(uris.get(0));
        } else {
            eb.uris(uris);
        }
        try (Environment environment = eb.build()) {
            for (int i = 0; i < partitions; i++) {
                String stream = Topo.partition(superStream, i);
                Consumer consumer = environment.consumerBuilder().stream(stream).name(Sac.GROUP)
                    .offset(OffsetSpecification.next())
                    .manualTrackingStrategy().builder()
                    .messageHandler((context, message) -> {
                    }).build();
                try {
                    Log.ev("stored", "s", i, "o", consumer.storedOffset());
                } catch (NoOffsetException e) {
                    Log.ev("stored", "s", i, "o", -1);
                } finally {
                    consumer.close();
                }
            }
        }
    }
}
