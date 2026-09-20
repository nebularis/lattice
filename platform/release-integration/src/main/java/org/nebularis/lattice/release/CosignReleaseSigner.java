package org.nebularis.lattice.release;

import java.net.URI;
import java.util.List;
import java.util.Optional;

/** Deployment adapter that delegates signing to a configured Cosign command. */
public final class CosignReleaseSigner implements ReleaseSigner {
    private final CommandRunner commands;
    private final String artifactRepository;

    public CosignReleaseSigner(CommandRunner commands, String artifactRepository) {
        this.commands = commands;
        this.artifactRepository = artifactRepository;
    }

    @Override
    public Optional<URI> sign(String artifactDigest) {
        commands.run(List.of("cosign", "sign", "--yes", artifactRepository + "@" + artifactDigest));
        return Optional.of(URI.create("oci://" + artifactRepository + "@" + artifactDigest + ".sig"));
    }
}
