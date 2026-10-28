// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.Map;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.model.Parts;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.writes.Command;

/** The library and assembly parts, the assemble job, and the record graph its update carries (CB1). */
class AssemblyTest {
    private static final String WS = Fixture.id(1);
    private static final String WRD = "https://www.nebularis.org/neuro-semantic/lattice/wording#";
    private static final String PREFIXES = Fixture.PREFIXES + "@prefix wrd: <" + WRD + "> .\n";
    private static final String LIBRARY = PREFIXES + "ex:form a wrd:Wording ; wrd:directlyComprises ex:c1 .\nex:c1 a wrd:Text .\n";
    private static final String ASSEMBLY = PREFIXES + """
        ex:a a cst:Assembly ; cst:assembles ex:form ; cst:choice ex:c1 ; cst:setting ex:v .
        ex:v a wrd:VariableValue ; wrd:forVariable ex:margin ; wrd:literalValue "2.5" .
        """;

    @TempDir Path dir;
    Fixture f;

    @BeforeEach
    void setUp() throws IOException {
        f = new Fixture(Fixture.assetsDir(dir));
        assertEquals(201, f.createWorkspace("Builder").status());
    }

    private static Model parse(String turtle) {
        return org.apache.jena.riot.RDFParser.fromString(turtle, org.apache.jena.riot.Lang.TURTLE).toModel();
    }

    @Test
    void formsGoToTheLibraryAndAnAssemblyWithItsValuesToTheAssembly() {
        Map<Resource, String> owners = Parts.owners(parse(LIBRARY + ASSEMBLY.substring(PREFIXES.length())));
        Map<String, String> byName = new java.util.HashMap<>();
        owners.forEach((r, part) -> byName.put(r.isURIResource() ? r.getURI().substring("https://example.org/".length()) : r.toString(), part));
        assertEquals("library", byName.get("form"));
        assertEquals("library", byName.get("c1"));
        assertEquals("assembly", byName.get("a"));
        assertEquals("assembly", byName.get("v"), "a value record uses Wording's terms but belongs to its assembly");
    }

    @Test
    void bothPartsAreSavedUnderTheirOwnRevisions() {
        assertEquals(204, f.put("/api/workspaces/" + WS + "/graphs/library", "\"0\"", LIBRARY).status());
        assertEquals(204, f.put("/api/workspaces/" + WS + "/graphs/assembly", "\"0\"", ASSEMBLY).status());
        assertEquals(422, f.put("/api/workspaces/" + WS + "/graphs/library", "\"1\"", ASSEMBLY).status(), "an assembly is not a form");
    }

    @Test
    void anAssembleJobIsQueuedWithItsInput() {
        ApiResponse job = f.post("/api/workspaces/" + WS + "/jobs", "kind=assemble&target=assembly", LIBRARY + ASSEMBLY.substring(PREFIXES.length()));
        assertEquals(202, job.status(), () -> new String(job.body(), StandardCharsets.UTF_8));
        String id = job.headers().get("Location").substring("/api/jobs/".length());
        Model description = f.store.graph(Graphs.job(id));
        Resource node = description.createResource(Graphs.job(id));
        assertTrue(description.contains(node, Cst.kind, Cst.Assemble));
        assertTrue(description.contains(node, Cst.target, Cst.target("assembly")));
        assertEquals(400, f.post("/api/workspaces/" + WS + "/jobs", "kind=assemble&target=library", LIBRARY).status());
    }

    private String queued(String kind, String target) {
        ApiResponse job = f.post("/api/workspaces/" + WS + "/jobs", "kind=" + kind + "&target=" + target, LIBRARY);
        assertEquals(202, job.status());
        return job.headers().get("Location").substring("/api/jobs/".length());
    }

    private Dataset update(String job, Model record) {
        Model description = f.store.graph(Graphs.job(job));
        Resource node = description.createResource(Graphs.job(job));
        description.removeAll(node, Cst.status, null);
        node.addProperty(Cst.status, Cst.Succeeded);
        Dataset d = DatasetFactory.create();
        d.addNamedModel(Graphs.job(job), description);
        if (record != null) {
            d.addNamedModel(Graphs.jobRecord(job), record);
        }
        return d;
    }

    @Test
    void anAssembleJobsUpdateWritesItsRecordWhichGoesWithTheJob() {
        String job = queued("assemble", "assembly");
        Model record = ModelFactory.createDefaultModel();
        record.createResource(Graphs.jobRecord(job) + "/record-1").addProperty(org.apache.jena.vocabulary.RDF.type, record.createResource(WRD + "AssembledWording"))
            .addProperty(record.createProperty(WRD + "includes"), record.createResource("https://example.org/c1"));
        assertEquals(200, f.writes.send(new Command(java.util.UUID.randomUUID().toString(), "worker", Command.Type.JOB_UPDATE, WS, job, null, null, null, null, null, update(job, record))).status());
        assertTrue(f.store.graph(Graphs.jobRecord(job)).isIsomorphicWith(record));
        assertEquals(204, f.send("DELETE", "/api/jobs/" + job, null, Map.of(), new byte[0]).status());
        assertTrue(f.store.graph(Graphs.jobRecord(job)).isEmpty());
    }

    @Test
    void aRecordIsRefusedFromAnotherKindOfJobOrWithForeignTerms() {
        Model record = ModelFactory.createDefaultModel();
        record.createResource("https://example.org/r").addProperty(record.createProperty(WRD + "includes"), record.createResource("https://example.org/c1"));
        String validate = queued("validate", "library");
        assertEquals(400, f.writes.send(Command.jobUpdate(WS, validate, update(validate, record))).status());

        String assemble = queued("assemble", "assembly");
        record.createResource("https://example.org/r").addProperty(record.createProperty("https://www.nebularis.org/neuro-semantic/lattice/persistence#label"), "x");
        assertEquals(400, f.writes.send(Command.jobUpdate(WS, assemble, update(assemble, record))).status());
        assertFalse(f.store.graph(Graphs.jobRecord(assemble)).size() > 0);
    }
}
