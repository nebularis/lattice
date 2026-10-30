// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writer;

import java.util.Map;
import org.nebularis.lattice.studio.settings.Secrets;

/** The writer's settings, read from the environment. A null field means the setting is absent. */
public record WriterConfig(String fusekiUrl, String fusekiDataset, String fusekiUser, String fusekiPassword,
                           String amqpUri, String streamUri, int jobRetentionDays) {

    public static WriterConfig fromEnv(Map<String, String> env) {
        String fuseki = required(env, "LATTICE_FUSEKI_URL");
        String amqp = Secrets.required(env, "LATTICE_AMQP_URI");
        String stream = Secrets.required(env, "LATTICE_STREAM_URI");
        int retention;
        try {
            retention = Integer.parseInt(env.getOrDefault("LATTICE_STUDIO_JOB_RETENTION_DAYS", "30").trim());
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("LATTICE_STUDIO_JOB_RETENTION_DAYS is not a number");
        }
        if (retention < 1) {
            throw new IllegalArgumentException("LATTICE_STUDIO_JOB_RETENTION_DAYS is at least 1");
        }
        return new WriterConfig(fuseki, env.getOrDefault("LATTICE_FUSEKI_WRITE_DATASET", "studio-write"),
            optional(env, "LATTICE_FUSEKI_USER"), Secrets.secret(env, "LATTICE_FUSEKI_PASSWORD"), amqp, stream, retention);
    }

    private static String required(Map<String, String> env, String name) {
        String value = optional(env, name);
        if (value == null) {
            throw new IllegalArgumentException(name + " is required");
        }
        return value;
    }

    private static String optional(Map<String, String> env, String name) {
        String value = env.get(name);
        return value == null || value.isBlank() ? null : value.trim();
    }
}
