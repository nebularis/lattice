package org.nebularis.lattice.release;

import java.util.Set;

public interface ReleaseStackAdapter {
    String adapterId();
    String adapterVersion();
    Set<ReleaseCapability> capabilities();
    ReleaseReceipt plan(ReleaseIntent intent);
    ReleaseReceipt publish(ReleaseIntent intent);

    default ReleaseReceipt promote(ReleaseReceipt receipt, String environmentBinding) {
        throw new UnsupportedOperationException("promotion is owned by the configured release stack");
    }

    default ReleaseReceipt rollback(ReleaseReceipt receipt, String rollbackTargetReleaseId) {
        throw new UnsupportedOperationException("rollback is owned by the configured release stack");
    }

    default ReleaseReceipt export(ReleaseReceipt receipt) {
        throw new UnsupportedOperationException("export is owned by the configured release stack");
    }

    default ReleaseReceipt restore(ReleaseReceipt receipt, String environmentBinding) {
        throw new UnsupportedOperationException("restore is owned by the configured release stack");
    }

    default ReleaseReceipt retire(ReleaseReceipt receipt, String retentionDecision) {
        throw new UnsupportedOperationException("retention is owned by the configured release stack");
    }
}
