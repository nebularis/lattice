// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.authoring;

import java.nio.file.Path;

/** The repository's contracts, from this module's directory, where Maven runs its tests. */
final class Paths {
    static final Path CONTRACTS = Path.of("..", "..", "contracts").toAbsolutePath().normalize();

    private Paths() {
    }
}
