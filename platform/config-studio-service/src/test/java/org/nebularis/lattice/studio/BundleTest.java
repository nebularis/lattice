// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.Map;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.Reply;
import org.nebularis.lattice.studio.writes.Writer;

/** A published version bundled with what it pins, and compiled in place of a body (ADR-A149 decisions 4 and 10). */
class BundleTest {
    private static final String WS = Fixture.id(1);
    private static final String BASE = "/api/workspaces/" + WS;
    private static final String CONFIG = Fixture.PREFIXES
        + "ex:cfg <https://www.nebularis.org/neuro-semantic/lattice/surface#label> \"one\" .";
    private static final String[] UNITS = {"https://example.org/unit/a", "https://example.org/unit/b", "https://example.org/unit/c"};
    private static final String[] DIGESTS = {"0123456789abcdef", "fedcba9876543210", "00112233445566ff"};

    @TempDir Path dir;
    Fixture f;

    @BeforeEach
    void setUp() throws IOException {
        f = new Fixture(Fixture.assetsDir(dir));
        assertEquals(201, f.createWorkspace("Plan").status());
        assertEquals(204, f.put(BASE + "/graphs/surface", "\"0\"", CONFIG).status());
    }

    private static String version(int i) {
        return UNITS[i] + "/rev/1-" + DIGESTS[i];
    }

    /** Version {@code i}'s content, pinning version {@code pinned} when it is not negative. */
    private static Model content(int i, int pinned) {
        Model m = ModelFactory.createDefaultModel();
        Resource v = m.createResource(version(i));
        v.addProperty(Cst.Fnd.hasIdentity, m.createResource(UNITS[i]));
        v.addProperty(m.createProperty("https://example.org/p"), DIGESTS[i]);
        if (pinned >= 0) {
            v.addProperty(Cst.pins, m.createResource(version(pinned)));
        }
        return m;
    }

    private void publish(int i, int pinned) {
        ApiResponse r = f.send("POST", BASE + "/jobs", "kind=publish&target=surface&unit=" + UNITS[i], Map.of(), new byte[0]);
        assertEquals(202, r.status());
        String job = r.headers().get("Location").substring("/api/jobs/".length());
        String iri = Graphs.job(job);
        Model m = ModelFactory.createDefaultModel().add(f.store.graph(iri));
        Resource node = m.createResource(iri);
        m.removeAll(node, Cst.status, null);
        node.addProperty(Cst.status, Cst.Succeeded);
        node.addProperty(Cst.lineage, m.createResource(UNITS[i]));
        node.addProperty(Cst.version, m.createResource(version(i)));
        node.addProperty(Cst.digest, DIGESTS[i].repeat(4));
        node.addProperty(Cst.unitKind, m.createResource("https://example.org/Kind"));
        java.io.StringWriter nt = new java.io.StringWriter();
        RDFDataMgr.write(nt, content(i, pinned), Lang.NTRIPLES);
        node.addProperty(Cst.artefact, m.createResource().addProperty(Cst.path, "version.nt")
            .addProperty(Cst.mediaType, "application/n-triples").addProperty(Cst.content, nt.toString()));
        Dataset d = DatasetFactory.create();
        d.addNamedModel(iri, m);
        assertEquals(200, f.writes.send(new Command(java.util.UUID.randomUUID().toString(), "worker", Command.Type.JOB_UPDATE, WS, job,
            null, null, null, null, null, d, null, false)).status());
        assertEquals(201, f.send("POST", BASE + "/publications", "job=" + job, Map.of(), new byte[0]).status());
    }

    private ApiResponse bundle(String iri) {
        return f.send("GET", "/api/registry/bundle", "iri=" + java.net.URLEncoder.encode(iri, StandardCharsets.UTF_8), Map.of(), new byte[0]);
    }

    private ApiResponse compile(String version) {
        return f.send("POST", BASE + "/jobs", "kind=compile&target=surface&version=" + java.net.URLEncoder.encode(version, StandardCharsets.UTF_8),
            Map.of(), new byte[0]);
    }

    @Test
    void aBundleHoldsTheVersionAndWhatItPinsEachUnderItsOwnName() {
        publish(2, -1);
        publish(1, 2);
        publish(0, 1);
        ApiResponse r = bundle(version(0));
        assertEquals(200, r.status());
        assertTrue(r.headers().get("Content-Type").startsWith("application/trig"));
        Dataset d = DatasetFactory.create();
        RDFDataMgr.read(d, new java.io.ByteArrayInputStream(r.body()), Lang.TRIG);
        assertTrue(d.getDefaultModel().isEmpty());
        java.util.Set<String> names = new java.util.HashSet<>();
        d.listNames().forEachRemaining(names::add);
        assertEquals(java.util.Set.of(version(0), version(1), version(2)), names);
        assertTrue(d.getNamedModel(version(0)).isIsomorphicWith(content(0, 1)));
        assertTrue(d.getNamedModel(version(1)).isIsomorphicWith(content(1, 2)));
        assertTrue(d.getNamedModel(version(2)).isIsomorphicWith(content(2, -1)));
        // A version that pins nothing bundles alone.
        Dataset leaf = DatasetFactory.create();
        RDFDataMgr.read(leaf, new java.io.ByteArrayInputStream(bundle(version(2)).body()), Lang.TRIG);
        assertEquals(1, leaf.asDatasetGraph().size());
    }

    @Test
    void anUnknownVersionHasNoBundle() {
        publish(0, -1);
        assertEquals(404, bundle(UNITS[1] + "/rev/1-" + DIGESTS[1]).status());
        assertEquals(404, bundle("not-a-version").status());
        assertEquals(404, f.send("GET", "/api/registry/bundle", Map.of(), null).status());
    }

    @Test
    void aCompileJobNamingAVersionReadsItsContent() {
        publish(0, -1);
        ApiResponse r = compile(version(0));
        assertEquals(202, r.status());
        String job = r.headers().get("Location").substring("/api/jobs/".length());
        Model m = f.store.graph(Graphs.job(job));
        Resource node = m.createResource(Graphs.job(job));
        assertTrue(m.contains(node, Cst.kind, Cst.Compile));
        assertTrue(m.contains(node, Cst.fromVersion, m.createResource(version(0))));
        assertTrue(f.store.graph(Graphs.jobInput(job)).isIsomorphicWith(content(0, -1)));
    }

    @Test
    void aCompileJobNamingAnUnknownVersionIsRefused() {
        assertEquals(404, compile(version(0)).status());
        assertEquals(404, compile("not-a-version").status());
    }
}
