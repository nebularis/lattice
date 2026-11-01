// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.events;

import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.BiPredicate;
import java.util.function.Function;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.atlas.json.JsonValue;
import org.nebularis.lattice.outbox.CloudEvent;
import org.nebularis.lattice.studio.auth.Principal;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The WebSocket notifier (PM-Q10 (a), PM-Q11 (c), PM-Q12). A session authenticates with its first frame, which carries the headers an
 * HTTP request of the browser would, since a browser cannot set headers on a WebSocket and a credential in the URL would be logged. It
 * then names the subjects it waits for with subscribe frames. An event goes to each session subscribed to its subject whose principal
 * may read it, checked as it is delivered, as a CloudEvent in JSON.
 *
 * <p>Client frames: {@code {"type":"auth","headers":{...}}}, {@code {"type":"subscribe","subject":"..."}} and
 * {@code {"type":"unsubscribe","subject":"..."}}. Server frames: {@code {"type":"ready","principal":"..."}}, {@code {"type":"subscribed","subject":"..."}},
 * {@code {"type":"error","message":"..."}}, and the events, which carry {@code specversion}.
 */
public final class Notifier {
    private static final Logger LOG = LoggerFactory.getLogger(Notifier.class);
    /** The subjects one session may wait for at once, so a session cannot make delivery scan without bound. */
    public static final int MAX_SUBJECTS = 200;
    /** A client frame is a few hundred bytes, so a longer one is refused unread. */
    public static final int MAX_FRAME = 16 * 1024;
    /** WebSocket close code 1008, a policy violation. */
    public static final int POLICY = 1008;

    /** The transport's side of one session. */
    public interface Socket {
        void send(String text);

        void close(int code, String reason);
    }

    private static final class Session {
        volatile Principal principal;
        final Set<String> subjects = ConcurrentHashMap.newKeySet();
    }

    private final Function<Map<String, String>, Principal> authenticate;
    private final BiPredicate<Principal, String> mayRead;
    private final Map<Socket, Session> sessions = new ConcurrentHashMap<>();

    public Notifier(Function<Map<String, String>, Principal> authenticate, BiPredicate<Principal, String> mayRead) {
        this.authenticate = authenticate;
        this.mayRead = mayRead;
    }

    public void opened(Socket socket) {
        sessions.put(socket, new Session());
    }

    public void closed(Socket socket) {
        sessions.remove(socket);
    }

    public int sessions() {
        return sessions.size();
    }

    /** One client frame. A frame that is malformed, or comes before the session authenticated, closes it. */
    public void message(Socket socket, String text) {
        Session session = sessions.get(socket);
        if (session == null) {
            return;
        }
        JsonObject frame = parse(text);
        String type = frame == null ? null : string(frame, "type");
        if (type == null) {
            refuse(socket, "a frame is a JSON object with a type");
            return;
        }
        if (session.principal == null) {
            if (!type.equals("auth") || !frame.hasKey("headers") || !frame.get("headers").isObject()) {
                refuse(socket, "the first frame authenticates, as {\"type\":\"auth\",\"headers\":{...}}");
                return;
            }
            Map<String, String> headers = new java.util.HashMap<>();
            JsonObject given = frame.get("headers").getAsObject();
            for (String key : given.keys()) {
                JsonValue v = given.get(key);
                if (v.isString()) {
                    headers.put(key.toLowerCase(java.util.Locale.ROOT), v.getAsString().value());
                }
            }
            Principal p = authenticate.apply(headers);
            if (p == null) {
                refuse(socket, "sign in first");
                return;
            }
            session.principal = p;
            socket.send("{\"type\":\"ready\",\"principal\":" + JSON.toStringFlat(new org.apache.jena.atlas.json.JsonString(p.name())) + "}");
            return;
        }
        String subject = string(frame, "subject");
        switch (type) {
            case "subscribe" -> {
                if (subject == null) {
                    refuse(socket, "a subscribe frame names a subject");
                } else if (session.subjects.size() >= MAX_SUBJECTS && !session.subjects.contains(subject)) {
                    socket.send(error("a session waits for at most " + MAX_SUBJECTS + " subjects at once"));
                } else if (!mayRead.test(session.principal, subject)) {
                    // Not found and not readable answer alike, so a subscriber learns nothing of a job it may not read.
                    socket.send(error("no such subject: " + subject));
                } else {
                    session.subjects.add(subject);
                    socket.send("{\"type\":\"subscribed\",\"subject\":" + JSON.toStringFlat(new org.apache.jena.atlas.json.JsonString(subject)) + "}");
                }
            }
            case "unsubscribe" -> {
                if (subject != null) {
                    session.subjects.remove(subject);
                }
            }
            default -> refuse(socket, "a frame's type is auth, subscribe or unsubscribe");
        }
    }

    /** Sends the event to each session subscribed to its subject whose principal may read it now. */
    public void deliver(CloudEvent event) {
        String text = null;
        for (Map.Entry<Socket, Session> e : sessions.entrySet()) {
            Session s = e.getValue();
            if (s.principal == null || !s.subjects.contains(event.subject()) || !mayRead.test(s.principal, event.subject())) {
                continue;
            }
            if (text == null) {
                text = json(event);
            }
            try {
                e.getKey().send(text);
            } catch (RuntimeException failed) {
                LOG.debug("a session closed while an event was sent to it: {}", failed.getMessage());
                sessions.remove(e.getKey());
            }
        }
    }

    /** The event in the CloudEvents JSON format, its data inlined since it is JSON. */
    public static String json(CloudEvent event) {
        JsonObject o = new JsonObject();
        o.put("specversion", "1.0");
        o.put("id", event.id().toString());
        o.put("source", event.source().toString());
        o.put("type", event.type());
        o.put("subject", event.subject());
        o.put("time", event.time().toString());
        o.put("datacontenttype", "application/json");
        event.extensions().forEach((k, v) -> o.put(k, v));
        o.put("data", JSON.parseAny(event.data()));
        return JSON.toStringFlat(o);
    }

    private static JsonObject parse(String text) {
        if (text == null || text.length() > MAX_FRAME) {
            return null;
        }
        try {
            JsonValue v = JSON.parseAny(text);
            return v.isObject() ? v.getAsObject() : null;
        } catch (RuntimeException e) {
            return null;
        }
    }

    private static String string(JsonObject o, String key) {
        JsonValue v = o.get(key);
        return v != null && v.isString() ? v.getAsString().value() : null;
    }

    private static String error(String message) {
        return "{\"type\":\"error\",\"message\":" + JSON.toStringFlat(new org.apache.jena.atlas.json.JsonString(message)) + "}";
    }

    private void refuse(Socket socket, String message) {
        socket.send(error(message));
        sessions.remove(socket);
        socket.close(POLICY, "refused");
    }
}
