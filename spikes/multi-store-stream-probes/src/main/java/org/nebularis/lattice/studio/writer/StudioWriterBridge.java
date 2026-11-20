// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writer;

import com.rabbitmq.stream.Environment;
import com.rabbitmq.stream.MessageHandler;
import java.util.List;
import org.nebularis.lattice.studio.writes.Reply;

/**
 * Runs a probe's batch through the studio's own {@link StreamWriter#apply}, with the offsets the studio's writer stores, so
 * the probe tests the writer's code and not a copy of it. In this package because {@code apply} is package-private.
 */
public final class StudioWriterBridge {
    /** The store write a probe stands in for. */
    public interface Store {
        void apply() throws InterruptedException;
    }

    private StudioWriterBridge() {
    }

    public static void apply(List<MessageHandler.Context> contexts, Store store, Environment environment) throws InterruptedException {
        List<StreamWriter.Item> batch = contexts.stream().map(context -> new StreamWriter.Item(context, null)).toList();
        StreamWriter.apply(batch, items -> {
            try {
                store.apply();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
            return items.stream().map(item -> Reply.ok(0)).toList();
        }, (item, reply) -> {
        }, StreamWriter.offsets(environment));
    }
}
