// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.template;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.authoring.TestSamples;
import org.nebularis.lattice.authoring.json.ContractSchemas;

class CatalogTest {
    private static final ContractSchemas SCHEMAS = new ContractSchemas();

    /** S3-08: the three templates load and summarise, and a bad resource fails naming the file. */
    @Test
    void loadsTheThreeTemplates() {
        TemplateCatalog catalog = new TemplateCatalog(SCHEMAS);

        assertEquals(TemplateCatalog.TEMPLATE_IDS, catalog.list().stream().map(TemplateSummary::templateId).toList());
        assertEquals(new TemplateSummary("software-licence", "Software Licence", "technology", "0.1.0"),
            catalog.list().get(1));
        assertTrue(catalog.get("software-licence").orElseThrow().section("grant").isPresent());
        assertTrue(catalog.raw("facility-agreement").isPresent());
        assertTrue(catalog.get("no-such-template").isEmpty());
    }

    /** S3-08 negative: a resource with no {@code sections}, and a resource that is not there. */
    @Test
    void rejectsATemplateResourceThatDoesNotValidate() {
        IllegalStateException invalid = assertThrows(IllegalStateException.class,
            () -> new TemplateCatalog(SCHEMAS, List.of("contracts/authoring/amqp-topology.json")));
        assertTrue(invalid.getMessage().contains("amqp-topology.json"), invalid.getMessage());

        IllegalStateException missing = assertThrows(IllegalStateException.class,
            () -> new TemplateCatalog(SCHEMAS, List.of("contracts/authoring/templates/no-such.json")));
        assertTrue(missing.getMessage().contains("no-such.json"), missing.getMessage());
    }

    @Test
    void loadsTheThreeSamples() {
        SampleCatalog catalog = new SampleCatalog(SCHEMAS);

        assertEquals(new SampleSummary("software-licence", "Software Licence (sample)", "software-licence"),
            catalog.list().get(1));
        assertEquals(TestSamples.read(TestSamples.FACILITY_AGREEMENT),
            catalog.get("facility-agreement").orElseThrow());
        assertTrue(catalog.raw("property-policy").isPresent());
        assertTrue(catalog.get("no-such-sample").isEmpty());
    }
}
