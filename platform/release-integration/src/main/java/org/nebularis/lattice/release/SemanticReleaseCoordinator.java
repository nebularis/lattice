package org.nebularis.lattice.release;

import java.util.Objects;

/** Only application boundary that invokes release-stack adapters for semantic releases. */
public final class SemanticReleaseCoordinator {
    private final SemanticReleaseAssemblyService assembly;
    private final ReleaseLedger ledger;

    public SemanticReleaseCoordinator(SemanticReleaseAssemblyService assembly, ReleaseLedger ledger) {
        this.assembly = Objects.requireNonNull(assembly, "assembly");
        this.ledger = Objects.requireNonNull(ledger, "ledger");
    }

    public ReleaseReceipt plan(ReleaseStackAdapter adapter, ReleaseIntent intent) {
        ReleaseIntent assembled = assembly.assemble(intent);
        ledger.recordIntent(assembled);
        ReleaseReceipt receipt = adapter.plan(assembled);
        ledger.recordReceipt(receipt);
        return receipt;
    }

    public ReleaseReceipt publish(ReleaseStackAdapter adapter, ReleaseIntent intent) {
        ReleaseIntent assembled = assembly.assemble(intent);
        ledger.recordIntent(assembled);
        ReleaseReceipt receipt = adapter.publish(assembled);
        ledger.recordReceipt(receipt);
        return receipt;
    }
}
