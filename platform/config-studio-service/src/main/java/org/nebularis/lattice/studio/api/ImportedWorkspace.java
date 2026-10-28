// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.api;

import java.util.Iterator;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.vocabulary.RDFS;
import org.nebularis.lattice.studio.store.Graphs;

/**
 * An exported workspace renamed under a new id: every graph name, and every IRI of the description, moves from the old
 * workspace's prefix to the new one's. The configurations' triples are kept as they are. The writer checks the rest.
 */
record ImportedWorkspace(Dataset graphs, String label, String problem) {
    private static final Pattern DESCRIPTION = Pattern.compile(
        Pattern.quote(Graphs.WORKSPACE_PREFIX) + "([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})");

    static ImportedWorkspace of(Dataset source, String newId) {
        if (!source.getDefaultModel().isEmpty()) {
            return refused("an export holds named graphs only");
        }
        String old = null;
        for (Iterator<Resource> it = source.listModelNames(); it.hasNext(); ) {
            Matcher m = DESCRIPTION.matcher(it.next().getURI());
            if (m.matches()) {
                if (old != null) {
                    return refused("an export holds one workspace");
                }
                old = m.group(1);
            }
        }
        if (old == null) {
            return refused("the export holds no workspace description");
        }
        String from = Graphs.workspace(old);
        String to = Graphs.workspace(newId);
        Dataset out = DatasetFactory.create();
        for (Iterator<Resource> it = source.listModelNames(); it.hasNext(); ) {
            String name = it.next().getURI();
            if (!name.equals(from) && !name.startsWith(from + ":")) {
                return refused("the export holds a graph of another workspace: " + name);
            }
            Model graph = source.getNamedModel(name);
            out.addNamedModel(to + name.substring(from.length()), name.equals(from) ? rename(graph, from, to) : graph);
        }
        Statement label = out.getNamedModel(to).createResource(to).getProperty(RDFS.label);
        return new ImportedWorkspace(out, label != null && label.getObject().isLiteral() ? label.getString() : "Imported workspace", null);
    }

    private static Model rename(Model description, String from, String to) {
        Model out = ModelFactory.createDefaultModel();
        description.listStatements().forEachRemaining(s -> out.add(
            (Resource) move(out, s.getSubject(), from, to), s.getPredicate(), move(out, s.getObject(), from, to)));
        return out;
    }

    private static RDFNode move(Model m, RDFNode node, String from, String to) {
        if (node.isURIResource()) {
            String iri = node.asResource().getURI();
            if (iri.equals(from) || iri.startsWith(from + ":")) {
                return m.createResource(to + iri.substring(from.length()));
            }
        }
        return node;
    }

    private static ImportedWorkspace refused(String problem) {
        return new ImportedWorkspace(null, null, problem);
    }
}
