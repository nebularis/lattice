// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.authoring;

import java.util.ArrayList;
import java.util.List;
import org.w3c.dom.Element;
import org.w3c.dom.Node;

/**
 * A document's structure as its markup states it, read from a DOM the schema has accepted. What the report's checks
 * read: sections in order, their clauses and definitions with each part of their text, and where unmarked text is.
 */
record Markup(String id, String templateKey, List<Section> sections, List<String> unmarkedIn) {

    record Section(String key, List<Item> items) {
    }

    /** A clause, or a definition with its term. */
    record Item(String id, boolean definition, String term, List<Part> parts) {
        String text() {
            StringBuilder b = new StringBuilder();
            parts.forEach(p -> b.append(p.text()));
            return b.toString();
        }
    }

    /** A run of literal text, a variable's display text with its key, or a reference's text with its target. */
    record Part(Kind kind, String text, String key) {
    }

    enum Kind { LITERAL, VARIABLE, REFERENCE }

    /** {@code unmarkedIn} holds a section key per run of unmarked text, null for text outside every section. */
    static Markup of(Element root) {
        List<Section> sections = new ArrayList<>();
        List<String> unmarked = new ArrayList<>();
        Element body = (Element) root.getElementsByTagNameNS(Documents.NAMESPACE, "body").item(0);
        for (Element child : children(body)) {
            if (child.getLocalName().equals("unmarked")) {
                unmarked.add(null);
                continue;
            }
            List<Item> items = new ArrayList<>();
            for (Element el : children(child)) {
                if (el.getLocalName().equals("unmarked")) {
                    unmarked.add(child.getAttribute("key"));
                    continue;
                }
                boolean definition = el.getLocalName().equals("definition");
                items.add(new Item(el.getAttribute("id"), definition, definition ? el.getAttribute("term") : null, parts(el)));
            }
            sections.add(new Section(child.getAttribute("key"), List.copyOf(items)));
        }
        Element template = (Element) root.getElementsByTagNameNS(Documents.NAMESPACE, "template").item(0);
        return new Markup(root.getAttribute("id"), template.getTextContent(), List.copyOf(sections), List.copyOf(unmarked));
    }

    private static List<Part> parts(Element el) {
        List<Part> parts = new ArrayList<>();
        for (Node n = el.getFirstChild(); n != null; n = n.getNextSibling()) {
            if (n.getNodeType() == Node.TEXT_NODE || n.getNodeType() == Node.CDATA_SECTION_NODE) {
                // Adjacent text nodes are one part, as the kit reads them.
                if (!parts.isEmpty() && parts.getLast().kind() == Kind.LITERAL) {
                    parts.set(parts.size() - 1, new Part(Kind.LITERAL, parts.getLast().text() + n.getNodeValue(), null));
                } else {
                    parts.add(new Part(Kind.LITERAL, n.getNodeValue(), null));
                }
            } else if (n instanceof Element mark) {
                boolean variable = mark.getLocalName().equals("var");
                parts.add(new Part(variable ? Kind.VARIABLE : Kind.REFERENCE, mark.getTextContent(),
                    mark.getAttribute(variable ? "key" : "target")));
            }
        }
        return List.copyOf(parts);
    }

    private static List<Element> children(Element parent) {
        List<Element> out = new ArrayList<>();
        for (Node n = parent.getFirstChild(); n != null; n = n.getNextSibling()) {
            if (n instanceof Element e) {
                out.add(e);
            }
        }
        return out;
    }
}
