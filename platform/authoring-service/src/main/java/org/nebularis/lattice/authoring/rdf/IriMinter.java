// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.rdf;

import java.util.regex.Pattern;

/**
 * The instance IRIs of plan \u00a72.3, as methods, each checking its argument against the \u00a72.4 pattern.
 * Constructed with the configured base IRI, which must end with {@code /}.
 */
public final class IriMinter {
    private static final Pattern UUID_PATTERN =
        Pattern.compile("^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$");
    private static final Pattern KEY_PATTERN = Pattern.compile("^[a-z][a-z0-9-]{0,39}$");
    private static final Pattern SECTION_KEY_PATTERN = Pattern.compile("^[a-z][a-z0-9-]{0,31}$");

    private final String base;

    public IriMinter(String base) {
        if (base == null || !base.endsWith("/")) {
            throw new IllegalArgumentException("base must end with '/': " + base);
        }
        this.base = base;
    }

    public String base() {
        return base;
    }

    public String registryGraph() {
        return base + "registry";
    }

    public String wording(String documentId) {
        return doc(documentId) + "wording";
    }

    public String section(String documentId, String sectionKey) {
        requireSectionKey(sectionKey, "sectionKey");
        return doc(documentId) + "section/" + sectionKey;
    }

    public String element(String documentId, String elementId) {
        requireUuid(elementId, "elementId");
        return doc(documentId) + "element/" + elementId;
    }

    public String textPart(String documentId, String elementId, int index) {
        requireNonNegative(index, "index");
        return element(documentId, elementId) + "/part/" + index;
    }

    public String variable(String documentId, String variableKey) {
        requireKey(variableKey, "variableKey");
        return doc(documentId) + "variable/" + variableKey;
    }

    public String revision(String documentId, int revision) {
        requirePositive(revision, "revision");
        return doc(documentId) + "rev/" + revision;
    }

    public String wordingGraph(String documentId, int revision) {
        return revision(documentId, revision) + "/wording-graph";
    }

    public String proposalGraph(String documentId, int revision) {
        return revision(documentId, revision) + "/proposal-graph";
    }

    public String analysisGraph(String documentId, int revision) {
        return revision(documentId, revision) + "/analysis-graph";
    }

    public String proposedRelation(String documentId, String elementId) {
        return element(documentId, elementId) + "/meaning";
    }

    public String parameterBinding(String documentId, String elementId, String slotName) {
        requireKey(slotName, "slotName");
        return proposedRelation(documentId, elementId) + "/binding/" + slotName;
    }

    public String partyRole(String documentId, String definitionElementId) {
        requireUuid(definitionElementId, "definitionElementId");
        return doc(documentId) + "role/" + definitionElementId;
    }

    public String analysisActivity(String proposalGraphIri) {
        return proposalGraphIri + "#activity";
    }

    private String doc(String documentId) {
        requireUuid(documentId, "documentId");
        return base + "doc/" + documentId + "/";
    }

    private static void requireUuid(String value, String name) {
        if (value == null || !UUID_PATTERN.matcher(value).matches()) {
            throw new IllegalArgumentException(name + " is not a Uuid: " + value);
        }
    }

    private static void requireKey(String value, String name) {
        if (value == null || !KEY_PATTERN.matcher(value).matches()) {
            throw new IllegalArgumentException(name + " is not a Key: " + value);
        }
    }

    private static void requireSectionKey(String value, String name) {
        if (value == null || !SECTION_KEY_PATTERN.matcher(value).matches()) {
            throw new IllegalArgumentException(name + " is not a SectionKey: " + value);
        }
    }

    private static void requireNonNegative(int value, String name) {
        if (value < 0) {
            throw new IllegalArgumentException(name + " must be >= 0: " + value);
        }
    }

    private static void requirePositive(int value, String name) {
        if (value < 1) {
            throw new IllegalArgumentException(name + " must be >= 1: " + value);
        }
    }
}
