// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.TreeMap;
import java.util.function.Consumer;
import java.util.stream.Stream;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.vocabulary.RDF;
import org.nebularis.lattice.studio.store.Cst;

/**
 * The surface compile job of the facility sample as the run worker reads it, with the artefacts of its {@code maintenance} group, which
 * {@code workers/tests/test_config_studio_surface_step_fixture.py} keeps equal to what the compiler gives. The job's other artefacts are the
 * compiled ontology modules, which a step does not read.
 */
final class SurfaceJob {
    static final Path DIR = Path.of("src", "test", "resources", "surface-job");

    private SurfaceJob() {
    }

    /** The job's artefacts by path, as the fixture holds them. */
    static Map<String, String> artefacts() throws IOException {
        Map<String, String> out = new TreeMap<>();
        try (Stream<Path> files = Files.walk(DIR)) {
            for (Path file : files.filter(Files::isRegularFile).sorted().toList()) {
                out.put(DIR.relativize(file).toString().replace('\\', '/'), Files.readString(file));
            }
        }
        return out;
    }

    static Model job() throws IOException {
        return build(artefacts());
    }

    /** The job with {@code change} applied to its artefacts first, for a test that changes what the job holds. */
    static Model job(Consumer<Map<String, String>> change) throws IOException {
        Map<String, String> artefacts = artefacts();
        change.accept(artefacts);
        return build(artefacts);
    }

    static Model build(Map<String, String> artefacts) {
        Model m = ModelFactory.createDefaultModel();
        Resource job = m.createResource(Examples.JOB).addProperty(RDF.type, Cst.Job).addProperty(Cst.kind, Cst.Compile)
            .addProperty(Cst.target, Cst.target("surface")).addProperty(Cst.status, Cst.Succeeded);
        int n = 0;
        for (Map.Entry<String, String> a : artefacts.entrySet()) {
            String media = a.getKey().endsWith(".json") ? "application/json" : a.getKey().endsWith(".rq") && a.getKey().contains("read-set") ? "application/sparql-query" : "application/sparql-update";
            job.addProperty(Cst.artefact, m.createResource(Examples.JOB + "#artefact-" + ++n).addProperty(Cst.group, "maintenance")
                .addProperty(Cst.path, a.getKey()).addProperty(Cst.mediaType, media).addProperty(Cst.content, a.getValue()));
        }
        return m;
    }
}
