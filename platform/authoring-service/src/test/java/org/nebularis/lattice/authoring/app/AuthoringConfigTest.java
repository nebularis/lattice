// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.app;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Map;
import org.junit.jupiter.api.Test;

class AuthoringConfigTest {
    private static final Map<String, String> REQUIRED = Map.of(
        "LATTICE_FUSEKI_ADMIN_PASSWORD", "s3cret",
        "LATTICE_AMQP_URI", "amqp://guest:guest@localhost:5672"
    );

    /** S5-01: defaults, overrides, and each invalid value naming its variable, never the password. */
    @Test
    void appliesDefaults() {
        AuthoringConfig config = AuthoringConfig.from(REQUIRED);

        assertEquals(8080, config.port());
        assertEquals("https://example.org/lattice/authoring/", config.baseIri());
        assertEquals("http://localhost:3030", config.fusekiUrl());
        assertEquals("authoring", config.fusekiDataset());
        assertEquals("admin", config.fusekiAdminUser());
        assertEquals("s3cret", config.fusekiAdminPassword());
        assertEquals("amqp://guest:guest@localhost:5672", config.amqpUri());
        assertFalse(config.seedSamples());
    }

    @Test
    void appliesOverrides() {
        Map<String, String> env = merge(REQUIRED, Map.of(
            "LATTICE_AUTHORING_PORT", "9090",
            "LATTICE_AUTHORING_BASE_IRI", "https://example.com/lattice/",
            "LATTICE_FUSEKI_URL", "http://fuseki:3030",
            "LATTICE_FUSEKI_DATASET", "wa5",
            "LATTICE_FUSEKI_ADMIN_USER", "operator",
            "LATTICE_AUTHORING_SEED_SAMPLES", "true"
        ));

        AuthoringConfig config = AuthoringConfig.from(env);

        assertEquals(9090, config.port());
        assertEquals("https://example.com/lattice/", config.baseIri());
        assertEquals("http://fuseki:3030", config.fusekiUrl());
        assertEquals("wa5", config.fusekiDataset());
        assertEquals("operator", config.fusekiAdminUser());
        assertTrue(config.seedSamples());
    }

    @Test
    void rejectsANonNumericPort() {
        Map<String, String> env = merge(REQUIRED, Map.of("LATTICE_AUTHORING_PORT", "abc"));

        IllegalArgumentException error = assertThrows(IllegalArgumentException.class, () -> AuthoringConfig.from(env));

        assertTrue(error.getMessage().contains("LATTICE_AUTHORING_PORT"), error.getMessage());
        assertTrue(error.getMessage().contains("abc"), error.getMessage());
        assertFalse(error.getMessage().contains("s3cret"), error.getMessage());
    }

    @Test
    void rejectsABaseIriWithNoTrailingSlash() {
        Map<String, String> env = merge(REQUIRED, Map.of("LATTICE_AUTHORING_BASE_IRI", "https://example.com"));

        IllegalArgumentException error = assertThrows(IllegalArgumentException.class, () -> AuthoringConfig.from(env));

        assertTrue(error.getMessage().contains("LATTICE_AUTHORING_BASE_IRI"), error.getMessage());
        assertFalse(error.getMessage().contains("s3cret"), error.getMessage());
    }

    @Test
    void rejectsAMissingPasswordWithoutEchoingIt() {
        Map<String, String> env = Map.of("LATTICE_AMQP_URI", "amqp://guest:guest@localhost:5672");

        IllegalArgumentException error = assertThrows(IllegalArgumentException.class, () -> AuthoringConfig.from(env));

        assertTrue(error.getMessage().contains("LATTICE_FUSEKI_ADMIN_PASSWORD"), error.getMessage());
    }

    @Test
    void rejectsAMissingAmqpUriWithoutEchoingIt() {
        Map<String, String> env = Map.of("LATTICE_FUSEKI_ADMIN_PASSWORD", "s3cret-password-value");

        IllegalArgumentException error = assertThrows(IllegalArgumentException.class, () -> AuthoringConfig.from(env));

        assertTrue(error.getMessage().contains("LATTICE_AMQP_URI"), error.getMessage());
        assertFalse(error.getMessage().contains("s3cret-password-value"), error.getMessage());
    }

    private static Map<String, String> merge(Map<String, String> base, Map<String, String> overrides) {
        var merged = new java.util.HashMap<>(base);
        merged.putAll(overrides);
        return merged;
    }
}
