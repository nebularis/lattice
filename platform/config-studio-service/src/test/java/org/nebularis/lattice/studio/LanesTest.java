// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.jobs.Lanes;
import org.nebularis.lattice.studio.jobs.Topology;
import org.nebularis.lattice.studio.store.Cst;

/** Which queue a job goes to (plan studio-worker-liveness, WL-Q3). */
class LanesTest {
    private static final String WS = Fixture.id(1);
    private static final String PATH = "/api/workspaces/" + WS + "/jobs";
    private static final String CONFIG = Fixture.PREFIXES + "ex:cfg <https://www.nebularis.org/neuro-semantic/lattice/surface#label> \"one\" .";
    private static final String JOB = "urn:lattice:studio:job:00000000-0000-0000-0000-000000000009";

    @TempDir Path dir;
    Fixture f;

    @BeforeEach
    void setUp() throws IOException {
        f = new Fixture(Fixture.assetsDir(dir));
        f.createWorkspace("One");
    }

    private static Model job(Resource kind, Resource target) {
        Model m = ModelFactory.createDefaultModel();
        Resource job = m.createResource(JOB).addProperty(Cst.kind, kind);
        if (target != null) {
            job.addProperty(Cst.target, target);
        }
        return m;
    }

    @Test
    void aProposalByALanguageModelAndAPublicationAreLong() {
        assertTrue(Lanes.isLong(job(Cst.Propose, Cst.LanguageModelProposer), JOB));
        assertTrue(Lanes.isLong(job(Cst.Propose, Cst.MappingLanguageModelProposer), JOB));
        assertTrue(Lanes.isLong(job(Cst.Publish, Cst.Surface), JOB));
    }

    @Test
    void everyOtherJobIsShort() {
        assertFalse(Lanes.isLong(job(Cst.Validate, Cst.Surface), JOB));
        assertFalse(Lanes.isLong(job(Cst.Compile, Cst.Persistence), JOB));
        assertFalse(Lanes.isLong(job(Cst.Propose, Cst.SentenceFormProposer), JOB));
        assertFalse(Lanes.isLong(job(Cst.Propose, Cst.OdrlProposer), JOB));
        assertFalse(Lanes.isLong(job(Cst.Rebuild, null), JOB));
        assertFalse(Lanes.isLong(job(Cst.Assemble, null), JOB));
    }

    @Test
    void aLongJobHasItsOwnRoutingKeyAndQueue() {
        assertEquals(Topology.JOBS_LONG_ROUTING_KEY, Lanes.routingKey(true));
        assertEquals(Topology.JOBS_ROUTING_KEY, Lanes.routingKey(false));
        assertFalse(Topology.JOBS_QUEUE.equals(Topology.JOBS_LONG_QUEUE));
    }

    @Test
    void theServicePublishesAProposalByAModelToTheLongLaneAndAValidationToTheShortOne() {
        assertEquals(202, f.post(PATH, "kind=validate&target=surface", CONFIG).status());
        assertEquals(202, f.post(PATH, "kind=propose&target=language-model", CONFIG).status());
        assertEquals(202, f.post(PATH, "kind=propose&target=sentence-forms", CONFIG).status());
        String validation = "urn:lattice:studio:job:" + Fixture.id(2);
        String proposal = "urn:lattice:studio:job:" + Fixture.id(3);
        String sentences = "urn:lattice:studio:job:" + Fixture.id(4);
        assertEquals(List.of(validation, proposal, sentences), f.bus.published());
        assertEquals(List.of(proposal), f.bus.publishedLong());
    }
}
