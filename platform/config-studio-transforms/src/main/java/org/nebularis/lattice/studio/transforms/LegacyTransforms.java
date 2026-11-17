// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import com.rabbitmq.client.AMQP;
import com.rabbitmq.client.Channel;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.util.function.Function;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.nebularis.lattice.studio.store.Graphs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The waiting transform route of ADR-A148, deprecated by ADR-A154 decision 13 and answered through the same execution as a run. A request
 * names a compile job in its {@code job} header and a reply queue, and is answered with a Turtle graph on that queue. A request it cannot
 * answer is dropped.
 */
final class LegacyTransforms implements Function<Message, Outcome> {
    private static final Logger LOG = LoggerFactory.getLogger(LegacyTransforms.class);

    /** Sends a reply. */
    interface Replies {
        void send(String replyTo, AMQP.BasicProperties properties, byte[] body) throws Exception;
    }

    /** Replies on {@code channel}, which is not safe for concurrent use, so each reply holds the channel's monitor. */
    static Replies onChannel(Channel channel) {
        return (replyTo, properties, body) -> {
            synchronized (channel) {
                channel.basicPublish("", replyTo, properties, body);
            }
        };
    }

    private final Function<String, Model> jobs;
    private final Replies replies;

    LegacyTransforms(Function<String, Model> jobs, Replies replies) {
        this.jobs = jobs;
        this.replies = replies;
    }

    /** Checks the request, whatever its sender checked (PRI-75), runs it and replies. The message is acknowledged whatever happened. */
    @Override
    public Outcome apply(Message m) {
        String jobIri = m.header("job") == null ? "" : m.header("job");
        String id = m.correlationId();
        if (m.replyTo() == null || id == null || !Graphs.isId(id) || !jobIri.startsWith(Graphs.JOB_PREFIX)
            || !Graphs.isId(jobIri.substring(Graphs.JOB_PREFIX.length()))) {
            LOG.warn("dropped a transform request without a reply queue, a correlation id and a job");
            return Outcome.ACK;
        }
        Model reply;
        try {
            reply = TransformRun.run(jobs.apply(jobIri), jobIri, "urn:lattice:studio:transform:" + id, m.contentType(),
                new String(m.body(), StandardCharsets.UTF_8));
        } catch (RuntimeException e) {
            LOG.error("a transform of {} failed", jobIri, e);
            return Outcome.ACK;
        }
        StringWriter turtle = new StringWriter();
        RDFDataMgr.write(turtle, reply, Lang.TURTLE);
        try {
            replies.send(m.replyTo(), new AMQP.BasicProperties.Builder().contentType("text/turtle").correlationId(id).build(),
                turtle.toString().getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) {
            LOG.warn("replying to a transform request failed", e);
        }
        return Outcome.ACK;
    }
}
