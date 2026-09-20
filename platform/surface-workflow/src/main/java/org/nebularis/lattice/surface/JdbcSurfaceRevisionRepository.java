package org.nebularis.lattice.surface;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import javax.sql.DataSource;
import org.nebularis.lattice.semantic.GraphReference;

/** PostgreSQL-backed operational ledger. Graph content remains in the semantic dataset. */
public final class JdbcSurfaceRevisionRepository implements SurfaceRevisionRepository {
    private final DataSource dataSource;

    public JdbcSurfaceRevisionRepository(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public VersionedSurfaceRevision create(SurfaceRevision revision) {
        String sql = "insert into surface_revision_ledger (revision_id, contract_id, tenant_id, project_id, state, contract_graph_iri, contract_graph_hash, profile_graph_iri, profile_graph_hash, generated_graph_iri, generated_graph_hash, approval_id, revision_version) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)";
        try (Connection connection = dataSource.getConnection(); PreparedStatement statement = connection.prepareStatement(sql)) {
            bindRevision(statement, revision, false);
            statement.executeUpdate();
            return find(revision.revisionId()).orElseThrow();
        } catch (SQLException error) {
            throw new IllegalStateException("could not create surface revision ledger entry", error);
        }
    }

    @Override
    public Optional<VersionedSurfaceRevision> find(String revisionId) {
        String sql = "select * from surface_revision_ledger where revision_id = ?";
        try (Connection connection = dataSource.getConnection(); PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, revisionId);
            try (ResultSet result = statement.executeQuery()) {
                return result.next() ? Optional.of(map(result)) : Optional.empty();
            }
        } catch (SQLException error) {
            throw new IllegalStateException("could not read surface revision ledger entry", error);
        }
    }

    @Override
    public List<VersionedSurfaceRevision> findByContract(String contractId) {
        String sql = "select * from surface_revision_ledger where contract_id = ? order by revision_id";
        try (Connection connection = dataSource.getConnection(); PreparedStatement statement = connection.prepareStatement(sql)) {
            statement.setString(1, contractId);
            try (ResultSet result = statement.executeQuery()) {
                List<VersionedSurfaceRevision> found = new ArrayList<>();
                while (result.next()) {
                    found.add(map(result));
                }
                return found;
            }
        } catch (SQLException error) {
            throw new IllegalStateException("could not list surface revision ledger entries", error);
        }
    }

    @Override
    public VersionedSurfaceRevision replace(String revisionId, long expectedVersion, SurfaceRevision nextRevision) {
        if (!revisionId.equals(nextRevision.revisionId())) {
            throw new IllegalArgumentException("revision ID cannot change during replacement");
        }
        String sql = "update surface_revision_ledger set state = ?, contract_graph_iri = ?, contract_graph_hash = ?, profile_graph_iri = ?, profile_graph_hash = ?, generated_graph_iri = ?, generated_graph_hash = ?, approval_id = ?, revision_version = revision_version + 1, recorded_at = current_timestamp where revision_id = ? and revision_version = ?";
        try (Connection connection = dataSource.getConnection(); PreparedStatement statement = connection.prepareStatement(sql)) {
            bindRevision(statement, nextRevision, true);
            statement.setString(9, revisionId);
            statement.setLong(10, expectedVersion);
            if (statement.executeUpdate() != 1) {
                throw new StaleSurfaceRevisionException(revisionId);
            }
            return find(revisionId).orElseThrow();
        } catch (SQLException error) {
            throw new IllegalStateException("could not replace surface revision ledger entry", error);
        }
    }

    private static void bindRevision(PreparedStatement statement, SurfaceRevision revision, boolean update) throws SQLException {
        int index = 1;
        if (!update) {
            statement.setString(index++, revision.revisionId());
            statement.setString(index++, revision.contractId());
            statement.setString(index++, revision.contractGraph().tenantId());
            statement.setString(index++, revision.contractGraph().projectId());
        }
        statement.setString(index++, revision.state().name());
        statement.setString(index++, revision.contractGraph().graphIri());
        statement.setString(index++, revision.contractGraph().revisionHash());
        statement.setString(index++, revision.profileGraph().graphIri());
        statement.setString(index++, revision.profileGraph().revisionHash());
        if (revision.generatedGraph().isPresent()) {
            statement.setString(index++, revision.generatedGraph().get().graphIri());
            statement.setString(index++, revision.generatedGraph().get().revisionHash());
        } else {
            statement.setNull(index++, java.sql.Types.VARCHAR);
            statement.setNull(index++, java.sql.Types.VARCHAR);
        }
        if (revision.approvalId().isPresent()) {
            statement.setString(index, revision.approvalId().get());
        } else {
            statement.setNull(index, java.sql.Types.VARCHAR);
        }
    }

    private static VersionedSurfaceRevision map(ResultSet result) throws SQLException {
        String tenantId = result.getString("tenant_id");
        String projectId = result.getString("project_id");
        GraphReference contractGraph = new GraphReference(tenantId, projectId, result.getString("contract_graph_iri"), result.getString("contract_graph_hash"));
        GraphReference profileGraph = new GraphReference(tenantId, projectId, result.getString("profile_graph_iri"), result.getString("profile_graph_hash"));
        String generatedIri = result.getString("generated_graph_iri");
        Optional<GraphReference> generatedGraph = generatedIri == null ? Optional.empty() : Optional.of(new GraphReference(tenantId, projectId, generatedIri, result.getString("generated_graph_hash")));
        Optional<String> approvalId = Optional.ofNullable(result.getString("approval_id"));
        SurfaceRevision revision = new SurfaceRevision(result.getString("revision_id"), result.getString("contract_id"), SurfaceRevisionState.valueOf(result.getString("state")), contractGraph, profileGraph, generatedGraph, approvalId);
        return new VersionedSurfaceRevision(revision, result.getLong("revision_version"), result.getObject("recorded_at", Instant.class));
    }
}
