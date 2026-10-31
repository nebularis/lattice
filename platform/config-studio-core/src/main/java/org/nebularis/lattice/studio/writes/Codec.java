// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writes;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.format.DateTimeParseException;
import java.util.HashMap;
import java.util.Map;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.riot.RDFParser;
import org.apache.jena.riot.RiotException;

/**
 * A command on the wire, as `contracts/config-studio/README.md` describes it: its fields as AMQP headers, its graphs as
 * N-Quads in the body. A reply is headers alone.
 */
public final class Codec {
    public static final String CONTENT_TYPE = "application/n-quads";

    private Codec() {
    }

    public static Map<String, Object> headers(Command c) {
        Map<String, Object> h = new HashMap<>();
        h.put("id", c.id());
        put(h, "sender", c.sender());
        h.put("command", c.type().wire);
        h.put("workspace", c.workspace());
        put(h, "job", c.job());
        put(h, "part", c.part());
        if (c.expect() != null) {
            h.put("expect", c.expect());
        }
        if (c.at() != null) {
            h.put("at", c.at().toString());
        }
        put(h, "label", c.label());
        put(h, "sample", c.sample());
        put(h, "principal", c.principal());
        if (c.admin()) {
            h.put("admin", true);
        }
        return h;
    }

    public static byte[] body(Command c) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        RDFDataMgr.write(out, c.body(), Lang.NQUADS);
        return out.toByteArray();
    }

    /** The command, or null when the headers or the body are not a command's. */
    public static Command decode(Map<String, Object> headers, byte[] body) {
        if (headers == null) {
            return null;
        }
        Command.Type type = Command.Type.of(text(headers, "command"));
        if (type == null) {
            return null;
        }
        Dataset graphs = DatasetFactory.create();
        try {
            RDFParser.create().source(new ByteArrayInputStream(body == null ? new byte[0] : body)).lang(Lang.NQUADS)
                .strict(true).parse(graphs.asDatasetGraph());
            Object expect = headers.get("expect");
            String at = text(headers, "at");
            return new Command(text(headers, "id"), text(headers, "sender"), type, text(headers, "workspace"),
                text(headers, "job"), text(headers, "part"),
                expect instanceof Number n ? n.longValue() : null, at == null ? null : Instant.parse(at),
                text(headers, "label"), text(headers, "sample"), graphs, text(headers, "principal"),
                Boolean.TRUE.equals(headers.get("admin")));
        } catch (RiotException | DateTimeParseException e) {
            return null;
        }
    }

    public static Map<String, Object> reply(Reply r) {
        return Map.of("status", r.status(), "revision", r.revision(), "message", r.message());
    }

    public static Reply reply(Map<String, Object> headers) {
        if (headers == null || !(headers.get("status") instanceof Number status)) {
            return new Reply(503, 0, "the writer's reply is malformed");
        }
        Object revision = headers.get("revision");
        return new Reply(status.intValue(), revision instanceof Number n ? n.longValue() : 0, String.valueOf(text(headers, "message")));
    }

    private static void put(Map<String, Object> h, String name, String value) {
        if (value != null) {
            h.put(name, value);
        }
    }

    /** AMQP gives a string header back as a LongString, whose toString is its text. */
    private static String text(Map<String, Object> headers, String name) {
        Object v = headers.get(name);
        return v == null ? null : new String(v instanceof byte[] b ? b : v.toString().getBytes(StandardCharsets.UTF_8), StandardCharsets.UTF_8);
    }
}
