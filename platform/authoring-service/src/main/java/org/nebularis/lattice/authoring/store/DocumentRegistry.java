// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.store;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.StmtIterator;
import org.apache.jena.vocabulary.RDF;
import org.nebularis.lattice.authoring.model.GraphRef;
import org.nebularis.lattice.authoring.rdf.IriMinter;
import org.nebularis.lattice.authoring.rdf.Vocab;

/**
 * The registry of documents this service knows about: one named graph (plan \u00a72.3's registry
 * graph), read, changed in a fresh in-memory model and put back, inside {@code synchronized}
 * methods so a read-modify-write race never loses an update (plan WA4).
 */
public final class DocumentRegistry {
    private final AuthoringStore store;
    private final IriMinter minter;
    private final String registryGraphIri;

    public DocumentRegistry(AuthoringStore store, IriMinter minter) {
        this.store = store;
        this.minter = minter;
        this.registryGraphIri = minter.registryGraph();
    }

    public synchronized int latestRevision(String documentId) {
        Model model = currentModel();
        Resource document = model.createResource(minter.document(documentId));
        if (!model.containsResource(document)) {
            return 0;
        }
        return document.getRequiredProperty(Vocab.WAP_LATEST_REVISION).getInt();
    }

    public synchronized Optional<DocumentView> find(String documentId) {
        Model model = currentModel();
        Resource document = model.createResource(minter.document(documentId));
        if (!model.containsResource(document)) {
            return Optional.empty();
        }
        return Optional.of(new DocumentView(
            documentId,
            document.getRequiredProperty(Vocab.DCTERMS_TITLE).getString(),
            document.getRequiredProperty(Vocab.WAP_TEMPLATE_ID).getString(),
            document.getRequiredProperty(Vocab.WAP_LATEST_REVISION).getInt()
        ));
    }

    public synchronized void record(String documentId, int revision, String title, String templateId,
                                    GraphRef wordingGraph) {
        Model model = currentModel();
        Resource document = model.createResource(minter.document(documentId));
        document.removeAll(Vocab.DCTERMS_TITLE);
        document.removeAll(Vocab.WAP_TEMPLATE_ID);
        document.removeAll(Vocab.WAP_LATEST_REVISION);
        document.addProperty(RDF.type, Vocab.WAP_AUTHORING_DOCUMENT);
        document.addProperty(Vocab.WAP_DOCUMENT_ID, documentId);
        document.addProperty(Vocab.DCTERMS_TITLE, title);
        document.addProperty(Vocab.WAP_TEMPLATE_ID, templateId);
        document.addProperty(Vocab.WAP_LATEST_REVISION, model.createTypedLiteral(revision));

        Resource revisionResource = model.createResource(minter.revision(documentId, revision));
        revisionResource.addProperty(RDF.type, Vocab.WAP_REVISION);
        revisionResource.addProperty(Vocab.WAP_REVISION_OF, document);
        revisionResource.addProperty(Vocab.WAP_REVISION_NUMBER, model.createTypedLiteral(revision));
        revisionResource.addProperty(Vocab.WAP_WORDING_GRAPH, model.createResource(wordingGraph.graphIri()));
        revisionResource.addProperty(Vocab.WAP_REVISION_HASH, wordingGraph.revisionHash());
        revisionResource.addProperty(Vocab.DCTERMS_CREATED,
            model.createTypedLiteral(Instant.now().toString(), XSDDatatype.XSDdateTime));

        store.putGraph(registryGraphIri, model);
    }

    public synchronized List<String> documentIds() {
        Model model = currentModel();
        List<String> ids = new ArrayList<>();
        StmtIterator statements = model.listStatements(null, RDF.type, Vocab.WAP_AUTHORING_DOCUMENT);
        while (statements.hasNext()) {
            ids.add(statements.next().getSubject().getProperty(Vocab.WAP_DOCUMENT_ID).getString());
        }
        return ids;
    }

    private Model currentModel() {
        return store.getGraph(registryGraphIri).orElseGet(ModelFactory::createDefaultModel);
    }
}
