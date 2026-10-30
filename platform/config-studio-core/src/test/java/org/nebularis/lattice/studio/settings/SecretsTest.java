// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.settings;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class SecretsTest {

    @Test
    void aSecretIsReadFromTheEnvironmentOrTheFileItNames(@TempDir Path dir) throws Exception {
        Path key = Files.writeString(dir.resolve("key"), "pw-test \n");
        assertEquals("pw-direct", Secrets.secret(Map.of("K", " pw-direct "), "K"));
        assertEquals("pw-test ", Secrets.secret(Map.of("K_FILE", key.toString()), "K"));
        Files.writeString(key, "pw-test-2\r\n");
        assertEquals("pw-test-2", Secrets.secret(Map.of("K_FILE", key.toString()), "K"));
        assertNull(Secrets.secret(Map.of(), "K"));
    }

    @Test
    void aSecretSetTwiceMissingOrEmptyIsRefusedWithoutItsValue(@TempDir Path dir) throws Exception {
        Path key = Files.writeString(dir.resolve("key"), "pw-hidden");
        var both = assertThrows(IllegalArgumentException.class, () -> Secrets.secret(Map.of("K", "pw-other", "K_FILE", key.toString()), "K"));
        assertTrue(both.getMessage().contains("both set"));
        assertFalse(both.getMessage().contains("pw-hidden") || both.getMessage().contains("pw-other"));
        assertThrows(IllegalArgumentException.class, () -> Secrets.secret(Map.of("K_FILE", dir.resolve("absent").toString()), "K"));
        Path empty = Files.writeString(dir.resolve("empty"), "\n");
        assertThrows(IllegalArgumentException.class, () -> Secrets.secret(Map.of("K_FILE", empty.toString()), "K"));
        assertThrows(IllegalArgumentException.class, () -> Secrets.required(Map.of(), "K"));
    }
}
