// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Resource;
import org.nebularis.lattice.persistence.Namespaces;
import org.nebularis.lattice.studio.store.Graphs;

/**
 * The landing places a compiled profile states (SVA-P1a, {@code dal:GraphPlace}), and the exact assignment of a changed graph to them. A place
 * with {@code dal:inGraph} is a graph and matches by equality. A place with {@code dal:inGraphNamed} is a template of the closed placeholders
 * {@code {root}}, {@code {newRev}} and {@code {month}}. It is rendered with the step's own values, {@code {root}} percent-encoded as
 * {@code ENCODE_FOR_URI} does, {@code {newRev}} as given and {@code {month}} the first seven characters of the stated transaction time, and the
 * result is compared for equality. Nothing is matched by a pattern or by a prefix.
 */
final class LandingPlaces {
    private LandingPlaces() {
    }

    /** One place of a profile. Exactly one of {@code graph} and {@code template} is set. */
    record Place(String iri, String role, String graph, String template) {
    }

    /** The values a template is rendered with. A value the step does not state is null, and a template that needs it renders as nothing. */
    record Values(String root, String newRev, String month) {
    }

    private static Property dal(Model m, String name) {
        return m.createProperty(Namespaces.DAL + name);
    }

    /**
     * The places the accesses of {@code profile}'s generated operations land in, by place IRI. An access lands where {@code dal:landsIn}
     * says. A place no access lands in is not part of the profile's writes and is left out.
     */
    static List<Place> of(Model model, Resource profile) {
        Set<Resource> found = new TreeSet<>(Comparator.comparing(Resource::getURI));
        for (RDFNode operation : model.listObjectsOfProperty(profile, dal(model, "generatedOperation")).toList()) {
            for (RDFNode access : model.listObjectsOfProperty(operation.asResource(), dal(model, "access")).toList()) {
                for (RDFNode place : model.listObjectsOfProperty(access.asResource(), dal(model, "landsIn")).toList()) {
                    if (place.isURIResource()) {
                        found.add(place.asResource());
                    }
                }
            }
        }
        List<Place> out = new ArrayList<>();
        for (Resource p : found) {
            RDFNode fixed = p.getPropertyResourceValue(dal(model, "inGraph"));
            RDFNode named = p.hasProperty(dal(model, "inGraphNamed")) ? p.getProperty(dal(model, "inGraphNamed")).getObject() : null;
            RDFNode role = p.getPropertyResourceValue(dal(model, "inGraphRole"));
            String roleName = role == null || !role.isURIResource() ? "" : role.asResource().getURI().replaceAll(".*[#/]", "");
            if (fixed != null && fixed.isURIResource()) {
                out.add(new Place(p.getURI(), roleName, fixed.asResource().getURI(), null));
            } else if (named != null && named.isLiteral()) {
                out.add(new Place(p.getURI(), roleName, null, named.asLiteral().getLexicalForm()));
            }
        }
        return List.copyOf(out);
    }

    /**
     * The graph a template names for these values, or null when it holds a placeholder outside the closed set or one whose value the step
     * does not state. {@code {root}} is encoded as {@code ENCODE_FOR_URI} does.
     */
    static String render(String template, Values values) {
        Map<String, String> by = new HashMap<>();
        by.put("{root}", values.root() == null ? null : Graphs.encodeForUri(values.root()));
        by.put("{newRev}", values.newRev());
        by.put("{month}", values.month());
        StringBuilder out = new StringBuilder();
        int i = 0;
        while (i < template.length()) {
            int open = template.indexOf('{', i);
            if (open < 0) {
                out.append(template, i, template.length());
                break;
            }
            int close = template.indexOf('}', open);
            if (close < 0) {
                return null;
            }
            out.append(template, i, open);
            String value = by.get(template.substring(open, close + 1));
            if (value == null) {
                return null;
            }
            out.append(value);
            i = close + 1;
        }
        return out.toString();
    }

    /** The places {@code graph} is, by equality, in the order of their IRIs. Empty when the graph is none of them. */
    static List<Place> assign(List<Place> places, String graph, Values values) {
        List<Place> out = new ArrayList<>();
        for (Place p : places) {
            String named = p.graph() != null ? p.graph() : render(p.template(), values);
            if (graph.equals(named)) {
                out.add(p);
            }
        }
        out.sort(Comparator.comparing(Place::iri));
        return out;
    }
}
