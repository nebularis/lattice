// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.vocabulary.RDF;
import org.nebularis.lattice.studio.store.Cst;

/** The `policies` example's compile job, as `TransformRunTest` builds it, with the order its artefacts are added in as a choice. */
final class Examples {
    static final Path EXAMPLE = Path.of("..", "..", "tools", "mork_transforms", "tests", "examples", "policies");
    static final String JOB = "urn:lattice:studio:job:00000000-0000-4000-8000-000000000001";
    static final String RUN = "urn:lattice:studio:run:3f2b8c1e-5a47-4d0e-9b1a-6c7d8e9f0a1b";

    private Examples() {
    }

    static Model compileJob(boolean reversed) throws IOException {
        Model m = ModelFactory.createDefaultModel();
        Resource job = m.createResource(JOB).addProperty(RDF.type, Cst.Job).addProperty(Cst.kind, Cst.Compile)
            .addProperty(Cst.target, Cst.target("mapping")).addProperty(Cst.status, Cst.Succeeded);
        List<String[]> artefacts = new ArrayList<>(List.of(
            new String[] {"urn:example:mapping/xml#Scheme", "xml.xsl", "application/xslt+xml"},
            new String[] {"urn:example:mapping/xml#Scheme", "xml.xsl.attribution.json", "application/json"},
            new String[] {"urn:example:mapping/json#Scheme", "json.jolt.json", "application/json"},
            new String[] {"urn:example:mapping/json#Scheme", "json.jolt.json.attribution.json", "application/json"},
            new String[] {"urn:example:mapping/rdf#Scheme", "Scheme.compiled.ttl", "text/turtle"}));
        if (reversed) {
            Collections.reverse(artefacts);
        }
        int n = 0;
        for (String[] a : artefacts) {
            job.addProperty(Cst.artefact, m.createResource(JOB + "#artefact-" + ++n).addProperty(Cst.group, a[0])
                .addProperty(Cst.path, a[1]).addProperty(Cst.mediaType, a[2])
                .addProperty(Cst.content, a[1].endsWith(".ttl") ? "" : Files.readString(EXAMPLE.resolve("compiled").resolve(a[1]))));
        }
        return m;
    }

    static String xmlSample() throws IOException {
        return Files.readString(EXAMPLE.resolve("source.xml"));
    }

    static String jsonSample() throws IOException {
        return Files.readString(EXAMPLE.resolve("source.json"));
    }
}
