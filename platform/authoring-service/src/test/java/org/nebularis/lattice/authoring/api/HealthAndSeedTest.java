// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.api;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;
import java.util.Optional;
import org.apache.jena.rdf.model.Model;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.authoring.ApiFixture;
import org.nebularis.lattice.authoring.app.SampleSeeder;
import org.nebularis.lattice.authoring.jobs.JobRegistry;
import org.nebularis.lattice.authoring.store.AuthoringStore;

class HealthAndSeedTest {

    /** S4-13: a store whose ping fails gives a degraded health response, amqp still up. */
    @Test
    void reportsDegradedHealthWhenTheStoreCannotBeReached() {
        ApiFixture fx = new ApiFixture();
        AuthoringStore failingStore = new AuthoringStore() {
            @Override
            public void ensureReady() {
            }

            @Override
            public boolean ping() {
                return false;
            }

            @Override
            public void putGraph(String graphIri, Model model) {
                throw new UnsupportedOperationException();
            }

            @Override
            public Optional<Model> getGraph(String graphIri) {
                throw new UnsupportedOperationException();
            }
        };
        AuthoringApi api = new AuthoringApi(fx.schemas, fx.templates, fx.samples, fx.minter, fx.mapper,
            fx.validator, fx.detector, fx.templateFindings, fx.conformanceChecker, failingStore, fx.registry,
            fx.bus, new JobRegistry(), fx.clock);

        ApiResponse<HealthView> response = api.health();

        assertEquals(503, response.status());
        assertEquals(HealthView.DEGRADED, response.body().status());
        assertEquals(HealthView.DOWN, response.body().fuseki());
        assertEquals(HealthView.UP, response.body().amqp());
    }

    /** S4-14: seeding twice on an empty registry seeds the three samples once each. */
    @Test
    void seedsEachSampleOnceOnly() {
        ApiFixture fx = new ApiFixture();
        SampleSeeder seeder = new SampleSeeder(fx.samples, fx.registry, fx.api);

        assertEquals(3, seeder.seed());
        assertEquals(3, fx.registry.documentIds().size());
        assertEquals(3, fx.bus.published().size());
        for (String sampleId : List.of("facility-agreement", "software-licence", "property-policy")) {
            String documentId = fx.samples.raw(sampleId).orElseThrow().get("documentId").asText();
            assertEquals(1, fx.registry.latestRevision(documentId));
        }

        assertEquals(0, seeder.seed());
        assertEquals(3, fx.bus.published().size());
    }
}
