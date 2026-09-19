package org.nebularis.lattice.release;

import static org.junit.jupiter.api.Assertions.assertTrue;
import java.nio.file.Files;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class OciLayoutBundleServiceTest {
    @TempDir java.nio.file.Path temporaryDirectory;

    @Test
    void exportsAndRestoresAnOciLayoutByVerifiedManifestDigest() {
        var source = temporaryDirectory.resolve("source");
        new OciLayoutReleaseAdapter(source, digest -> Optional.empty()).publish(OciLayoutReleaseAdapterTestIntent.create());
        var service = new OciLayoutBundleService();
        String digest = service.exportBundle(source, temporaryDirectory.resolve("export"));
        var restored = temporaryDirectory.resolve("restored");
        service.restoreBundle(temporaryDirectory.resolve("export"), restored, digest);
        assertTrue(Files.exists(restored.resolve("index.json")));
    }
}