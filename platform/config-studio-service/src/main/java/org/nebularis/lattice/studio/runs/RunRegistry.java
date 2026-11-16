// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.runs;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.function.BiPredicate;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.atlas.json.JsonValue;
import org.nebularis.lattice.studio.auth.Principal;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The memory of the service instance that accepted a run (ADR-A154 decisions 4 to 6, 9 and 10). It holds who submitted each pending
 * run, from which tab, for which workspace and until when, and forwards the run's frames to the submitting tab or to a request waiting
 * for them. Every instance is given every frame and only the one holding the run forwards it. The entry is coordination state (PRI-52)
 * and losing it loses only runs in flight.
 *
 * <p>It knows nothing of the broker or of HTTP. Time is an input (PRI-56): it reads a {@link Clock} and schedules a run's deadline
 * on the {@link Timers} it is given, so a test drives both.
 *
 * <p>Threads. Frames arrive on a broker consumer's thread, acceptance on request threads and a deadline on the timers' thread. Two
 * kinds of lock keep them apart. One lock, {@code index}, guards the maps and is held only to read or change them, never while a run's
 * frames are sent and never while an entry's lock is awaited. Each run's entry has a lock of its own, held while one of its frames is
 * checked, sent and counted, so the frames of one run never interleave, a deadline cannot overtake a frame in flight and a run ends
 * once. An entry's lock may take {@code index} (to forget the run). {@code index} never takes an entry's lock, so the order is fixed
 * and no deadlock can arise. Frames of different runs hold different entry locks, and wait for one another only for the
 * duration of a map operation.
 */
public final class RunRegistry {
    private static final Logger LOG = LoggerFactory.getLogger(RunRegistry.class);

    /** The CloudEvent type of a run's frame, which is also its routing key on the events exchange. */
    public static final String FRAME_TYPE = "org.nebularis.lattice.studio.run.frame";
    /** The source of an event the service publishes to a tab. */
    public static final java.net.URI SERVICE_SOURCE = java.net.URI.create("urn:lattice:studio:service");
    /** The runs one tab may have pending (ADR-A154 decision 9). */
    public static final int MAX_PENDING_PER_TAB = 4;
    /** The frames a run may send, and so the highest sequence number of a worker's frame is one less. */
    public static final int MAX_FRAMES = 128;
    /** The text of one frame, in bytes as UTF-8. */
    public static final int MAX_TEXT_BYTES = 49_152;

    private static final Set<String> FRAME_PROPERTIES = Set.of("run", "seq", "last", "part", "text", "more", "status", "message", "conforms");
    private static final Set<String> PART_PROPERTIES = Set.of("index", "role", "mediaType", "path", "group", "step");
    private static final Set<String> ROLES = Set.of("check", "request", "report", "artefact", "delta", "outcome");
    private static final java.util.regex.Pattern RUN_IRI = java.util.regex.Pattern.compile(
        "urn:lattice:studio:run:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}");

    /** Schedules a run's deadline. */
    public interface Timers {
        /** Runs {@code task} when {@code delay} has passed, and returns what cancels it. */
        Cancellable schedule(Duration delay, Runnable task);
    }

    /** A scheduled task that can be called off. */
    public interface Cancellable {
        void cancel();
    }

    /** One frame as a sink receives it, flat JSON of the frame object. */
    public record Frame(String json, int seq, boolean last) {
    }

    /** Where a run's frames go. Called with the run's lock held, so a sink must not call back into the registry. */
    public interface Sink {
        void send(Frame frame);

        /** The failed last frame the service makes when a run did not end by its deadline. A tab is sent it like any frame. */
        default void expired(Frame frame) {
            send(frame);
        }
    }

    /** A sink that gathers frames for a request that waits for them (ADR-A154 decision 10). */
    public static final class Collector implements Sink {
        private final TreeMap<Integer, String> frames = new TreeMap<>();
        private final CountDownLatch done = new CountDownLatch(1);
        private boolean ended;
        private boolean timedOut;

        @Override
        public synchronized void send(Frame frame) {
            if (ended) {
                return;
            }
            frames.putIfAbsent(frame.seq(), frame.json());
            if (frame.last()) {
                end();
            }
        }

        /** The run's deadline passed, and the request answers that it timed out. The frame the service made is not part of the answer. */
        @Override
        public synchronized void expired(Frame frame) {
            if (!ended) {
                timedOut = true;
                end();
            }
        }

        private void end() {
            ended = true;
            done.countDown();
        }

        /** Waits up to {@code timeout} for the last frame or the deadline, and says whether either came. */
        public boolean await(Duration timeout) throws InterruptedException {
            return done.await(Math.max(0, timeout.toNanos()), TimeUnit.NANOSECONDS);
        }

        /** Whether the run ended at its deadline rather than by its last frame. */
        public synchronized boolean timedOut() {
            return timedOut;
        }

        /** The frames in sequence order, each the first seen for its number. */
        public synchronized List<String> frames() {
            return new ArrayList<>(frames.values());
        }

        /** The frames as a JSON array. */
        public synchronized String json() {
            return "[" + String.join(",", frames.values()) + "]";
        }
    }

    /** The answer to {@link #accept}. {@code retryAfterSeconds} is positive only when the run was refused. */
    public record Admission(boolean accepted, long retryAfterSeconds) {
    }

    private static final class Entry {
        final String run;
        final Principal principal;
        final String tab;
        final String workspace;
        final Instant deadline;
        final Sink sink;
        /** Guarded by this entry. */
        int frames;
        int highestSeq = -1;
        boolean ended;
        Cancellable timer;

        Entry(String run, Principal principal, String tab, String workspace, Instant deadline, Sink sink) {
            this.run = run;
            this.principal = principal;
            this.tab = tab;
            this.workspace = workspace;
            this.deadline = deadline;
            this.sink = sink;
        }

        String tabKey() {
            return keyOf(principal.name(), tab);
        }
    }

    private static String keyOf(String principal, String tab) {
        return principal + "\n" + tab;
    }

    private final Clock clock;
    private final Timers timers;
    private final BiPredicate<Principal, String> mayRead;
    private final Object index = new Object();
    /** Guarded by {@code index}. */
    private final Map<String, Entry> runs = new HashMap<>();
    /** The pending runs of each tab, guarded by {@code index}. */
    private final Map<String, List<Entry>> tabs = new HashMap<>();

    /** {@code mayRead} says whether a principal may read a workspace, by the rule a read of the workspace follows, from the graph as it is now. */
    public RunRegistry(Clock clock, Timers timers, BiPredicate<Principal, String> mayRead) {
        this.clock = clock;
        this.timers = timers;
        this.mayRead = mayRead;
    }

    /** Timers on a scheduled executor. The delay is real time, since a deadline is the wall clock's. */
    public static Timers timers(java.util.concurrent.ScheduledExecutorService executor) {
        return (delay, task) -> {
            java.util.concurrent.ScheduledFuture<?> f = executor.schedule(task, Math.max(0, delay.toNanos()), TimeUnit.NANOSECONDS);
            return () -> f.cancel(false);
        };
    }

    /**
     * Records a pending run, or refuses it when its tab already has {@link #MAX_PENDING_PER_TAB}, saying in seconds how long until the
     * earliest of their deadlines. The caller records a run before it publishes it, since a worker may answer before the publish returns.
     */
    public Admission accept(String run, Principal principal, String tab, String workspace, Instant deadline, Sink sink) {
        Entry entry = new Entry(run, principal, tab, workspace, deadline, sink);
        // The entry's lock is held until its timer is set, so a frame that comes at once waits and then ends the run with a timer to cancel.
        synchronized (entry) {
            synchronized (index) {
                List<Entry> pending = tabs.computeIfAbsent(entry.tabKey(), k -> new ArrayList<>());
                if (pending.size() >= MAX_PENDING_PER_TAB) {
                    Instant earliest = pending.stream().map(e -> e.deadline).min(Instant::compareTo).orElse(deadline);
                    long seconds = Math.max(1, (Duration.between(clock.instant(), earliest).toMillis() + 999) / 1000);
                    return new Admission(false, seconds);
                }
                if (runs.containsKey(run)) {
                    throw new IllegalStateException("the run " + run + " is already pending");
                }
                pending.add(entry);
                runs.put(run, entry);
            }
            entry.timer = timers.schedule(Duration.between(clock.instant(), deadline), () -> expire(entry));
        }
        return new Admission(true, 0);
    }

    /** Forgets a run without sending anything, as when the broker did not take its request. */
    public void cancel(String run) {
        Entry entry;
        synchronized (index) {
            entry = runs.get(run);
        }
        if (entry != null) {
            synchronized (entry) {
                forget(entry);
            }
        }
    }

    /** How many entries the registry holds in all its maps, which is zero when no run is pending. */
    public int size() {
        synchronized (index) {
            return runs.size() + tabs.size();
        }
    }

    /** How many runs the tab has pending. */
    public int pending(String principal, String tab) {
        synchronized (index) {
            List<Entry> pending = tabs.get(keyOf(principal, tab));
            return pending == null ? 0 : pending.size();
        }
    }

    /**
     * Handles a frame read from the events exchange. A frame of a run this instance does not hold is ignored. Any other is validated
     * before anything else, since the service cannot know the frame was not forged or altered on the way (PRI-75), and one that does not
     * hold is dropped and logged without its text. A valid frame is sent when its principal may read the workspace now, and withheld
     * otherwise, so the run stays pending until its deadline.
     */
    public void frame(String frameJson) {
        try {
            handle(frameJson);
        } catch (RuntimeException e) {
            LOG.warn("a run frame could not be handled: {}", e.toString());
        }
    }

    private void handle(String frameJson) {
        JsonObject o = parse(frameJson);
        if (o == null) {
            LOG.warn("a run frame was dropped, since it is not a JSON object");
            return;
        }
        JsonValue named = o.get("run");
        Entry entry = null;
        if (named != null && named.isString()) {
            synchronized (index) {
                entry = runs.get(named.getAsString().value());
            }
        }
        if (entry == null) {
            // Every instance reads every event, and only the one that accepted the run forwards it.
            if (named == null || !named.isString() || !RUN_IRI.matcher(named.getAsString().value()).matches()) {
                LOG.warn("a run frame was dropped, since its run is not a run IRI");
            }
            return;
        }
        String problem = problem(o, entry.run);
        if (problem != null) {
            LOG.warn("a frame of {} was dropped: {}", entry.run, problem);
            return;
        }
        int seq = whole(o.get("seq"));
        boolean last = o.get("last").getAsBoolean().value();
        synchronized (entry) {
            if (entry.ended) {
                return;
            }
            entry.frames++;
            if (entry.frames > MAX_FRAMES) {
                // The worker holds the limit, and a run that goes past it ends here with the failure it would have sent.
                deliver(entry, failed(entry, "the result of the run is too large, so narrow what is run"), false);
                forget(entry);
                return;
            }
            if (deliver(entry, new Frame(JSON.toStringFlat(o), seq, last), false)) {
                entry.highestSeq = Math.max(entry.highestSeq, seq);
            }
            if (last) {
                forget(entry);
            }
        }
    }

    /** The deadline of a run. If it has not ended by then, its sink is sent one failed last frame and the run is forgotten. */
    private void expire(Entry entry) {
        synchronized (entry) {
            if (entry.ended) {
                return;
            }
            deliver(entry, failed(entry, "the run did not finish by its deadline"), true);
            forget(entry);
        }
    }

    private Frame failed(Entry entry, String message) {
        JsonObject o = new JsonObject();
        o.put("run", entry.run);
        o.put("seq", entry.highestSeq + 1);
        o.put("last", true);
        o.put("status", "failed");
        o.put("message", message);
        return new Frame(JSON.toStringFlat(o), entry.highestSeq + 1, true);
    }

    /** Sends the frame when the principal may read the workspace now, and says whether it did. Called with the entry's lock held. */
    private boolean deliver(Entry entry, Frame frame, boolean deadline) {
        boolean may;
        try {
            may = mayRead.test(entry.principal, entry.workspace);
        } catch (RuntimeException e) {
            LOG.warn("whether {} may read a workspace could not be decided, so a frame of {} is withheld: {}", entry.principal.name(), entry.run, e.toString());
            may = false;
        }
        if (!may) {
            return false;
        }
        try {
            if (deadline) {
                entry.sink.expired(frame);
            } else {
                entry.sink.send(frame);
            }
        } catch (RuntimeException e) {
            // A tab that cannot be reached must not keep a run alive or stop its other frames.
            LOG.warn("a frame of {} could not be sent: {}", entry.run, e.toString());
            return false;
        }
        return true;
    }

    /** Removes every trace of the run. Called with the entry's lock held. */
    private void forget(Entry entry) {
        if (entry.ended) {
            return;
        }
        entry.ended = true;
        if (entry.timer != null) {
            entry.timer.cancel();
        }
        synchronized (index) {
            runs.remove(entry.run);
            List<Entry> pending = tabs.get(entry.tabKey());
            if (pending != null) {
                pending.remove(entry);
                if (pending.isEmpty()) {
                    tabs.remove(entry.tabKey());
                }
            }
        }
    }

    private static JsonObject parse(String text) {
        if (text == null) {
            return null;
        }
        try {
            JsonValue v = JSON.parseAny(text);
            return v.isObject() ? v.getAsObject() : null;
        } catch (RuntimeException e) {
            return null;
        }
    }

    /** Why the frame does not hold against `run-frame.schema.json` for the run, or null. The text of the frame is never in the reason. */
    static String problem(JsonObject o, String run) {
        for (String key : o.keys()) {
            if (!FRAME_PROPERTIES.contains(key)) {
                return "it has a property the schema does not name";
            }
        }
        if (!o.hasKey("run") || !o.get("run").isString() || !o.get("run").getAsString().value().equals(run)) {
            return "its run is not the run held";
        }
        Integer seq = whole(o.get("seq"));
        if (seq == null || seq < 0 || seq > MAX_FRAMES - 1) {
            return "its seq is not a whole number from 0 to " + (MAX_FRAMES - 1);
        }
        JsonValue last = o.get("last");
        if (last == null || !last.isBoolean()) {
            return "its last is not a boolean";
        }
        if (o.hasKey("text")) {
            if (!o.get("text").isString()) {
                return "its text is not a string";
            }
            if (o.get("text").getAsString().value().getBytes(StandardCharsets.UTF_8).length > MAX_TEXT_BYTES) {
                return "its text is over " + MAX_TEXT_BYTES + " bytes";
            }
        }
        if (o.hasKey("more") && !o.get("more").isBoolean()) {
            return "its more is not a boolean";
        }
        if (o.hasKey("conforms") && !o.get("conforms").isBoolean()) {
            return "its conforms is not a boolean";
        }
        if (o.hasKey("message") && (!o.get("message").isString() || o.get("message").getAsString().value().isEmpty())) {
            return "its message is not a non-empty string";
        }
        String status = null;
        if (o.hasKey("status")) {
            JsonValue s = o.get("status");
            status = s.isString() ? s.getAsString().value() : null;
            if (!"succeeded".equals(status) && !"failed".equals(status)) {
                return "its status is neither succeeded nor failed";
            }
        }
        if (last.getAsBoolean().value()) {
            if (status == null) {
                return "a last frame has no status";
            }
            if (o.hasKey("more") && o.get("more").getAsBoolean().value()) {
                return "a last frame says more is coming";
            }
            if (status.equals("failed") && (!o.hasKey("message") || o.hasKey("conforms"))) {
                return "a failed frame needs a message and has no conforms";
            }
            if (status.equals("succeeded") && o.hasKey("message")) {
                return "a succeeded frame has no message";
            }
        } else if (o.hasKey("status") || o.hasKey("message") || o.hasKey("conforms")) {
            return "a frame that is not last carries a status, a message or conforms";
        }
        if (o.hasKey("part")) {
            return partProblem(o.get("part"));
        }
        return null;
    }

    private static String partProblem(JsonValue p) {
        if (!p.isObject()) {
            return "its part is not an object";
        }
        JsonObject part = p.getAsObject();
        for (String key : part.keys()) {
            if (!PART_PROPERTIES.contains(key)) {
                return "its part has a property the schema does not name";
            }
        }
        Integer index = whole(part.get("index"));
        if (index == null || index < 0 || index > 127) {
            return "its part's index is not a whole number from 0 to 127";
        }
        JsonValue role = part.get("role");
        if (role == null || !role.isString() || !ROLES.contains(role.getAsString().value())) {
            return "its part's role is not one the schema names";
        }
        JsonValue media = part.get("mediaType");
        if (media == null || !media.isString() || media.getAsString().value().isEmpty()) {
            return "its part's mediaType is not a non-empty string";
        }
        for (String key : new String[] {"path", "group"}) {
            if (part.hasKey(key) && (!part.get(key).isString() || part.get(key).getAsString().value().isEmpty())) {
                return "its part's " + key + " is not a non-empty string";
            }
        }
        if (part.hasKey("step")) {
            Integer step = whole(part.get("step"));
            if (step == null || step < 0) {
                return "its part's step is not a whole number from 0";
            }
        }
        return null;
    }

    /** The value as an int when it is a JSON number with no fraction, else null. */
    private static Integer whole(JsonValue v) {
        if (v == null || !v.isNumber()) {
            return null;
        }
        BigDecimal n = new BigDecimal(v.getAsNumber().value().toString());
        try {
            return n.intValueExact();
        } catch (ArithmeticException e) {
            return null;
        }
    }
}
