// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.events;

import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.BiPredicate;
import java.util.function.Function;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.atlas.json.JsonString;
import org.apache.jena.atlas.json.JsonValue;
import org.nebularis.lattice.outbox.CloudEvent;
import org.nebularis.lattice.studio.auth.Principal;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The relay's watchers and its check at delivery (PM-Q10 (a), PM-Q20 (d)). The broker has already checked who a tab is, so a frame
 * arrives with the principal's name its topic carries. A tab names the subjects it waits for with subscribe frames, each carrying
 * the headers an HTTP request of the browser would, so the relay knows the principal and whether it administers. An event goes to
 * each tab watching its subject whose principal may read it, checked as it is delivered, as a CloudEvent in JSON.
 *
 * <p>Frames: {@code {"type":"subscribe","subject":"...","headers":{...}}}, {@code {"type":"unsubscribe","subject":"..."}} and
 * {@code {"type":"gone"}}, the last also a tab's will message. The relay answers {@code {"type":"error","message":"..."}}, and sends
 * the events, which carry {@code specversion}.
 */
public final class Notifier {
    private static final Logger LOG = LoggerFactory.getLogger(Notifier.class);
    /** The subjects one tab may wait for at once, so a tab cannot make delivery scan without bound. */
    public static final int MAX_SUBJECTS = 200;
    /** The tabs one principal may hold at once. */
    public static final int MAX_TABS = 20;
    /** A frame is a few hundred bytes, or a few KiB with a token, so a longer one is dropped unread. */
    public static final int MAX_FRAME = 16 * 1024;

    /** Where a tab's frames are sent. */
    public interface Socket {
        void send(String text);
    }

    private record Session(String user, Socket socket, Set<String> subjects, Principal[] principal) {
    }

    private final Function<Map<String, String>, Principal> authenticate;
    private final BiPredicate<Principal, String> mayRead;
    private final Map<String, Session> sessions = new ConcurrentHashMap<>();

    public Notifier(Function<Map<String, String>, Principal> authenticate, BiPredicate<Principal, String> mayRead) {
        this.authenticate = authenticate;
        this.mayRead = mayRead;
    }

    public int sessions() {
        return sessions.size();
    }

    /** One frame from the tab {@code tab} of the principal named {@code user}, as the broker vouched. A malformed frame is dropped. */
    public void message(String user, String tab, Socket socket, String text) {
        JsonObject frame = parse(text);
        String type = frame == null ? null : string(frame, "type");
        if (type == null) {
            return;
        }
        String key = user + "\n" + tab;
        String subject = string(frame, "subject");
        switch (type) {
            case "gone" -> sessions.remove(key);
            case "unsubscribe" -> {
                Session s = sessions.get(key);
                if (s != null && subject != null) {
                    s.subjects.remove(subject);
                }
            }
            case "subscribe" -> {
                Principal p = principal(frame);
                if (p == null || !p.name().equals(user)) {
                    // The headers must name the principal the broker let in, so a frame cannot borrow another's admin rights.
                    socket.send(error("a subscribe frame carries its principal's own headers"));
                    return;
                }
                Session s = sessions.get(key);
                if (s == null) {
                    if (sessions.values().stream().filter(o -> o.user.equals(user)).count() >= MAX_TABS) {
                        socket.send(error("a principal watches from at most " + MAX_TABS + " tabs at once"));
                        return;
                    }
                    s = sessions.computeIfAbsent(key, k -> new Session(user, socket, ConcurrentHashMap.newKeySet(), new Principal[1]));
                }
                s.principal[0] = p;
                if (subject == null) {
                    socket.send(error("a subscribe frame names a subject"));
                } else if (s.subjects.size() >= MAX_SUBJECTS && !s.subjects.contains(subject)) {
                    socket.send(error("a tab waits for at most " + MAX_SUBJECTS + " subjects at once"));
                } else if (!mayRead.test(p, subject)) {
                    // Not found and not readable answer alike, so a watcher learns nothing of a job it may not read.
                    socket.send(error("no such subject: " + subject));
                } else {
                    s.subjects.add(subject);
                }
            }
            default -> {
            }
        }
    }

    /** Sends the event to each tab watching its subject whose principal may read it now. */
    public void deliver(CloudEvent event) {
        String text = null;
        for (Map.Entry<String, Session> e : sessions.entrySet()) {
            Session s = e.getValue();
            Principal p = s.principal[0];
            if (p == null || !s.subjects.contains(event.subject()) || !mayRead.test(p, event.subject())) {
                continue;
            }
            if (text == null) {
                text = json(event);
            }
            try {
                s.socket.send(text);
            } catch (RuntimeException failed) {
                LOG.debug("an event could not be sent to a tab: {}", failed.getMessage());
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

    private Principal principal(JsonObject frame) {
        if (!frame.hasKey("headers") || !frame.get("headers").isObject()) {
            return null;
        }
        Map<String, String> headers = new java.util.HashMap<>();
        JsonObject given = frame.get("headers").getAsObject();
        for (String key : given.keys()) {
            JsonValue v = given.get(key);
            if (v.isString()) {
                headers.put(key.toLowerCase(java.util.Locale.ROOT), v.getAsString().value());
            }
        }
        return authenticate.apply(headers);
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
        return "{\"type\":\"error\",\"message\":" + JSON.toStringFlat(new JsonString(message)) + "}";
    }
}
