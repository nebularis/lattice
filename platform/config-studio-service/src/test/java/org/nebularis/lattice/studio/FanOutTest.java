// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.graph.Triple;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.query.QueryExecutionFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.vocabulary.RDF;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.Maintenance;
import org.nebularis.lattice.studio.writes.Command;

/**
 * A write that changes a source also keeps the rows of the other sources it reaches, in its own request (PM-2). The contract is
 * {@code workspace-current}, which reads from a workspace's description into the graph of a lineage, so a publication that moves the lineage
 * changes the rows of every description that follows it. The operations are the surface compiler's, in {@code src/test/resources/fan-out},
 * and the expectation is the meaning of the promotion written as one query over every graph of the store.
 */
class FanOutTest {
    private static final String UNIT = "https://example.org/unit/scheme";
    private static final String KIND = "https://example.org/Kind";
    private static final String CONFIG = Fixture.PREFIXES + "ex:cfg <https://www.nebularis.org/neuro-semantic/lattice/surface#label> \"one\" .";
    private static final String WORKSPACE_CURRENT = Promotions.NS + "workspaceCurrent";
    private static final Path OPERATIONS = Path.of("src", "test", "resources", "fan-out");

    @TempDir Path dir;
    Fixture f;

    private static final class Promotions {
        static final String NS = org.nebularis.lattice.studio.store.Promotions.NS;
    }

    private Fixture fixture(Maintenance maintenance) throws IOException {
        return new Fixture(Fixture.assetsDir(dir.resolve("assets")), null, Set.of(), Clock.fixed(Instant.parse("2026-10-27T10:00:00Z"), ZoneOffset.UTC), maintenance);
    }

    @BeforeEach
    void setUp() throws IOException {
        f = fixture(Maintenance.load(OPERATIONS));
    }

    private ApiResponse as(String method, String path, String query, String body) {
        return f.send(method, path, query, new HashMap<>(Map.of("content-type", Fixture.TURTLE)), body == null ? new byte[0] : body.getBytes(StandardCharsets.UTF_8));
    }

    private static String version(String digest) {
        return UNIT + "/rev/1-" + digest;
    }

    /** A job the worker has finished, as the other tests write it. */
    private String finishedJob(String ws, String query, String body, Model artefactContent, Map<String, String> more) {
        ApiResponse r = as("POST", "/api/workspaces/" + ws + "/jobs", query, body);
        assertEquals(202, r.status());
        String job = r.headers().get("Location").substring("/api/jobs/".length());
        String iri = Graphs.job(job);
        Model m = ModelFactory.createDefaultModel().add(f.store.graph(iri));
        org.apache.jena.rdf.model.Resource node = m.createResource(iri);
        m.removeAll(node, Cst.status, null);
        node.addProperty(Cst.status, Cst.Succeeded);
        more.forEach((p, o) -> {
            if (o.startsWith("http") || o.startsWith("urn")) {
                node.addProperty(m.createProperty(Cst.NS + p), m.createResource(o));
            } else {
                node.addProperty(m.createProperty(Cst.NS + p), o);
            }
        });
        java.io.StringWriter nt = new java.io.StringWriter();
        RDFDataMgr.write(nt, artefactContent, Lang.NTRIPLES);
        node.addProperty(Cst.artefact, m.createResource().addProperty(Cst.path, "version.nt").addProperty(Cst.mediaType, "application/n-triples")
            .addProperty(Cst.content, nt.toString()));
        Dataset d = DatasetFactory.create();
        d.addNamedModel(iri, m);
        assertEquals(200, f.writes.send(new Command(UUID.randomUUID().toString(), "worker", Command.Type.JOB_UPDATE, ws, job, null, null, null, null, null, d, null, false)).status());
        return job;
    }

    private Model concepts(String digest) {
        Model m = ModelFactory.createDefaultModel();
        m.createResource(version(digest)).addProperty(Cst.Fnd.hasIdentity, m.createResource(UNIT));
        m.createResource(UNIT + "/fire").addProperty(RDF.type, m.createResource("http://www.w3.org/2004/02/skos/core#Concept"))
            .addProperty(m.createProperty("http://www.w3.org/2004/02/skos/core#inScheme"), m.createResource(version(digest)));
        return m;
    }

    /** The workspace's surface part, which a publication reads. */
    private void prepare(String ws) {
        assertEquals(204, f.put("/api/workspaces/" + ws + "/graphs/surface", "\"0\"", CONFIG).status());
    }

    private void publish(String ws, String digest) {
        String job = finishedJob(ws, "kind=publish&target=surface&unit=" + UNIT, CONFIG, concepts(digest),
            Map.of("lineage", UNIT, "version", version(digest), "unitKind", KIND, "digest", digest.repeat(4)));
        assertEquals(201, as("POST", "/api/workspaces/" + ws + "/publications", "job=" + job, null).status());
    }

    private void follow(String ws) {
        assertEquals(200, as("PUT", "/api/workspaces/" + ws + "/dependencies", null, Fixture.PREFIXES + "<urn:lattice:studio:ws:" + ws + "> cst:dependsOn <" + UNIT + "> .").status());
    }

    /** What the promotion means, over every graph of the store but the derived partitions: each workspace with the current version of each lineage it follows. */
    private Set<String> meaning() {
        Model world = ModelFactory.createDefaultModel();
        for (String g : f.store.graphNames()) {
            if (!g.startsWith(Graphs.PROMOTED_PREFIX)) {
                world.add(f.store.rawGraph(g));
            }
        }
        Set<String> out = new TreeSet<>();
        String query = "PREFIX cst: <" + Cst.NS + "> SELECT ?w ?v WHERE { ?w a cst:Workspace ; cst:dependsOn ?u . ?u cst:current ?v }";
        try (var exec = QueryExecutionFactory.create(query, world)) {
            exec.execSelect().forEachRemaining(row -> out.add(row.getResource("w").getURI() + " " + row.getResource("v").getURI()));
        }
        return out;
    }

    /** What the store holds as the promotion's rows, in the partition of each source. */
    private Set<String> held() {
        Set<String> out = new TreeSet<>();
        for (String g : f.store.graphNames()) {
            if (g.startsWith(Graphs.PROMOTED_PREFIX)) {
                f.store.rawGraph(g).listStatements(null, f.store.rawGraph(g).createProperty(WORKSPACE_CURRENT), (org.apache.jena.rdf.model.RDFNode) null)
                    .forEachRemaining(st -> out.add(st.getSubject().getURI() + " " + st.getObject().asResource().getURI()));
            }
        }
        return out;
    }

    @Test
    void aPublicationMovesTheRowsOfTheDescriptionsThatFollowTheLineageInTheSameRequest() {
        assertEquals(201, f.createWorkspace("One").status());
        String ws = Fixture.id(1);
        prepare(ws);
        publish(ws, "0123456789abcdef");
        follow(ws);
        assertEquals(Set.of(Graphs.workspace(ws) + " " + version("0123456789abcdef")), held(), "the description's own write reads the lineage's graph");
        assertEquals(meaning(), held());

        publish(ws, "fedcba9876543210");
        assertEquals(Set.of(Graphs.workspace(ws) + " " + version("fedcba9876543210")), held(), "the publication wrote the lineage, and the description's partition moved with it");
        assertEquals(meaning(), held());
    }

    @Test
    void withoutTheReachTheRowsStayAsTheDescriptionLeftThemWhichIsTheDifferenceThisSliceMakes() throws IOException {
        // the same operations with no reach query, so a write keeps only the source it writes
        Maintenance own = Maintenance.of(java.nio.file.Files.readString(OPERATIONS.resolve("partition-clear.rq")), Map.of("description", List.of(
            new Maintenance.Fill("workspace-current", java.nio.file.Files.readString(OPERATIONS.resolve("workspace-current-fill-all.rq"))))));
        f = fixture(own);
        assertEquals(201, f.createWorkspace("One").status());
        String ws = Fixture.id(1);
        prepare(ws);
        publish(ws, "0123456789abcdef");
        follow(ws);
        publish(ws, "fedcba9876543210");
        assertEquals(Set.of(Graphs.workspace(ws) + " " + version("0123456789abcdef")), held());
        assertTrue(!meaning().equals(held()), "the rows are stale, which is what a write that keeps only its own source leaves");
    }

    @Test
    void theSourcesAWriteReachesAreThoseOfEveryWorkspaceThatFollowsTheLineage() {
        assertEquals(201, f.createWorkspace("One").status());
        assertEquals(201, as("POST", "/api/workspaces", null, Fixture.PREFIXES + "ex:a ex:p ex:b .").status());
        prepare(Fixture.id(1));
        publish(Fixture.id(1), "0123456789abcdef");
        for (String ws : List.of(Fixture.id(1), Fixture.id(2))) {
            follow(ws);
        }
        Maintenance m = Maintenance.load(OPERATIONS);
        Triple moved = Triple.create(NodeFactory.createURI(UNIT), Cst.current.asNode(), NodeFactory.createURI(version("fedcba9876543210")));
        Set<String> reached = new TreeSet<>();
        m.reach("description", List.of(moved)).forEach(q -> reached.addAll(f.store.sources(q)));
        assertEquals(new TreeSet<>(List.of(Graphs.description(Fixture.id(1)), Graphs.description(Fixture.id(2)))), reached);
        Triple unrelated = Triple.create(NodeFactory.createURI("urn:x:other"), Cst.current.asNode(), NodeFactory.createURI("urn:x:v"));
        Set<String> none = new TreeSet<>();
        m.reach("description", List.of(unrelated)).forEach(q -> none.addAll(f.store.sources(q)));
        assertEquals(Set.of(), none, "a lineage nobody follows reaches no source");
    }
}
