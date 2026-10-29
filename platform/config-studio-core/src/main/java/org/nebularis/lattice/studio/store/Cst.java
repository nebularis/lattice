// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.store;

import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.ResourceFactory;

/** The terms of `contracts/config-studio/studio-vocabulary.ttl` that the service writes or reads. */
public final class Cst {
    public static final String NS = "https://www.nebularis.org/neuro-semantic/lattice/config-studio#";

    public static final Resource Workspace = r("Workspace");
    public static final Resource Job = r("Job");
    public static final Resource Validate = r("Validate");
    public static final Resource Compile = r("Compile");
    public static final Resource Persistence = r("Persistence");
    public static final Resource Surface = r("Surface");
    public static final Resource Queued = r("Queued");
    public static final Resource Failed = r("Failed");
    public static final Resource Running = r("Running");
    public static final Resource Succeeded = r("Succeeded");

    public static final Property baselineGraph = p("baselineGraph");
    public static final Property baselineRevision = p("baselineRevision");
    public static final Property surfaceRevision = p("surfaceRevision");
    public static final Property persistenceRevision = p("persistenceRevision");
    public static final Property createdAt = p("createdAt");
    public static final Property modifiedAt = p("modifiedAt");
    public static final Property kind = p("kind");
    public static final Property target = p("target");
    public static final Property status = p("status");
    public static final Property workspace = p("workspace");
    public static final Property configGraph = p("configGraph");
    public static final Property submittedAt = p("submittedAt");
    public static final Property startedAt = p("startedAt");
    public static final Property finishedAt = p("finishedAt");
    public static final Property failureMessage = p("failureMessage");
    public static final Property fromSample = p("fromSample");
    public static final Resource Receipt = r("Receipt");
    public static final Property commandId = p("commandId");
    public static final Property command = p("command");
    public static final Property sender = p("sender");
    public static final Property job = p("job");
    public static final Property requestedAt = p("requestedAt");
    public static final Property committedAt = p("committedAt");
    public static final Property wrote = p("wrote");
    public static final Property receiptRevision = p("receiptRevision");
    public static final Resource Analyse = r("Analyse");
    public static final Resource Assemble = r("Assemble");
    public static final Resource Propose = r("Propose");
    public static final Resource DryRunJob = r("DryRunJob");
    public static final Resource SentenceFormProposer = r("SentenceFormProposer");
    public static final Resource LanguageModelProposer = r("LanguageModelProposer");
    public static final Resource OdrlProposer = r("OdrlProposer");
    public static final Resource ImportDocument = r("ImportDocument");
    public static final Property documentContent = p("documentContent");
    public static final Property documentMediaType = p("documentMediaType");
    public static final Resource Document = r("Document");
    public static final Property document = p("document");
    public static final Property template = p("template");
    /** {@code cst:revision}, a document's revision. A graph's is {@link #revision(String)}. */
    public static final Property documentRevision = p("revision");
    public static final Property markup = p("markup");
    public static final Resource DocumentTemplate = r("DocumentTemplate");
    public static final Resource DocumentSample = r("DocumentSample");
    public static final Property templateKey = p("templateKey");
    public static final Property sampleKey = p("sampleKey");
    public static final Property section = p("section");
    public static final Property sectionKey = p("sectionKey");
    public static final Property order = p("order");
    public static final Property elementKind = p("elementKind");
    public static final Property required = p("required");
    public static final Property code = p("code");
    public static final Property check = p("check");
    public static final Property detectionKind = p("detectionKind");
    public static final Property partIndex = p("partIndex");
    public static final Property start = p("start");
    public static final Property end = p("end");
    public static final Property action = p("action");
    public static final Property suggestedKey = p("suggestedKey");
    public static final Property suggestedValueType = p("suggestedValueType");
    public static final Property suggestedTarget = p("suggestedTarget");

    private Cst() {
    }

    /** The revision property of a named graph, {@code cst:<name>Revision}. */
    public static Property revision(String graph) {
        return p(graph + "Revision");
    }

    /** The job target naming a configuration graph, {@code cst:Surface} for "surface". */
    public static Resource target(String graph) {
        // The assembly part's target would otherwise be cst:Assembly, the class of what it holds.
        if (graph.equals("assembly")) {
            return r("AssemblyTarget");
        }
        return r(Character.toUpperCase(graph.charAt(0)) + graph.substring(1));
    }

    private static Resource r(String name) {
        return ResourceFactory.createResource(NS + name);
    }

    private static Property p(String name) {
        return ResourceFactory.createProperty(NS + name);
    }
}
