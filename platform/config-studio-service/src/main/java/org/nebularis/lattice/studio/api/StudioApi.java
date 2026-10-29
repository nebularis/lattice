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
import java.util.Set;
import java.util.UUID;
import java.util.function.Supplier;
import java.util.regex.Pattern;
import java.util.stream.Collectors;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RiotException;
import org.apache.jena.vocabulary.RDF;
import org.nebularis.lattice.studio.jobs.JobBus;
import org.nebularis.lattice.studio.model.Parts;
import org.nebularis.lattice.studio.model.Workspace;
import org.nebularis.lattice.studio.authoring.Documents;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
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
    private static final List<String> COMPILED = List.of("eligibility", "surface", "persistence");
    /** The proposers a propose job may name, and the target each is recorded as (ADR-A138 decision 5). */
    private static final Map<String, Resource> PROPOSERS = Map.of(
        "sentence-forms", Cst.SentenceFormProposer, "language-model", Cst.LanguageModelProposer, "odrl", Cst.OdrlProposer);

    private static final String TRIG = "application/trig";

    /** Reads only. Every write goes through {@code writes}, to the writer of its workspace. */
    private final StudioStore store;
    private final Writes writes;
    private final JobBus bus;
    private final Clock clock;
    private final Supplier<UUID> ids;
    private final Path assets;
    /** The optional features the deployment turned on, from {@code LATTICE_STUDIO_FEATURES}. */
    private final Set<String> features;

    private final Documents documents = new Documents();
    private final StudioMcp mcp;

    public StudioApi(StudioStore store, Writes writes, JobBus bus, Clock clock, Supplier<UUID> ids, Path assets) {
        this(store, writes, bus, clock, ids, assets, Set.of());
    }

    public StudioApi(StudioStore store, Writes writes, JobBus bus, Clock clock, Supplier<UUID> ids, Path assets,
                     Set<String> features) {
        this.features = Set.copyOf(features);
        this.store = store;
        this.writes = writes;
        this.bus = bus;
        this.clock = clock;
        this.ids = ids;
        this.assets = assets;
        this.mcp = new StudioMcp(store, writes, clock, ids, assets);
    }

    public ApiResponse handle(ApiRequest req) {
        try {
            if (req.path().equals("/mcp")) {
                return secure(mcp.handle(req));
            }
            return secure(negotiate(req, route(req)));
        } catch (RuntimeException e) {
            LOG.error("{} {} failed", req.method(), req.path(), e);
            return secure(ApiResponse.text(500, "internal error"));
        }
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
            if (s.length == 3 && s[2].equals("export")) {
                return method.equals("GET") ? export(ws) : notAllowed("GET");
            }
            if (s.length == 4 && s[2].equals("graphs") && GRAPH_NAMES.contains(s[3])) {
                return switch (method) {
                    case "GET" -> getGraph(ws, s[3]);
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
        Workspace ws = Workspace.created(id, label, now, sample);
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
        out.addNamedModel(Graphs.workspace(id), ws.toModel());
        for (long n = 1; n <= ws.revision("baseline"); n++) {
            add(out, Graphs.baseline(id, n));
        }
        for (String name : TARGETS) {
            add(out, Graphs.config(id, name));
        }
        for (String doc : ws.documents().keySet()) {
            add(out, Graphs.document(id, doc));
        }
        String file = ws.label().replaceAll("[^A-Za-z0-9._-]+", "-").replaceAll("^-+|-+$", "");
        return new ApiResponse(200, new LinkedHashMap<>(Map.of("Content-Type", TRIG + "; charset=utf-8",
            "Content-Disposition", "attachment; filename=\"" + (file.isEmpty() ? "workspace" : file) + ".trig\"")), Turtle.writeTrig(out));
    }

    private void add(org.apache.jena.query.Dataset out, String graph) {
        Model m = store.graph(graph);
        if (!m.isEmpty()) {
            out.addNamedModel(graph, m);
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
            case 404 -> notFound();
            case 503 -> ApiResponse.text(503, reply.message());
            default -> ApiResponse.text(400, reply.message());
        };
    }

    // --- documents ---------------------------------------------------------------------------

    private ApiResponse listDocuments(String id) {
        if (load(id) == null) {
            return notFound();
        }
        Model description = store.graph(Graphs.workspace(id));
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
        Model graph = store.graph(Graphs.document(id, doc));
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
        Model graph = store.graph(Graphs.document(id, doc));
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
        if ("propose".equals(kind) && "odrl".equals(target) && !features.contains("odrl")) {
            return notFound();
        }
        if (!("validate".equals(kind) && TARGETS.contains(target)) && !("compile".equals(kind) && COMPILED.contains(target))
            && !("assemble".equals(kind) && "assembly".equals(target))
            && !("propose".equals(kind) && PROPOSERS.containsKey(target))
            && !("dry-run".equals(kind) && "meaning".equals(target))) {
            return ApiResponse.text(400, "kind must be validate, with target one of " + TARGETS + ", compile, with target one of " + COMPILED
                + ", assemble, with target assembly, propose, with target one of " + PROPOSERS.keySet()
                + ", dry-run, with target meaning, or analyse, with target a document");
        }
        Workspace ws = load(id);
        if (ws == null) {
            return notFound();
        }
        ApiResponse bad = checkBody(req);
        if (bad != null) {
            return bad;
        }
        Model config = parse(req);
        if (config == null) {
            return ApiResponse.text(400, "the body does not parse as its Content-Type");
        }
        if ("odrl".equals(target)) {
            // Each component validates what it receives (PRI-75, STD-279).
            List<Resource> documents = config.listSubjectsWithProperty(RDF.type, Cst.ImportDocument).toList();
            if (documents.size() != 1 || !documents.get(0).hasProperty(Cst.documentContent)
                || !documents.get(0).hasProperty(Cst.documentMediaType)) {
                return ApiResponse.text(422, "an odrl import needs exactly one cst:ImportDocument with a cst:documentContent and a cst:documentMediaType");
            }
        }
        String job = ids.get().toString();
        String jobIri = Graphs.job(job);
        Model description = jobDescription(jobIri, id, ws, kind, target, Graphs.jobInput(job));
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
        Model input = store.graph(Graphs.document(id, doc));
        String job = ids.get().toString();
        String jobIri = Graphs.job(job);
        Model description = jobDescription(jobIri, id, ws, "analyse", null, Graphs.jobInput(job));
        description.createResource(jobIri).addProperty(Cst.target, description.createResource(Graphs.document(id, doc)));
        return publishJob(id, job, description, input);
    }

    private Model jobDescription(String jobIri, String ws, Workspace workspace, String kind, String target, String input) {
        Model m = org.apache.jena.rdf.model.ModelFactory.createDefaultModel();
        Resource job = m.createResource(jobIri);
        job.addProperty(RDF.type, Cst.Job);
        job.addProperty(Cst.kind, switch (kind) {
            case "validate" -> Cst.Validate;
            case "compile" -> Cst.Compile;
            case "assemble" -> Cst.Assemble;
            case "propose" -> Cst.Propose;
            case "dry-run" -> Cst.DryRunJob;
            default -> Cst.Analyse;
        });
        if (target != null) {
            job.addProperty(Cst.target, kind.equals("propose") ? PROPOSERS.get(target) : Cst.target(target));
        }
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

    private Workspace load(String id) {
        return Workspace.from(id, store.graph(Graphs.workspace(id)));
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
