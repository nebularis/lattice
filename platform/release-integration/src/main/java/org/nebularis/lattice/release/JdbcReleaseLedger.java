package org.nebularis.lattice.release;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import javax.sql.DataSource;

/** PostgreSQL append ledger for LATTICE semantic release evidence. */
public final class JdbcReleaseLedger implements ReleaseLedger {
    private final DataSource dataSource;

    public JdbcReleaseLedger(DataSource dataSource) { this.dataSource = dataSource; }

    @Override
    public void recordIntent(ReleaseIntent intent) {
        execute("insert into release_ledger_intent (release_id, correlation_id, intent_json) values (?, ?, ?::jsonb) on conflict (release_id) do nothing", intent.releaseId(), intent.correlationId(), ReleaseEvidenceJson.intent(intent));
        recordEvent(new ReleaseLedgerEvent(intent.releaseId(), ReleaseLedgerEvent.Kind.INTENT_ASSEMBLED, intent.correlationId(), Instant.now(), "intent:" + intent.releaseId()));
    }

    @Override
    public void recordReceipt(ReleaseReceipt receipt) {
        execute("insert into release_ledger_receipt (release_id, correlation_id, receipt_json) values (?, ?, ?::jsonb) on conflict (release_id) do update set receipt_json = excluded.receipt_json, correlation_id = excluded.correlation_id", receipt.releaseId(), receipt.correlationId(), ReleaseEvidenceJson.receipt(receipt));
        recordEvent(new ReleaseLedgerEvent(receipt.releaseId(), ReleaseLedgerEvent.Kind.RECEIPT_RECORDED, receipt.correlationId(), Instant.now(), receipt.artifactDigest()));
    }

    @Override
    public void recordEvent(ReleaseLedgerEvent event) {
        execute("insert into release_ledger_event (release_id, kind, correlation_id, recorded_at, evidence_reference) values (?, ?, ?, ?, ?)", event.releaseId(), event.kind().name(), event.correlationId(), event.recordedAt(), event.evidenceReference());
    }

    @Override
    public List<ReleaseLedgerEvent> events(String releaseId) {
        try (Connection connection = dataSource.getConnection(); PreparedStatement statement = connection.prepareStatement("select * from release_ledger_event where release_id = ? order by recorded_at, event_id")) {
            statement.setString(1, releaseId);
            try (ResultSet result = statement.executeQuery()) {
                List<ReleaseLedgerEvent> events = new ArrayList<>();
                while (result.next()) events.add(new ReleaseLedgerEvent(releaseId, ReleaseLedgerEvent.Kind.valueOf(result.getString("kind")), result.getString("correlation_id"), result.getObject("recorded_at", Instant.class), result.getString("evidence_reference")));
                return events;
            }
        } catch (SQLException error) { throw new IllegalStateException("could not list release ledger events", error); }
    }

    private void execute(String sql, Object... values) {
        try (Connection connection = dataSource.getConnection(); PreparedStatement statement = connection.prepareStatement(sql)) {
            for (int index = 0; index < values.length; index++) statement.setObject(index + 1, values[index]);
            statement.executeUpdate();
        } catch (SQLException error) { throw new IllegalStateException("could not write release ledger", error); }
    }
}
