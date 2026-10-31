// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.store;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Path;
import java.util.Iterator;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import java.util.TreeSet;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.query.QueryExecutionFactory;
import org.apache.jena.query.QueryFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.ResourceFactory;
import org.apache.jena.rdfconnection.RDFConnection;
import org.apache.jena.sparql.core.DatasetGraph;
import org.apache.jena.sparql.core.Quad;
import org.apache.jena.update.Update;
import org.apache.jena.update.UpdateRequest;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.nebularis.lattice.persistence.PayloadException;
import org.nebularis.lattice.studio.store.StudioOperations.Family;

/** The operations layer on Jena in memory, against the profile and operations the stage tool wrote. */
class StudioOperationsTest {
    private static final String RECORDED_AT = org.nebularis.lattice.persistence.Namespaces.PAT + "recordedAt";
    private static final String CAUSE = "urn:ex:cause";
    private static final String ACTOR = "urn:ex:actor";
    private static StudioOperations ops;

    /** A store that lets the test see every quad. */
    private record Fixture(DatasetGraph dataset, StudioStore store) {
        static Fixture create() {
            DatasetGraph dataset = DatasetFactory.createTxnMem().asDatasetGraph();
            return new Fixture(dataset, new StudioStore(RDFConnection.connect(DatasetFactory.wrap(dataset))));
        }

        void run(List<Update> updates) {
            UpdateRequest request = new UpdateRequest();
            updates.forEach(request::add);
            store.update(request);
        }

        /** Every quad, with the store's {@code NOW()} in a receipt blanked. */
        Set<String> quads() {
            Set<String> out = new TreeSet<>();
            for (Iterator<Quad> it = dataset.find(); it.hasNext();) {
                Quad q = it.next();
                String object = q.getPredicate().getURI().equals(RECORDED_AT) ? "<recorded>" : q.getObject().toString();
                out.add(q.getGraph() + " " + q.getSubject() + " " + q.getPredicate() + " " + object);
            }
            return out;
        }
    }

    @BeforeAll
    static void load() {
        ops = StudioOperations.load(Path.of(System.getProperty("studio.assets"), "persistence"), 1L);
    }

    private static Model model(String root, String tag, int n) {
        Model m = ModelFactory.createDefaultModel();
        for (int i = 0; i < n; i++) {
            m.add(ResourceFactory.createResource(root), ResourceFactory.createProperty("urn:ex:p/" + i), tag + " " + i);
        }
        return m;
    }

    private static String rootOf(Family f) {
        return "urn:ex:" + f.name().toLowerCase() + "/1";
    }

    @ParameterizedTest
    @EnumSource(Family.class)
    void eachFamilyCreatesReplacesAndTombstones(Family f) {
        Fixture s = Fixture.create();
        String root = rootOf(f);
        Model first = model(root, "first", 5);
        Model second = model(root, "second", 4);
        assertEquals(Optional.empty(), ops.seq(s.store, f, root));

        s.run(ops.create(f, root, first, "urn:txn:t/1"));
        assertEquals(Optional.of(1L), ops.seq(s.store, f, root));
        assertTrue(s.store.graph(ops.graph(f, root)).isIsomorphicWith(first));
        assertEquals(Optional.of(ops.revision(f, root, 1)), ops.claimed(s.store, "urn:txn:t/1"));

        s.run(ops.replace(f, root, 1, second, first, second, "urn:txn:t/2"));
        assertEquals(Optional.of(2L), ops.seq(s.store, f, root));
        assertTrue(s.store.graph(ops.graph(f, root)).isIsomorphicWith(second));
        assertEquals(Optional.of(ops.revision(f, root, 2)), ops.claimed(s.store, "urn:txn:t/2"));

        Set<String> before = s.quads();
        s.run(ops.replace(f, root, 1, first, first, second, "urn:txn:t/3"));
        assertEquals(before, s.quads(), "a stale expectation writes nothing");
        s.run(ops.replace(f, root, 2, first, first, second, "urn:txn:t/2"));
        assertEquals(before, s.quads(), "a replay of a claimed transaction writes nothing");
        s.run(ops.create(f, root, first, "urn:txn:t/4"));
        assertEquals(before, s.quads(), "a create over a version row writes nothing");
        s.run(ops.tombstone(f, root, 1, "urn:txn:t/5", CAUSE, ACTOR));
        assertEquals(before, s.quads(), "a stale tombstone writes nothing");

        s.run(ops.tombstone(f, root, 2, "urn:txn:t/6", CAUSE, ACTOR));
        assertTrue(s.store.rawGraph(ops.graph(f, root)).isEmpty());
        assertEquals(Optional.empty(), ops.seq(s.store, f, root));
    }

    @ParameterizedTest
    @EnumSource(value = Family.class, names = {"PART", "DOCUMENT"})
    void aLinearReplaceLeavesWhatTheGeneratedReplaceLeaves(Family f) {
        String root = rootOf(f);
        Model old = model(root, "old", 300);
        Model next = model(root, "old", 150).add(model(root, "new", 300).difference(model(root, "new", 150)));
        Model asserted = next.difference(old);
        Model retracted = old.difference(next);
        assertFalse(asserted.isEmpty());
        assertFalse(retracted.isEmpty());

        Fixture generated = Fixture.create();
        Fixture linear = Fixture.create();
        generated.run(ops.create(f, root, old, "urn:txn:l/1"));
        linear.run(ops.create(f, root, old, "urn:txn:l/1"));
        assertEquals(generated.quads(), linear.quads());

        generated.run(ops.replace(f, root, 1, next, asserted, retracted, "urn:txn:l/2"));
        List<Update> two = ops.replaceLinear(f, root, 1, next, asserted, retracted, "urn:txn:l/2");
        assertEquals(2, two.size());
        linear.run(two);
        assertEquals(Optional.of(2L), ops.seq(linear.store, f, root));
        assertEquals(generated.quads(), linear.quads());
        assertTrue(linear.store.graph(ops.graph(f, root)).isIsomorphicWith(next));

        Set<String> before = linear.quads();
        linear.run(ops.replaceLinear(f, root, 1, old, retracted, asserted, "urn:txn:l/3"));
        assertEquals(before, linear.quads(), "a stale linear replace deletes nothing");
        linear.run(ops.replaceLinear(f, root, 2, old, retracted, asserted, "urn:txn:l/2"));
        assertEquals(before, linear.quads(), "a replayed linear replace deletes nothing");
    }

    @Test
    void aLinearReplaceIsOnlyForPartsAndDocuments() {
        assertThrows(IllegalArgumentException.class,
            () -> ops.replaceLinear(Family.LINEAGE, "urn:ex:l", 1, model("urn:ex:l", "x", 1), null, null, "urn:txn:x/1"));
    }

    @ParameterizedTest
    @EnumSource(value = Family.class, names = {"PART", "DOCUMENT"})
    void theLogHoldsTheDeltaGiven(Family f) {
        String root = rootOf(f);
        Model old = model(root, "old", 10);
        Model next = model(root, "new", 8);
        Model asserted = model(root, "asserted", 3);
        Model retracted = model(root, "retracted", 2);
        for (boolean linear : new boolean[] {false, true}) {
            Fixture s = Fixture.create();
            s.run(ops.create(f, root, old, "urn:txn:d/1"));
            s.run(linear ? ops.replaceLinear(f, root, 1, next, asserted, retracted, "urn:txn:d/2")
                : ops.replace(f, root, 1, next, asserted, retracted, "urn:txn:d/2"));
            String rev = ops.revision(f, root, 2);
            assertTrue(s.store.rawGraph(rev + "/add").isIsomorphicWith(asserted), "add graph, linear " + linear);
            assertTrue(s.store.rawGraph(rev + "/del").isIsomorphicWith(retracted), "del graph, linear " + linear);
            assertTrue(s.store.rawGraph(ops.revision(f, root, 1) + "/add").isIsomorphicWith(old), "the create's add graph");
        }
    }

    @Test
    void aBlankNodeIsRefusedBeforeAnythingIsBuilt() {
        Fixture s = Fixture.create();
        String root = rootOf(Family.PART);
        Model blank = model(root, "x", 2);
        blank.add(ResourceFactory.createResource(root), ResourceFactory.createProperty("urn:ex:child"), blank.createResource());
        assertThrows(PayloadException.class, () -> ops.create(Family.PART, root, blank, "urn:txn:b/1"));
        s.run(ops.create(Family.PART, root, model(root, "x", 2), "urn:txn:b/2"));
        Model skolemised = Skolem.skolemise(blank);
        assertThrows(PayloadException.class, () -> ops.replace(Family.PART, root, 1, blank, null, null, "urn:txn:b/3"));
        assertThrows(PayloadException.class, () -> ops.replaceLinear(Family.PART, root, 1, model(root, "x", 1), blank, null, "urn:txn:b/3"));
        s.run(ops.replace(Family.PART, root, 1, skolemised, null, null, "urn:txn:b/4"));
        assertTrue(s.store.graph(ops.graph(Family.PART, root)).isIsomorphicWith(Skolem.unskolemise(skolemised)));
        assertTrue(s.store.rawGraph(ops.graph(Family.PART, root)).listObjects().filterKeep(o -> o.isURIResource()
            && Skolem.isSkolem(o.asNode())).hasNext(), "the store keeps the skolem IRI");
    }

    @Test
    void aGraphIsNamedAsTheGeneratedTextNamesIt() {
        String root = "urn:ex:a/b:c~d";
        var query = QueryFactory.create("SELECT (IRI(CONCAT(\"urn:lattice:studio:part/\", ENCODE_FOR_URI(\"" + root + "\"))) AS ?g) {}");
        String expected;
        try (var exec = QueryExecutionFactory.create(query, DatasetFactory.create())) {
            expected = exec.execSelect().next().getResource("g").getURI();
        }
        assertTrue(expected.contains("%3A") && expected.contains("%2F") && expected.contains("~"), expected);
        assertEquals(expected, ops.graph(Family.PART, root));
    }

    @Test
    void aRootThatTheEncodingEscapesIsWrittenToItsGraph() {
        Fixture s = Fixture.create();
        String root = "urn:ex:a/b:c";
        Model payload = model(root, "x", 3);
        s.run(ops.create(Family.PART, root, payload, "urn:txn:g/1"));
        assertEquals("urn:lattice:studio:part/urn%3Aex%3Aa%2Fb%3Ac", ops.graph(Family.PART, root));
        assertTrue(s.store.graph("urn:lattice:studio:part/urn%3Aex%3Aa%2Fb%3Ac").isIsomorphicWith(payload),
            "the generated guard accepted the graph, so the store computes the same name");
        assertEquals(Optional.of(1L), ops.seq(s.store, Family.PART, root));
        assertEquals("urn:rev:studio/urn%3Aex%3Aa%2Fb%3Ac/e0000000000000000001/0000000000000000002", ops.revision(Family.PART, root, 2));
    }

    @Test
    void aLiteralThatReadsLikeAVariableOrASlotIsStoredAsItIs() {
        Fixture s = Fixture.create();
        String root = rootOf(Family.PART);
        Model payload = ModelFactory.createDefaultModel();
        payload.add(ResourceFactory.createResource(root), ResourceFactory.createProperty("urn:ex:p"), "$root ?g $epoch {{{assertTriples}}} {{{payloadTriples}}}");
        s.run(ops.create(Family.PART, root, payload, "urn:txn:i/1"));
        assertTrue(s.store.graph(ops.graph(Family.PART, root)).isIsomorphicWith(payload));
        s.run(ops.replace(Family.PART, root, 1, payload, payload, payload, "urn:txn:i/2"));
        assertTrue(s.store.rawGraph(ops.revision(Family.PART, root, 2) + "/add").isIsomorphicWith(payload));
    }
}
