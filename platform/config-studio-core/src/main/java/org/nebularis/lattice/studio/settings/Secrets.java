// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.settings;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

/**
 * Secrets read from the environment or from a file the environment names, the env and file reference implementations of
 * the {@code SecretProvider} seam (ADR-A71), as the worker reads them.
 *
 * <p>A secret {@code NAME} is read from the file {@code NAME_FILE} names when that is set, the value alone, as Docker and
 * Kubernetes secrets and the Vault Agent and CSI driver write them, or else from {@code NAME}. Setting both is refused. One
 * trailing line ending is dropped and nothing else is changed. A secret's value is never put into an error message.
 */
public final class Secrets {

    private Secrets() {
    }

    /** The secret's value, or null when neither {@code name} nor {@code name_FILE} is set or the value is blank. */
    public static String secret(Map<String, String> env, String name) {
        String path = trimmed(env.get(name + "_FILE"));
        String direct = trimmed(env.get(name));
        if (path != null && direct != null) {
            throw new IllegalArgumentException(name + " and " + name + "_FILE are both set, and only one may be");
        }
        if (path == null) {
            return direct;
        }
        String value;
        try {
            value = Files.readString(Path.of(path), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new IllegalArgumentException(name + "_FILE names " + path + ", which cannot be read (" + e.getClass().getSimpleName() + ")");
        }
        value = value.endsWith("\r\n") ? value.substring(0, value.length() - 2) : value.endsWith("\n") ? value.substring(0, value.length() - 1) : value;
        if (value.isEmpty()) {
            throw new IllegalArgumentException(name + "_FILE names " + path + ", which is empty");
        }
        return value;
    }

    /** As {@link #secret}, refusing a secret that is not set. */
    public static String required(Map<String, String> env, String name) {
        String value = secret(env, name);
        if (value == null) {
            throw new IllegalArgumentException(name + " or " + name + "_FILE is required");
        }
        return value;
    }

    private static String trimmed(String value) {
        return value == null || value.isBlank() ? null : value.trim();
    }
}
