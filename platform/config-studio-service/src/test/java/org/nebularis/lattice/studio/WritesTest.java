// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.util.Map;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.vocabulary.RDFS;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.writes.Codec;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.Reply;
import org.nebularis.lattice.studio.writes.Writer;

/** The writer of a partition, the codec of its messages, and export and import. */
class WritesTest {
    private static final String WS = Fixture.id(1);
    private static final String SURFACE = "/api/workspaces/" + WS + "/graphs/surface";
    private static final String CONFIG = Fixture.PREFIXES
        + "ex:cfg <https://www.nebularis.org/neuro-semantic/lattice/surface#label> \"one\" .";

    @TempDir Path dir;
    Fixture f;
    Writer writer;

    @BeforeEach
    void setUp() throws IOException {
        f = new Fixture(Fixture.assetsDir(dir));
        writer = new Writer(f.store, Clock.systemUTC());
        assertEquals(201, f.createWorkspace("Plan").status());
    }

    /** Submits a validation, returning the job's id. */
    private String job() {
        ApiResponse r = f.post("/api/workspaces/" + WS + "/jobs", "kind=validate&target=surface", CONFIG);
        assertEquals(202, r.status());
        return r.headers().get("Location").substring("/api/jobs/".length());
    }

    private static Dataset only(String graph, Model m) {
        Dataset d = DatasetFactory.create();
        d.addNamedModel(graph, m);
        return d;
    }

    @Test
    void aCommandSurvivesTheWire() {
        Model graph = Fixture.model(CONFIG);
        Command sent = Command.save(WS, "surface", 3, Instant.parse("2026-10-28T09:00:00Z"), graph);
        Command got = Codec.decode(Codec.headers(sent), Codec.body(sent));
        assertNotNull(got);
        assertEquals(sent.type(), got.type());
        assertEquals(WS, got.workspace());
        assertEquals("surface", got.part());
        assertEquals(3L, got.expect());
        assertEquals(sent.at(), got.at());
        assertTrue(graph.isIsomorphicWith(got.body().getDefaultModel()));
        Reply reply = Codec.reply(Codec.reply(Reply.stale(4)));
        assertEquals(412, reply.status());
        assertEquals(4, reply.revision());
    }

    @Test
    void aMessageThatIsNotACommandDecodesToNothing() {
        assertNull(Codec.decode(Map.of("command", "drop-everything", "workspace", WS), new byte[0]));
        assertNull(Codec.decode(Map.of("command", "save", "workspace", WS), "not n-quads".getBytes(StandardCharsets.UTF_8)));
        assertEquals(503, Codec.reply(Map.of()).status());
    }

    @Test
    void theWriterKeepsTheRevisionGuardTheServiceUsedToHold() {
        Model graph = Fixture.model(CONFIG);
        Instant at = Instant.parse("2026-10-28T09:00:00Z");
        assertEquals(Reply.ok(1), writer.apply(Command.save(WS, "surface", 0, at, graph)));
        Reply stale = writer.apply(Command.save(WS, "surface", 0, at, graph));
        assertEquals(412, stale.status());
        assertEquals(1, stale.revision());
        assertEquals(404, writer.apply(Command.save(Fixture.id(9), "surface", 0, at, graph)).status());
    }

    @Test
    void theWriterRefusesWhatItsSenderShouldHaveRefused() {
        Instant at = Instant.parse("2026-10-28T09:00:00Z");
        assertEquals(400, writer.apply(Command.save("not-an-id", "surface", 0, at, Fixture.model(CONFIG))).status());
        assertEquals(400, writer.apply(Command.save(WS, "nonsense", 0, at, Fixture.model(CONFIG))).status());
        assertEquals(400, writer.apply(Command.save(WS, "persistence", 0, at, Fixture.model(CONFIG))).status(),
            "a surface subject in the persistence graph");
        assertEquals(400, writer.apply(Command.create(WS, "Again", at, null, ModelFactory.createDefaultModel())).status(),
            "the workspace exists");
        assertEquals(400, writer.apply(Command.create(Fixture.id(5), "x", at, "../etc", ModelFactory.createDefaultModel())).status());
    }

    @Test
    void aJobUpdateMayChangeOnlyTheStatusAndTheResults() {
        String job = job();
        String jobIri = Graphs.job(job);
        Model current = f.store.graph(jobIri);
        Resource node = current.createResource(jobIri);

        Model running = ModelFactory.createDefaultModel().add(current);
        running.removeAll(node, Cst.status, null);
        running.add(node, Cst.status, Cst.Running);
        assertEquals(200, writer.apply(Command.jobUpdate(WS, job, only(jobIri, running))).status());

        // rdflib writes back a dateTime the service wrote with Z as +00:00, the same value.
        Model rewritten = ModelFactory.createDefaultModel().add(running);
        String submitted = rewritten.getProperty(node, Cst.submittedAt).getString();
        rewritten.removeAll(node, Cst.submittedAt, null);
        rewritten.add(node, Cst.submittedAt, rewritten.createTypedLiteral(submitted.replace("Z", "+00:00"),
            org.apache.jena.datatypes.xsd.XSDDatatype.XSDdateTime));
        assertEquals(200, writer.apply(Command.jobUpdate(WS, job, only(jobIri, rewritten))).status());

        Model moved = ModelFactory.createDefaultModel().add(running);
        moved.removeAll(node, Cst.configGraph, null);
        moved.add(node, Cst.configGraph, moved.createResource(Graphs.baseline(WS, 1)));
        assertEquals(400, writer.apply(Command.jobUpdate(WS, job, only(jobIri, moved))).status(), "a job pointed at another graph");
        assertEquals(400, writer.apply(Command.jobUpdate(Fixture.id(7), job, only(jobIri, running))).status(), "another workspace's job");

        assertEquals(204, f.send("DELETE", "/api/jobs/" + job, Map.of(), null).status());
        assertEquals(404, writer.apply(Command.jobUpdate(WS, job, only(jobIri, running))).status(), "a deleted job stays deleted");
        assertTrue(f.store.graph(jobIri).isEmpty());
    }

    @Test
    void theWriterRefusesAJobWhoseContextGraphIsNotAConfigurationPartOfItsWorkspace() {
        String job = job();
        String fresh = Fixture.id(8);
        Model description = ModelFactory.createDefaultModel();
        f.store.graph(Graphs.job(job)).listStatements().forEachRemaining(s -> {
            if (!s.getPredicate().equals(Cst.configGraph)) {
                description.add(s.getSubject().isURIResource() ? description.createResource(Graphs.job(fresh)) : s.getSubject(), s.getPredicate(), s.getObject());
            }
        });
        Resource node = description.createResource(Graphs.job(fresh));
        node.addProperty(Cst.configGraph, description.createResource(Graphs.jobInput(fresh)));
        Dataset good = only(Graphs.job(fresh), description);
        good.addNamedModel(Graphs.jobInput(fresh), Fixture.model(CONFIG));
        assertTrue(description.contains(node, Cst.contextGraph), "the service named the other parts");
        Model foreign = ModelFactory.createDefaultModel().add(description);
        foreign.add(node, Cst.contextGraph, foreign.createResource(Graphs.config(Fixture.id(7), "mapping")));
        Dataset bad = only(Graphs.job(fresh), foreign);
        bad.addNamedModel(Graphs.jobInput(fresh), Fixture.model(CONFIG));
        assertEquals(400, writer.apply(Command.submitJob(WS, fresh, bad)).status(), "another workspace's graph as context");
        assertEquals(200, writer.apply(Command.submitJob(WS, fresh, good)).status());
    }

    @Test
    void deletingAWorkspaceDeletesItsJobs() {
        String job = job();
        assertEquals(204, f.send("DELETE", "/api/workspaces/" + WS, Map.of(), null).status());
        assertTrue(f.store.graph(Graphs.job(job)).isEmpty());
        assertTrue(f.store.graph(Graphs.jobInput(job)).isEmpty());
    }

    @Test
    void anExportImportsAsANewWorkspaceWithItsRevisions() {
        assertEquals(204, f.put(SURFACE, "\"0\"", CONFIG).status());
        ApiResponse export = f.get("/api/workspaces/" + WS + "/export");
        assertEquals(200, export.status());
        assertTrue(export.headers().get("Content-Type").startsWith("application/trig"));
        assertEquals("attachment; filename=\"Plan.trig\"", export.headers().get("Content-Disposition"));

        ApiResponse imported = f.send("POST", "/api/workspaces", null,
            Map.of("content-type", "application/trig", "slug", "Copy"), export.body());
        assertEquals(201, imported.status());
        String copy = Fixture.id(2);
        assertEquals("/api/workspaces/" + copy, imported.headers().get("Location"));
        Model description = f.store.graph(Graphs.workspace(copy));
        Resource ws = description.createResource(Graphs.workspace(copy));
        assertEquals("Copy", ws.getProperty(RDFS.label).getString());
        assertEquals(1, ws.getProperty(Cst.surfaceRevision).getLong());
        assertEquals(Graphs.baseline(copy, 1), ws.getProperty(Cst.baselineGraph).getResource().getURI());
        assertTrue(Fixture.model(CONFIG).isIsomorphicWith(f.store.graph(Graphs.config(copy, "surface"))));
        assertTrue(f.store.graph(Graphs.config(WS, "surface")).isIsomorphicWith(f.store.graph(Graphs.config(copy, "surface"))),
            "the original is untouched");
    }

    @Test
    void anImportOfAnotherShapeIsRefused() {
        String twoWorkspaces = "<" + Graphs.workspace(Fixture.id(8)) + "> { <urn:a> <urn:p> 1 }\n"
            + "<" + Graphs.workspace(Fixture.id(9)) + "> { <urn:a> <urn:p> 1 }\n";
        String strayGraph = "<" + Graphs.workspace(Fixture.id(8)) + "> { <urn:a> <urn:p> 1 }\n<urn:elsewhere> { <urn:a> <urn:p> 1 }\n";
        for (String body : new String[] {twoWorkspaces, strayGraph, "{ <urn:a> <urn:p> 1 }", "<" + Graphs.workspace(Fixture.id(8)) + "> { <urn:a> <urn:p> 1 }"}) {
            ApiResponse r = f.send("POST", "/api/workspaces", null, Map.of("content-type", "application/trig"),
                body.getBytes(StandardCharsets.UTF_8));
            assertEquals(422, r.status(), body);
        }
        assertEquals(400, f.send("POST", "/api/workspaces", null, Map.of("content-type", "application/trig"),
            "not trig {".getBytes(StandardCharsets.UTF_8)).status());
    }

    @Test
    void aWorkspaceRemembersTheSampleItCameFrom() {
        ApiResponse r = f.send("POST", "/api/workspaces", "sample=lending", Map.of("content-type", Fixture.TURTLE),
            (Fixture.PREFIXES + "ex:a ex:p ex:b .").getBytes(StandardCharsets.UTF_8));
        assertEquals(201, r.status());
        String id = r.headers().get("Location").substring("/api/workspaces/".length());
        Resource ws = f.store.graph(Graphs.workspace(id)).createResource(Graphs.workspace(id));
        assertEquals("urn:lattice:studio:sample:lending", ws.getProperty(Cst.fromSample).getResource().getURI());
        for (String bad : new String[] {"sample=missing", "sample=..%2Fx"}) {
            assertEquals(400, f.send("POST", "/api/workspaces", bad, Map.of("content-type", Fixture.TURTLE),
                (Fixture.PREFIXES + "ex:a ex:p ex:b .").getBytes(StandardCharsets.UTF_8)).status(), bad);
        }
    }

}
