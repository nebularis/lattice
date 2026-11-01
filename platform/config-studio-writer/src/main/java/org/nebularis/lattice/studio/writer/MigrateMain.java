// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writer;

import java.time.Clock;
import org.nebularis.lattice.studio.store.StudioOperations;
import org.nebularis.lattice.studio.store.StudioStore;

/**
 * Migrates a store written before phase D onto the generated persistence operations, once ({@link Migration}). It is configured as
 * the writer is, backs the dataset up to the assets folder first, and with {@code --dry-run} writes nothing and prints what it would do.
 */
public final class MigrateMain {
    private MigrateMain() {
    }

    public static void main(String[] args) {
        boolean dryRun = false;
        for (String arg : args) {
            if (arg.equals("--dry-run")) {
                dryRun = true;
            } else {
                System.err.println("usage: MigrateMain [--dry-run]");
                System.exit(2);
            }
        }
        WriterConfig config = WriterConfig.fromEnv(System.getenv());
        try (StudioStore store = StudioStore.fuseki(config.fusekiUrl(), config.fusekiDataset(), config.fusekiUser(), config.fusekiPassword())) {
            StudioOperations ops = StudioOperations.load(config.assets().resolve("persistence"), config.epoch());
            Migration.Summary s = new Migration(store, ops, config.assets(), Clock.systemUTC(), System.out).run(dryRun);
            System.out.println((dryRun ? "Dry run, nothing written. Would migrate " : "Migrated ") + s.workspaces() + " workspaces, "
                + s.parts() + " parts, " + s.revisions() + " baseline revisions, " + s.documents() + " documents, " + s.imports()
                + " imports, " + s.lineages() + " lineages and " + s.versions() + " versions, dropping " + s.graphsDropped() + " graphs");
            s.skipped().forEach(m -> System.out.println("Skipped: " + m));
            if (s.backup() != null) {
                System.out.println("Backup: " + s.backup());
            }
        }
    }
}
