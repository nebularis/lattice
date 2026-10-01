// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.app;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Path;
import java.util.List;
import java.util.jar.JarFile;
import org.junit.jupiter.api.Test;

/** S5-07: the shaded jar's {@code --self-check} runs standalone, proving Jena initialises from it. */
class SelfCheckIT {
    private static final String LIFECYCLE_SERVICE = "META-INF/services/org.apache.jena.sys.JenaSubsystemLifecycle";

    /**
     * The five Jena subsystems that must each contribute a line to the merged services file
     * (plan WA5 self-probe): one jar per subsystem, so a plain (non-merging) shade would keep only
     * whichever jar's file is processed last and silently drop the rest.
     */
    private static final List<String> EXPECTED_SUBSYSTEMS = List.of(
        "org.apache.jena.sys.InitJenaCore",
        "org.apache.jena.riot.system.InitRIOT",
        "org.apache.jena.sparql.system.InitARQ",
        "org.apache.jena.shacl.sys.InitShacl",
        "org.apache.jena.rdfs.sys.InitRDFS"
    );

    @Test
    void theShadedJarsSelfCheckExitsZero() throws IOException, InterruptedException {
        Path jar = Path.of(System.getProperty("user.dir")).resolve("target/authoring-service.jar");

        Process process = new ProcessBuilder("java", "-jar", jar.toString(), "--self-check")
            .redirectErrorStream(true)
            .start();
        String output = new String(process.getInputStream().readAllBytes());
        int exitCode = process.waitFor();

        assertEquals(0, exitCode, output);
        assertTrue(output.contains("self-check ok"), output);
    }

    /**
     * The self-check above passes even with the five jena-* subsystem registrations merged down to
     * whichever one jar's file shade kept, since nothing on that code path happens to need the
     * dropped ones. This asserts the thing {@code ServicesResourceTransformer} is actually
     * responsible for, so the self-probe has something that fails when it is removed.
     */
    @Test
    void theShadedJarMergesEveryJenaSubsystemRegistration() throws IOException {
        Path jar = Path.of(System.getProperty("user.dir")).resolve("target/authoring-service.jar");

        List<String> providers;
        try (JarFile jarFile = new JarFile(jar.toFile())) {
            try (var in = jarFile.getInputStream(jarFile.getJarEntry(LIFECYCLE_SERVICE))) {
                providers = new String(in.readAllBytes(), java.nio.charset.StandardCharsets.UTF_8).lines().toList();
            }
        }

        assertTrue(providers.containsAll(EXPECTED_SUBSYSTEMS),
            "expected " + EXPECTED_SUBSYSTEMS + " but the merged jar only has " + providers);
    }
}

