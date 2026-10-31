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
import java.time.Duration;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.function.Supplier;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.ResourceFactory;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RiotException;
import org.apache.jena.vocabulary.RDF;
import org.apache.jena.vocabulary.RDFS;
import org.nebularis.lattice.studio.auth.Authenticator;
import org.nebularis.lattice.studio.auth.LocalAuthenticator;
import org.nebularis.lattice.studio.auth.Principal;
import org.nebularis.lattice.studio.jobs.JobBus;
import org.nebularis.lattice.studio.jobs.Refresher;
import org.nebularis.lattice.studio.model.Parts;
import org.nebularis.lattice.studio.model.Workspace;
import org.nebularis.lattice.studio.authoring.Documents;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.StudioOperations;
import org.nebularis.lattice.studio.store.StudioOperations.Family;
import org.nebularis.lattice.studio.store.StudioStore;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.Reply;
import org.nebularis.lattice.studio.writes.Writes;
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
    private static final List<String> COMPILED = List.of("eligibility", "surface", "persistence", "mapping");
    /** The proposers a propose job may name, and the target each is recorded as (ADR-A138 decision 5). */
    private static final Map<String, Resource> PROPOSERS = Map.of(
        "sentence-forms", Cst.SentenceFormProposer, "language-model", Cst.LanguageModelProposer, "odrl", Cst.OdrlProposer,
        "mapping-language-model", Cst.MappingLanguageModelProposer, "rml", Cst.RmlImporter);

    private static final String TRIG = "application/trig";

    /** Reads only. Every write goes through {@code writes}, to the writer of its workspace. */
    private final StudioStore store;
    private final StudioOperations ops;
    private final Writes writes;
    private final JobBus bus;
    private final Clock clock;
    private final Supplier<UUID> ids;
    private final Path assets;
    /** The optional features the deployment turned on, from {@code LATTICE_STUDIO_FEATURES}. */
    private final Set<String> features;

    private final Authenticator auth;
    /** The principal of the request this thread serves, set and cleared by {@link #handle}. */
    private static final ThreadLocal<Principal> CURRENT = new ThreadLocal<>();

    /** Rebuilds the projections after a write that changes a source (ADR-A149 decision 14). */
    private final Refresher refresher;
    private static final Duration AWAIT_REFRESH = Duration.ofSeconds(10);
    private static final Duration REFRESH_TIMEOUT = Duration.ofSeconds(60);

    private final Documents documents = new Documents();
    private final StudioMcp mcp;

    public StudioApi(StudioStore store, StudioOperations ops, Writes writes, JobBus bus, Clock clock, Supplier<UUID> ids, Path assets) {
        this(store, ops, writes, bus, clock, ids, assets, Set.of());
    }

    public StudioApi(StudioStore store, StudioOperations ops, Writes writes, JobBus bus, Clock clock, Supplier<UUID> ids, Path assets,
                     Set<String> features) {
        this(store, ops, writes, bus, clock, ids, assets, features, LocalAuthenticator.developers());
    }

    public StudioApi(StudioStore store, StudioOperations ops, Writes writes, JobBus bus, Clock clock, Supplier<UUID> ids, Path assets,
                     Set<String> features, Authenticator auth) {
        this.features = Set.copyOf(features);
        this.store = store;
        this.ops = ops;
        this.auth = auth;
        // Every write carries the principal of the request it serves (PRI-54), which handle() has authenticated.
        this.writes = c -> {
            Principal p = CURRENT.get();
            Reply reply = writes.send(p == null ? c : c.by(p.name(), p.admin()));
            afterWrite(c, reply);
            return reply;
        };
        this.refresher = new Refresher(this::refreshOnce);
        this.bus = bus;
        this.clock = clock;
        this.ids = ids;
        this.assets = assets;
        this.mcp = new StudioMcp(store, ops, this.writes, clock, ids, assets, this::runTool);
    }

    /** Requests a refresh of every projection, as the service does when it starts. */
    public void refresh() {
        refresher.request();
    }

    /** Waits until no refresh is queued or running, which a test needs to read the projections a request left. */
    public boolean awaitProjections(Duration timeout) {
        return refresher.awaitIdle(timeout);
    }

    /**
     * Marks the projections stale after a command that changes one's source. A reply that a listing read next must show waits
     * for the refresh, a save or a job does not.
     */
    private void afterWrite(Command c, Reply reply) {
        // A refresh job's own submission and deletion name no workspace and change no projection's source.
        if (!reply.applied() || c.workspace() == null) {
            return;
        }
        switch (c.type()) {
            case CREATE, IMPORT, DELETE_WORKSPACE, SET_ACCESS, SET_DEPENDENCIES, PUBLISH, FENCE, RELEASE -> refresher.awaitFresh(AWAIT_REFRESH);
            case SAVE, SAVE_DOCUMENT, DELETE_DOCUMENT, SUBMIT_JOB, DELETE_JOB -> refresher.request();
            default -> { }
        }
    }

    /**
     * One refresh: submits a refresh job, which names no workspace, hands it to the worker, waits for it to finish and deletes it.
     * It throws when the job fails or the worker does not finish it in time.
     */
    private void refreshOnce() throws Exception {
        String job = UUID.randomUUID().toString();
        String jobIri = Graphs.job(job);
        Model description = org.apache.jena.rdf.model.ModelFactory.createDefaultModel();
        description.createResource(jobIri).addProperty(RDF.type, Cst.Job).addProperty(Cst.kind, Cst.Refresh).addProperty(Cst.status, Cst.Queued)
            .addProperty(Cst.submittedAt, description.createTypedLiteral(now().toString(), XSDDatatype.XSDdateTime));
        org.apache.jena.query.Dataset graphs = org.apache.jena.query.DatasetFactory.create();
        graphs.addNamedModel(jobIri, description);
        Reply sent = writes.send(Command.submitRefresh(job, graphs));
        if (!sent.applied()) {
            throw new IllegalStateException("the refresh job was refused: " + sent.message());
        }
        try {
            bus.publish(jobIri);
            Resource node = ResourceFactory.createResource(jobIri);
            long deadline = System.nanoTime() + REFRESH_TIMEOUT.toNanos();
            while (System.nanoTime() < deadline) {
                Model m = store.graph(jobIri);
                if (m.contains(node, Cst.status, Cst.Succeeded)) {
                    return;
                }
                if (m.contains(node, Cst.status, Cst.Failed)) {
                    throw new IllegalStateException("the refresh job failed: " + m.getProperty(node, Cst.failureMessage).getString());
                }
                Thread.sleep(25);
            }
            throw new java.util.concurrent.TimeoutException("the worker did not finish the refresh job in " + REFRESH_TIMEOUT.toSeconds() + " s");
        } finally {
            writes.send(Command.deleteRefresh(job));
        }
    }

    public ApiResponse handle(ApiRequest req) {
        try {
            // Health and the session's description answer anyone, so a browser can learn how to sign in.
            if (req.path().equals("/api/health") || req.path().equals("/api/session")) {
                return secure(req.path().equals("/api/session") ? session(req) : negotiate(req, route(req)));
            }
            Principal principal = auth.authenticate(req);
            if (principal == null) {
                return secure(ApiResponse.text(401, "sign in first").with("WWW-Authenticate", "Bearer realm=\"lattice-studio\""));
            }
            CURRENT.set(principal);
            try {
                if (req.path().equals("/mcp")) {
                    return secure(mcp.handle(req));
                }
                return secure(negotiate(req, route(req)));
            } finally {
                CURRENT.remove();
            }
        } catch (RuntimeException e) {
            LOG.error("{} {} failed", req.method(), req.path(), e);
            return secure(ApiResponse.text(500, "internal error"));
        }
    }

    /** How to sign in, from the authenticator's settings, and who the request is when it authenticates (ADR-A149 decision 8). */
    private ApiResponse session(ApiRequest req) {
        if (!req.method().equals("GET")) {
            return notAllowed("GET");
        }
        Map<String, Object> out = new java.util.LinkedHashMap<>(auth.settings());
        Principal p = auth.authenticate(req);
        if (p != null) {
            out.put("principal", p.name());
            out.put("admin", p.admin());
        }
        return new ApiResponse(200, Map.of("Content-Type", "application/json"), com.nimbusds.jose.util.JSONObjectUtils.toJSONString(out).getBytes(StandardCharsets.UTF_8));
    }

    /**
     * Rewrites a Turtle response as RDF/XML when the request prefers it. Every route answers in Turtle, so this is the one
     * place the syntax is chosen. An ETag names a graph's revision and is the same in either syntax.
     * ponytail: re-parses and re-writes per request, about 60 ms for the 640 KB vocabulary. Cache by ETag if it matters.
     */
    private static ApiResponse negotiate(ApiRequest req, ApiResponse r) {
        if (!r.headers().getOrDefault("Content-Type", "").startsWith("text/turtle")) {
            return r;
        }
        r = r.with("Vary", "Accept");
        if (!Turtle.prefersXml(req.header("accept"))) {
            return r;
        }
        byte[] xml;
        try {
            xml = Turtle.writeXml(Turtle.parse(r.body()));
        } catch (RuntimeException e) {
            // RDF/XML cannot write a predicate whose IRI does not end in an XML name, such as one ending in a digit.
            return ApiResponse.text(406, "this graph cannot be written as RDF/XML: " + e.getMessage()).with("Vary", "Accept");
        }
        return new ApiResponse(r.status(), r.with("Content-Type", ApiResponse.RDF_XML).headers(), xml);
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
        if (s.length == 1 && s[0].equals("features")) {
            return method.equals("GET") ? features() : notAllowed("GET");
        }
        if (s.length == 1 && s[0].equals("vocabulary")) {
            return method.equals("GET") ? vocabulary(req) : notAllowed("GET");
        }
        if (s.length == 1 && s[0].equals("publication-units")) {
            return method.equals("GET") ? asset("publication-units.ttl") : notAllowed("GET");
        }
        if (s[0].equals("registry") && s.length <= 2) {
            return method.equals("GET") ? registry(req, s.length == 1 ? null : s[1]) : notAllowed("GET");
        }
        if (s.length == 1 && s[0].equals("samples")) {
            return method.equals("GET") ? asset("samples.ttl") : notAllowed("GET");
        }
        if (s.length == 2 && s[0].equals("samples") && SAMPLE_ID.matcher(s[1]).matches()) {
            return method.equals("GET") ? asset("samples/" + s[1] + ".ttl") : notAllowed("GET");
        }
        if (s.length == 1 && s[0].equals("document-templates")) {
            return method.equals("GET") ? ApiResponse.turtle(200, Turtle.write(documents.templates())) : notAllowed("GET");
        }
        if (s.length == 1 && s[0].equals("document-samples")) {
            return method.equals("GET") ? ApiResponse.turtle(200, Turtle.write(documents.samples())) : notAllowed("GET");
        }
        if (s.length == 2 && s[0].equals("document-samples")) {
            if (!method.equals("GET")) {
                return notAllowed("GET");
            }
            byte[] sample = documents.sample(s[1]);
            return sample == null ? notFound() : xml(200, sample);
        }
        if (s.length == 1 && s[0].equals("workspaces")) {
            return switch (method) {
                case "GET" -> ApiResponse.turtle(200, Turtle.write(readableWorkspaces(store)));
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
            if (s.length == 3 && s[2].equals("access")) {
                return method.equals("POST") ? setAccess(req, ws) : notAllowed("POST");
            }
            if (s.length == 3 && s[2].equals("dependencies")) {
                return method.equals("PUT") ? putDependencies(req, ws) : notAllowed("PUT");
            }
            if (s.length == 3 && s[2].equals("export")) {
                return method.equals("GET") ? export(ws) : notAllowed("GET");
            }
            if (s.length == 4 && s[2].equals("graphs") && GRAPH_NAMES.contains(s[3])) {
                return switch (method) {
                    case "GET" -> getGraph(ws, s[3], query(req.query()).get("revision"));
                    case "PUT" -> putGraph(req, ws, s[3]);
                    default -> notAllowed("GET, PUT");
                };
            }
            if (s.length == 3 && s[2].equals("documents")) {
                return method.equals("GET") ? listDocuments(ws) : notAllowed("GET");
            }
            if (s.length == 4 && s[2].equals("documents") && Graphs.isId(s[3])) {
                return switch (method) {
                    case "GET" -> getDocument(req, ws, s[3]);
                    case "PUT" -> putDocument(req, ws, s[3]);
                    case "DELETE" -> deleteDocument(ws, s[3]);
                    default -> notAllowed("GET, PUT, DELETE");
                };
            }
            if (s.length == 5 && s[2].equals("documents") && Graphs.isId(s[3]) && s[4].equals("report")) {
                return method.equals("GET") ? documentReport(ws, s[3]) : notAllowed("GET");
            }
            if (s.length == 3 && s[2].equals("transforms")) {
                return method.equals("POST") ? transform(req, ws) : notAllowed("POST");
            }
            if (s.length == 3 && s[2].equals("publications")) {
                return method.equals("POST") ? publish(req, ws) : notAllowed("POST");
            }
            if (s.length == 3 && s[2].equals("imports")) {
                return method.equals("POST") ? fence(req, ws) : notAllowed("POST");
            }
            if (s.length == 4 && s[2].equals("imports") && Graphs.isDigest(s[3])) {
                return switch (method) {
                    case "GET" -> getImport(ws, s[3]);
                    case "DELETE" -> releaseImport(ws, s[3]);
                    default -> notAllowed("GET, DELETE");
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

    private ApiResponse features() {
        String json = features.stream().sorted().map(f -> "\"" + f + "\"").collect(Collectors.joining(","));
        return new ApiResponse(200, Map.of("Content-Type", "application/json"),
            ("{\"features\":[" + json + "]}").getBytes(StandardCharsets.UTF_8));
    }

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
        if (media(req).equals(TRIG)) {
            return importWorkspace(req);
        }
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
        String sample = query(req.query()).get("sample");
        if (sample != null && (!SAMPLE_ID.matcher(sample).matches() || read("samples/" + sample + ".ttl") == null)) {
            return ApiResponse.text(400, "sample names no staged sample");
        }
        Model baseline = parse(req);
        if (baseline == null) {
            return ApiResponse.text(400, "the body does not parse as its Content-Type");
        }
        List<String> strangers = Parts.strangers(baseline, "baseline", 5);
        if (!strangers.isEmpty()) {
            return ApiResponse.text(422, "the baseline holds terms of another part: " + String.join(", ", strangers));
        }
        String id = ids.get().toString();
        Instant now = now();
        Reply reply = writes.send(Command.create(id, label, now, sample, baseline));
        if (!reply.applied()) {
            return refusal(reply);
        }
        Workspace ws = Workspace.created(id, label, now, sample, CURRENT.get() == null ? null : CURRENT.get().name());
        return ApiResponse.turtle(201, Turtle.write(ws.toModel())).with("Location", "/api/workspaces/" + id);
    }

    /** A workspace exported by {@link #export}, recreated under a new id. Its jobs are not exported, so none are imported. */
    private ApiResponse importWorkspace(ApiRequest req) {
        if (req.body() != null && req.body().length > MAX_BODY_BYTES) {
            return tooLarge();
        }
        String label;
        try {
            label = req.header("slug") == null ? null : slug(req.header("slug"));
        } catch (IllegalArgumentException e) {
            return ApiResponse.text(400, "Slug is not percent-encoded UTF-8");
        }
        org.apache.jena.query.Dataset graphs;
        try {
            graphs = Turtle.parseTrig(req.body() == null ? new byte[0] : req.body());
        } catch (RiotException e) {
            return ApiResponse.text(400, "the body does not parse as TriG");
        }
        String id = ids.get().toString();
        ImportedWorkspace imported = ImportedWorkspace.of(graphs, id);
        if (imported.problem() != null) {
            return ApiResponse.text(422, imported.problem());
        }
        String name = label != null ? label : imported.label();
        Reply reply = writes.send(Command.importing(id, now(), name, imported.graphs()));
        if (!reply.applied()) {
            return reply.status() == 400 ? ApiResponse.text(422, reply.message()) : refusal(reply);
        }
        Workspace ws = load(id);
        return ApiResponse.turtle(201, Turtle.write(ws.toModel())).with("Location", "/api/workspaces/" + id);
    }

    /** Every graph of a workspace but its jobs, as TriG, to save to a file or to import elsewhere. */
    private ApiResponse export(String id) {
        Workspace ws = load(id);
        if (ws == null) {
            return notFound();
        }
        org.apache.jena.query.Dataset out = org.apache.jena.query.DatasetFactory.create();
        // Each graph is named by its aggregate's root, so an export does not depend on how the store names its graphs.
        out.addNamedModel(Graphs.workspace(id), ws.toModel());
        for (String name : GRAPH_NAMES) {
            add(out, Graphs.partRoot(id, name), Graphs.config(id, name));
        }
        for (String doc : ws.documents().keySet()) {
            add(out, Graphs.document(id, doc), Graphs.documentGraph(id, doc));
        }
        String file = ws.label().replaceAll("[^A-Za-z0-9._-]+", "-").replaceAll("^-+|-+$", "");
        return new ApiResponse(200, new LinkedHashMap<>(Map.of("Content-Type", TRIG + "; charset=utf-8",
            "Content-Disposition", "attachment; filename=\"" + (file.isEmpty() ? "workspace" : file) + ".trig\"")), Turtle.writeTrig(out));
    }

    private void add(org.apache.jena.query.Dataset out, String name, String graph) {
        Model m = store.graph(graph);
        if (!m.isEmpty()) {
            out.addNamedModel(name, m);
        }
    }

    private ApiResponse describe(String id) {
        Workspace ws = load(id);
        return ws == null ? notFound() : ApiResponse.turtle(200, Turtle.write(ws.toModel()));
    }

    /** Deletes the workspace's graphs and its jobs. */
    private ApiResponse deleteWorkspace(String id) {
        Reply reply = writes.send(Command.deleteWorkspace(id));
        return reply.applied() ? ApiResponse.empty(204) : refusal(reply);
    }

    /** The part as saved, or as it was at {@code revision}, rebuilt from the patch log, with that revision as its ETag. */
    private ApiResponse getGraph(String id, String name, String revision) {
        Workspace ws = load(id);
        if (ws == null) {
            return notFound();
        }
        long current = ws.revision(name);
        long at = current;
        if (revision != null) {
            try {
                at = Long.parseLong(revision);
            } catch (NumberFormatException e) {
                return ApiResponse.text(400, "revision is a whole number");
            }
            if (at < 1 || at > current) {
                return notFound();
            }
        }
        Model graph = at == current ? store.graph(Graphs.config(id, name))
            : ops.asOf(store, Family.PART, Graphs.partRoot(id, name), current, at);
        return ApiResponse.turtle(200, Turtle.write(graph)).with("ETag", etag(at));
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
        Model graph = parse(req);
        if (graph == null) {
            return ApiResponse.text(400, "the body does not parse as its Content-Type");
        }
        List<String> strangers = Parts.strangers(graph, name, 5);
        if (!strangers.isEmpty()) {
            return ApiResponse.text(422, "the graph holds terms of another part: " + String.join(", ", strangers));
        }
        Long expect = revisionOf(ifMatch);
        Reply reply = expect == null ? null : writes.send(Command.save(id, name, expect, now(), graph));
        if (reply == null || reply.status() == 412) {
            long current = reply == null ? load(id).revision(name) : reply.revision();
            return ApiResponse.text(412, "If-Match is not the current revision").with("ETag", etag(current));
        }
        return reply.applied() ? ApiResponse.empty(204).with("ETag", etag(reply.revision())) : refusal(reply);
    }

    /** The revision an If-Match of ours names, or null for any other value. */
    private static Long revisionOf(String ifMatch) {
        String v = ifMatch.trim();
        if (v.length() < 3 || v.charAt(0) != '"' || v.charAt(v.length() - 1) != '"') {
            return null;
        }
        try {
            long n = Long.parseLong(v.substring(1, v.length() - 1));
            return n < 0 ? null : n;
        } catch (NumberFormatException e) {
            return null;
        }
    }

    /** A writer's refusal as the HTTP answer to the request that caused it. */
    private static ApiResponse refusal(Reply reply) {
        return switch (reply.status()) {
            case 403 -> ApiResponse.text(403, reply.message());
            case 404 -> notFound();
            case 503 -> ApiResponse.text(503, reply.message());
            default -> ApiResponse.text(400, reply.message());
        };
    }

    // --- documents ---------------------------------------------------------------------------

    private ApiResponse listDocuments(String id) {
        Workspace ws = load(id);
        if (ws == null) {
            return notFound();
        }
        Model description = ws.toModel();
        Model out = org.apache.jena.rdf.model.ModelFactory.createDefaultModel();
        description.listResourcesWithProperty(RDF.type, Cst.Document).forEachRemaining(d -> out.add(d.listProperties()));
        return ApiResponse.turtle(200, Turtle.write(out));
    }

    /** The markup when the request prefers XML to Turtle, otherwise the document's graph as RDF. */
    private ApiResponse getDocument(ApiRequest req, String id, String doc) {
        Workspace ws = load(id);
        if (ws == null || !ws.documents().containsKey(doc)) {
            return notFound();
        }
        Model graph = store.graph(Graphs.documentGraph(id, doc));
        String etag = etag(ws.documentRevision(doc));
        if (Turtle.prefers(req.header("accept"), "application/xml")) {
            org.apache.jena.rdf.model.Statement markup = graph.createResource(Graphs.documentNode(doc)).getProperty(Cst.markup);
            return markup == null ? notFound() : xml(200, markup.getString().getBytes(StandardCharsets.UTF_8)).with("ETag", etag).with("Vary", "Accept");
        }
        return ApiResponse.turtle(200, Turtle.write(graph)).with("ETag", etag);
    }

    /** The report on the document as saved, computed on each request, with the document's revision as its ETag. */
    private ApiResponse documentReport(String id, String doc) {
        Workspace ws = load(id);
        if (ws == null || !ws.documents().containsKey(doc)) {
            return notFound();
        }
        Model graph = store.graph(Graphs.documentGraph(id, doc));
        org.apache.jena.rdf.model.Statement markup = graph.createResource(Graphs.documentNode(doc)).getProperty(Cst.markup);
        if (markup == null) {
            return notFound();
        }
        return ApiResponse.turtle(200, Turtle.write(documents.report(doc, markup.getString(), graph))).with("ETag", etag(ws.documentRevision(doc)));
    }

    private ApiResponse putDocument(ApiRequest req, String id, String doc) {
        Workspace ws = load(id);
        if (ws == null) {
            return notFound();
        }
        if (!media(req).equals("application/xml")) {
            return ApiResponse.text(415, "Content-Type must be application/xml");
        }
        if (req.body() != null && req.body().length > MAX_BODY_BYTES) {
            return tooLarge();
        }
        String ifMatch = req.header("if-match");
        if (ifMatch == null) {
            return ApiResponse.text(428, "If-Match is required");
        }
        Long expect = revisionOf(ifMatch);
        if (expect == null) {
            return ApiResponse.text(412, "If-Match is not the current revision").with("ETag", etag(ws.documentRevision(doc)));
        }
        Documents.Read read = documents.read(req.body() == null ? new byte[0] : req.body(), doc, expect + 1);
        if (read.problem() != null) {
            return ApiResponse.text(read.status(), read.problem());
        }
        Reply reply = writes.send(Command.saveDocument(id, doc, expect, now(), read.title(), read.template(), read.graph()));
        if (reply.status() == 412) {
            return ApiResponse.text(412, "If-Match is not the current revision").with("ETag", etag(reply.revision()));
        }
        return reply.applied() ? ApiResponse.empty(204).with("ETag", etag(reply.revision())) : refusal(reply);
    }

    private ApiResponse deleteDocument(String id, String doc) {
        Workspace ws = load(id);
        if (ws == null || !ws.documents().containsKey(doc)) {
            return notFound();
        }
        Reply reply = writes.send(Command.deleteDocument(id, doc));
        return reply.applied() ? ApiResponse.empty(204) : refusal(reply);
    }

    private static ApiResponse xml(int status, byte[] body) {
        return new ApiResponse(status, new LinkedHashMap<>(Map.of("Content-Type", "application/xml; charset=utf-8")), body);
    }

    // --- jobs ------------------------------------------------------------------------------

    private ApiResponse submitJob(ApiRequest req, String id) {
        Map<String, String> query = query(req.query());
        String kind = query.get("kind");
        String target = query.get("target");
        if ("analyse".equals(kind)) {
            return submitAnalysis(id, target);
        }
        if ("publish".equals(kind)) {
            return submitPublish(id, target, query.get("unit"), query.get("graph"));
        }
        if ("propose".equals(kind) && "odrl".equals(target) && !features.contains("odrl")) {
            return notFound();
        }
        if (!("validate".equals(kind) && TARGETS.contains(target)) && !("compile".equals(kind) && COMPILED.contains(target))
            && !("assemble".equals(kind) && "assembly".equals(target)) && !("fence".equals(kind) && "import".equals(target))
            && !("propose".equals(kind) && PROPOSERS.containsKey(target))
            && !("dry-run".equals(kind) && ("meaning".equals(target) || "mapping".equals(target)))) {
            return ApiResponse.text(400, "kind must be validate, with target one of " + TARGETS + ", compile, with target one of " + COMPILED
                + ", assemble, with target assembly, propose, with target one of " + PROPOSERS.keySet()
                + ", dry-run, with target meaning or mapping, fence, with target import, or analyse, with target a document");
        }
        Workspace ws = load(id);
        if (ws == null) {
            return notFound();
        }
        String fromVersion = "compile".equals(kind) ? query.get("version") : null;
        Model config;
        if (fromVersion != null) {
            // A published version is compiled as it stands, so the registry's content is the input (ADR-A149 decision 10).
            config = versionContent(fromVersion);
            if (config.isEmpty()) {
                return ApiResponse.text(404, "the registry holds no such version");
            }
        } else {
            ApiResponse bad = checkBody(req);
            if (bad != null) {
                return bad;
            }
            config = parse(req);
            if (config == null) {
                return ApiResponse.text(400, "the body does not parse as its Content-Type");
            }
        }
        if ("odrl".equals(target) || "rml".equals(target) || ("dry-run".equals(kind) && "mapping".equals(target))) {
            // Each component validates what it receives (PRI-75, STD-298). A mapping's dry run reads its sample source from one.
            List<Resource> documents = config.listSubjectsWithProperty(RDF.type, Cst.ImportDocument).toList();
            if (documents.size() != 1 || !documents.get(0).hasProperty(Cst.documentContent)
                || !documents.get(0).hasProperty(Cst.documentMediaType)) {
                return ApiResponse.text(422, "an odrl import and a mapping's dry run each need exactly one cst:ImportDocument with a cst:documentContent and a cst:documentMediaType");
            }
        }
        if ("mapping-language-model".equals(target)) {
            // A proposal reads one source vocabulary and at most one sample source, each with its content and media type.
            List<Resource> documents = config.listSubjectsWithProperty(RDF.type, Cst.ImportDocument).toList();
            long sources = documents.stream().filter(d -> d.hasProperty(Cst.documentRole, Cst.SourceVocabulary)).count();
            long samples = documents.stream().filter(d -> d.hasProperty(Cst.documentRole, Cst.SampleSource)).count();
            if (sources != 1 || samples > 1 || documents.size() != sources + samples
                || documents.stream().anyMatch(d -> !d.hasProperty(Cst.documentContent) || !d.hasProperty(Cst.documentMediaType))) {
                return ApiResponse.text(422, "a mapping proposal needs one cst:ImportDocument of role cst:SourceVocabulary and at most one of role cst:SampleSource, each with a cst:documentContent and a cst:documentMediaType");
            }
        }
        if ("fence".equals(kind)) {
            Principal p = CURRENT.get();
            if (p != null && !ws.writableBy(p.name(), p.admin())) {
                return ApiResponse.text(403, p.name() + " may not import into this workspace, which is " + ws.mode());
            }
        }
        String job = ids.get().toString();
        String jobIri = Graphs.job(job);
        Model description = jobDescription(jobIri, id, ws, kind, target, Graphs.jobInput(job));
        if (fromVersion != null) {
            description.createResource(jobIri).addProperty(Cst.fromVersion, description.createResource(fromVersion));
        }
        return publishJob(id, job, description, config);
    }

    private ApiResponse publishJob(String id, String job, Model description, Model config) {
        String jobIri = Graphs.job(job);
        org.apache.jena.query.Dataset graphs = org.apache.jena.query.DatasetFactory.create();
        graphs.addNamedModel(jobIri, description);
        graphs.addNamedModel(Graphs.jobInput(job), config);
        Reply reply = writes.send(Command.submitJob(id, job, graphs));
        if (!reply.applied()) {
            return refusal(reply);
        }
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
            org.apache.jena.query.Dataset failed = org.apache.jena.query.DatasetFactory.create();
            failed.addNamedModel(jobIri, description);
            writes.send(Command.jobUpdate(id, job, failed));
        }
        return ApiResponse.turtle(202, Turtle.write(description)).with("Location", "/api/jobs/" + job);
    }

    /** An analysis reads the document as saved, so the request has no body, and the job's input is the document's graph. */
    private ApiResponse submitAnalysis(String id, String doc) {
        Workspace ws = load(id);
        if (ws == null || doc == null || !Graphs.isId(doc) || !ws.documents().containsKey(doc)) {
            return notFound();
        }
        Model input = store.graph(Graphs.documentGraph(id, doc));
        String job = ids.get().toString();
        String jobIri = Graphs.job(job);
        Model description = jobDescription(jobIri, id, ws, "analyse", null, Graphs.jobInput(job));
        description.createResource(jobIri).addProperty(Cst.target, description.createResource(Graphs.document(id, doc)));
        return publishJob(id, job, description, input);
    }

    /**
     * A publish job versions one unit of a saved part, so its input is the part as stored and the request has no body.
     * Only a principal who may write the workspace submits one.
     */
    private ApiResponse submitPublish(String id, String target, String unit, String importDigest) {
        boolean fromImport = "import".equals(target);
        if (!(Workspace.CONFIGS.contains(target) || (fromImport && Graphs.isDigest(importDigest))) || !Graphs.isUnitIri(unit)) {
            return ApiResponse.text(400, "kind publish needs a target that is one of " + Workspace.CONFIGS
                + ", or import with the graph's digest, and a unit that is an absolute http, https or urn IRI the studio did not mint");
        }
        Workspace ws = load(id);
        if (ws == null) {
            return notFound();
        }
        Principal p = CURRENT.get();
        if (p != null && !ws.writableBy(p.name(), p.admin())) {
            return ApiResponse.text(403, p.name() + " may not publish from this workspace, which is " + ws.mode());
        }
        if (fromImport && !ws.imports().containsKey(Graphs.importGraph(importDigest))) {
            return notFound();
        }
        String graph = fromImport ? Graphs.importedGraph(importDigest) : Graphs.config(id, target);
        String job = ids.get().toString();
        Model description = jobDescription(Graphs.job(job), id, ws, "publish", target, Graphs.jobInput(job));
        description.createResource(Graphs.job(job)).addProperty(Cst.unit, description.createResource(unit));
        return publishJob(id, job, description, store.graph(graph));
    }

    /**
     * Puts the version a finished publish job made into the registry. The writer decides whether it is new, current
     * already, or lost a race, and answers 201 with the lineage's registry graph, or 200 when it was current already.
     */
    private ApiResponse publish(ApiRequest req, String id) {
        String job = query(req.query()).get("job");
        if (load(id) == null || job == null || !Graphs.isId(job)) {
            return notFound();
        }
        Resource node = ResourceFactory.createResource(Graphs.job(job));
        Model m = store.graph(Graphs.job(job));
        if (!m.contains(node, Cst.workspace, ResourceFactory.createResource(Graphs.workspace(id)))) {
            return notFound();
        }
        Resource lineage = uri(m, node, Cst.lineage);
        Resource version = uri(m, node, Cst.version);
        String content = null;
        for (Resource artefact : m.listObjectsOfProperty(node, Cst.artefact).toList().stream().filter(o -> o.isResource()).map(o -> o.asResource()).toList()) {
            if (artefact.hasLiteral(Cst.path, "version.nt") && artefact.hasProperty(Cst.content)) {
                content = artefact.getProperty(Cst.content).getString();
            }
        }
        if (!m.contains(node, Cst.kind, Cst.Publish) || !m.contains(node, Cst.status, Cst.Succeeded) || lineage == null
            || version == null || !m.contains(node, Cst.digest) || content == null) {
            return ApiResponse.text(409, "the job is not a finished publish job with a version to publish");
        }
        Model graph;
        try {
            graph = Turtle.parse(content.getBytes(StandardCharsets.UTF_8), Lang.NTRIPLES);
        } catch (RiotException e) {
            return ApiResponse.text(422, "the job's version.nt does not parse as N-Triples");
        }
        Reply reply = writes.send(Command.publish(id, lineage.getURI(), version.getURI(), graph));
        if (!reply.applied()) {
            return refusal(reply);
        }
        byte[] registry = Turtle.write(store.graph(Graphs.lineage(lineage.getURI())));
        return ApiResponse.turtle("current".equals(reply.message()) ? 200 : 201, registry)
            .with("Location", "/api/registry/lineage?iri=" + java.net.URLEncoder.encode(lineage.getURI(), StandardCharsets.UTF_8));
    }

    /**
     * Puts the import a finished fence job read into the store, once by its digest, and into this workspace's holdings.
     * Answers 201 with the workspace's description.
     */
    private ApiResponse fence(ApiRequest req, String id) {
        Map<String, String> query = query(req.query());
        String job = query.get("job");
        String label = query.get("label") == null ? "Import" : query.get("label").trim();
        if (load(id) == null || job == null || !Graphs.isId(job)) {
            return notFound();
        }
        if (label.isEmpty() || label.length() > 200) {
            return ApiResponse.text(400, "label is 1 to 200 characters");
        }
        Resource node = ResourceFactory.createResource(Graphs.job(job));
        Model m = store.graph(Graphs.job(job));
        if (!m.contains(node, Cst.workspace, ResourceFactory.createResource(Graphs.workspace(id)))) {
            return notFound();
        }
        String content = null;
        for (Resource artefact : m.listObjectsOfProperty(node, Cst.artefact).toList().stream().filter(o -> o.isResource()).map(o -> o.asResource()).toList()) {
            if (artefact.hasLiteral(Cst.path, "import.nt") && artefact.hasProperty(Cst.content)) {
                content = artefact.getProperty(Cst.content).getString();
            }
        }
        var digest = m.getProperty(node, Cst.digest);
        if (!m.contains(node, Cst.kind, Cst.Fence) || !m.contains(node, Cst.status, Cst.Succeeded) || digest == null || content == null) {
            return ApiResponse.text(409, "the job is not a finished fence job with an import to hold");
        }
        Model graph;
        try {
            graph = Turtle.parse(content.getBytes(StandardCharsets.UTF_8), Lang.NTRIPLES);
        } catch (RiotException e) {
            return ApiResponse.text(422, "the job's import.nt does not parse as N-Triples");
        }
        Reply reply = writes.send(Command.fence(id, digest.getString(), label, graph));
        Workspace held = reply.applied() ? load(id) : null;
        return held == null ? refusal(reply) : ApiResponse.turtle(201, Turtle.write(held.toModel()))
            .with("Location", "/api/workspaces/" + id + "/imports/" + digest.getString());
    }

    private ApiResponse getImport(String id, String digest) {
        Workspace ws = load(id);
        if (ws == null || !ws.imports().containsKey(Graphs.importGraph(digest))) {
            return notFound();
        }
        return ApiResponse.turtle(200, Turtle.write(store.graph(Graphs.importedGraph(digest))));
    }

    /** The workspace stops holding the import. The graph stays, since other workspaces may hold it. */
    private ApiResponse releaseImport(String id, String digest) {
        Workspace ws = load(id);
        if (ws == null || !ws.imports().containsKey(Graphs.importGraph(digest))) {
            return notFound();
        }
        Reply reply = writes.send(Command.release(id, digest));
        return reply.applied() ? ApiResponse.empty(204) : refusal(reply);
    }

    private static Resource uri(Model m, Resource s, org.apache.jena.rdf.model.Property p) {
        var o = m.getProperty(s, p);
        return o != null && o.getObject().isURIResource() ? o.getResource() : null;
    }

    private Model jobDescription(String jobIri, String ws, Workspace workspace, String kind, String target, String input) {
        Model m = org.apache.jena.rdf.model.ModelFactory.createDefaultModel();
        Resource job = m.createResource(jobIri);
        job.addProperty(RDF.type, Cst.Job);
        job.addProperty(Cst.kind, switch (kind) {
            case "validate" -> Cst.Validate;
            case "compile" -> Cst.Compile;
            case "publish" -> Cst.Publish;
            case "fence" -> Cst.Fence;
            case "assemble" -> Cst.Assemble;
            case "propose" -> Cst.Propose;
            case "dry-run" -> Cst.DryRunJob;
            case "tool" -> Cst.ToolCall;
            default -> Cst.Analyse;
        });
        if (target != null) {
            job.addProperty(Cst.target, kind.equals("propose") ? PROPOSERS.get(target) : Cst.target(target));
        }
        job.addProperty(Cst.workspace, m.createResource(Graphs.workspace(ws)));
        job.addProperty(Cst.configGraph, m.createResource(input));
        job.addProperty(Cst.baselineGraph, m.createResource(workspace.baselineGraph()));
        if (List.of("validate", "compile", "dry-run").contains(kind)) {
            // A job reads the workspace's other parts as context, and validates only its target (ADR-A149).
            for (String part : Workspace.CONFIGS) {
                if (!part.equals(target)) {
                    job.addProperty(Cst.contextGraph, m.createResource(Graphs.config(ws, part)));
                }
            }
        }
        if (kind.equals("publish")) {
            // A publish job's input is its saved part, and the other parts tell the worker what the workspace has not published.
            for (String part : Workspace.CONFIGS) {
                if (!part.equals(target)) {
                    job.addProperty(Cst.contextGraph, m.createResource(Graphs.config(ws, part)));
                }
            }
        }
        if (List.of("validate", "compile", "dry-run", "publish").contains(kind)) {
            for (String dependency : workspace.dependencies()) {
                String graph = dependencyGraph(dependency);
                if (graph != null) {
                    job.addProperty(Cst.contextGraph, m.createResource(graph));
                }
            }
            workspace.imports().keySet().forEach(root -> job.addProperty(Cst.contextGraph, m.createResource(Graphs.importedGraphOf(root))));
        }
        job.addProperty(Cst.status, Cst.Queued);
        job.addProperty(Cst.submittedAt, m.createTypedLiteral(now().toString(), XSDDatatype.XSDdateTime));
        return m;
    }

    /**
     * Runs one of MORK's proposal tools in the worker for the MCP server, as a tool job of the workspace whose input is
     * {@code input}, and waits for it: the finished job graph, or null when the worker did not finish it within two
     * minutes. The job stays in the store as any job does, and is swept with them.
     */
    Model runTool(String ws, Model input) {
        Workspace workspace = load(ws);
        if (workspace == null) {
            return null;
        }
        String job = ids.get().toString();
        String jobIri = Graphs.job(job);
        ApiResponse published = publishJob(ws, job, jobDescription(jobIri, ws, workspace, "tool", null, Graphs.jobInput(job)), input);
        if (published.status() != 202) {
            return null;
        }
        Resource j = ResourceFactory.createResource(jobIri);
        for (int n = 0; n < 1200; n++) {
            Model m = store.graph(jobIri);
            if (m.contains(j, Cst.status, Cst.Succeeded) || m.contains(j, Cst.status, Cst.Failed)) {
                return m;
            }
            try {
                Thread.sleep(100);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return null;
            }
        }
        return null;
    }

    /** How long a transform waits for the transforms worker. A warm run takes milliseconds (ADR-A148). */
    private static final java.time.Duration TRANSFORM_TIMEOUT = java.time.Duration.ofSeconds(30);
    private static final List<String> SAMPLE_TYPES = List.of("application/xml", "text/xml", "application/json");

    /**
     * Runs the transforms a compile job of the mapping part wrote over a sample source in XML or JSON, through the
     * transforms worker, and answers with its reply. Nothing is stored, since a run is derived and can be repeated.
     */
    private ApiResponse transform(ApiRequest req, String id) {
        String job = query(req.query()).get("job");
        if (load(id) == null || job == null || !Graphs.isId(job)) {
            return notFound();
        }
        Resource compile = ResourceFactory.createResource(Graphs.job(job));
        Model m = store.graph(Graphs.job(job));
        if (!m.contains(compile, Cst.workspace, ResourceFactory.createResource(Graphs.workspace(id)))) {
            return notFound();
        }
        if (!m.contains(compile, Cst.kind, Cst.Compile) || !m.contains(compile, Cst.target, Cst.target("mapping"))
            || !m.contains(compile, Cst.status, Cst.Succeeded)) {
            return ApiResponse.text(409, "the job is not a finished compilation of the mapping part");
        }
        String media = media(req);
        if (!SAMPLE_TYPES.contains(media)) {
            return ApiResponse.text(415, "Content-Type must be one of " + SAMPLE_TYPES);
        }
        byte[] sample = req.body() == null ? new byte[0] : req.body();
        if (sample.length > MAX_BODY_BYTES) {
            return tooLarge();
        }
        String run = ids.get().toString();
        byte[] reply;
        try {
            reply = bus.transform(run, Graphs.job(job), media, sample, TRANSFORM_TIMEOUT);
        } catch (Exception e) {
            if (e instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            LOG.error("asking for a transform of {} failed", job, e);
            return ApiResponse.text(503, "the transform could not be handed to the transforms worker");
        }
        if (reply == null) {
            return ApiResponse.text(504, "no transforms worker answered within " + TRANSFORM_TIMEOUT.toSeconds() + " s");
        }
        // Each component validates what it receives (PRI-75): the reply is Turtle describing this run.
        Model answer;
        try {
            answer = Turtle.parse(reply, Lang.TURTLE);
        } catch (RiotException e) {
            answer = null;
        }
        if (answer == null || !answer.contains(ResourceFactory.createResource("urn:lattice:studio:transform:" + run), RDF.type, Cst.Transform)) {
            return ApiResponse.text(502, "the transforms worker's reply does not describe the run");
        }
        return ApiResponse.turtle(200, Turtle.write(answer));
    }

    private ApiResponse listJobs(String id) {
        if (load(id) == null) {
            return notFound();
        }
        return ApiResponse.turtle(200, Turtle.write(store.compileJobs(Graphs.workspace(id))));
    }

    /**
     * The registry, which every signed-in principal reads (ADR-A149 decision 4): its lineages with their current versions,
     * one lineage's graph by {@code iri}, or one version's content by {@code iri}.
     */
    private ApiResponse registry(ApiRequest req, String what) {
        if (what == null) {
            return ApiResponse.turtle(200, Turtle.write(store.registry()));
        }
        String iri = query(req.query()).get("iri");
        if (what.equals("bundle")) {
            return bundle(iri);
        }
        if (what.equals("holders")) {
            return holders(iri);
        }
        if (what.equals("terms")) {
            String text = query(req.query()).get("q");
            return text == null || text.isBlank() ? ApiResponse.text(400, "q is the text a concept's label contains")
                : ApiResponse.turtle(200, Turtle.write(store.terms(text.strip())));
        }
        Model m;
        if (what.equals("lineage") && Graphs.isUnitIri(iri)) {
            m = store.graph(Graphs.lineage(iri));
        } else if (what.equals("version") && iri != null && iri.matches(".+/rev/1-[0-9a-f]{16}")) {
            String lineage = iri.substring(0, iri.lastIndexOf("/rev/1-"));
            m = Graphs.isUnitIri(lineage) ? store.graph(Graphs.version(lineage, iri.substring(iri.length() - 16))) : org.apache.jena.rdf.model.ModelFactory.createDefaultModel();
        } else {
            return notFound();
        }
        return m.isEmpty() ? notFound() : ApiResponse.turtle(200, Turtle.write(m));
    }

    /**
     * The workspaces that follow a lineage, pin one of its versions or a version, or hold an import, with their summaries,
     * from the holders projection. A workspace the request's principal may not read is left out.
     */
    private ApiResponse holders(String iri) {
        if (iri == null || !(Graphs.isImportGraph(iri) || Graphs.isUnitIri(iri.replaceFirst("/rev/1-[0-9a-f]{16}$", "")))) {
            return ApiResponse.text(400, "iri is a lineage, a version or an import's root");
        }
        Model edges = store.holders(iri);
        Model summaries = store.summaries();
        Model out = readable(edges.listSubjects().toList().stream()
            .map(w -> summaries.getResource(w.getURI())).filter(w -> w.hasProperty(RDF.type, Cst.Workspace)).toList());
        edges.listStatements().forEachRemaining(st -> {
            if (out.containsResource(st.getSubject())) {
                out.add(st);
            }
        });
        return ApiResponse.turtle(200, Turtle.write(out));
    }

    private static final int BUNDLE_LIMIT = 1000;

    /** A version's content from the registry, empty when {@code iri} is not a version it holds. */
    private Model versionContent(String iri) {
        var v = iri == null ? null : VERSION_IRI.matcher(iri);
        return v != null && v.matches() && Graphs.isUnitIri(v.group(1))
            ? store.graph(Graphs.version(v.group(1), v.group(2))) : org.apache.jena.rdf.model.ModelFactory.createDefaultModel();
    }

    /**
     * A version and, transitively, every version it pins, each in a graph named by its own IRI so that the file stands
     * apart from this studio (ADR-A149 decision 10). A pin the registry does not hold, or that names a member of a
     * version, is left out.
     */
    private ApiResponse bundle(String iri) {
        org.apache.jena.query.Dataset out = org.apache.jena.query.DatasetFactory.create();
        java.util.ArrayDeque<String> queue = new java.util.ArrayDeque<>();
        queue.add(iri == null ? "" : iri);
        while (!queue.isEmpty()) {
            String next = queue.poll();
            if (out.containsNamedModel(next)) {
                continue;
            }
            Model content = versionContent(next);
            if (content.isEmpty()) {
                if (out.isEmpty()) {
                    return notFound();
                }
                continue;
            }
            if (out.asDatasetGraph().size() >= BUNDLE_LIMIT) {
                return ApiResponse.text(422, "the bundle would hold more than " + BUNDLE_LIMIT + " versions");
            }
            out.addNamedModel(next, content);
            content.listObjectsOfProperty(content.createResource(next), Cst.pins).forEachRemaining(o -> {
                if (o.isURIResource()) {
                    queue.add(o.asResource().getURI());
                }
            });
        }
        return new ApiResponse(200, new LinkedHashMap<>(Map.of("Content-Type", TRIG + "; charset=utf-8")), Turtle.writeTrig(out));
    }

    private ApiResponse getJob(String job) {
        Model m = store.graph(Graphs.job(job));
        org.apache.jena.rdf.model.Statement ws = m.createResource(Graphs.job(job)).getProperty(Cst.workspace);
        boolean visible = ws != null && ws.getObject().isURIResource()
            && load(ws.getResource().getURI().substring(Graphs.WORKSPACE_PREFIX.length())) != null;
        return visible ? ApiResponse.turtle(200, Turtle.write(m)) : notFound();
    }

    private ApiResponse deleteJob(String job) {
        Model m = store.graph(Graphs.job(job));
        org.apache.jena.rdf.model.Statement ws = m.createResource(Graphs.job(job)).getProperty(Cst.workspace);
        if (ws == null || !ws.getObject().isURIResource()) {
            return notFound();
        }
        String id = ws.getResource().getURI().substring(Graphs.WORKSPACE_PREFIX.length());
        Reply reply = writes.send(Command.deleteJob(id, job));
        return reply.applied() ? ApiResponse.empty(204) : refusal(reply);
    }

    // --- helpers ---------------------------------------------------------------------------

    /** The workspace, or null when it does not exist or the request's principal may not read it (ADR-A149 decision 9). */
    private Workspace load(String id) {
        Workspace ws = ops.workspace(store, id);
        return ws != null && readable(ws) ? ws : null;
    }

    static boolean readable(Workspace ws) {
        Principal p = CURRENT.get();
        return p == null || ws.readableBy(p.name(), p.admin());
    }

    /** The summary of each workspace the request's principal may read, from the summaries projection in one read. */
    static Model readableWorkspaces(StudioStore store) {
        Model all = store.summaries();
        return readable(all.listSubjectsWithProperty(RDF.type, Cst.Workspace).toList());
    }

    /** The statements about those of {@code workspaces}, nodes of a summaries model, that the request's principal may read. */
    private static Model readable(List<Resource> workspaces) {
        Principal p = CURRENT.get();
        Model out = org.apache.jena.rdf.model.ModelFactory.createDefaultModel();
        for (Resource w : workspaces) {
            var mode = w.getPropertyResourceValue(Cst.mode);
            var owner = w.getProperty(Cst.owner);
            if (p == null || Workspace.readable(mode == null ? Workspace.SHARED : Cst.modeName(mode), owner == null ? null : owner.getString(), p.name(), p.admin())) {
                out.add(w.listProperties());
                w.listProperties(Cst.document).forEachRemaining(d -> out.add(d.getResource().listProperties()));
                w.listProperties(Cst.holdsImport).forEachRemaining(h -> out.add(h.getResource().listProperties()));
            }
        }
        return out;
    }

    /** Sets a workspace's mode, and its owner when an administrator names one, from {@code mode} and {@code owner}. */
    private ApiResponse setAccess(ApiRequest req, String id) {
        if (load(id) == null) {
            return notFound();
        }
        Map<String, String> q = query(req.query());
        String mode = q.get("mode");
        String owner = q.get("owner");
        if (mode == null || !Workspace.MODES.contains(mode) || (owner != null && !owner.matches("[^\\s]{1,200}"))) {
            return ApiResponse.text(400, "mode is one of " + Workspace.MODES + ", and owner, when given, a principal's name");
        }
        Reply reply = writes.send(Command.setAccess(id, mode, owner));
        return reply.applied() ? describe(id) : refusal(reply);
    }

    /** Replaces a workspace's dependencies with the {@code cst:dependsOn} triples of the body, each naming what the registry holds. */
    private ApiResponse putDependencies(ApiRequest req, String id) {
        if (load(id) == null) {
            return notFound();
        }
        ApiResponse bad = checkBody(req);
        if (bad != null) {
            return bad;
        }
        Model body = parse(req);
        if (body == null) {
            return ApiResponse.text(400, "the body does not parse as its Content-Type");
        }
        for (RDFNode o : body.listObjectsOfProperty(Cst.dependsOn).toList()) {
            if (o.isURIResource() && dependencyGraph(o.asResource().getURI()) == null && Graphs.isUnitIri(o.asResource().getURI().replaceFirst("/rev/1-[0-9a-f]{16}$", ""))) {
                return ApiResponse.text(422, "the registry holds nothing named " + o.asResource().getURI());
            }
        }
        Reply reply = writes.send(Command.setDependencies(id, body));
        return reply.applied() ? describe(id) : refusal(reply);
    }

    private static final java.util.regex.Pattern VERSION_IRI = java.util.regex.Pattern.compile("(.+)/rev/1-([0-9a-f]{16})");

    /**
     * The graph a dependency resolves to now, a pinned version's own or a followed lineage's current version's, or null
     * when the registry holds nothing for it.
     */
    private String dependencyGraph(String iri) {
        var version = VERSION_IRI.matcher(iri);
        if (version.matches()) {
            String graph = Graphs.version(version.group(1), version.group(2));
            return store.graph(graph).isEmpty() ? null : graph;
        }
        Model lineage = store.graph(Graphs.lineage(iri));
        var current = lineage.getProperty(lineage.createResource(iri), Cst.current);
        if (current == null || !current.getObject().isURIResource()) {
            return null;
        }
        var v = VERSION_IRI.matcher(current.getResource().getURI());
        return v.matches() && v.group(1).equals(iri) ? Graphs.version(iri, v.group(2)) : null;
    }

    private Instant now() {
        return clock.instant().truncatedTo(ChronoUnit.SECONDS);
    }

    private static String etag(long revision) {
        return "\"" + revision + "\"";
    }

    private static String media(ApiRequest req) {
        String type = req.header("content-type");
        return type == null ? "" : type.split(";", 2)[0].trim().toLowerCase(Locale.ROOT);
    }

    /** 415 for a content type other than Turtle or RDF/XML, 413 for a body over the limit, otherwise null. */
    private static ApiResponse checkBody(ApiRequest req) {
        String media = media(req);
        if (!media.equals("text/turtle") && !media.equals(Turtle.RDF_XML)) {
            return ApiResponse.text(415, "Content-Type must be text/turtle or application/rdf+xml");
        }
        if (req.body() != null && req.body().length > MAX_BODY_BYTES) {
            return tooLarge();
        }
        return null;
    }

    public static ApiResponse tooLarge() {
        return ApiResponse.text(413, "the body is over 5 MiB");
    }

    /** The body in the syntax its Content-Type names, which {@link #checkBody} has allowed, or null if it does not parse. */
    private static Model parse(ApiRequest req) {
        try {
            byte[] body = req.body() == null ? new byte[0] : req.body();
            return Turtle.parse(body, media(req).equals(Turtle.RDF_XML) ? Lang.RDFXML : Lang.TURTLE);
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
