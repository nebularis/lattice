// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.api;

/** The response of {@code GET /api/health}: {@code status}, {@code fuseki} and {@code amqp}. */
public record HealthView(String status, String fuseki, String amqp) {
    public static final String OK = "ok";
    public static final String DEGRADED = "degraded";
    public static final String UP = "up";
    public static final String DOWN = "down";

    public static HealthView of(boolean storeUp, boolean busUp) {
        String overall = (storeUp && busUp) ? OK : DEGRADED;
        return new HealthView(overall, storeUp ? UP : DOWN, busUp ? UP : DOWN);
    }
}
