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
        require(SECTION_KEY_PATTERN, sectionKey, "sectionKey", "SectionKey");
        return doc(documentId) + "section/" + sectionKey;
    }

    public String element(String documentId, String elementId) {
        require(UUID_PATTERN, elementId, "elementId", "Uuid");
        return doc(documentId) + "element/" + elementId;
    }

    public String textPart(String documentId, String elementId, int index) {
        requireAtLeast(index, 0, "index");
        return element(documentId, elementId) + "/part/" + index;
    }

    public String variable(String documentId, String variableKey) {
        require(KEY_PATTERN, variableKey, "variableKey", "Key");
        return doc(documentId) + "variable/" + variableKey;
    }

    public String revision(String documentId, int revision) {
        requireAtLeast(revision, 1, "revision");
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
        require(KEY_PATTERN, slotName, "slotName", "Key");
        return proposedRelation(documentId, elementId) + "/binding/" + slotName;
    }

    public String partyRole(String documentId, String definitionElementId) {
        require(UUID_PATTERN, definitionElementId, "definitionElementId", "Uuid");
        return doc(documentId) + "role/" + definitionElementId;
    }

    public String analysisActivity(String proposalGraphIri) {
        return proposalGraphIri + "#activity";
    }

    private String doc(String documentId) {
        require(UUID_PATTERN, documentId, "documentId", "Uuid");
        return base + "doc/" + documentId + "/";
    }

    private static void require(Pattern pattern, String value, String name, String type) {
        if (value == null || !pattern.matcher(value).matches()) {
            throw new IllegalArgumentException(name + " is not a " + type + ": " + value);
        }
    }

    private static void requireAtLeast(int value, int minimum, String name) {
        if (value < minimum) {
            throw new IllegalArgumentException(name + " must be >= " + minimum + ": " + value);
        }
    }
}
