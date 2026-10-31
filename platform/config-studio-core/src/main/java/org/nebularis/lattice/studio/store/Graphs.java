// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.store;

import java.util.regex.Pattern;

/** The graph IRIs of `contracts/config-studio/README.md`. Ids are lower-case UUIDs. */
public final class Graphs {
    public static final String WORKSPACE_PREFIX = "urn:lattice:studio:ws:";
    public static final String JOB_PREFIX = "urn:lattice:studio:job:";
    private static final Pattern UUID = Pattern.compile("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}");

    /** The registry's graphs, a lineage's and each of its versions', named by the profile's rule. They belong to no workspace. */
    public static final String LINEAGE_PREFIX = "urn:lattice:studio:lineage/";
    public static final String VERSION_PREFIX = "urn:lattice:studio:version/";

    private Graphs() {
    }

    public static boolean isId(String s) {
        return s != null && UUID.matcher(s).matches();
    }

    public static String workspace(String ws) {
        return WORKSPACE_PREFIX + ws;
    }

    // The graph of each aggregate is named by the profile's rule, the prefix and the encoded root, exactly as
    // StudioOperations.graph names it (contracts/config-studio/persistence-profile.ttl). A test holds them equal.
    public static final String DESCRIPTION_PREFIX = "urn:lattice:studio:description/";
    public static final String PART_PREFIX = "urn:lattice:studio:part/";
    public static final String DOCUMENT_GRAPH_PREFIX = "urn:lattice:studio:document/";
    public static final String IMPORTED_PREFIX = "urn:lattice:studio:imported/";

    /** As SPARQL's {@code ENCODE_FOR_URI}, which leaves the letters, the digits and {@code -_.~} and encodes every other UTF-8 byte. */
    public static String encodeForUri(String text) {
        StringBuilder out = new StringBuilder();
        for (byte b : text.getBytes(java.nio.charset.StandardCharsets.UTF_8)) {
            char c = (char) (b & 0xFF);
            if (c < 128 && (Character.isLetterOrDigit(c) || "-_.~".indexOf(c) >= 0)) {
                out.append(c);
            } else {
                out.append('%').append(String.format("%02X", b & 0xFF));
            }
        }
        return out.toString();
    }

    /** The graph of the description aggregate of workspace {@code ws}, whose root is {@link #workspace}. */
    public static String description(String ws) {
        return DESCRIPTION_PREFIX + encodeForUri(workspace(ws));
    }

    /** The root of part {@code name} of workspace {@code ws}, for every name in {@code Workspace.GRAPHS}. */
    public static String partRoot(String ws, String name) {
        return workspace(ws) + "/part/" + name;
    }

    /** The graph of part {@code name} of workspace {@code ws}. */
    public static String config(String ws, String name) {
        return PART_PREFIX + encodeForUri(partRoot(ws, name));
    }

    /** The baseline is a part like the others, read as saved (PB-D12). */
    public static String baseline(String ws) {
        return config(ws, "baseline");
    }

    /** The root of document {@code doc} of workspace {@code ws}, whose IRI is also the document's. */
    public static String document(String ws, String doc) {
        return workspace(ws) + ":document:" + doc;
    }

    /** The graph of document {@code doc} of workspace {@code ws}. */
    public static String documentGraph(String ws, String doc) {
        return DOCUMENT_GRAPH_PREFIX + encodeForUri(document(ws, doc));
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

    /** The graph of the lineage {@code lineageIri}, whose root is the lineage's IRI. */
    public static String lineage(String lineageIri) {
        return LINEAGE_PREFIX + encodeForUri(lineageIri);
    }

    /** The immutable graph of a version, whose root is its IRI, the lineage's, {@code /rev/1-} and {@code digest16}. */
    public static String version(String lineageIri, String digest16) {
        return VERSION_PREFIX + encodeForUri(lineageIri + "/rev/1-" + digest16);
    }

    /** Whether {@code iri} may name a published unit, an absolute http, https or urn IRI that the studio did not mint. */
    public static boolean isUnitIri(String iri) {
        if (iri == null || iri.length() > 500 || iri.startsWith("urn:lattice:studio:")) {
            return false;
        }
        try {
            java.net.URI u = new java.net.URI(iri);
            return u.isAbsolute() && java.util.Set.of("http", "https", "urn").contains(u.getScheme());
        } catch (java.net.URISyntaxException e) {
            return false;
        }
    }

    private static final Pattern VERSION_GRAPH = Pattern.compile(Pattern.quote(VERSION_PREFIX) + "[A-Za-z0-9%._~-]+%2Frev%2F1-[0-9a-f]{16}");

    /** Whether {@code iri} names a version's graph, which is immutable and readable by everyone. */
    public static boolean isVersionGraph(String iri) {
        return iri != null && VERSION_GRAPH.matcher(iri).matches();
    }

    /** An import graph is global and immutable, stored once by the digest of its content whichever workspaces hold it. */
    public static final String IMPORT_PREFIX = "urn:lattice:studio:import:";
    private static final Pattern DIGEST = Pattern.compile("[0-9a-f]{64}");

    public static boolean isDigest(String s) {
        return s != null && DIGEST.matcher(s).matches();
    }

    /** The root of the import of {@code digest64}, which {@code cst:holdsImport} names. */
    public static String importGraph(String digest64) {
        return IMPORT_PREFIX + digest64;
    }

    /** The graph that holds the import of {@code digest64}. */
    public static String importedGraph(String digest64) {
        return importedGraphOf(importGraph(digest64));
    }

    /** The graph that holds the import whose root is {@code root}. */
    public static String importedGraphOf(String root) {
        return IMPORTED_PREFIX + encodeForUri(root);
    }

    public static boolean isImportedGraph(String iri) {
        return iri != null && iri.startsWith(IMPORTED_PREFIX + encodeForUri(IMPORT_PREFIX))
            && isDigest(iri.substring((IMPORTED_PREFIX + encodeForUri(IMPORT_PREFIX)).length()));
    }

    public static boolean isImportGraph(String iri) {
        return iri != null && iri.startsWith(IMPORT_PREFIX) && isDigest(iri.substring(IMPORT_PREFIX.length()));
    }
}
