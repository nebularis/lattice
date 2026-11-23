// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.List;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.query.ARQ;
import org.apache.jena.query.ReadWrite;
import org.apache.jena.sparql.ARQConstants;
import org.apache.jena.sparql.core.DatasetGraph;
import org.apache.jena.sparql.core.DatasetGraphFactory;
import org.apache.jena.sparql.core.Quad;
import org.apache.jena.sparql.exec.UpdateExec;
import org.apache.jena.sparql.expr.NodeValue;
import org.apache.jena.system.Txn;
import org.apache.jena.update.UpdateFactory;
import org.junit.jupiter.api.Test;

/**
 * Probe for the clock the generated persistence writes read (TD-256, slice SVA-P3). A SPARQL Update runs over an in-memory Jena dataset
 * with a time set in advance in the execution's context and in the dataset's context, and the test records that {@code NOW()} ignores
 * it. Jena's {@code Context.setCurrentDateTime} overwrites {@code ARQConstants.sysCurrentTime} unconditionally, in
 * {@code UpdateProcessorBase}, {@code UpdateEngineBase} and again in {@code QueryExecDataset.init} for the WHERE of each operation, so
 * every operation of one request reads the clock afresh and no stated time reaches it. A Jena that starts honouring a stated time fails
 * these tests, and the simulator can then pin the transaction time as the maintainer decided on 2026-11-19.
 */
class NowPinningProbeTest {
    private static final Node PIN = NodeValue.makeDateTime("2026-03-31T23:59:58Z").asNode();
    /**
     * Each operation joins the {@code urn:load} triples with themselves first, so it takes long enough that the clock has moved on by the time
     * the next operation reads it, whatever the resolution of the engine's clock.
     */
    private static final String LOAD = "?a <urn:load> ?b . ?c <urn:load> ?d .";
    private static final String REQUEST = """
        INSERT { GRAPH <urn:g:one> { <urn:s> <urn:now> ?t . <urn:s> <urn:month> ?m } } WHERE { LOAD BIND(NOW() AS ?t) BIND(SUBSTR(STR(NOW()),1,7) AS ?m) } ;
        INSERT { GRAPH ?g { <urn:s> <urn:now> ?t } } WHERE { LOAD BIND(NOW() AS ?t) BIND(IRI(CONCAT("urn:g:txlog/", SUBSTR(STR(NOW()),1,7))) AS ?g) } ;
        INSERT { GRAPH <urn:g:three> { <urn:s> <urn:now> ?t } } WHERE { LOAD BIND(NOW() AS ?t) }
        """.replace("LOAD", LOAD);

    private static DatasetGraph loaded() {
        DatasetGraph ds = DatasetGraphFactory.createTxnMem();
        Txn.executeWrite(ds, () -> {
            for (int i = 0; i < 250; i++) {
                ds.add(Quad.defaultGraphIRI, NodeFactory.createURI("urn:load:" + i), NodeFactory.createURI("urn:load"), NodeFactory.createURI("urn:o"));
            }
        });
        return ds;
    }

    private static List<String> timesOf(DatasetGraph ds) {
        List<String> out = new ArrayList<>();
        ds.find(Node.ANY, Node.ANY, NodeFactory.createURI("urn:now"), Node.ANY).forEachRemaining(q -> out.add(q.getObject().getLiteralLexicalForm()));
        out.sort(null);
        return out;
    }

    private static List<String> graphsOf(DatasetGraph ds) {
        List<String> out = new ArrayList<>();
        ds.listGraphNodes().forEachRemaining(g -> out.add(g.getURI()));
        out.sort(null);
        return out;
    }

    private static void assertClockWasRead(DatasetGraph ds) {
        List<String> times = timesOf(ds);
        assertEquals(3, times.size(), times.toString());
        for (String t : times) {
            assertNotEquals("2026-03-31T23:59:58Z", t, "the stated time reached NOW()");
        }
        // The engine read the clock for each operation, so the times differ from each other, and none of them is the stated one. A test of the
        // current year would fail at a new year, and these hold whenever they run.
        assertTrue(new java.util.HashSet<>(times).size() > 1, "the clock was read afresh for each operation, so the times are not all equal: " + times);
        // The month graph is the month of the clock the engine read, not of the stated time.
        assertFalse(graphsOf(ds).contains("urn:g:txlog/2026-03"), graphsOf(ds).toString());
    }

    @Test
    void aTimeSetOnTheExecutionDoesNotReachNow() {
        DatasetGraph ds = loaded();
        UpdateExec.dataset(ds).update(UpdateFactory.create(REQUEST)).set(ARQConstants.sysCurrentTime, PIN).build().execute();
        assertClockWasRead(ds);
    }

    @Test
    void aTimeSetOnTheDatasetContextDoesNotReachNow() {
        DatasetGraph ds = loaded();
        ds.getContext().set(ARQConstants.sysCurrentTime, PIN);
        UpdateExec.dataset(ds).update(UpdateFactory.create(REQUEST)).build().execute();
        assertClockWasRead(ds);
    }

    @Test
    void aTimeSetOnTheExecutionDoesNotReachNowInsideAWriteTransaction() {
        DatasetGraph ds = loaded();
        ds.begin(ReadWrite.WRITE);
        try {
            UpdateExec.dataset(ds).update(UpdateFactory.create(REQUEST)).set(ARQConstants.sysCurrentTime, PIN).build().execute();
            ds.commit();
        } finally {
            ds.end();
        }
        assertClockWasRead(ds);
    }

    @Test
    void theArqVersionTheProbeRanOn() {
        // Recorded so a change of the version the module resolves is noticed with the result above.
        assertEquals("6.2.0", ARQ.VERSION);
    }
}
