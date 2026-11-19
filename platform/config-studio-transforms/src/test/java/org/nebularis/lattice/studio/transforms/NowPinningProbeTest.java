// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.query.ARQ;
import org.apache.jena.query.ReadWrite;
import org.apache.jena.sparql.ARQConstants;
import org.apache.jena.sparql.core.DatasetGraph;
import org.apache.jena.sparql.core.DatasetGraphFactory;
import org.apache.jena.sparql.exec.UpdateExec;
import org.apache.jena.sparql.expr.NodeValue;
import org.apache.jena.update.UpdateFactory;
import org.junit.jupiter.api.Test;

/**
 * Probe for the clock the generated persistence writes read (TD-171, slice SVA-P3). A SPARQL Update runs over an in-memory Jena dataset
 * with a time set in advance in the execution's context and in the dataset's context, and the test records that {@code NOW()} ignores
 * it. Jena's {@code Context.setCurrentDateTime} overwrites {@code ARQConstants.sysCurrentTime} unconditionally, in
 * {@code UpdateProcessorBase}, {@code UpdateEngineBase} and again in {@code QueryExecDataset.init} for the WHERE of each operation, so
 * every operation of one request reads the clock afresh and no stated time reaches it. A Jena that starts honouring a stated time fails
 * these tests, and the simulator can then pin the transaction time as the maintainer decided on 2026-11-19.
 */
class NowPinningProbeTest {
    private static final Node PIN = NodeValue.makeDateTime("2026-03-31T23:59:58Z").asNode();
    private static final String REQUEST = """
        INSERT { GRAPH <urn:g:one> { <urn:s> <urn:now> ?t . <urn:s> <urn:month> ?m } } WHERE { BIND(NOW() AS ?t) BIND(SUBSTR(STR(NOW()),1,7) AS ?m) } ;
        INSERT { GRAPH ?g { <urn:s> <urn:now> ?t } } WHERE { BIND(NOW() AS ?t) BIND(IRI(CONCAT("urn:g:txlog/", SUBSTR(STR(NOW()),1,7))) AS ?g) } ;
        INSERT { GRAPH <urn:g:three> { <urn:s> <urn:now> ?t } } WHERE { BIND(NOW() AS ?t) }
        """;

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
            assertTrue(t.startsWith(String.valueOf(OffsetDateTime.now(ZoneOffset.UTC).getYear())), t);
        }
        // The month graph is the month of the clock the engine read, not of the stated time.
        assertFalse(graphsOf(ds).contains("urn:g:txlog/2026-03"), graphsOf(ds).toString());
    }

    @Test
    void aTimeSetOnTheExecutionDoesNotReachNow() {
        DatasetGraph ds = DatasetGraphFactory.createTxnMem();
        UpdateExec.dataset(ds).update(UpdateFactory.create(REQUEST)).set(ARQConstants.sysCurrentTime, PIN).build().execute();
        assertClockWasRead(ds);
    }

    @Test
    void aTimeSetOnTheDatasetContextDoesNotReachNow() {
        DatasetGraph ds = DatasetGraphFactory.createTxnMem();
        ds.getContext().set(ARQConstants.sysCurrentTime, PIN);
        UpdateExec.dataset(ds).update(UpdateFactory.create(REQUEST)).build().execute();
        assertClockWasRead(ds);
    }

    @Test
    void aTimeSetOnTheExecutionDoesNotReachNowInsideAWriteTransaction() {
        DatasetGraph ds = DatasetGraphFactory.createTxnMem();
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
