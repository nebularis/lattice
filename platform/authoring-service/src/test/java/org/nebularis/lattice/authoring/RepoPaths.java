// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring;

import java.nio.file.Path;

/** Repository-relative paths for tests, which Surefire runs with the module directory as cwd. */
public final class RepoPaths {
    private RepoPaths() {
    }

    public static Path contracts() {
        return Path.of(System.getProperty("user.dir")).resolve("../../contracts").normalize();
    }
}
