// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writes;

/** Hands a write to the writer that owns its workspace and waits for its reply. */
public interface Writes extends AutoCloseable {
    Reply send(Command command);

    @Override
    default void close() {
    }
}
