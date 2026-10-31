// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Map;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.vocabulary.RDF;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.StudioOperations;
import org.nebularis.lattice.studio.store.StudioStore;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.DirectWrites;
import org.nebularis.lattice.studio.writes.Writer;

class SweeperTest {
    private static final String WS = "00000000-0000-4000-8000-000000000001";
    private static final Instant AT = Instant.parse("2026-10-27T10:00:00Z");

    private static final StudioOperations OPS = StudioOperations.load(java.nio.file.Path.of(System.getProperty("studio.assets"), "persistence"), 1L);

    private final StudioStore store = StudioStore.inMemory();
    private final DirectWrites writes = new DirectWrites(new Writer(store, OPS, Clock.fixed(AT, ZoneOffset.UTC)));

    /** A finished job of the workspace, as the service submits it and the worker ends it. */
    private String job(String id, String finished) {
        String jobIri = Graphs.job(id);
        Model m = ModelFactory.createDefaultModel();
        Resource job = m.createResource(jobIri);
        job.addProperty(RDF.type, Cst.Job).addProperty(Cst.workspace, m.createResource(Graphs.workspace(WS)))
            .addProperty(Cst.configGraph, m.createResource(Graphs.jobInput(id)))
            .addProperty(Cst.baselineGraph, m.createResource(Graphs.baseline(WS))).addProperty(Cst.status, Cst.Queued);
        Dataset submitted = DatasetFactory.create();
        submitted.addNamedModel(jobIri, m);
        Model input = ModelFactory.createDefaultModel();
        input.add(input.createResource("urn:x:c"), input.createProperty("https://www.nebularis.org/neuro-semantic/lattice/surface#label"), "one");
        submitted.addNamedModel(Graphs.jobInput(id), input);
        assertEquals(200, writes.send(Command.submitJob(WS, id, submitted)).status());
        Model done = ModelFactory.createDefaultModel().add(m);
        done.removeAll(job, Cst.status, null);
        done.add(job, Cst.status, Cst.Succeeded).add(job, Cst.finishedAt, done.createTypedLiteral(finished, XSDDatatype.XSDdateTime));
        Dataset update = DatasetFactory.create();
        update.addNamedModel(jobIri, done);
        assertEquals(200, writes.send(Command.jobUpdate(WS, id, update)).status());
        return id;
    }

    @Test
    void sweepsOnlyJobsFinishedBeforeTheRetention() {
        assertEquals(200, writes.send(Command.create(WS, "Plan", AT, null, ModelFactory.createDefaultModel())).status());
        String old = job("00000000-0000-4000-8000-000000000002", "2026-09-01T00:00:00Z");
        String fresh = job("00000000-0000-4000-8000-000000000003", "2026-10-27T00:00:00Z");
        Clock now = Clock.fixed(Instant.parse("2026-10-28T00:00:00Z"), ZoneOffset.UTC);
        try (Sweeper sweeper = new Sweeper(store, writes, now, Duration.ofDays(30))) {
            assertEquals(1, sweeper.sweep());
        }
        assertTrue(store.graph(Graphs.job(old)).isEmpty());
        assertTrue(store.graph(Graphs.jobReceipts(old)).isEmpty());
        assertTrue(!store.graph(Graphs.job(fresh)).isEmpty());
    }

    @Test
    void theConfigNeedsTheStoreTheBrokerAndTheStream() {
        Map<String, String> env = Map.of("LATTICE_FUSEKI_URL", "http://f", "LATTICE_AMQP_URI", "amqp://a", "LATTICE_STREAM_URI", "rabbitmq-stream://s");
        WriterConfig c = WriterConfig.fromEnv(env);
        assertEquals("studio-write", c.fusekiDataset());
        assertEquals(30, c.jobRetentionDays());
        assertEquals(java.nio.file.Path.of(".build/config-studio"), c.assets());
        assertEquals(1L, c.epoch());
        WriterConfig set = WriterConfig.fromEnv(Map.of("LATTICE_FUSEKI_URL", "http://f", "LATTICE_AMQP_URI", "amqp://a",
            "LATTICE_STREAM_URI", "rabbitmq-stream://s", "LATTICE_STUDIO_ASSETS", "/srv/assets", "LATTICE_STUDIO_EPOCH", "3"));
        assertEquals(java.nio.file.Path.of("/srv/assets"), set.assets());
        assertEquals(3L, set.epoch());
        for (String missing : env.keySet()) {
            Map<String, String> less = new java.util.HashMap<>(env);
            less.remove(missing);
            org.junit.jupiter.api.Assertions.assertThrows(IllegalArgumentException.class, () -> WriterConfig.fromEnv(less), missing);
        }
    }
}
