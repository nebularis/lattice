// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import java.io.IOException;
import java.util.List;

/** Where a run's frames go. */
interface FrameSink {
    /** Publishes the frames of one run, as JSON text, in order. Returns once the broker has confirmed them, and throws when it did not. */
    void publish(String run, List<String> frames) throws IOException;
}
