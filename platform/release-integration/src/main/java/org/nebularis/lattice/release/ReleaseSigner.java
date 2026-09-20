package org.nebularis.lattice.release;

import java.net.URI;
import java.util.Optional;

public interface ReleaseSigner {
    Optional<URI> sign(String artifactDigest);
}
