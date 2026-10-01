// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.store;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Optional;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.vocabulary.RDF;
import org.apache.jena.vocabulary.RDFS;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.testcontainers.containers.GenericContainer;
import org.testcontainers.containers.wait.strategy.Wait;
import org.testcontainers.utility.DockerImageName;

/** S5-02: {@link FusekiAuthoringStore} against a real Fuseki container. */
class FusekiAuthoringStoreIT {
    private static GenericContainer<?> fuseki;
    private static FusekiAuthoringStore store;

    @BeforeAll
    static void startFuseki() {
        fuseki = new GenericContainer<>(DockerImageName.parse("stain/jena-fuseki:5.1.0"))
            .withEnv("ADMIN_PASSWORD", "lattice")
            .withExposedPorts(3030)
            .waitingFor(Wait.forHttp("/$/ping").forStatusCode(200));
        fuseki.start();
        store = new FusekiAuthoringStore(
            "http://" + fuseki.getHost() + ":" + fuseki.getMappedPort(3030), "wa5-store-it", "admin", "lattice");
    }

    @AfterAll
    static void stopFuseki() {
        fuseki.stop();
    }

    @Test
    void createsTheDatasetOnceAndTransfersGraphs() {
        store.ensureReady();
        store.ensureReady();
        assertTrue(store.ping());

        String graphIri = "https://example.org/lattice/authoring/doc/wa5/rev/1/wording-graph";
        Model model = ModelFactory.createDefaultModel();
        model.createResource("https://example.org/lattice/authoring/doc/wa5/wording")
            .addProperty(RDF.type, model.createResource("https://www.nebularis.org/neuro-semantic/lattice/wording#Wording"))
            .addProperty(RDFS.label, "WA5 integration test");

        store.putGraph(graphIri, model);
        Model fetched = store.getGraph(graphIri).orElseThrow();
        assertTrue(fetched.isIsomorphicWith(model));

        assertEquals(Optional.empty(),
            store.getGraph("https://example.org/lattice/authoring/doc/wa5/rev/9/wording-graph"));
    }
}
