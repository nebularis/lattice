// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.apache.jena.atlas.json.JSON;
import org.apache.jena.atlas.json.JsonObject;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.ResourceFactory;
import org.apache.jena.vocabulary.RDF;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.writes.Command;

/** MORK's proposal tools on the studio's MCP server: the staged ones, and those the worker runs, with a stand-in worker. */
class McpMorkTest {
    private static final String WS = Fixture.id(1);
    private static final String MORK = "http://www.nebularis.org/ontologies/Mork#";
    private static final String DECODED = "@prefix mork: <" + MORK + "> .\n<https://example.org/p#S> a mork:MappingScheme .\n"
        + "<https://example.org/p#M> a mork:Datum ; mork:mappingScheme <https://example.org/p#S> .\n";

    @TempDir Path dir;
    Fixture f;
    final List<String> asked = new ArrayList<>();

    @BeforeEach
    void setUp() throws IOException {
        Path assets = Fixture.assetsDir(dir);
        Files.writeString(assets.resolve("vocabulary.ttl"), Fixture.PREFIXES);
        Path mork = Files.createDirectories(assets.resolve("mork").resolve("cards"));
        Files.writeString(mork.getParent().resolve("teaching-pack.txt"), "# MTP\n");
        Files.writeString(mork.resolve("instrument.txt"), "ins:Permission | class | Permission\n");
        Files.writeString(mork.getParent().resolve("describe.json"), "{\"ins:Permission\": \"# ins:Permission (owl:Class), in instrument\\n- (law I8)\\n\"}");
        Fixture[] holder = new Fixture[1];
        // The stand-in worker answers a tool job at once, as the real one would, from the request it reads.
        f = new Fixture(assets, jobIri -> {
            Fixture fx = holder[0];
            String job = jobIri.substring(jobIri.lastIndexOf(':') + 1);
            Model input = fx.store.graph(Graphs.jobInput(job));
            String tool = input.listObjectsOfProperty(Cst.toolName).next().asLiteral().getString();
            asked.add(tool);
            Model done = fx.store.graph(jobIri);
            Resource j = done.createResource(jobIri);
            done.removeAll(j, Cst.status, null);
            j.addProperty(Cst.status, Cst.Succeeded);
            Resource a = done.createResource(jobIri + "#artefact-1").addProperty(RDF.type, done.createResource(Cst.NS + "Artefact"))
                .addProperty(Cst.path, "result").addProperty(Cst.content, tool.equals("decode_mcn") ? DECODED : tool + " ran")
                .addProperty(done.createProperty(Cst.NS + "mediaType"), "text/plain").addProperty(done.createProperty(Cst.NS + "group"), tool);
            j.addProperty(Cst.artefact, a);
            Dataset update = DatasetFactory.create();
            update.addNamedModel(jobIri, done);
            fx.writes.send(Command.jobUpdate(WS, job, update));
        });
        holder[0] = f;
        assertEquals(201, f.send("POST", "/api/workspaces", null, new HashMap<>(Map.of("content-type", Fixture.TURTLE)),
            Fixture.PREFIXES.getBytes(StandardCharsets.UTF_8)).status());
    }

    private String call(String tool, String arguments) {
        ApiResponse r = f.send("POST", "/mcp", null, new HashMap<>(Map.of("content-type", "application/json")),
            ("{\"jsonrpc\":\"2.0\",\"id\":7,\"method\":\"tools/call\",\"params\":{\"name\":\"" + tool + "\",\"arguments\":" + arguments + "}}")
                .getBytes(StandardCharsets.UTF_8));
        JsonObject result = JSON.parse(new String(r.body(), StandardCharsets.UTF_8)).get("result").getAsObject();
        return result.get("content").getAsArray().get(0).getAsObject().get("text").getAsString().value();
    }

    @Test
    void theStagedToolsAreServedWithoutTheWorker() {
        assertEquals("# MTP\n", call("mork_teaching_pack", "{}"));
        assertTrue(call("mork_target_cards", "{\"layers\":\"instrument\"}").contains("ins:Permission | class"));
        assertTrue(call("mork_describe_term", "{\"term\":\"ins:Permission\"}").contains("(law I8)"));
        assertTrue(call("mork_describe_term", "{\"term\":\"ins:Nothing\"}").startsWith("No LATTICE layer declares"));
        assertTrue(call("mork_target_cards", "{\"layers\":\"secrets\"}").startsWith("No layer is named"));
        assertEquals(List.of(), asked);
    }

    @Test
    void aToolThatReadsASourceRunsInTheWorker() {
        assertEquals("check_mapping ran", call("mork_check_mapping", "{\"workspace\":\"" + WS + "\",\"mcn\":\"%M S\"}"));
        assertEquals("candidate_terms ran", call("mork_candidate_terms", "{\"workspace\":\"" + WS + "\",\"source\":\"<urn:a> <urn:b> <urn:c> .\",\"term\":\"ex:X\"}"));
        assertEquals(List.of("check_mapping", "candidate_terms"), asked);
    }

    @Test
    void aProposalIsSavedToTheMappingPartWithItsRunAndNeverTwice() {
        String saved = call("mork_propose_mapping", "{\"workspace\":\"" + WS + "\",\"mcn\":\"...\",\"model\":\"a model\",\"inputTokens\":\"1200\"}");
        assertTrue(saved.startsWith("Saved 1 mappings"), saved);
        Model mapping = f.store.graph(Graphs.config(WS, "mapping"));
        Resource m = ResourceFactory.createResource("https://example.org/p#M");
        Resource run = mapping.getRequiredProperty(m, mapping.createProperty("http://www.w3.org/ns/prov#wasGeneratedBy")).getResource();
        assertTrue(mapping.contains(run, RDF.type, mapping.createResource(MORK + "ProposalRun")));
        assertEquals(1200, mapping.getRequiredProperty(run, mapping.createProperty(MORK + "inputTokens")).getInt());
        assertTrue(call("mork_propose_mapping", "{\"workspace\":\"" + WS + "\",\"mcn\":\"...\"}").contains("already holds"));
    }
}
