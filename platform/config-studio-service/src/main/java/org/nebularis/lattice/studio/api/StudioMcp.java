// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.api;

import java.io.IOException;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Supplier;
import java.util.regex.Pattern;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonArray;
import org.apache.jena.atlas.json.JsonNull;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.atlas.json.JsonParseException;
import org.apache.jena.atlas.json.JsonValue;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.ResourceFactory;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.vocabulary.RDF;
import org.apache.jena.vocabulary.RDFS;
import org.apache.jena.vocabulary.SKOS;
import org.nebularis.lattice.studio.model.Parts;
import org.nebularis.lattice.studio.model.Workspace;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.StudioStore;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.Reply;
import org.nebularis.lattice.studio.writes.Writes;

/**
 * The studio as a Model Context Protocol server, over the Streamable HTTP transport at {@code /mcp}
 * (contracts/config-studio/README.md, ADR-A138 BQ-2). An MCP host reads the library's clauses and proposes stated
 * meaning with its own model, and every proposal is saved to the review configuration as a save from the browser is,
 * waiting for a person's decision. It also offers MORK's proposal tools, so a host proposes a mapping scheme with its own
 * model and saves it to a workspace's mapping part for review there: those that read no source are served as staged,
 * and those that read a source or a sample run in the worker as a tool job. The server holds no model and calls none. Requests are answered whole, never
 * streamed, so a session holds nothing but the client's name for the proposals it makes.
 */
final class StudioMcp {
    static final List<String> VERSIONS = List.of("2025-11-25", "2025-06-18", "2025-03-26");
    private static final String INS = "https://www.nebularis.org/neuro-semantic/lattice/instrument#";
    private static final String INS_VOC = "https://www.nebularis.org/neuro-semantic/lattice/instrument/vocab#";
    private static final String PTY = "https://www.nebularis.org/neuro-semantic/lattice/party#";
    private static final String WRD = "https://www.nebularis.org/neuro-semantic/lattice/wording#";
    private static final String FND = "https://www.nebularis.org/neuro-semantic/lattice/foundation#";
    private static final Pattern LOCAL_ORIGIN = Pattern.compile("https?://(localhost|127\\.0\\.0\\.1|\\[::1\\])(:\\d+)?");
    private static final int MAX_SESSIONS = 1000;

    private final StudioStore store;
    private final Writes writes;
    private final Clock clock;
    private final Supplier<UUID> ids;
    private final Path assets;
    private final java.util.function.BiFunction<String, Model, Model> tools;
    private final Map<String, String> clients = new ConcurrentHashMap<>();
    private volatile Model vocabulary;

    StudioMcp(StudioStore store, Writes writes, Clock clock, Supplier<UUID> ids, Path assets,
              java.util.function.BiFunction<String, Model, Model> tools) {
        this.tools = tools;
        this.store = store;
        this.writes = writes;
        this.clock = clock;
        this.ids = ids;
        this.assets = assets;
    }

    ApiResponse handle(ApiRequest req) {
        String origin = req.header("origin");
        if (origin != null && !LOCAL_ORIGIN.matcher(origin.trim()).matches()) {
            return ApiResponse.text(403, "an MCP request is accepted from localhost only");
        }
        if (!req.method().equals("POST")) {
            return ApiResponse.text(405, "the studio's MCP server answers POST only, and opens no stream").with("Allow", "POST");
        }
        JsonValue message;
        try {
            message = JSON.parseAny(new String(req.body() == null ? new byte[0] : req.body(), StandardCharsets.UTF_8));
        } catch (JsonParseException e) {
            return json(error(JsonNull.instance, -32700, "the body is not JSON"));
        }
        if (!message.isObject()) {
            return json(error(JsonNull.instance, -32600, "a request is one JSON-RPC object, and batches are not accepted"));
        }
        JsonObject m = message.getAsObject();
        if (!m.hasKey("id")) {
            return ApiResponse.empty(202);
        }
        JsonValue id = m.get("id");
        String method = m.hasKey("method") && m.get("method").isString() ? m.get("method").getAsString().value() : "";
        JsonObject params = m.hasKey("params") && m.get("params").isObject() ? m.get("params").getAsObject() : new JsonObject();
        try {
            return switch (method) {
                case "initialize" -> initialize(id, params);
                case "ping" -> json(result(id, new JsonObject()));
                case "tools/list" -> json(result(id, tools()));
                case "tools/call" -> json(result(id, call(params, req.header("mcp-session-id"))));
                case "prompts/list" -> json(result(id, prompts()));
                case "prompts/get" -> json(result(id, prompt(params)));
                default -> json(error(id, -32601, "no method " + method));
            };
        } catch (InvalidParams e) {
            return json(error(id, -32602, e.getMessage()));
        }
    }

    // --- the protocol -------------------------------------------------------------------------------------------

    private ApiResponse initialize(JsonValue id, JsonObject params) {
        String asked = params.hasKey("protocolVersion") && params.get("protocolVersion").isString()
            ? params.get("protocolVersion").getAsString().value() : "";
        JsonObject result = new JsonObject();
        result.put("protocolVersion", VERSIONS.contains(asked) ? asked : VERSIONS.getFirst());
        JsonObject capabilities = new JsonObject();
        capabilities.put("tools", new JsonObject());
        capabilities.put("prompts", new JsonObject());
        result.put("capabilities", capabilities);
        JsonObject info = new JsonObject();
        info.put("name", "lattice-configuration-studio");
        info.put("version", "1");
        result.put("serverInfo", info);
        result.put("instructions", "Read a workspace's clauses and propose the stated meaning each states. A proposal waits for a person to "
            + "confirm, retarget, decline or defer it in the studio. Name only the relation kinds, roles and activities read_clause lists.");
        String session = UUID.randomUUID().toString();
        if (clients.size() < MAX_SESSIONS) {
            clients.put(session, clientName(params));
        }
        return json(result(id, result)).with("Mcp-Session-Id", session);
    }

    private static String clientName(JsonObject params) {
        if (params.hasKey("clientInfo") && params.get("clientInfo").isObject()) {
            JsonObject info = params.get("clientInfo").getAsObject();
            String name = text(info, "name");
            String version = text(info, "version");
            if (name != null) {
                return "assistant " + name + (version == null ? "" : " " + version);
            }
        }
        return "assistant, an MCP client that gave no name";
    }

    private static JsonObject tools() {
        JsonArray list = new JsonArray();
        list.add(tool("list_workspaces", "List the studio's workspaces by id and label.", schema(Map.of(), List.of())));
        list.add(tool("list_clauses", "List the texts of a workspace's library forms, with each one's IRI, number, text, and whether it has "
            + "stated meaning, a proposal waiting, or neither.", schema(Map.of("workspace", "the workspace's id"), List.of("workspace"))));
        list.add(tool("read_clause", "Read one clause: its text, its stated meaning in plain words, and the relation kinds, roles and activities "
            + "a proposal for it may name.", schema(Map.of("workspace", "the workspace's id", "clause", "the clause's IRI"), List.of("workspace", "clause"))));
        Map<String, String> propose = new LinkedHashMap<>();
        propose.put("workspace", "the workspace's id");
        propose.put("clause", "the clause's IRI");
        propose.put("kind", "a relation kind's label, as read_clause lists them");
        propose.put("role", "the label of the role that bears the relation: the obligor, or the holder");
        propose.put("counterRole", "the label of the role it is owed to: the obligee, or the counterparty");
        propose.put("activity", "an activity's label, as read_clause lists them");
        propose.put("evidence", "the words of the clause the proposal rests on");
        list.add(tool("propose", "Propose the stated meaning of one clause, as a proposal waiting for a person's decision in the studio. "
            + "It is never stated meaning until someone confirms it.", schema(propose, List.of("workspace", "clause", "kind", "evidence"))));
        morkTools(list);
        JsonObject out = new JsonObject();
        out.put("tools", list);
        return out;
    }

    /** MORK's proposal tools, for proposing a mapping scheme (MORK README §5.18). */
    private static void morkTools(JsonArray list) {
        String source = "the source vocabulary, as Turtle";
        list.add(tool("mork_teaching_pack", "MORK's teaching pack: its notation, doctrine, worked cassettes, the translation table of legal words "
            + "and MCN's codebook. Read it before proposing a mapping.", schema(Map.of(), List.of())));
        list.add(tool("mork_target_cards", "One line per term of the named LATTICE layers: its CURIE, kind, label, definition or utility, and place.",
            schema(Map.of("layers", "layer names, comma-separated: instrument, eligibility, party, behaviour, quantification, foundation, vocabulary, wording"),
                List.of("layers"))));
        list.add(tool("mork_describe_term", "One LATTICE term in depth: its comment and utility, its place, the properties of it and to it, "
            + "its individuals, and the laws its layer's shapes state. Read it for each target term a mapping writes.",
            schema(Map.of("term", "a CURIE, such as ins:Permission"), List.of("term"))));
        list.add(tool("mork_source_cards", "One line per term of a source vocabulary.",
            schema(Map.of("workspace", "the workspace's id", "source", source, "namespace", "the source's own namespace, to read only its terms"),
                List.of("workspace", "source"))));
        list.add(tool("mork_candidate_terms", "The LATTICE terms likeliest to match one source term, best first.",
            schema(Map.of("workspace", "the workspace's id", "source", source, "term", "a CURIE or IRI of the source vocabulary",
                "namespace", "the source's own namespace"), List.of("workspace", "source", "term"))));
        list.add(tool("mork_check_mapping", "Decode, validate and compile a proposal in MCN, check its target terms, and run it over a sample "
            + "source when one is given, holding what it writes to LATTICE's laws. Findings at severity info are not errors. Run it until it reports no error.",
            schema(Map.of("workspace", "the workspace's id", "mcn", "the proposal, in MCN", "sample", "a sample source as Turtle"), List.of("workspace", "mcn"))));
        list.add(tool("mork_propose_mapping", "Save a checked proposal to a workspace's mapping part, with a proposal run recording the model and the "
            + "tokens it spent, for a person to review in the studio's mapping mode. It is never accepted until someone reviews it.",
            schema(Map.of("workspace", "the workspace's id", "mcn", "the proposal, in MCN, with a base of its own", "model", "the model that proposed it",
                "inputTokens", "the tokens the model read, as a number", "outputTokens", "the tokens it wrote, as a number"), List.of("workspace", "mcn"))));
    }

    private static JsonObject tool(String name, String description, JsonObject inputSchema) {
        JsonObject t = new JsonObject();
        t.put("name", name);
        t.put("description", description);
        t.put("inputSchema", inputSchema);
        return t;
    }

    private static JsonObject schema(Map<String, String> properties, List<String> required) {
        JsonObject s = new JsonObject();
        s.put("type", "object");
        JsonObject props = new JsonObject();
        properties.forEach((k, v) -> {
            JsonObject p = new JsonObject();
            p.put("type", "string");
            p.put("description", v);
            props.put(k, p);
        });
        s.put("properties", props);
        JsonArray req = new JsonArray();
        required.forEach(req::add);
        s.put("required", req);
        s.put("additionalProperties", false);
        return s;
    }

    private JsonObject prompts() {
        JsonArray list = new JsonArray();
        JsonObject p = new JsonObject();
        p.put("name", "mtp-l0");
        p.put("description", "The first layer of MORK's teaching pack, MTP.");
        list.add(p);
        JsonObject out = new JsonObject();
        out.put("prompts", list);
        return out;
    }

    private JsonObject prompt(JsonObject params) {
        if (!"mtp-l0".equals(text(params, "name"))) {
            throw new InvalidParams("no prompt is named " + text(params, "name"));
        }
        String body;
        try {
            body = Files.readString(assets.resolve("prompts").resolve("mtp-l0.txt"), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new InvalidParams("the prompt is not staged: run mise run build:config-studio-assets");
        }
        JsonObject content = new JsonObject();
        content.put("type", "text");
        content.put("text", body);
        JsonObject message = new JsonObject();
        message.put("role", "user");
        message.put("content", content);
        JsonArray messages = new JsonArray();
        messages.add(message);
        JsonObject out = new JsonObject();
        out.put("description", "The first layer of MORK's teaching pack, MTP.");
        out.put("messages", messages);
        return out;
    }

    // --- the tools ----------------------------------------------------------------------------------------------

    private JsonObject call(JsonObject params, String session) {
        String name = text(params, "name");
        JsonObject args = params.hasKey("arguments") && params.get("arguments").isObject() ? params.get("arguments").getAsObject() : new JsonObject();
        try {
            String text = switch (name == null ? "" : name) {
                case "list_workspaces" -> listWorkspaces();
                case "list_clauses" -> listClauses(workspace(args));
                case "read_clause" -> readClause(workspace(args), required(args, "clause"));
                case "propose" -> propose(workspace(args), args, session);
                case "mork_teaching_pack" -> staged("teaching-pack.txt");
                case "mork_target_cards" -> targetCards(required(args, "layers"));
                case "mork_describe_term" -> describeTerm(required(args, "term"));
                case "mork_source_cards" -> morkTool(workspace(args), "source_cards", args);
                case "mork_candidate_terms" -> morkTool(workspace(args), "candidate_terms", args);
                case "mork_check_mapping" -> morkTool(workspace(args), "check_mapping", args);
                case "mork_propose_mapping" -> proposeMapping(workspace(args), args, session);
                default -> throw new InvalidParams("no tool is named " + name);
            };
            return content(text, false);
        } catch (Refusal e) {
            // A refusal is the tool's answer, so the model reads it and can correct itself.
            return content(e.getMessage(), true);
        }
    }

    private String listWorkspaces() {
        Model all = StudioApi.readableWorkspaces(store);
        List<String> lines = new ArrayList<>();
        all.listResourcesWithProperty(RDF.type, Cst.Workspace).forEachRemaining(ws -> lines.add(
            ws.getURI().substring(Graphs.WORKSPACE_PREFIX.length()) + "  " + label(all, ws)));
        lines.sort(Comparator.naturalOrder());
        return lines.isEmpty() ? "The studio has no workspace." : String.join("\n", lines);
    }

    private String listClauses(Workspace ws) {
        Model world = world(ws);
        Set<RDFNode> stated = new HashSet<>(world.listObjectsOfProperty(p(INS + "expressedIn")).toList());
        Set<RDFNode> waiting = waiting(world);
        List<String> lines = new ArrayList<>();
        for (Resource c : clauses(world)) {
            String state = stated.contains(c) ? "stated meaning" : waiting.contains(c) ? "a proposal waiting" : "no meaning yet";
            lines.add(objectId(world, c) + "  " + c.getURI() + "  [" + state + "]\n    " + text(world, c));
        }
        return lines.isEmpty() ? "The library holds no clause." : String.join("\n", lines);
    }

    private String readClause(Workspace ws, String clause) {
        Model world = world(ws);
        Resource c = world.createResource(clause);
        if (!clauses(world).contains(c)) {
            throw new Refusal("No clause of the library is " + clause + ". list_clauses lists them.");
        }
        StringBuilder out = new StringBuilder();
        out.append("Clause ").append(objectId(world, c)).append(": ").append(text(world, c)).append("\n\nStated meaning:\n");
        List<String> said = new ArrayList<>();
        world.listSubjectsWithProperty(p(INS + "expressedIn"), c).forEachRemaining(term ->
            world.listSubjectsWithProperty(p(INS + "arisesUnder"), term).forEachRemaining(r -> said.add("  " + say(world, r))));
        out.append(said.isEmpty() ? "  none\n" : String.join("\n", said) + "\n");
        Context ctx = context(world, own(ws));
        out.append("\nA proposal may name\n  relation kinds: ").append(String.join(", ", ctx.kinds.keySet()))
            .append("\n  roles: ").append(ctx.roles.isEmpty() ? "none declared" : String.join(", ", ctx.roles.keySet()))
            .append("\n  activities: ").append(String.join(", ", ctx.activities.keySet()));
        return out.toString();
    }

    private String propose(Workspace ws, JsonObject args, String session) {
        String clause = required(args, "clause");
        Model world = world(ws);
        Resource c = world.createResource(clause);
        if (!clauses(world).contains(c)) {
            throw new Refusal("No clause of the library is " + clause + ". list_clauses lists them.");
        }
        Context ctx = context(world, own(ws));
        Resource kind = pick(ctx.kinds, required(args, "kind"), "relation kind");
        Resource role = optionalPick(ctx.roles, text(args, "role"), "role");
        Resource counter = optionalPick(ctx.roles, text(args, "counterRole"), "role");
        Resource activity = optionalPick(ctx.activities, text(args, "activity"), "activity");
        String evidence = required(args, "evidence");
        if (evidence.length() > 1000) {
            throw new Refusal("The evidence is at most 1000 characters.");
        }
        String base = "urn:lattice:studio:proposal:" + ids.get();
        Resource existing = world.listSubjectsWithProperty(p(INS + "expressedIn"), c).nextOptional().orElse(null);
        Model payload = ModelFactory.createDefaultModel();
        payload.setNsPrefix("ins", INS);
        payload.setNsPrefix("ins-voc", INS_VOC);
        Resource term = existing != null ? payload.createResource(existing.getURI()) : payload.createResource(base + "/term")
            .addProperty(RDF.type, payload.createResource(INS + "Term")).addProperty(RDF.type, payload.createResource(INS + "Template"))
            .addProperty(p(INS + "expressedIn"), c);
        Resource relation = payload.createResource(base + "/relation").addProperty(RDF.type, kind)
            .addProperty(RDF.type, payload.createResource(INS + "Template")).addProperty(p(INS + "arisesUnder"), term);
        boolean obligation = ctx.obligations.contains(kind);
        if (role != null) {
            relation.addProperty(p(INS + (obligation ? "obligor" : "holder")), role);
        }
        if (counter != null) {
            relation.addProperty(p(INS + (obligation ? "obligee" : "counterparty")), counter);
        }
        if (activity != null) {
            relation.addProperty(p(INS + "activity"), activity);
        }
        StringWriter turtle = new StringWriter();
        RDFDataMgr.write(turtle, payload, Lang.TURTLE);
        String proposer = session == null ? null : clients.get(session);
        for (int attempt = 0; attempt < 2; attempt++) {
            Workspace now = Workspace.from(ws.id(), store.graph(Graphs.workspace(ws.id())));
            Model review = store.graph(Graphs.config(ws.id(), "review"));
            Resource proposal = review.createResource(base).addProperty(RDF.type, cst("Proposal"))
                .addProperty(cstp("span"), c).addProperty(cstp("proposer"), "assistant")
                .addProperty(cstp("proposerVersion"), proposer == null ? "assistant, an MCP client with no session" : proposer)
                .addProperty(cstp("proposedAt"), review.createTypedLiteral(instant().toString(), XSDDatatype.XSDdateTime))
                .addProperty(cstp("evidence"), evidence).addProperty(cstp("payload"), turtle.toString());
            if (existing == null) {
                proposal.addProperty(cstp("proposes"), review.createResource(base + "/term"));
            }
            proposal.addProperty(cstp("proposes"), review.createResource(base + "/relation"));
            Reply reply = writes.send(Command.save(ws.id(), "review", now.revision("review"), instant(), review));
            if (reply.applied()) {
                return "Proposed " + say(payload.union(world), relation) + " for clause " + objectId(world, c)
                    + ", as " + base + ". It waits for a person's decision in the studio.";
            }
            if (reply.status() != 412) {
                throw new Refusal("The proposal could not be saved: " + reply.message());
            }
        }
        throw new Refusal("The review configuration kept changing while the proposal was saved. Try again.");
    }

    // --- MORK's proposal tools -----------------------------------------------------------------------------------

    private static final List<String> LAYERS = List.of("instrument", "eligibility", "party", "behaviour", "quantification", "foundation", "vocabulary", "wording");
    private static final String PROV = "http://www.w3.org/ns/prov#";
    private static final String MORK = "http://www.nebularis.org/ontologies/Mork#";
    private static final int MAX_DOCUMENT = 2_000_000;

    private String staged(String name) {
        try {
            return Files.readString(assets.resolve("mork").resolve(name), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new Refusal("MORK's tools are not staged: run mise run build:config-studio-assets");
        }
    }

    private String targetCards(String layers) {
        StringBuilder out = new StringBuilder();
        for (String layer : layers.split(",")) {
            String name = layer.trim();
            if (!LAYERS.contains(name)) {
                throw new Refusal("No layer is named " + name + ". Choose from " + String.join(", ", LAYERS) + ".");
            }
            out.append(staged("cards/" + name + ".txt")).append('\n');
        }
        return out.toString();
    }

    private String describeTerm(String term) {
        JsonObject terms = JSON.parse(staged("describe.json"));
        if (!terms.hasKey(term)) {
            throw new Refusal("No LATTICE layer declares " + term + ". Name a term by its CURIE, as the target cards do.");
        }
        return terms.get(term).getAsString().value();
    }

    /** Runs a tool in the worker with its documents and arguments, and gives its result. */
    private String morkTool(Workspace ws, String name, JsonObject args) {
        Model input = ModelFactory.createDefaultModel();
        String base = "urn:lattice:studio:ws:" + ws.id() + ":tool/" + ids.get();
        JsonObject arguments = new JsonObject();
        for (String key : List.of("namespace", "term", "mcn")) {
            if (text(args, key) != null) {
                arguments.put(key, text(args, key));
            }
        }
        input.createResource(base).addProperty(RDF.type, Cst.ToolRequest).addProperty(Cst.toolName, name)
            .addProperty(Cst.toolArguments, arguments.toString());
        document(input, base + "/source", text(args, "source"), Cst.SourceVocabulary);
        document(input, base + "/sample", text(args, "sample"), Cst.SampleSource);
        Model job = tools.apply(ws.id(), input);
        if (job == null) {
            throw new Refusal("The worker did not answer within two minutes. Is it running?");
        }
        String failure = job.listObjectsOfProperty(Cst.failureMessage).nextOptional().map(n -> n.asLiteral().getString()).orElse(null);
        if (failure != null) {
            throw new Refusal(name + " failed: " + failure);
        }
        return job.listSubjectsWithProperty(Cst.path, "result").nextOptional()
            .map(a -> a.getProperty(Cst.content).getString()).orElseThrow(() -> new Refusal(name + " gave no result."));
    }

    private static void document(Model input, String node, String text, Resource role) {
        if (text == null || text.isBlank()) {
            return;
        }
        if (text.length() > MAX_DOCUMENT) {
            throw new Refusal("A document is at most " + MAX_DOCUMENT + " characters.");
        }
        input.createResource(node).addProperty(RDF.type, Cst.ImportDocument).addProperty(Cst.documentRole, role)
            .addProperty(Cst.documentContent, text).addProperty(Cst.documentMediaType, "text/turtle");
    }

    /** Decodes a proposal in the worker, and saves it to the mapping part with its run, refusing one that names a node the workspace holds. */
    private String proposeMapping(Workspace ws, JsonObject args, String session) {
        JsonObject decode = new JsonObject();
        decode.put("mcn", required(args, "mcn"));
        Model proposal = ModelFactory.createDefaultModel();
        RDFDataMgr.read(proposal, new java.io.StringReader(morkTool(ws, "decode_mcn", decode)), null, Lang.TURTLE);
        Model world = world(ws);
        List<String> clashes = proposal.listSubjects().filterKeep(Resource::isURIResource).filterKeep(s -> world.contains(s, null))
            .mapWith(Resource::getURI).toList();
        if (!clashes.isEmpty()) {
            throw new Refusal("The proposal names " + clashes.get(0) + ", which the workspace already holds. Give it a base of its own.");
        }
        if (Parts.strangers(proposal, "mapping", 1).size() > 0) {
            throw new Refusal("The proposal holds what is not a mapping: " + Parts.strangers(proposal, "mapping", 1).get(0) + ".");
        }
        Resource run = proposal.createResource("urn:lattice:studio:ws:" + ws.id() + ":run/" + ids.get())
            .addProperty(RDF.type, proposal.createResource(MORK + "ProposalRun")).addProperty(RDF.type, proposal.createResource(PROV + "Activity"))
            .addProperty(proposal.createProperty(MORK + "teachingPackVersion"), "MTP, through the studio's MCP server")
            .addProperty(proposal.createProperty(PROV + "endedAtTime"), proposal.createTypedLiteral(instant().toString(), XSDDatatype.XSDdateTime));
        String client = session == null ? null : clients.get(session);
        String model = text(args, "model") != null ? text(args, "model") : client != null ? client : "an MCP client";
        run.addProperty(proposal.createProperty(MORK + "proposerModel"), model);
        for (String key : List.of("inputTokens", "outputTokens")) {
            String n = text(args, key);
            if (n != null) {
                if (!n.matches("\\d{1,12}")) {
                    throw new Refusal(key + " is a whole number.");
                }
                run.addProperty(proposal.createProperty(MORK + key), proposal.createTypedLiteral(n, XSDDatatype.XSDnonNegativeInteger));
            }
        }
        List<Resource> mappings = proposal.listSubjectsWithProperty(proposal.createProperty(MORK + "mappingScheme")).toList();
        mappings.forEach(m -> m.addProperty(proposal.createProperty(PROV + "wasGeneratedBy"), run));
        for (int attempt = 0; attempt < 2; attempt++) {
            Workspace now = Workspace.from(ws.id(), store.graph(Graphs.workspace(ws.id())));
            Model mapping = store.graph(Graphs.config(ws.id(), "mapping")).add(proposal);
            Reply reply = writes.send(Command.save(ws.id(), "mapping", now.revision("mapping"), instant(), mapping));
            if (reply.applied()) {
                return "Saved " + mappings.size() + " mappings to the mapping part as " + run.getURI()
                    + ". A person reviews each in the studio's mapping mode.";
            }
            if (reply.status() != 412) {
                throw new Refusal("The proposal could not be saved: " + reply.message());
            }
        }
        throw new Refusal("The mapping part kept changing while the proposal was saved. Try again.");
    }

    // --- reading the workspace ----------------------------------------------------------------------------------

    private record Context(Map<String, Resource> kinds, Set<Resource> obligations, Map<String, Resource> roles, Map<String, Resource> activities) {
    }

    private Workspace workspace(JsonObject args) {
        String id = required(args, "workspace");
        Workspace ws = Graphs.isId(id) ? Workspace.from(id, store.graph(Graphs.workspace(id))) : null;
        if (ws == null || !StudioApi.readable(ws)) {
            throw new Refusal("No workspace has the id " + id + ". list_workspaces lists them.");
        }
        return ws;
    }

    /** The workspace's baseline and configurations, with the served vocabulary for kinds and activities. */
    private Model world(Workspace ws) {
        return own(ws).union(vocabulary());
    }

    /** The workspace's baseline and configurations alone, where its own roles are. */
    private Model own(Workspace ws) {
        Model own = ModelFactory.createDefaultModel();
        own.add(store.graph(ws.baselineGraph()));
        for (String part : Workspace.GRAPHS.subList(1, Workspace.GRAPHS.size())) {
            own.add(store.graph(Graphs.config(ws.id(), part)));
        }
        return own;
    }

    private Model vocabulary() {
        Model v = vocabulary;
        if (v == null) {
            v = ModelFactory.createDefaultModel();
            Path file = assets.resolve("vocabulary.ttl");
            if (Files.isRegularFile(file)) {
                RDFDataMgr.read(v, file.toUri().toString(), Lang.TURTLE);
            }
            vocabulary = v;
        }
        return v;
    }

    private static List<Resource> clauses(Model world) {
        Set<Resource> assembled = new HashSet<>();
        world.listResourcesWithProperty(RDF.type, world.createResource(WRD + "AssembledWording")).forEachRemaining(assembled::add);
        List<Resource> out = new ArrayList<>();
        world.listResourcesWithProperty(RDF.type, world.createResource(WRD + "Text")).forEachRemaining(r -> {
            if (r.isURIResource() && !assembled.contains(r) && !text(world, r).isBlank()) {
                out.add(r);
            }
        });
        out.sort(Comparator.comparing((Resource r) -> objectId(world, r), StudioMcp::byNumber).thenComparing(Resource::getURI));
        return out;
    }

    private static Set<RDFNode> waiting(Model world) {
        Set<RDFNode> out = new HashSet<>();
        world.listResourcesWithProperty(RDF.type, cst("Proposal")).forEachRemaining(p -> {
            if (!p.hasProperty(cstp("decision")) && p.hasProperty(cstp("span"))) {
                out.add(p.getProperty(cstp("span")).getObject());
            }
        });
        return out;
    }

    /** The kinds and activities the vocabulary declares, and the roles the workspace itself declares, as proposers read them. */
    private static Context context(Model world, Model own) {
        Map<String, Resource> kinds = new java.util.TreeMap<>();
        Set<Resource> obligations = new HashSet<>();
        Resource relation = world.createResource(INS + "LegalRelation");
        Resource obligation = world.createResource(INS + "Obligation");
        for (Resource k : subclasses(world, relation)) {
            kinds.put(label(world, k), k);
            if (subclasses(world, obligation).contains(k) || k.equals(obligation)) {
                obligations.add(k);
            }
        }
        Map<String, Resource> roles = new java.util.TreeMap<>();
        own.listResourcesWithProperty(RDF.type, own.createResource(PTY + "Role")).forEachRemaining(r -> {
            if (r.isURIResource()) {
                roles.put(label(own, r), r);
            }
        });
        Map<String, Resource> activities = new java.util.TreeMap<>();
        world.listResourcesWithProperty(SKOS.inScheme, world.createResource(INS_VOC + "Activities")).forEachRemaining(a -> {
            if (a.isURIResource()) {
                activities.put(label(world, a), a);
            }
        });
        return new Context(kinds, obligations, roles, activities);
    }

    private static Set<Resource> subclasses(Model world, Resource of) {
        Set<Resource> out = new HashSet<>();
        List<Resource> pending = new ArrayList<>(List.of(of));
        while (!pending.isEmpty()) {
            Resource r = pending.removeLast();
            world.listResourcesWithProperty(RDFS.subClassOf, r).forEachRemaining(s -> {
                if (s.isURIResource() && out.add(s)) {
                    pending.add(s);
                }
            });
        }
        return out;
    }

    private static Resource pick(Map<String, Resource> table, String label, String what) {
        for (Map.Entry<String, Resource> e : table.entrySet()) {
            if (e.getKey().equalsIgnoreCase(label.trim())) {
                return e.getValue();
            }
        }
        throw new Refusal("No " + what + " is labelled " + label + ". The workspace declares: "
            + (table.isEmpty() ? "none" : String.join(", ", table.keySet())) + ".");
    }

    private static Resource optionalPick(Map<String, Resource> table, String label, String what) {
        return label == null || label.isBlank() ? null : pick(table, label, what);
    }

    /** A relation in plain words, roles as roles: "Borrower must Pay Lender". */
    private static String say(Model world, Resource relation) {
        String kind = relation.listProperties(RDF.type).toList().stream().map(Statement::getResource)
            .filter(t -> t.getURI() != null && t.getURI().startsWith(INS) && !t.getURI().equals(INS + "Template"))
            .map(t -> label(world, t)).findFirst().orElse("relation");
        List<String> words = new ArrayList<>();
        for (String p : List.of("obligor", "holder")) {
            relation.listProperties(p(INS + p)).forEachRemaining(s -> words.add(label(world, s.getResource())));
        }
        words.add("(" + kind.toLowerCase(Locale.ROOT) + ")");
        Statement activity = relation.getProperty(p(INS + "activity"));
        if (activity != null) {
            words.add(label(world, activity.getResource()));
        }
        for (String p : List.of("obligee", "counterparty")) {
            relation.listProperties(p(INS + p)).forEachRemaining(s -> words.add(label(world, s.getResource())));
        }
        return String.join(" ", words);
    }

    /** A text's parts in order, a variable shown by its key. */
    private static String text(Model world, Resource element) {
        List<Resource> parts = new ArrayList<>(element.listProperties(p(WRD + "hasTextPart")).mapWith(Statement::getResource).toList());
        parts.sort(Comparator.comparingLong(p -> p.hasProperty(p(WRD + "partIndex")) ? p.getProperty(p(WRD + "partIndex")).getLong() : 0));
        StringBuilder out = new StringBuilder();
        for (Resource part : parts) {
            if (part.hasProperty(p(WRD + "partText"))) {
                out.append(part.getProperty(p(WRD + "partText")).getString());
            } else if (part.hasProperty(p(WRD + "refersToVariable"))) {
                RDFNode identity = part.getProperty(p(WRD + "refersToVariable")).getObject();
                Resource variable = world.listSubjectsWithProperty(p(FND + "hasIdentity"), identity).nextOptional().orElse(null);
                Statement key = variable == null ? null : variable.getProperty(p(WRD + "variableKey"));
                out.append('{').append(key == null ? "variable" : key.getString()).append('}');
            }
        }
        return out.toString();
    }

    /** Object ids in reading order: 5.2A before 5.3 before 12.1, numbers compared as numbers. */
    static int byNumber(String a, String b) {
        String[] x = a.split("(?<=\\d)(?=\\D)|(?<=\\D)(?=\\d)");
        String[] y = b.split("(?<=\\d)(?=\\D)|(?<=\\D)(?=\\d)");
        for (int i = 0; i < Math.min(x.length, y.length); i++) {
            boolean digits = !x[i].isEmpty() && !y[i].isEmpty() && Character.isDigit(x[i].charAt(0)) && Character.isDigit(y[i].charAt(0));
            int c = digits ? new java.math.BigInteger(x[i]).compareTo(new java.math.BigInteger(y[i])) : x[i].compareTo(y[i]);
            if (c != 0) {
                return c;
            }
        }
        return Integer.compare(x.length, y.length);
    }

    private static String objectId(Model world, Resource element) {
        Statement s = element.getProperty(p(WRD + "objectId"));
        return s == null ? "" : s.getString();
    }

    private static String label(Model world, Resource r) {
        for (Property p : List.of(RDFS.label, SKOS.prefLabel)) {
            Statement s = world.getResource(r.getURI() == null ? "" : r.getURI()).getProperty(p);
            if (s != null && s.getObject().isLiteral()) {
                return s.getString();
            }
        }
        String iri = r.getURI() == null ? r.toString() : r.getURI();
        String local = iri.substring(Math.max(iri.lastIndexOf('#'), iri.lastIndexOf('/')) + 1);
        // An unlabelled class reads as words: ContinuingObligation as "Continuing obligation".
        String words = local.replaceAll("(?<=[a-z])(?=[A-Z])", " ").toLowerCase(Locale.ROOT);
        return words.isEmpty() ? local : Character.toUpperCase(words.charAt(0)) + words.substring(1);
    }

    // --- helpers ------------------------------------------------------------------------------------------------

    private Instant instant() {
        return clock.instant().truncatedTo(ChronoUnit.SECONDS);
    }

    private static Resource cst(String name) {
        return ResourceFactory.createResource(Cst.NS + name);
    }

    private static Property cstp(String name) {
        return ResourceFactory.createProperty(Cst.NS + name);
    }

    private static Property p(String iri) {
        return ResourceFactory.createProperty(iri);
    }

    private static String text(JsonObject o, String key) {
        return o.hasKey(key) && o.get(key).isString() ? o.get(key).getAsString().value() : null;
    }

    private static String required(JsonObject o, String key) {
        String v = text(o, key);
        if (v == null || v.isBlank()) {
            throw new InvalidParams("the argument " + key + " is required");
        }
        return v.trim();
    }

    private static JsonObject content(String text, boolean isError) {
        JsonObject item = new JsonObject();
        item.put("type", "text");
        item.put("text", text);
        JsonArray content = new JsonArray();
        content.add(item);
        JsonObject out = new JsonObject();
        out.put("content", content);
        out.put("isError", isError);
        return out;
    }

    private static JsonObject result(JsonValue id, JsonObject result) {
        JsonObject out = new JsonObject();
        out.put("jsonrpc", "2.0");
        out.put("id", id);
        out.put("result", result);
        return out;
    }

    private static JsonObject error(JsonValue id, int code, String message) {
        JsonObject e = new JsonObject();
        e.put("code", code);
        e.put("message", message);
        JsonObject out = new JsonObject();
        out.put("jsonrpc", "2.0");
        out.put("id", id);
        out.put("error", e);
        return out;
    }

    private static ApiResponse json(JsonObject body) {
        return new ApiResponse(200, new LinkedHashMap<>(Map.of("Content-Type", "application/json")),
            JSON.toStringFlat(body).getBytes(StandardCharsets.UTF_8));
    }

    /** A request whose parameters the protocol refuses, answered with JSON-RPC's invalid params. */
    private static class InvalidParams extends RuntimeException {
        InvalidParams(String message) {
            super(message);
        }
    }

    /** A tool's refusal, answered as the tool's result with isError, so the model reads why. */
    private static final class Refusal extends InvalidParams {
        Refusal(String message) {
            super(message);
        }
    }
}
