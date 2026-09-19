package org.nebularis.lattice.surface;

public final class StaleSurfaceRevisionException extends IllegalStateException {
    public StaleSurfaceRevisionException(String revisionId) {
        super("surface revision has changed since it was read: " + revisionId);
    }
}
