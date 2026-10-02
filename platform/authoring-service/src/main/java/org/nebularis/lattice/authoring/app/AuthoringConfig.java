// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.app;

import java.util.Map;

/**
 * The service's environment variables (plan WA5). Invalid values throw {@link IllegalArgumentException}
 * naming the variable; a secret's value is never included in the message.
 */
public record AuthoringConfig(
    int port,
    String baseIri,
    String fusekiUrl,
    String fusekiDataset,
    String fusekiAdminUser,
    String fusekiAdminPassword,
    String amqpUri,
    boolean seedSamples
) {
    private static final String PORT = "LATTICE_AUTHORING_PORT";
    private static final String BASE_IRI = "LATTICE_AUTHORING_BASE_IRI";
    private static final String FUSEKI_URL = "LATTICE_FUSEKI_URL";
    private static final String FUSEKI_DATASET = "LATTICE_FUSEKI_DATASET";
    private static final String FUSEKI_ADMIN_USER = "LATTICE_FUSEKI_ADMIN_USER";
    private static final String FUSEKI_ADMIN_PASSWORD = "LATTICE_FUSEKI_ADMIN_PASSWORD";
    private static final String AMQP_URI = "LATTICE_AMQP_URI";
    private static final String SEED_SAMPLES = "LATTICE_AUTHORING_SEED_SAMPLES";

    public static AuthoringConfig from(Map<String, String> env) {
        String baseIri = env.getOrDefault(BASE_IRI, "https://example.org/lattice/authoring/");
        if (!baseIri.endsWith("/")) {
            throw new IllegalArgumentException(BASE_IRI + " must end with '/': " + baseIri);
        }
        return new AuthoringConfig(
            parsePort(env.getOrDefault(PORT, "8080")),
            baseIri,
            env.getOrDefault(FUSEKI_URL, "http://localhost:3030"),
            env.getOrDefault(FUSEKI_DATASET, "authoring"),
            env.getOrDefault(FUSEKI_ADMIN_USER, "admin"),
            require(env, FUSEKI_ADMIN_PASSWORD),
            require(env, AMQP_URI),
            Boolean.parseBoolean(env.getOrDefault(SEED_SAMPLES, "false"))
        );
    }

    private static int parsePort(String value) {
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException(PORT + " is not a number: " + value, e);
        }
    }

    private static String require(Map<String, String> env, String name) {
        String value = env.get(name);
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(name + " is required");
        }
        return value;
    }
}
