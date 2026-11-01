// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writes;

/**
 * One writer in this process, for tests and a run without a broker. Writes take turns, which is what one partition's
 * writer does, so the behaviour is the same as with RabbitMQ and one writer.
 */
public final class DirectWrites implements Writes {
    private final Writer writer;

    public DirectWrites(Writer writer) {
        this.writer = writer;
    }

    @Override
    public synchronized Reply send(Command command) {
        return writer.apply(command);
    }

    /** Several commands as one writer would take them from its queue, in one request. */
    public synchronized java.util.List<Reply> sendAll(java.util.List<Command> commands) {
        return writer.apply(commands);
    }
}
