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

/** PostgreSQL registry for immutable Surface graph-family metadata. */
public final class JdbcSurfaceGraphFamilyRegistry implements SurfaceGraphFamilyRegistry {
    private final DataSource dataSource;

    public JdbcSurfaceGraphFamilyRegistry(DataSource dataSource) {
        this.dataSource = dataSource;
    }

    @Override
    public SurfaceGraphArtifact register(SurfaceGraphArtifact artifact) {
        String insert = "insert into surface_graph_artifact (tenant_id, project_id, graph_iri, graph_hash, family, owner_revision_id, registered_at) values (?, ?, ?, ?, ?, ?, ?) on conflict (tenant_id, project_id, graph_iri) do nothing";
        try (Connection connection = dataSource.getConnection(); PreparedStatement statement = connection.prepareStatement(insert)) {
            statement.setString(1, artifact.reference().tenantId());
            statement.setString(2, artifact.reference().projectId());
            statement.setString(3, artifact.reference().graphIri());
            statement.setString(4, artifact.reference().revisionHash());
            statement.setString(5, artifact.family().name());
            statement.setString(6, artifact.ownerRevisionId());
            statement.setObject(7, artifact.registeredAt());
            statement.executeUpdate();
        } catch (SQLException error) {
            throw new IllegalStateException("could not register Surface graph artifact", error);
        }
        SurfaceGraphArtifact persisted = findByGraphIri(artifact.reference().tenantId(), artifact.reference().projectId(), artifact.reference().graphIri()).orElseThrow();
        if (persisted.family() != artifact.family() || !persisted.reference().revisionHash().equals(artifact.reference().revisionHash()) || !persisted.ownerRevisionId().equals(artifact.ownerRevisionId())) {
            throw new ImmutableGraphConflictException(artifact.reference().graphIri());
        }
        return persisted;
    }

    @Override
    public Optional<SurfaceGraphArtifact> findByGraphIri(String tenantId, String projectId, String graphIri) {
        String select = "select * from surface_graph_artifact where tenant_id = ? and project_id = ? and graph_iri = ?";
        try (Connection connection = dataSource.getConnection(); PreparedStatement statement = connection.prepareStatement(select)) {
            statement.setString(1, tenantId);
            statement.setString(2, projectId);
            statement.setString(3, graphIri);
            try (ResultSet result = statement.executeQuery()) {
                return result.next() ? Optional.of(map(result)) : Optional.empty();
            }
        } catch (SQLException error) {
            throw new IllegalStateException("could not find Surface graph artifact", error);
        }
    }

    @Override
    public List<SurfaceGraphArtifact> findByOwnerRevision(String ownerRevisionId) {
        String select = "select * from surface_graph_artifact where owner_revision_id = ? order by family, graph_iri";
        try (Connection connection = dataSource.getConnection(); PreparedStatement statement = connection.prepareStatement(select)) {
            statement.setString(1, ownerRevisionId);
            try (ResultSet result = statement.executeQuery()) {
                List<SurfaceGraphArtifact> found = new ArrayList<>();
                while (result.next()) {
                    found.add(map(result));
                }
                return found;
            }
        } catch (SQLException error) {
            throw new IllegalStateException("could not list Surface graph artifacts", error);
        }
    }

    private static SurfaceGraphArtifact map(ResultSet result) throws SQLException {
        GraphReference reference = new GraphReference(result.getString("tenant_id"), result.getString("project_id"), result.getString("graph_iri"), result.getString("graph_hash"));
        return new SurfaceGraphArtifact(SurfaceGraphFamily.valueOf(result.getString("family")), reference, result.getString("owner_revision_id"), result.getObject("registered_at", Instant.class));
    }
}
