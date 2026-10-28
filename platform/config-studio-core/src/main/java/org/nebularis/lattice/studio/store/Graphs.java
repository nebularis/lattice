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

    /** The graph of document {@code doc} of workspace {@code ws}, whose IRI is also the document's. */
    public static String document(String ws, String doc) {
        return workspace(ws) + ":document:" + doc;
    }

    /** The id of the document {@code iri} names in workspace {@code ws}, or null when it names none. */
    public static String documentId(String ws, String iri) {
        String prefix = workspace(ws) + ":document:";
        return iri != null && iri.startsWith(prefix) && isId(iri.substring(prefix.length())) ? iri.substring(prefix.length()) : null;
    }

    /**
     * The base the Wording IRIs of every document are minted under. A document's id is a UUID, so its IRIs need no
     * workspace's, and they stay the same when an export is imported under another workspace.
     */
    public static final String DOCUMENT_BASE = "urn:lattice:studio:documents/";

    /** The node of document {@code doc} inside its graph, which the kit mints and which holds its markup. */
    public static String documentNode(String doc) {
        return DOCUMENT_BASE + "doc/" + doc + "/";
    }

    public static String job(String job) {
        return JOB_PREFIX + job;
    }

    public static String jobInput(String job) {
        return job(job) + ":input";
    }

    /** The assembled wordings an assemble job gave, written with its result and deleted with it. */
    public static String jobRecord(String job) {
        return job(job) + ":record";
    }

    /** The store's own receipts, of deletions whose workspace is gone with its graphs. */
    public static final String STORE_RECEIPTS = "urn:lattice:studio:receipts";

    /** The receipts of a workspace's writes, kept while it is. */
    public static String receipts(String ws) {
        return workspace(ws) + ":receipts";
    }

    /** The receipts of a job's writes, deleted with the job. */
    public static String jobReceipts(String job) {
        return job(job) + ":receipts";
    }

    public static String receipt(String command) {
        return "urn:lattice:studio:receipt:" + command;
    }
}
