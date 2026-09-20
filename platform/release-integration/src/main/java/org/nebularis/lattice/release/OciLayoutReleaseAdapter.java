package org.nebularis.lattice.release;

import java.io.IOException;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Optional;
import java.util.Set;

/** Writes OCI Image Layout release bundles without requiring a registry client. */
public final class OciLayoutReleaseAdapter implements ReleaseStackAdapter {
    private static final String OCI_MANIFEST = "application/vnd.oci.image.manifest.v1+json";
    private static final String OCI_CONFIG = "application/vnd.oci.image.config.v1+json";
    private static final String INTENT_MEDIA_TYPE = "application/vnd.nebularis.lattice.release-intent.v1+json";
    private static final String INVENTORY_MEDIA_TYPE = "application/vnd.nebularis.lattice.release-inventory.v1+json";
    private final Path root;
    private final ReleaseSigner signer;

    public OciLayoutReleaseAdapter(Path root, ReleaseSigner signer) {
        this.root = root;
        this.signer = signer;
    }

    @Override
    public String adapterId() {
        return "oci-image-layout";
    }

    @Override
    public String adapterVersion() {
        return "1.0.0";
    }

    @Override
    public Set<ReleaseCapability> capabilities() {
        return Set.of(ReleaseCapability.PACKAGE, ReleaseCapability.SIGN, ReleaseCapability.PUBLISH, ReleaseCapability.VERIFY, ReleaseCapability.EXPORT);
    }

    @Override
    public ReleaseReceipt plan(ReleaseIntent intent) {
        String digest = digest(canonicalIntent(intent));
        return receipt(intent, ReleaseReceipt.State.PLANNED, digest, Optional.empty());
    }

    @Override
    public ReleaseReceipt publish(ReleaseIntent intent) {
        try {
            Files.createDirectories(root.resolve("blobs/sha256"));
            write(root.resolve("oci-layout"), "{\"imageLayoutVersion\":\"1.0.0\"}");
            Descriptor config = writeBlob("{}", OCI_CONFIG);
            Descriptor intentLayer = writeBlob(canonicalIntent(intent), INTENT_MEDIA_TYPE);
            Descriptor inventoryLayer = writeBlob(canonicalInventory(intent), INVENTORY_MEDIA_TYPE);
            String manifest = "{\"schemaVersion\":2,\"mediaType\":\"" + OCI_MANIFEST + "\",\"config\":" + config.json() + ",\"layers\":[" + intentLayer.json() + "," + inventoryLayer.json() + "]}";
            Descriptor manifestDescriptor = writeBlob(manifest, OCI_MANIFEST);
            String index = "{\"schemaVersion\":2,\"manifests\":[" + manifestDescriptor.json() + "]}";
            write(root.resolve("index.json"), index);
            return receipt(intent, ReleaseReceipt.State.PUBLISHED, manifestDescriptor.digest(), signer.sign(manifestDescriptor.digest()));
        } catch (IOException error) {
            throw new IllegalStateException("could not write OCI release layout", error);
        }
    }

    private ReleaseReceipt receipt(ReleaseIntent intent, ReleaseReceipt.State state, String digest, Optional<URI> signature) {
        return new ReleaseReceipt(intent.releaseId(), adapterId(), adapterVersion(), intent.correlationId(), state, digest, URI.create("oci://lattice/" + digest), signature, Optional.empty());
    }

    private Descriptor writeBlob(String content, String mediaType) throws IOException {
        byte[] bytes = content.getBytes(StandardCharsets.UTF_8);
        String digest = digest(bytes);
        Path location = root.resolve("blobs/sha256").resolve(digest.substring("sha256:".length()));
        if (!Files.exists(location)) {
            Files.write(location, bytes);
        }
        return new Descriptor(mediaType, digest, bytes.length);
    }

    private static void write(Path location, String content) throws IOException {
        Files.writeString(location, content, StandardCharsets.UTF_8);
    }

    private static String canonicalIntent(ReleaseIntent intent) {
        String graphs = intent.graphReferences().stream().map(graph -> "{\"graphIri\":\"" + json(graph.graphIri()) + "\",\"projectId\":\"" + json(graph.projectId()) + "\",\"revisionHash\":\"" + json(graph.revisionHash()) + "\",\"tenantId\":\"" + json(graph.tenantId()) + "\"}").reduce((left, right) -> left + "," + right).orElse("");
        String outputs = intent.generatedOutputs().stream().map(output -> "{\"digest\":\"" + json(output.digest()) + "\",\"mediaType\":\"" + json(output.mediaType()) + "\",\"uri\":\"" + json(output.uri().toString()) + "\"}").reduce((left, right) -> left + "," + right).orElse("");
        String gates = intent.semanticGates().stream().map(gate -> "{\"evidenceDigest\":\"" + json(gate.evidenceDigest()) + "\",\"gate\":\"" + json(gate.gate()) + "\",\"outcome\":\"passed\"}").reduce((left, right) -> left + "," + right).orElse("");
        var requirements = intent.requirements();
        String requirementJson = "{\"approvalEvidenceDigest\":\"" + json(requirements.approvalEvidenceDigest()) + "\",\"canonicalisationVersion\":\"" + json(requirements.canonicalisationVersion()) + "\",\"impactEvidenceDigest\":\"" + json(requirements.impactEvidenceDigest()) + "\",\"profileId\":\"" + json(requirements.profileId()) + "\",\"profileRevisionHash\":\"" + json(requirements.profileRevisionHash()) + "\"}";
        return "{\"correlationId\":\"" + json(intent.correlationId()) + "\",\"environment\":\"" + json(intent.environment()) + "\",\"generatedOutputs\":[" + outputs + "],\"graphReferences\":[" + graphs + "],\"legalHold\":" + intent.legalHold() + ",\"projectId\":\"" + json(intent.projectId()) + "\",\"releaseId\":\"" + json(intent.releaseId()) + "\",\"requirements\":" + requirementJson + ",\"retentionClass\":\"" + json(intent.retentionClass()) + "\",\"semanticGates\":[" + gates + "],\"tenantId\":\"" + json(intent.tenantId()) + "\"}";
    }

    private static String canonicalInventory(ReleaseIntent intent) {
        return "{\"releaseId\":\"" + json(intent.releaseId()) + "\",\"graphRevisionHashes\":[" + intent.graphReferences().stream().map(graph -> "\"" + json(graph.revisionHash()) + "\"").reduce((left, right) -> left + "," + right).orElse("") + "],\"outputDigests\":[" + intent.generatedOutputs().stream().map(output -> "\"" + json(output.digest()) + "\"").reduce((left, right) -> left + "," + right).orElse("") + "]}";
    }

    private static String json(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }

    private static String digest(String content) {
        return digest(content.getBytes(StandardCharsets.UTF_8));
    }

    private static String digest(byte[] content) {
        try {
            return "sha256:" + HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(content));
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 is unavailable", error);
        }
    }

    private record Descriptor(String mediaType, String digest, long size) {
        String json() {
            return "{\"mediaType\":\"" + mediaType + "\",\"digest\":\"" + digest + "\",\"size\":" + size + "}";
        }
    }
}