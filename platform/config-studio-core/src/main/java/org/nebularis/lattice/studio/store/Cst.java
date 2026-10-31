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
    /** A job kind that versions a unit of a configuration part for publication (ADR-A149). */
    public static final Resource Publish = r("Publish");
    /** An event of a lineage's registry graph, the publication of one version. */
    /** A job kind that reads imported RDF and gives the digest of its content (ADR-A149 decision 6). */
    public static final Resource Fence = r("Fence");
    public static final Resource Publication = r("Publication");
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
    /** A graph a job reads as context and never validates, one of its workspace's configuration parts other than its target. */
    public static final Property contextGraph = p("contextGraph");
    public static final Property submittedAt = p("submittedAt");
    public static final Property startedAt = p("startedAt");
    public static final Property finishedAt = p("finishedAt");
    public static final Property failureMessage = p("failureMessage");
    public static final Property artefact = p("artefact");
    public static final Property path = p("path");
    public static final Property content = p("content");
    public static final Property mediaType = p("mediaType");
    public static final Property group = p("group");
    public static final Property stratum = p("stratum");
    public static final Property conforms = p("conforms");
    public static final Property report = p("report");
    public static final Resource Artefact = r("Artefact");
    public static final Resource Transform = r("Transform");
    public static final Property compileJob = p("compileJob");
    public static final Property fromSample = p("fromSample");
    public static final Resource Receipt = r("Receipt");
    public static final Property commandId = p("commandId");
    public static final Property command = p("command");
    public static final Property sender = p("sender");
    /** Who asked for a write, as the service authenticated them (PRI-54). */
    public static final Property principal = p("principal");
    /** The principal who owns a workspace (ADR-A149 decision 9). */
    public static final Property owner = p("owner");
    /** A workspace's mode, {@code cst:Locked}, {@code cst:ReadOnly} or {@code cst:Shared}. */
    public static final Property mode = p("mode");

    /** The mode node of {@code name}, one of {@code Workspace.MODES}. */
    public static Resource mode(String name) {
        return ResourceFactory.createResource(NS + switch (name) {
            case "locked" -> "Locked";
            case "read-only" -> "ReadOnly";
            default -> "Shared";
        });
    }

    /** The name of mode node {@code node}, or null when it names none. */
    public static String modeName(Resource node) {
        return switch (node.isURIResource() ? node.getURI() : "") {
            case NS + "Locked" -> "locked";
            case NS + "ReadOnly" -> "read-only";
            case NS + "Shared" -> "shared";
            default -> null;
        };
    }
    /** A published lineage a workspace follows, or a version it pins (ADR-A149 decision 5). */
    public static final Property dependsOn = p("dependsOn");
    /** An import graph a workspace holds, stored once by its digest. */
    public static final Property holdsImport = p("holdsImport");
    public static final Property job = p("job");
    /** The unit IRI a publish job versions, which becomes the lineage. */
    public static final Property unit = p("unit");
    public static final Property lineage = p("lineage");
    public static final Property version = p("version");
    /** The first 64 hexadecimal digits of a version's digest, of which its IRI holds 16. */
    public static final Property digest = p("digest");
    public static final Property unitKind = p("unitKind");
    /** A lineage's latest version. */
    public static final Property current = p("current");
    public static final Property sequence = p("sequence");
    public static final Property previousPublication = p("previousPublication");
    public static final Property publishedAt = p("publishedAt");
    public static final Property fromWorkspace = p("fromWorkspace");
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
    public static final Resource MappingLanguageModelProposer = r("MappingLanguageModelProposer");
    public static final Resource RmlImporter = r("RmlImporter");
    public static final Resource ToolCall = r("ToolCall");
    public static final Resource ToolRequest = r("ToolRequest");
    public static final Property toolName = p("toolName");
    public static final Property toolArguments = p("toolArguments");
    public static final Property documentRole = p("documentRole");
    public static final Resource SourceVocabulary = r("SourceVocabulary");
    public static final Resource SampleSource = r("SampleSource");
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

    /** Foundation's terms for versions and identity. */
    public static final class Fnd {
        public static final String NS = "https://www.nebularis.org/neuro-semantic/lattice/foundation#";
        public static final Resource PersistentIdentity = ResourceFactory.createResource(NS + "PersistentIdentity");
        public static final Property hasVersion = ResourceFactory.createProperty(NS + "hasVersion");
        public static final Property supersededBy = ResourceFactory.createProperty(NS + "supersededBy");
        public static final Property hasIdentity = ResourceFactory.createProperty(NS + "hasIdentity");

        private Fnd() {
        }
    }

    /** PROV's terms for a publication. */
    public static final class Prov {
        public static final String NS = "http://www.w3.org/ns/prov#";
        public static final Resource Activity = ResourceFactory.createResource(NS + "Activity");
        public static final Property generated = ResourceFactory.createProperty(NS + "generated");

        private Prov() {
        }
    }

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
