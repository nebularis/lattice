// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.Map;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Resource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;

/** The studio as an MCP server: the protocol, the four tools, refusals and the prompt (ADR-A138 BQ-2). */
class McpTest {
    private static final String WS = Fixture.id(1);
    private static final String INS = "https://www.nebularis.org/neuro-semantic/lattice/instrument#";
    private static final String CLAUSE = "https://example.org/cl-1";
    private static final String PREFIXES = Fixture.PREFIXES
        + "@prefix wrd: <https://www.nebularis.org/neuro-semantic/lattice/wording#> .\n"
        + "@prefix ins: <" + INS + "> .\n@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n"
        + "@prefix skos: <http://www.w3.org/2004/02/skos/core#> .\n@prefix pty: <https://www.nebularis.org/neuro-semantic/lattice/party#> .\n"
        + "@prefix ins-voc: <https://www.nebularis.org/neuro-semantic/lattice/instrument/vocab#> .\n";

    @TempDir Path dir;
    Fixture f;

    @BeforeEach
    void setUp() throws IOException {
        Path assets = Fixture.assetsDir(dir);
        Files.writeString(assets.resolve("vocabulary.ttl"), PREFIXES
            + "ins:Obligation rdfs:subClassOf ins:LegalRelation ; rdfs:label \"Obligation\" .\n"
            + "ins:Permission rdfs:subClassOf ins:LegalRelation ; rdfs:label \"Permission\" .\n"
            + "ins-voc:Pay skos:inScheme ins-voc:Activities ; skos:prefLabel \"Pay\" .\n");
        Files.createDirectories(assets.resolve("prompts"));
        Files.writeString(assets.resolve("prompts").resolve("mtp-l0.txt"), "# MORK Teaching Pack L0\n");
        f = new Fixture(assets);
        Map<String, String> headers = new HashMap<>(Map.of("content-type", Fixture.TURTLE));
        assertEquals(201, f.send("POST", "/api/workspaces", null, headers,
            (PREFIXES + "ex:Borrower a pty:Role ; rdfs:label \"Borrower\" .\nex:Lender a pty:Role ; rdfs:label \"Lender\" .\n").getBytes(StandardCharsets.UTF_8)).status());
        assertEquals(204, f.put("/api/workspaces/" + WS + "/graphs/library", "\"0\"", PREFIXES
            + "ex:form a wrd:Wording ; wrd:directlyComprises <" + CLAUSE + "> .\n"
            + "<" + CLAUSE + "> a wrd:Text ; wrd:objectId \"1\" ; wrd:hasTextPart [ wrd:partIndex 0 ; wrd:partText \"The borrower shall pay the lender.\" ] .\n").status());
    }

    private ApiResponse rpc(String body, Map<String, String> extra) {
        Map<String, String> headers = new HashMap<>(Map.of("content-type", "application/json"));
        headers.putAll(extra);
        return f.send("POST", "/mcp", null, headers, body.getBytes(StandardCharsets.UTF_8));
    }

    private JsonObject call(String method, String params, String session) {
        ApiResponse r = rpc("{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"" + method + "\",\"params\":" + params + "}",
            session == null ? Map.of() : Map.of("mcp-session-id", session));
        assertEquals(200, r.status());
        return JSON.parse(new String(r.body(), StandardCharsets.UTF_8));
    }

    private static String text(JsonObject response) {
        return response.get("result").getAsObject().get("content").getAsArray().get(0).getAsObject().get("text").getAsString().value();
    }

    private String initialize() {
        ApiResponse r = rpc("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2025-06-18\","
            + "\"capabilities\":{},\"clientInfo\":{\"name\":\"test-host\",\"version\":\"9\"}}}", Map.of());
        JsonObject result = JSON.parse(new String(r.body(), StandardCharsets.UTF_8)).get("result").getAsObject();
        assertEquals("2025-06-18", result.get("protocolVersion").getAsString().value());
        assertTrue(result.get("capabilities").getAsObject().hasKey("tools"));
        return r.headers().get("Mcp-Session-Id");
    }

    @Test
    void theProtocolIsAnsweredAsStreamableHttpWithoutAStream() {
        assertTrue(initialize() != null);
        ApiResponse later = rpc("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2099-01-01\"}}", Map.of());
        assertTrue(new String(later.body(), StandardCharsets.UTF_8).contains("2025-11-25"), "an unknown version gets the latest");
        assertEquals(202, rpc("{\"jsonrpc\":\"2.0\",\"method\":\"notifications/initialized\"}", Map.of()).status());
        assertEquals(405, f.send("GET", "/mcp", null, Map.of(), new byte[0]).status());
        assertEquals(403, rpc("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"ping\"}", Map.of("origin", "https://evil.example")).status());
        assertEquals(200, rpc("{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"ping\"}", Map.of("origin", "http://localhost:6274")).status());
        assertTrue(call("nope", "{}", null).hasKey("error"));
        assertEquals(4, call("tools/list", "{}", null).get("result").getAsObject().get("tools").getAsArray().size());
    }

    @Test
    void aClauseIsListedAndReadWithWhatAProposalMayName() {
        String list = text(call("tools/call", "{\"name\":\"list_clauses\",\"arguments\":{\"workspace\":\"" + WS + "\"}}", null));
        assertTrue(list.contains(CLAUSE) && list.contains("no meaning yet") && list.contains("The borrower shall pay the lender."), list);
        String read = text(call("tools/call", "{\"name\":\"read_clause\",\"arguments\":{\"workspace\":\"" + WS + "\",\"clause\":\"" + CLAUSE + "\"}}", null));
        assertTrue(read.contains("relation kinds: Obligation, Permission") && read.contains("roles: Borrower, Lender") && read.contains("activities: Pay"), read);
        assertTrue(text(call("tools/call", "{\"name\":\"list_workspaces\",\"arguments\":{}}", null)).contains(WS));
    }

    @Test
    void aProposalWaitsForAPersonsDecisionAndNamesItsClient() {
        String session = initialize();
        JsonObject r = call("tools/call", "{\"name\":\"propose\",\"arguments\":{\"workspace\":\"" + WS + "\",\"clause\":\"" + CLAUSE
            + "\",\"kind\":\"Obligation\",\"role\":\"Borrower\",\"counterRole\":\"Lender\",\"activity\":\"Pay\",\"evidence\":\"shall pay\"}}", session);
        assertFalse(r.get("result").getAsObject().get("isError").getAsBoolean().value(), text(r));
        assertTrue(text(r).contains("Borrower (obligation) Pay Lender"), text(r));
        Model review = f.store.graph(Graphs.config(WS, "review"));
        Resource proposal = review.listResourcesWithProperty(org.apache.jena.vocabulary.RDF.type, review.createResource(Cst.NS + "Proposal")).next();
        assertFalse(proposal.hasProperty(review.createProperty(Cst.NS + "decision")), "nothing the server does decides");
        assertEquals("assistant", proposal.getProperty(review.createProperty(Cst.NS + "proposer")).getString());
        assertEquals("assistant test-host 9", proposal.getProperty(review.createProperty(Cst.NS + "proposerVersion")).getString());
        assertTrue(proposal.getProperty(review.createProperty(Cst.NS + "payload")).getString().contains("obligor"));
        assertTrue(text(call("tools/call", "{\"name\":\"list_clauses\",\"arguments\":{\"workspace\":\"" + WS + "\"}}", null)).contains("a proposal waiting"));
    }

    @Test
    void anUndeclaredLabelIsRefusedWithWhatIsDeclared() {
        JsonObject r = call("tools/call", "{\"name\":\"propose\",\"arguments\":{\"workspace\":\"" + WS + "\",\"clause\":\"" + CLAUSE
            + "\",\"kind\":\"Obligation\",\"role\":\"Guarantor\",\"evidence\":\"x\"}}", null);
        assertTrue(r.get("result").getAsObject().get("isError").getAsBoolean().value());
        assertTrue(text(r).contains("No role is labelled Guarantor") && text(r).contains("Borrower, Lender"), text(r));
        assertTrue(f.store.graph(Graphs.config(WS, "review")).isEmpty());
        JsonObject missing = call("tools/call", "{\"name\":\"propose\",\"arguments\":{\"workspace\":\"" + WS + "\"}}", null);
        assertEquals(-32602, missing.get("error").getAsObject().get("code").getAsNumber().value().intValue());
        JsonObject noWorkspace = call("tools/call", "{\"name\":\"list_clauses\",\"arguments\":{\"workspace\":\"nope\"}}", null);
        assertTrue(noWorkspace.get("result").getAsObject().get("isError").getAsBoolean().value());
    }

    @Test
    void mtpIsServedAsAPrompt() {
        JsonObject list = call("prompts/list", "{}", null);
        assertEquals("mtp-l0", list.get("result").getAsObject().get("prompts").getAsArray().get(0).getAsObject().get("name").getAsString().value());
        JsonObject got = call("prompts/get", "{\"name\":\"mtp-l0\"}", null);
        assertTrue(JSON.toStringFlat(got).contains("MORK Teaching Pack L0"));
    }
}
