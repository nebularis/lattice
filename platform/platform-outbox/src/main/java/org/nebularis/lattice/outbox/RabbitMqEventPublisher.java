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
            // The CloudEvents AMQP binding in binary mode: the attributes are application properties prefixed "cloudEvents:", and
            // the body is the data alone, so a consumer reads the subject and source without parsing it.
            Map<String, Object> headers = new java.util.HashMap<>();
            headers.put("cloudEvents:specversion", "1.0");
            headers.put("cloudEvents:id", event.id().toString());
            headers.put("cloudEvents:source", event.source().toString());
            headers.put("cloudEvents:type", event.type());
            headers.put("cloudEvents:subject", event.subject());
            headers.put("cloudEvents:time", event.time().toString());
            event.extensions().forEach((name, value) -> headers.put("cloudEvents:" + name, value));
            var properties = new AMQP.BasicProperties.Builder()
                .contentType("application/json")
                .headers(headers)
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
