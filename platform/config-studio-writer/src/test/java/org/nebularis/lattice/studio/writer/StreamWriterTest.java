// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import org.junit.jupiter.api.Test;

class StreamWriterTest {
    @Test
    void aReplyToKeptAsAnAmqp10AddressNamesItsQueue() {
        // As RabbitMQ 4.4 stores the service's reply_to in the stream, observed on the live stack.
        assertEquals("amq.rabbitmq.reply-to.g1h2AA5yZXBseUA0MjM1NTc4MAAAA4EAAAAAauDz0A==.LqwAPs8fRHKo/CMG+E+NJw==",
            StreamWriter.queue("/queues/amq.rabbitmq.reply-to.g1h2AA5yZXBseUA0MjM1NTc4MAAAA4EAAAAAauDz0A%3D%3D.LqwAPs8fRHKo%2FCMG%2BE%2BNJw%3D%3D"));
        assertEquals("plain", StreamWriter.queue("plain"));
        assertNull(StreamWriter.queue(null));
    }
}
