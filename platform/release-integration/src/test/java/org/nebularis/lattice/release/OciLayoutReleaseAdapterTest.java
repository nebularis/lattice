package org.nebularis.lattice.release;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import java.net.URI;
import java.nio.file.Files;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.semantic.GraphReference;

class OciLayoutReleaseAdapterTest {
    @TempDir
    java.nio.file.Path temporaryDirectory;

    @Test
    void publishesAnOciImageLayoutWithADigestAddressedReceipt() throws Exception {
        var adapter = new OciLayoutReleaseAdapter(temporaryDirectory, digest -> Optional.of(URI.create("https://signer.test/" + digest)));
        var receipt = adapter.publish(intent());
        assertEquals(ReleaseReceipt.State.PUBLISHED, receipt.state());
        assertTrue(Files.exists(temporaryDirectory.resolve("oci-layout")));
        assertTrue(Files.exists(temporaryDirectory.resolve("index.json")));
        assertTrue(Files.exists(temporaryDirectory.resolve("blobs/sha256/").resolve(receipt.artifactDigest().substring("sha256:".length()))));
    }

    private static ReleaseIntent intent() {
        String digest = "sha256:" + "a".repeat(64);
        return new ReleaseIntent("release-1", "tenant", "project", "correlation", "staging", List.of(new GraphReference("tenant", "project", "https://example.test/graphs/contract", digest)), List.of(new ContentReference("application/n-quads", digest, URI.create("https://example.test/output"))), List.of(new SemanticGateEvidence("parity", "passed", digest)), new ReleaseRequirements("https://example.test/profiles/default", digest, "srf-canon/1", digest, digest), Optional.empty(), "standard", false);
    }
}