// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import java.io.IOException;
import java.io.StringWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.function.Consumer;
import java.util.stream.Stream;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.vocabulary.RDF;
import org.nebularis.lattice.studio.store.Cst;

/**
 * The persistence compile job of the facility sample as the run worker reads it: the compiled profile the canvas fixture keeps, and the
 * SPARQL of the facility's operations that {@code workers/tests/test_config_studio_compiled_fixture.py} keeps equal to what the compiler gives.
 */
final class FacilityJob {
    static final Path PROFILE = Path.of("..", "..", "apps", "config-studio", "e2e", "fixtures", "compiled-profile-facility.ttl");
    static final Path OPERATIONS = Path.of("src", "test", "resources", "facility-job");
    static final Path SAMPLES = Path.of("..", "..", "contracts", "config-studio", "samples");
    static final String CLASS = "https://example.org/lending#Facility";

    private FacilityJob() {
    }

    /** The job, with {@code profile} run over the compiled profile's model first, for a test that changes what a profile states. */
    static Model job(Consumer<Model> profile) throws IOException {
        Model compiled = ModelFactory.createDefaultModel();
        RDFDataMgr.read(compiled, PROFILE.toUri().toString(), Lang.TURTLE);
        profile.accept(compiled);
        StringWriter turtle = new StringWriter();
        RDFDataMgr.write(turtle, compiled, Lang.TURTLE);
        Model m = ModelFactory.createDefaultModel();
        Resource job = m.createResource(Examples.JOB).addProperty(RDF.type, Cst.Job).addProperty(Cst.kind, Cst.Compile)
            .addProperty(Cst.target, Cst.target("persistence")).addProperty(Cst.status, Cst.Succeeded);
        int n = 0;
        job.addProperty(Cst.artefact, m.createResource(Examples.JOB + "#artefact-" + ++n).addProperty(Cst.group, "profile")
            .addProperty(Cst.path, "compiled-profile.ttl").addProperty(Cst.mediaType, "text/turtle").addProperty(Cst.content, turtle.toString()));
        for (Path file : operations()) {
            String path = OPERATIONS.relativize(file).toString().replace('\\', '/');
            job.addProperty(Cst.artefact, m.createResource(Examples.JOB + "#artefact-" + ++n).addProperty(Cst.group, "Facility")
                .addProperty(Cst.path, path).addProperty(Cst.mediaType, "application/sparql-query").addProperty(Cst.content, Files.readString(file)));
        }
        return m;
    }

    static Model job() throws IOException {
        return job(m -> { });
    }

    /** The SPARQL files of the facility's operations, in path order. */
    static List<Path> operations() throws IOException {
        try (Stream<Path> files = Files.walk(OPERATIONS)) {
            return files.filter(f -> f.toString().endsWith(".rq")).sorted().toList();
        }
    }
}
