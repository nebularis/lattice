// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.writes;

/**
 * What a writer answers: an HTTP-like status, the revision a save moved to or the current one a stale save lost to, and
 * a message for a refusal. 200 applied, 400 refused as malformed, 404 no such workspace or job, 412 a stale revision,
 * 503 no writer answered.
 */
public record Reply(int status, long revision, String message) {
    public static Reply ok() {
        return new Reply(200, 0, "");
    }

    public static Reply ok(long revision) {
        return new Reply(200, revision, "");
    }

    public static Reply refused(String message) {
        return new Reply(400, 0, message);
    }

    public static Reply notFound() {
        return new Reply(404, 0, "not found");
    }

    public static Reply stale(long current) {
        return new Reply(412, current, "If-Match is not the current revision");
    }

    public boolean applied() {
        return status == 200;
    }
}
