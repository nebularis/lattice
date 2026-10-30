// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;
import java.util.TreeMap;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.vocabulary.RDF;
import org.junit.jupiter.api.Test;
import org.nebularis.lattice.studio.store.Cst;

/** Runs the `policies` example's compiled transforms, which `tools/mork_transforms`'s tests keep equal to the compiler's. */
class TransformRunTest {
    private static final Path EXAMPLE = Path.of("..", "..", "tools", "mork_transforms", "tests", "examples", "policies");
    private static final String JOB = "urn:lattice:studio:job:00000000-0000-4000-8000-000000000001";
    private static final String RUN = "urn:lattice:studio:transform:00000000-0000-4000-8000-000000000002";

    private static Model compileJob() throws IOException {
        Model m = ModelFactory.createDefaultModel();
        Resource job = m.createResource(JOB).addProperty(RDF.type, Cst.Job).addProperty(Cst.kind, Cst.Compile)
            .addProperty(Cst.target, Cst.target("mapping")).addProperty(Cst.status, Cst.Succeeded);
        int n = 0;
        for (String[] a : new String[][] {
            {"urn:example:mapping/xml#Scheme", "xml.xsl", "application/xslt+xml"},
            {"urn:example:mapping/xml#Scheme", "xml.xsl.attribution.json", "application/json"},
            {"urn:example:mapping/json#Scheme", "json.jolt.json", "application/json"},
            {"urn:example:mapping/json#Scheme", "json.jolt.json.attribution.json", "application/json"},
            {"urn:example:mapping/rdf#Scheme", "Scheme.compiled.ttl", "text/turtle"}}) {
            job.addProperty(Cst.artefact, m.createResource(JOB + "#artefact-" + ++n).addProperty(Cst.group, a[0])
                .addProperty(Cst.path, a[1]).addProperty(Cst.mediaType, a[2])
                .addProperty(Cst.content, a[1].endsWith(".ttl") ? "" : Files.readString(EXAMPLE.resolve("compiled").resolve(a[1]))));
        }
        return m;
    }

    /** Each mapping's artefact, by the mapping's local name. */
    private static Map<String, String> byMapping(Model reply) {
        Map<String, String> out = new TreeMap<>();
        for (Statement s : reply.getResource(RUN).listProperties(Cst.artefact).toList()) {
            out.put(s.getResource().getProperty(Cst.group).getString().replaceAll(".*#", ""), s.getResource().getProperty(Cst.content).getString());
        }
        return out;
    }

    private static long notRun(Model reply) {
        return reply.listStatements(null, Cst.code, "NotRun").toList().size();
    }

    @Test
    void anXmlSampleRunsTheStylesheetAndEachTripleGoesToTheMappingThatWroteIt() throws IOException {
        Model reply = TransformRun.run(compileJob(), JOB, RUN, "application/xml", Files.readString(EXAMPLE.resolve("source.xml")));
        assertTrue(reply.contains(reply.getResource(RUN), Cst.status, Cst.Succeeded));
        Map<String, String> wrote = byMapping(reply);
        assertEquals(java.util.Set.of("Cover", "Holder", "Insurer", "Peril", "Policy", "Status"), wrote.keySet());
        assertTrue(wrote.get("Policy").contains("<urn:example:base/policy/P-1> <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <urn:example:target#Policy> ."));
        assertTrue(wrote.get("Insurer").contains("<urn:example:target#Acme> <urn:example:target#insures> <urn:example:base/policy/P-1> ."));
        assertTrue(wrote.get("Cover").contains("<urn:example:target#coverOf> <urn:example:base/policy/P-1> ."));
        assertTrue(wrote.get("Peril").contains("<urn:example:target#peril> <urn:example:target#Fire> ."));
        assertEquals(2, notRun(reply), "the JSON scheme and the RDF scheme are reported as not run");
    }

    @Test
    void aJsonSampleRunsTheChainAndAMalformedOneFailsTheRun() throws IOException {
        Model reply = TransformRun.run(compileJob(), JOB, RUN, "application/json", Files.readString(EXAMPLE.resolve("source.json")));
        assertTrue(reply.contains(reply.getResource(RUN), Cst.status, Cst.Succeeded));
        assertTrue(byMapping(reply).get("Cover").contains("<urn:example:base/cover/policies/0/covers/1> <urn:example:target#coverOf> <urn:example:base/policy/P-1> ."));
        Model bad = TransformRun.run(compileJob(), JOB, RUN, "application/json", "{not json");
        assertTrue(bad.contains(bad.getResource(RUN), Cst.status, Cst.Failed));
        Model turtle = TransformRun.run(compileJob(), JOB, RUN, "text/turtle", "");
        assertTrue(turtle.contains(turtle.getResource(RUN), Cst.status, Cst.Failed));
    }
}
