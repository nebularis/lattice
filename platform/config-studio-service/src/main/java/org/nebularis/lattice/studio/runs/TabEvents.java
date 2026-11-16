// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.runs;

/** Publishes to a tab's events topic, {@code studio/u/<name>/<tab>/events}, the topic a job's event reaches the tab on. */
public interface TabEvents {
    /** Publishes {@code eventJson}, a CloudEvent in JSON, to the events topic of the tab {@code tab} of the principal named {@code principal}. */
    void publish(String principal, String tab, String eventJson);
}
