// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

/** What to do with a message once its handling ended. */
enum Outcome {
    /** Acknowledge it. */
    ACK,
    /** Reject it without requeue. */
    REJECT,
    /** Reject it with requeue, so the broker redelivers it and a worker then says it was lost. */
    REQUEUE
}
