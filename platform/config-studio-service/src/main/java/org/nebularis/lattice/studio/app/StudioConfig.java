// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.app;

import java.nio.file.Path;
import java.util.Map;

/** The service's settings, read from the environment. A null field means the setting is absent. */
public record StudioConfig(int port, String bind, Path assets, Path staticDir, String fusekiUrl,
                           String fusekiDataset, String fusekiUser, String fusekiPassword, String amqpUri,
                           int writers, int jobRetentionDays) {

    public static StudioConfig fromEnv(Map<String, String> env) {
        int port;
        try {
            port = Integer.parseInt(env.getOrDefault("LATTICE_STUDIO_PORT", "8090").trim());
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("LATTICE_STUDIO_PORT is not a number");
        }
        if (port < 0 || port > 65535) {
            throw new IllegalArgumentException("LATTICE_STUDIO_PORT is out of range");
        }
        int writers = number(env, "LATTICE_STUDIO_WRITERS", 1);
        int retention = number(env, "LATTICE_STUDIO_JOB_RETENTION_DAYS", 30);
        if (retention < 1) {
            throw new IllegalArgumentException("LATTICE_STUDIO_JOB_RETENTION_DAYS is at least 1");
        }
        return new StudioConfig(port, env.getOrDefault("LATTICE_STUDIO_BIND", "127.0.0.1"),
            Path.of(env.getOrDefault("LATTICE_STUDIO_ASSETS", ".build/config-studio")),
            optional(env, "LATTICE_STUDIO_STATIC") == null ? null : Path.of(optional(env, "LATTICE_STUDIO_STATIC")),
            optional(env, "LATTICE_FUSEKI_URL"), env.getOrDefault("LATTICE_FUSEKI_DATASET", "studio"),
            optional(env, "LATTICE_FUSEKI_USER"), optional(env, "LATTICE_FUSEKI_PASSWORD"),
            optional(env, "LATTICE_AMQP_URI"), writers, retention);
    }

    /** 0 writers runs no writer in this instance, which then relies on another's. */
    private static int number(Map<String, String> env, String name, int fallback) {
        try {
            return Integer.parseInt(env.getOrDefault(name, Integer.toString(fallback)).trim());
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException(name + " is not a number");
        }
    }

    private static String optional(Map<String, String> env, String name) {
        String value = env.get(name);
        return value == null || value.isBlank() ? null : value.trim();
    }
}
