// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.store;

import java.util.regex.Pattern;

/** The graph IRIs of `contracts/config-studio/README.md`. Ids are lower-case UUIDs. */
public final class Graphs {
    public static final String WORKSPACE_PREFIX = "urn:lattice:studio:ws:";
    public static final String JOB_PREFIX = "urn:lattice:studio:job:";
    private static final Pattern UUID = Pattern.compile("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}");

    private Graphs() {
    }

    public static boolean isId(String s) {
        return s != null && UUID.matcher(s).matches();
    }

    public static String workspace(String ws) {
        return WORKSPACE_PREFIX + ws;
    }

    public static String baseline(String ws, long revision) {
        return workspace(ws) + ":baseline:" + revision;
    }

    /** {@code name} is {@code surface} or {@code persistence}. */
    public static String config(String ws, String name) {
        return workspace(ws) + ":" + name;
    }

    public static String job(String job) {
        return JOB_PREFIX + job;
    }

    public static String jobInput(String job) {
        return job(job) + ":input";
    }
}
