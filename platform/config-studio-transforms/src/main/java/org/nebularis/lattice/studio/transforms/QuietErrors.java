// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import org.apache.jena.riot.RiotException;
import org.apache.jena.riot.system.ErrorHandler;

/**
 * The parse handler for input a run is given. A warning is dropped, since Jena warns of every {@code urn:g:} graph IRI that its namespace
 * identifier is under two characters, and an error is thrown with its position and is not logged, so a bad input costs the worker's log nothing.
 */
final class QuietErrors implements ErrorHandler {
    static final QuietErrors INSTANCE = new QuietErrors();

    private QuietErrors() {
    }

    private static String format(String message, long line, long col) {
        return "[line: " + line + ", col: " + col + "] " + message;
    }

    @Override
    public void warning(String message, long line, long col) {
        // Dropped.
    }

    @Override
    public void error(String message, long line, long col) {
        throw new RiotException(format(message, line, col));
    }

    @Override
    public void fatal(String message, long line, long col) {
        throw new RiotException(format(message, line, col));
    }
}
