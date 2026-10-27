// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.jobs;

import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/** A bus that only remembers what was published. Jobs stay queued, so this is for tests and a broker-less run. */
public final class RecordingJobBus implements JobBus {
    private final List<String> published = new CopyOnWriteArrayList<>();

    @Override
    public void publish(String jobIri) {
        published.add(jobIri);
    }

    public List<String> published() {
        return List.copyOf(published);
    }
}
