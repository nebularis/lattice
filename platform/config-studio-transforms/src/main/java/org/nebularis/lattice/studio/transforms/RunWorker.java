// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.OffsetDateTime;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.function.Function;
import java.util.regex.Pattern;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.rdf.model.Model;
import org.nebularis.lattice.studio.store.Graphs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Handles the messages of one run queue (contract Runs, ADR-A154 decisions 6, 7 and 12). A request is checked before anything is done
 * (PRI-75), and the handler then publishes the run's frames and returns what to do with the message, which the queue's consumer does
 * only afterwards. The clock is an input (PRI-56), and nothing here reads another.
 *
 * <p>An execution runs on a thread of its own, so the handler's thread can wait for it only until the run's deadline. At the deadline
 * the execution is interrupted and nothing more is published for the run. Neither Saxon's XSLT processing nor JOLT polls the
 * interrupt flag, so an interrupt does not stop one that is busy. It is abandoned, still running on its daemon thread until the engine
 * returns, which frees the handler and the queue's slot at the deadline and costs the thread and its memory until then. A run's
 * input is bounded to 5 MiB and the stylesheets and chains are the compiler's, which keeps the time an abandoned execution can use short
 * in practice, and it is a limit of the engines rather than of this worker.
 */
final class RunWorker implements Function<Message, Outcome>, AutoCloseable {
    private static final Logger LOG = LoggerFactory.getLogger(RunWorker.class);
    static final int MAX_INPUT_BYTES = 5 * 1024 * 1024;
    private static final Pattern RUN_IRI = Pattern.compile("urn:lattice:studio:run:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}");
    private static final Map<String, Set<String>> TARGETS = Map.of("sample", Set.of("mapping"), "simulate", Set.of("persistence", "surface"));
    private static final Set<String> RDF_SAMPLES = Set.of("text/turtle", "application/n-triples");

    private record Request(String run, String job, String kind, String target, Instant deadline) {
    }

    private final String kind;
    private final Function<String, Model> jobs;
    private final FrameSink sink;
    private final Clock clock;
    private final ExecutorService executions = Executors.newCachedThreadPool(r -> {
        Thread t = new Thread(r, "run-execution");
        t.setDaemon(true);
        return t;
    });

    /** A handler for the queue of {@code kind} runs, which reads compile jobs with {@code jobs}. */
    RunWorker(String kind, Function<String, Model> jobs, FrameSink sink, Clock clock) {
        this.kind = kind;
        this.jobs = jobs;
        this.sink = sink;
        this.clock = clock;
    }

    @Override
    public Outcome apply(Message message) {
        Request request;
        try {
            request = read(message);
        } catch (IllegalArgumentException e) {
            // The reason names a header, never a value or the body.
            LOG.warn("rejected a run request: {}", e.getMessage());
            return Outcome.REJECT;
        }
        if (message.redelivered()) {
            return publish(request.run(), RunFrames.failed(request.run(), "A worker stopped during the run, so run it again."));
        }
        if (!clock.instant().isBefore(request.deadline())) {
            // The service sends the failed frame of a run that passed its deadline.
            return Outcome.ACK;
        }
        if (request.kind().equals("simulate")) {
            return publish(request.run(), RunFrames.failed(request.run(), "Simulators run in a later slice (SVA-P3), so this run was not started."));
        }
        String type = message.contentType() == null ? "" : message.contentType().split(";", 2)[0].trim().toLowerCase(Locale.ROOT);
        if (RDF_SAMPLES.contains(type)) {
            return publish(request.run(), RunFrames.failed(request.run(), "RDF samples run in a later slice (SVA-M3a), so this run was not started."));
        }
        if (message.body().length > MAX_INPUT_BYTES) {
            return publish(request.run(), RunFrames.failed(request.run(), "The sample is over 5 MiB, so this run was not started."));
        }
        String sample = new String(message.body(), StandardCharsets.UTF_8);
        Future<TransformRun.Result> execution = executions.submit(() -> {
            Model job;
            try {
                job = jobs.apply(request.job());
            } catch (RuntimeException e) {
                LOG.warn("the compile job of a run could not be read", e);
                return new TransformRun.Result("The compile job could not be read, so this run was not started.", List.of());
            }
            return TransformRun.execute(job, request.job(), message.contentType(), sample);
        });
        long millis = Duration.between(clock.instant(), request.deadline()).toMillis();
        TransformRun.Result result;
        try {
            result = execution.get(Math.max(millis, 0), TimeUnit.MILLISECONDS);
        } catch (TimeoutException e) {
            execution.cancel(true);
            LOG.warn("a run passed its deadline and was stopped");
            return Outcome.ACK;
        } catch (ExecutionException e) {
            LOG.error("a run failed", e.getCause());
            return publish(request.run(), RunFrames.failed(request.run(), "The run failed, so run it again."));
        } catch (InterruptedException e) {
            execution.cancel(true);
            Thread.currentThread().interrupt();
            return Outcome.REQUEUE;
        }
        return publish(request.run(), RunFrames.of(request.run(), result));
    }

    /** Checks the headers as the service did. Throws a reason that names a header, never its value. */
    private Request read(Message m) {
        String run = m.header("run");
        String job = m.header("job");
        String kindHeader = m.header("kind");
        String target = m.header("target");
        String deadline = m.header("deadline");
        for (String[] h : new String[][] {{"run", run}, {"job", job}, {"kind", kindHeader}, {"target", target}, {"deadline", deadline}}) {
            if (h[1] == null || h[1].isEmpty()) {
                throw new IllegalArgumentException("header " + h[0] + " is missing");
            }
        }
        if (!RUN_IRI.matcher(run).matches()) {
            throw new IllegalArgumentException("header run is not a run IRI");
        }
        if (!job.startsWith(Graphs.JOB_PREFIX) || !Graphs.isId(job.substring(Graphs.JOB_PREFIX.length()))) {
            throw new IllegalArgumentException("header job is not a job IRI");
        }
        if (!TARGETS.getOrDefault(kindHeader, Set.of()).contains(target)) {
            throw new IllegalArgumentException("headers kind and target are not a pair a run takes");
        }
        if (!kindHeader.equals(kind)) {
            throw new IllegalArgumentException("header kind is not one this queue carries");
        }
        Instant at;
        try {
            at = OffsetDateTime.parse(deadline).toInstant();
        } catch (DateTimeParseException e) {
            throw new IllegalArgumentException("header deadline is not a dateTime with a time zone");
        }
        return new Request(run, job, kindHeader, target, at);
    }

    private Outcome publish(String run, List<JsonObject> frames) {
        try {
            sink.publish(run, frames.stream().map(JSON::toStringFlat).toList());
            return Outcome.ACK;
        } catch (IOException | RuntimeException e) {
            // Not acknowledged, so the broker redelivers it and a worker then says the run was lost.
            LOG.warn("publishing the frames of a run failed", e);
            return Outcome.REQUEUE;
        }
    }

    @Override
    public void close() {
        executions.shutdownNow();
    }
}
