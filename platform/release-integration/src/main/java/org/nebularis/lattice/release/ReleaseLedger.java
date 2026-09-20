package org.nebularis.lattice.release;

import java.util.List;

public interface ReleaseLedger {
    void recordIntent(ReleaseIntent intent);
    void recordReceipt(ReleaseReceipt receipt);
    void recordEvent(ReleaseLedgerEvent event);
    List<ReleaseLedgerEvent> events(String releaseId);
}
