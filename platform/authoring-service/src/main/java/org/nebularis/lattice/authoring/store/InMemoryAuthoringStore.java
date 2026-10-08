// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.store;

import java.util.Optional;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.query.ReadWrite;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;

/** An {@link AuthoringStore} over an in-memory Jena dataset, for tests and the default wiring. */
public final class InMemoryAuthoringStore implements AuthoringStore {
    private final Dataset dataset = DatasetFactory.createTxnMem();

    @Override
    public void ensureReady() {
        // always ready
    }

    @Override
    public boolean ping() {
        return true;
    }

    @Override
    public void putGraph(String graphIri, Model model) {
        dataset.begin(ReadWrite.WRITE);
        try {
            Model named = dataset.getNamedModel(graphIri);
            named.removeAll();
            named.add(model);
            dataset.commit();
        } finally {
            dataset.end();
        }
    }

    @Override
    public Optional<Model> getGraph(String graphIri) {
        dataset.begin(ReadWrite.READ);
        try {
            if (!dataset.containsNamedModel(graphIri)) {
                return Optional.empty();
            }
            return Optional.of(ModelFactory.createDefaultModel().add(dataset.getNamedModel(graphIri)));
        } finally {
            dataset.end();
        }
    }
}
