// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.store;

import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.ResourceFactory;

/** The terms of `contracts/config-studio/studio-vocabulary.ttl` that the service writes or reads. */
public final class Cst {
    public static final String NS = "https://www.nebularis.org/neuro-semantic/lattice/poc/config-studio#";

    public static final Resource Workspace = r("Workspace");
    public static final Resource Job = r("Job");
    public static final Resource Validate = r("Validate");
    public static final Resource Compile = r("Compile");
    public static final Resource Persistence = r("Persistence");
    public static final Resource Surface = r("Surface");
    public static final Resource Queued = r("Queued");
    public static final Resource Failed = r("Failed");

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

    private Cst() {
    }

    private static Resource r(String name) {
        return ResourceFactory.createResource(NS + name);
    }

    private static Property p(String name) {
        return ResourceFactory.createProperty(NS + name);
    }
}
