// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import com.rabbitmq.client.Connection;
import com.rabbitmq.client.Delivery;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.nebularis.lattice.studio.jobs.Amqp;
import org.nebularis.lattice.studio.jobs.Topology;
import org.nebularis.lattice.studio.settings.Secrets;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.StudioStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The Configuration Studio's transforms worker (ADR-A148). It answers each request on {@code lattice.studio.transforms},
 * a sample source naming a compile job of the mapping part in its {@code job} header, on the sender's reply queue, and
 * stays running so the engines and the stylesheets they compiled stay warm. It reads the store and never writes it.
 */
public final class TransformsMain {
    private static final Logger LOG = LoggerFactory.getLogger(TransformsMain.class);

    private TransformsMain() {
    }

    public static void main(String[] args) throws Exception {
        Map<String, String> env = System.getenv();
        String fuseki = env.get("LATTICE_FUSEKI_URL");
        if (fuseki == null || fuseki.isBlank()) {
            throw new IllegalArgumentException("LATTICE_FUSEKI_URL is required");
        }
        StudioStore store = StudioStore.fuseki(fuseki.trim(), env.getOrDefault("LATTICE_FUSEKI_DATASET", "studio"),
            env.get("LATTICE_FUSEKI_USER"), Secrets.secret(env, "LATTICE_FUSEKI_PASSWORD"));
        Connection connection = Amqp.connect(Secrets.required(env, "LATTICE_AMQP_URI"), "config-studio-transforms");
        Channel channel = connection.createChannel();
        Topology.declare(channel);
        channel.basicQos(1);
        channel.basicConsume(Topology.TRANSFORMS_QUEUE, false, (tag, delivery) -> {
            try {
                answer(channel, store, delivery);
            } finally {
                channel.basicAck(delivery.getEnvelope().getDeliveryTag(), false);
            }
        }, tag -> LOG.warn("the transforms queue cancelled this consumer"));
        Runtime.getRuntime().addShutdownHook(new Thread(() -> {
            try {
                connection.close();
            } catch (Exception e) {
                LOG.debug("closing the RabbitMQ connection failed", e);
            }
            store.close();
        }));
        LOG.info("Configuration Studio transforms worker running");
    }

    /** Checks the request, whatever its sender checked (PRI-75), runs it and replies. A request it cannot answer is dropped. */
    static void answer(Channel channel, StudioStore store, Delivery delivery) {
        AMQP.BasicProperties p = delivery.getProperties();
        Object job = p.getHeaders() == null ? null : p.getHeaders().get("job");
        String jobIri = job == null ? "" : job.toString();
        String id = p.getCorrelationId();
        if (p.getReplyTo() == null || id == null || !Graphs.isId(id) || !jobIri.startsWith(Graphs.JOB_PREFIX)
            || !Graphs.isId(jobIri.substring(Graphs.JOB_PREFIX.length()))) {
            LOG.warn("dropped a transform request without a reply queue, a correlation id and a job");
            return;
        }
        Model reply;
        try {
            reply = TransformRun.run(store.graph(jobIri), jobIri, "urn:lattice:studio:transform:" + id, p.getContentType(),
                new String(delivery.getBody(), StandardCharsets.UTF_8));
        } catch (RuntimeException e) {
            LOG.error("a transform of {} failed", jobIri, e);
            return;
        }
        StringWriter turtle = new StringWriter();
        RDFDataMgr.write(turtle, reply, Lang.TURTLE);
        try {
            channel.basicPublish("", p.getReplyTo(), new AMQP.BasicProperties.Builder().contentType("text/turtle").correlationId(id).build(),
                turtle.toString().getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) {
            LOG.warn("replying to a transform request failed", e);
        }
    }
}
