package org.nebularis.lattice.release;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;

/** Exports and restores OCI Image Layout bundles without a registry dependency. */
public final class OciLayoutBundleService {
    public String exportBundle(Path layout, Path bundle) {
        copyTree(layout, bundle);
        return manifestDigest(bundle);
    }

    public void restoreBundle(Path bundle, Path target, String expectedManifestDigest) {
        String actual = manifestDigest(bundle);
        if (!actual.equals(expectedManifestDigest)) throw new IllegalArgumentException("exported OCI bundle digest does not match expected manifest");
        copyTree(bundle, target);
        if (!manifestDigest(target).equals(expectedManifestDigest)) throw new IllegalStateException("restored OCI bundle verification failed");
    }

    private static String manifestDigest(Path layout) {
        try { return "sha256:" + HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(layout.resolve("index.json")))); }
        catch (Exception error) { throw new IllegalStateException("could not read OCI bundle index", error); }
    }

    private static void copyTree(Path source, Path target) {
        try (var paths = Files.walk(source)) {
            paths.forEach(path -> {
                try {
                    Path destination = target.resolve(source.relativize(path));
                    if (Files.isDirectory(path)) Files.createDirectories(destination); else Files.copy(path, destination, java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                } catch (IOException error) { throw new IllegalStateException("could not copy OCI bundle", error); }
            });
        } catch (IOException error) { throw new IllegalStateException("could not export OCI bundle", error); }
    }
}
