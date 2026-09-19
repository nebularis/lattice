package org.nebularis.lattice.semantic.fuseki;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.io.StringWriter;
import java.util.EnumSet;
import java.util.Set;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.riot.RDFFormat;
import org.apache.jena.rdfconnection.RDFConnection;
import org.apache.jena.rdfconnection.RDFConnectionRemote;
import org.nebularis.lattice.semantic.DatasetCapability;
import org.nebularis.lattice.semantic.DatasetSnapshot;
import org.nebularis.lattice.semantic.GraphReference;
import org.nebularis.lattice.semantic.ScopedDataset;

public final class FusekiScopedDataset implements ScopedDataset {
    private final String queryEndpoint;

    public FusekiScopedDataset(String queryEndpoint) {
        this.queryEndpoint = queryEndpoint;
    }

    @Override
    public Set<DatasetCapability> capabilities() {
        return EnumSet.of(DatasetCapability.NAMED_GRAPH_READ, DatasetCapability.NAMED_GRAPH_WRITE, DatasetCapability.TRANSACTIONS);
    }

    @Override
    public DatasetSnapshot read(GraphReference reference) {
        try (RDFConnection connection = RDFConnectionRemote.newBuilder().destination(queryEndpoint).build()) {
            StringWriter writer = new StringWriter();
            RDFDataMgr.write(writer, connection.fetch(reference.graphIri()), RDFFormat.NTRIPLES_UTF8);
            String canonicalTriples = writer.toString();
            return new DatasetSnapshot(reference, canonicalTriples, sha256(canonicalTriples));
        }
    }

    private static String sha256(String text) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8));
            return java.util.HexFormat.of().formatHex(digest);
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 is unavailable", error);
        }
    }
}
