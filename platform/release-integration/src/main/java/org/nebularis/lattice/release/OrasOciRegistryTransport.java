package org.nebularis.lattice.release;

import java.nio.file.Path;
import java.util.List;

/** Deployment adapter that pushes a verified OCI layout through a configured ORAS command. */
public final class OrasOciRegistryTransport {
    private final CommandRunner commands;

    public OrasOciRegistryTransport(CommandRunner commands) { this.commands = commands; }

    public void push(Path layout, String targetReference) {
        commands.run(List.of("oras", "cp", "--from-oci-layout", layout.toString(), targetReference));
    }
}
