package org.nebularis.lattice.outbox;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Map;

public final class RabbitMqEventPublisher implements EventPublisher {
    private final Channel channel;
    private final String exchange;

    public RabbitMqEventPublisher(Channel channel, String exchange) {
        this.channel = channel;
        this.exchange = exchange;
    }

    public void declareTopology(String queue, String deadLetterExchange) throws IOException {
        channel.exchangeDeclare(exchange, "topic", true);
        channel.exchangeDeclare(deadLetterExchange, "topic", true);
        channel.queueDeclare(queue, true, false, false, Map.of("x-dead-letter-exchange", deadLetterExchange));
        channel.queueBind(queue, exchange, "#");
    }

    @Override
    public void publish(CloudEvent event) {
        try {
            var properties = new AMQP.BasicProperties.Builder()
                .contentType("application/cloudevents+json")
                .messageId(event.id().toString())
                .correlationId(event.extensions().get("correlationid"))
                .type(event.type())
                .deliveryMode(2)
                .build();
            channel.basicPublish(exchange, event.type(), properties, event.data().getBytes(StandardCharsets.UTF_8));
        } catch (IOException error) {
            throw new IllegalStateException("could not publish CloudEvent", error);
        }
    }
}
