package org.nebularis.lattice.surface;

public final class ImmutableGraphConflictException extends IllegalStateException {
    public ImmutableGraphConflictException(String graphIri) {
        super("a different immutable graph artifact is already registered for: " + graphIri);
    }
}
