// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import com.rabbitmq.client.Delivery;
import java.util.Map;

/** A delivery as the worker reads it, apart from the broker's types. */
record Message(long tag, boolean redelivered, Map<String, Object> headers, String contentType, String replyTo, String correlationId, byte[] body) {
    static Message of(Delivery d) {
        var p = d.getProperties();
        return new Message(d.getEnvelope().getDeliveryTag(), d.getEnvelope().isRedeliver(),
            p.getHeaders() == null ? Map.of() : p.getHeaders(), p.getContentType(), p.getReplyTo(), p.getCorrelationId(), d.getBody());
    }

    /** A header as text, or null when it is absent. */
    String header(String name) {
        Object v = headers.get(name);
        return v == null ? null : v.toString();
    }
}
