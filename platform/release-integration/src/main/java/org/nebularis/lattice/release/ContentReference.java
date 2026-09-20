package org.nebularis.lattice.release;

import java.net.URI;
import java.util.Objects;

public record ContentReference(String mediaType, String digest, URI uri) {
    public ContentReference {
        require(mediaType, "mediaType");
        requireDigest(digest);
        Objects.requireNonNull(uri, "uri");
    }

    static void require(String value, String name) {
        if (Objects.requireNonNull(value, name).isBlank()) {
            throw new IllegalArgumentException(name + " must not be blank");
        }
    }

    static void requireDigest(String digest) {
        if (Objects.requireNonNull(digest, "digest").matches("sha256:[a-f0-9]{64}") == false) {
            throw new IllegalArgumentException("digest must be a lowercase SHA-256 digest");
        }
    }
}
