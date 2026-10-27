// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.api;

import java.io.IOException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Clock;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Supplier;
import java.util.regex.Pattern;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.riot.RiotException;
import org.apache.jena.vocabulary.RDF;
import org.nebularis.lattice.studio.jobs.JobBus;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.StudioStore;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Every business rule of the studio's HTTP contract, with no HTTP framework in sight. */
public final class StudioApi {
    public static final int MAX_BODY_BYTES = 5 * 1024 * 1024;
    private static final Logger LOG = LoggerFactory.getLogger(StudioApi.class);
    private static final Pattern SAMPLE_ID = Pattern.compile("[a-z0-9][a-z0-9-]*");
    private static final List<String> GRAPH_NAMES = Workspace.GRAPHS;
    /** The configurations a job checks, and those of them that compile. */
    private static final List<String> TARGETS = GRAPH_NAMES.subList(1, GRAPH_NAMES.size());
    private static final List<String> COMPILED = List.of("eligibility", "surface", "persistence");

    private final StudioStore store;
    private final JobBus bus;
    private final Clock clock;
    private final Supplier<UUID> ids;
    private final Path assets;
    /**
     * One lock per workspace, for the If-Match check and the update that follows it. Two service
     * instances would race, and the proof of concept runs one.
     */
    private final ConcurrentHashMap<String, Object> locks = new ConcurrentHashMap<>();

    public StudioApi(StudioStore store, JobBus bus, Clock clock, Supplier<UUID> ids, Path assets) {
        this.store = store;
        this.bus = bus;
        this.clock = clock;
        this.ids = ids;
        this.assets = assets;
    }

    public ApiResponse handle(ApiRequest req) {
        try {
            return secure(route(req));
        } catch (RuntimeException e) {
            LOG.error("{} {} failed", req.method(), req.path(), e);
            return secure(ApiResponse.text(500, "internal error"));
        }
    }

    private static ApiResponse secure(ApiResponse r) {
        r = r.with("X-Content-Type-Options", "nosniff");
        return r.headers().containsKey("Cache-Control") ? r : r.with("Cache-Control", "no-store");
    }

    private ApiResponse route(ApiRequest req) {
        String path = req.path();
        if (!path.startsWith("/api/")) {
            return notFound();
        }
        String[] s = path.substring(5).split("/", -1);
        String method = req.method();
        if (s.length == 1 && s[0].equals("health")) {
            return method.equals("GET") ? ApiResponse.text(200, "ok") : notAllowed("GET");
        }
        if (s.length == 1 && s[0].equals("vocabulary")) {
            return method.equals("GET") ? vocabulary(req) : notAllowed("GET");
        }
        if (s.length == 1 && s[0].equals("samples")) {
            return method.equals("GET") ? asset("samples.ttl") : notAllowed("GET");
        }
        if (s.length == 2 && s[0].equals("samples") && SAMPLE_ID.matcher(s[1]).matches()) {
            return method.equals("GET") ? asset("samples/" + s[1] + ".ttl") : notAllowed("GET");
        }
        if (s.length == 1 && s[0].equals("workspaces")) {
            return switch (method) {
                case "GET" -> ApiResponse.turtle(200, Turtle.write(store.workspaces()));
                case "POST" -> createWorkspace(req);
                default -> notAllowed("GET, POST");
            };
        }
        if (s.length >= 2 && s[0].equals("workspaces") && Graphs.isId(s[1])) {
            String ws = s[1];
            if (s.length == 2) {
                return switch (method) {
                    case "GET" -> describe(ws);
                    case "DELETE" -> deleteWorkspace(ws);
                    default -> notAllowed("GET, DELETE");
                };
            }
            if (s.length == 4 && s[2].equals("graphs") && GRAPH_NAMES.contains(s[3])) {
                return switch (method) {
                    case "GET" -> getGraph(ws, s[3]);
                    case "PUT" -> putGraph(req, ws, s[3]);
                    default -> notAllowed("GET, PUT");
                };
            }
            if (s.length == 3 && s[2].equals("jobs")) {
                return switch (method) {
                    case "GET" -> listJobs(ws);
                    case "POST" -> submitJob(req, ws);
                    default -> notAllowed("GET, POST");
                };
            }
        }
        if (s.length == 2 && s[0].equals("jobs") && Graphs.isId(s[1])) {
            return switch (method) {
                case "GET" -> getJob(s[1]);
                case "DELETE" -> deleteJob(s[1]);
                default -> notAllowed("GET, DELETE");
            };
        }
        return notFound();
    }

    // --- static assets ---------------------------------------------------------------------

    private ApiResponse vocabulary(ApiRequest req) {
        byte[] bytes = read("vocabulary.ttl");
        if (bytes == null) {
            return notFound();
        }
        String etag = "\"" + sha256(bytes).substring(0, 32) + "\"";
        String cache = "no-cache";
        if (matches(req.header("if-none-match"), etag)) {
            return ApiResponse.empty(304).with("ETag", etag).with("Cache-Control", cache);
        }
        return ApiResponse.turtle(200, bytes).with("ETag", etag).with("Cache-Control", cache);
    }

    private ApiResponse asset(String relative) {
        byte[] bytes = read(relative);
        return bytes == null ? notFound() : ApiResponse.turtle(200, bytes);
    }

    /** Reads a staged file. The names are fixed or checked against {@code SAMPLE_ID}, so no path escapes. */
    private byte[] read(String relative) {
        try {
            Path file = assets.resolve(relative).normalize();
            return file.startsWith(assets.normalize()) && Files.isRegularFile(file) ? Files.readAllBytes(file) : null;
        } catch (IOException e) {
            LOG.warn("cannot read {}", relative, e);
            return null;
        }
    }

    // --- workspaces ------------------------------------------------------------------------

    private ApiResponse createWorkspace(ApiRequest req) {
        ApiResponse bad = checkBody(req);
        if (bad != null) {
            return bad;
        }
        String label;
        try {
            label = slug(req.header("slug"));
        } catch (IllegalArgumentException e) {
            return ApiResponse.text(400, "Slug is not percent-encoded UTF-8");
        }
        Model baseline = parse(req.body());
        if (baseline == null) {
            return ApiResponse.text(400, "the body is not valid Turtle");
        }
        String id = ids.get().toString();
        Instant now = now();
        Workspace ws = Workspace.created(id, label, now);
        store.write(List.of(), Map.of(Graphs.workspace(id), ws.toModel(), ws.baselineGraph(), baseline));
        return ApiResponse.turtle(201, Turtle.write(ws.toModel())).with("Location", "/api/workspaces/" + id);
    }

    private ApiResponse describe(String id) {
        Workspace ws = load(id);
        return ws == null ? notFound() : ApiResponse.turtle(200, Turtle.write(ws.toModel()));
    }

    private ApiResponse deleteWorkspace(String id) {
        synchronized (lock(id)) {
            Workspace ws = load(id);
            if (ws == null) {
                return notFound();
            }
            List<String> graphs = new java.util.ArrayList<>();
            for (long n = 1; n <= ws.revision("baseline"); n++) {
                graphs.add(Graphs.baseline(id, n));
            }
            for (String name : TARGETS) {
                graphs.add(Graphs.config(id, name));
            }
            graphs.add(Graphs.workspace(id));
            store.drop(graphs);
            return ApiResponse.empty(204);
        }
    }

    private ApiResponse getGraph(String id, String name) {
        Workspace ws = load(id);
        if (ws == null) {
            return notFound();
        }
        String graph = name.equals("baseline") ? ws.baselineGraph() : Graphs.config(id, name);
        return ApiResponse.turtle(200, Turtle.write(store.graph(graph))).with("ETag", etag(ws.revision(name)));
    }

    private ApiResponse putGraph(ApiRequest req, String id, String name) {
        if (load(id) == null) {
            return notFound();
        }
        ApiResponse bad = checkBody(req);
        if (bad != null) {
            return bad;
        }
        String ifMatch = req.header("if-match");
        if (ifMatch == null) {
            return ApiResponse.text(428, "If-Match is required");
        }
        Model graph = parse(req.body());
        if (graph == null) {
            return ApiResponse.text(400, "the body is not valid Turtle");
        }
        synchronized (lock(id)) {
            Workspace ws = load(id);
            if (ws == null) {
                return notFound();
            }
            if (!etag(ws.revision(name)).equals(ifMatch.trim())) {
                return ApiResponse.text(412, "If-Match is not the current revision").with("ETag", etag(ws.revision(name)));
            }
            long next = ws.revision(name) + 1;
            Workspace updated = ws.revised(name, next, now());
            // The configuration and the revision move in one update request, so they never disagree.
            String target = name.equals("baseline") ? updated.baselineGraph() : Graphs.config(id, name);
            store.write(List.of(), Map.of(target, graph, Graphs.workspace(id), updated.toModel()));
            return ApiResponse.empty(204).with("ETag", etag(next));
        }
    }

    // --- jobs ------------------------------------------------------------------------------

    private ApiResponse submitJob(ApiRequest req, String id) {
        Map<String, String> query = query(req.query());
        String kind = query.get("kind");
        String target = query.get("target");
        if (!("validate".equals(kind) && TARGETS.contains(target)) && !("compile".equals(kind) && COMPILED.contains(target))) {
            return ApiResponse.text(400, "kind must be validate, with target one of " + TARGETS + ", or compile, with target one of " + COMPILED);
        }
        Workspace ws = load(id);
        if (ws == null) {
            return notFound();
        }
        ApiResponse bad = checkBody(req);
        if (bad != null) {
            return bad;
        }
        Model config = parse(req.body());
        if (config == null) {
            return ApiResponse.text(400, "the body is not valid Turtle");
        }
        String job = ids.get().toString();
        String jobIri = Graphs.job(job);
        Model description = jobDescription(jobIri, id, ws, kind, target, Graphs.jobInput(job));
        store.write(List.of(), Map.of(jobIri, description, Graphs.jobInput(job), config));
        try {
            bus.publish(jobIri);
        } catch (Exception e) {
            if (e instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            LOG.error("publishing {} failed", jobIri, e);
            description.removeAll(description.createResource(jobIri), Cst.status, null);
            description.createResource(jobIri).addProperty(Cst.status, Cst.Failed)
                .addProperty(Cst.failureMessage, "the job could not be handed to the worker: " + e.getClass().getSimpleName());
            store.write(List.of(), Map.of(jobIri, description));
        }
        return ApiResponse.turtle(202, Turtle.write(description)).with("Location", "/api/jobs/" + job);
    }

    private Model jobDescription(String jobIri, String ws, Workspace workspace, String kind, String target, String input) {
        Model m = org.apache.jena.rdf.model.ModelFactory.createDefaultModel();
        Resource job = m.createResource(jobIri);
        job.addProperty(RDF.type, Cst.Job);
        job.addProperty(Cst.kind, kind.equals("validate") ? Cst.Validate : Cst.Compile);
        job.addProperty(Cst.target, Cst.target(target));
        job.addProperty(Cst.workspace, m.createResource(Graphs.workspace(ws)));
        job.addProperty(Cst.configGraph, m.createResource(input));
        job.addProperty(Cst.baselineGraph, m.createResource(workspace.baselineGraph()));
        job.addProperty(Cst.status, Cst.Queued);
        job.addProperty(Cst.submittedAt, m.createTypedLiteral(now().toString(), XSDDatatype.XSDdateTime));
        return m;
    }

    private ApiResponse listJobs(String id) {
        if (load(id) == null) {
            return notFound();
        }
        return ApiResponse.turtle(200, Turtle.write(store.compileJobs(Graphs.workspace(id))));
    }

    private ApiResponse getJob(String job) {
        Model m = store.graph(Graphs.job(job));
        return m.isEmpty() ? notFound() : ApiResponse.turtle(200, Turtle.write(m));
    }

    private ApiResponse deleteJob(String job) {
        if (store.graph(Graphs.job(job)).isEmpty()) {
            return notFound();
        }
        store.drop(List.of(Graphs.job(job), Graphs.jobInput(job)));
        return ApiResponse.empty(204);
    }

    // --- helpers ---------------------------------------------------------------------------

    private Workspace load(String id) {
        return Workspace.from(id, store.graph(Graphs.workspace(id)));
    }

    private Object lock(String id) {
        return locks.computeIfAbsent(id, k -> new Object());
    }

    private Instant now() {
        return clock.instant().truncatedTo(ChronoUnit.SECONDS);
    }

    private static String etag(long revision) {
        return "\"" + revision + "\"";
    }

    /** 415 for a content type other than text/turtle, 413 for a body over the limit, otherwise null. */
    private static ApiResponse checkBody(ApiRequest req) {
        String type = req.header("content-type");
        String media = type == null ? "" : type.split(";", 2)[0].trim().toLowerCase(Locale.ROOT);
        if (!media.equals("text/turtle")) {
            return ApiResponse.text(415, "Content-Type must be text/turtle");
        }
        if (req.body() != null && req.body().length > MAX_BODY_BYTES) {
            return tooLarge();
        }
        return null;
    }

    public static ApiResponse tooLarge() {
        return ApiResponse.text(413, "the body is over 5 MiB");
    }

    private static Model parse(byte[] body) {
        try {
            return Turtle.parse(body == null ? new byte[0] : body);
        } catch (RiotException e) {
            return null;
        }
    }

    /** The percent-decoded, trimmed Slug, or a default label when it is missing or blank. */
    static String slug(String header) {
        if (header == null) {
            return "Untitled workspace";
        }
        String decoded = URLDecoder.decode(header.replace("+", "%2B"), StandardCharsets.UTF_8).trim();
        return decoded.isEmpty() ? "Untitled workspace" : decoded;
    }

    private static Map<String, String> query(String raw) {
        Map<String, String> out = new LinkedHashMap<>();
        if (raw == null || raw.isEmpty()) {
            return out;
        }
        try {
            for (String pair : raw.split("&")) {
                String[] kv = pair.split("=", 2);
                out.putIfAbsent(URLDecoder.decode(kv[0], StandardCharsets.UTF_8),
                    kv.length == 2 ? URLDecoder.decode(kv[1], StandardCharsets.UTF_8) : "");
            }
        } catch (IllegalArgumentException e) {
            out.clear();
        }
        return out;
    }

    private static boolean matches(String ifNoneMatch, String etag) {
        if (ifNoneMatch == null) {
            return false;
        }
        for (String candidate : ifNoneMatch.split(",")) {
            String c = candidate.trim();
            if (c.equals("*") || (c.startsWith("W/") ? c.substring(2) : c).equals(etag)) {
                return true;
            }
        }
        return false;
    }

    private static String sha256(byte[] bytes) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

    private static ApiResponse notFound() {
        return ApiResponse.text(404, "not found");
    }

    private static ApiResponse notAllowed(String allow) {
        return ApiResponse.text(405, "method not allowed").with("Allow", allow);
    }
}
