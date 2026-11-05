// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writes;

import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Resource;
import org.nebularis.lattice.outbox.CloudEvent;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;

/**
 * The studio's completion events (PM-Q10 (a), PM-Q12): a CloudEvent for each applied write that changes a job, on one topic exchange,
 * naming the job and carrying its status and workspace, never its content (ADR-A30). A notifier for each transport delivers it to
 * the subscribers who may read the job.
 */
public final class StudioEvents {
    /** The topic exchange every event is published to, with its type as the routing key. */
    public static final String EXCHANGE = "lattice.studio.events";
    /** A job's status or results changed. */
    public static final String JOB_UPDATED = "org.nebularis.lattice.studio.job.updated";
    public static final URI SOURCE = URI.create("urn:lattice:studio:writer");

    private StudioEvents() {
    }

    /** The event for an applied job update, or null when the command is not one. Its id is the command's, so a redelivery repeats it. */
    public static CloudEvent of(Command c, Instant at) {
        if (c.type() != Command.Type.JOB_UPDATE || c.job() == null) {
            return null;
        }
        String job = Graphs.job(c.job());
        Model update = c.body().getNamedModel(job);
        Resource status = update.createResource(job).getPropertyResourceValue(Cst.status);
        String name = status == null ? null : status.getURI().substring(status.getURI().lastIndexOf('#') + 1);
        String data = "{\"status\":" + quoted(name) + ",\"workspace\":" + quoted(c.workspace()) + "}";
        return new CloudEvent(id(c.id()), SOURCE, JOB_UPDATED, job, at, Map.of(), data);
    }

    private static UUID id(String commandId) {
        try {
            return UUID.fromString(commandId);
        } catch (IllegalArgumentException e) {
            return UUID.nameUUIDFromBytes(commandId.getBytes(StandardCharsets.UTF_8));
        }
    }

    /** A JSON string, or null. The values are an id or a term's local name, so only a quote and a backslash need escaping. */
    private static String quoted(String s) {
        return s == null ? "null" : "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"") + "\"";
    }
}
