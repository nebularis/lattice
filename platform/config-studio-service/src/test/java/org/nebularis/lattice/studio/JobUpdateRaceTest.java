// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Proxy;
import java.nio.file.Path;
import java.time.Clock;
import java.util.List;
import org.apache.jena.query.Dataset;
import org.apache.jena.query.DatasetFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdfconnection.RDFConnection;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.nebularis.lattice.studio.store.StudioStore;
import org.nebularis.lattice.studio.writes.Command;
import org.nebularis.lattice.studio.writes.Reply;
import org.nebularis.lattice.studio.writes.Writer;

/**
 * Two writers on one job (TD-181). A second writer reads the job, the first applies the job's success, and the second's request
 * then lands. The second store runs the first writer's update just before its own first request, so the order is fixed and no
 * thread is involved.
 */
class JobUpdateRaceTest {
    private static final String WS = Fixture.id(1);

    @TempDir Path dir;
    Fixture f;
    String jobIri;

    @BeforeEach
    void setUp() throws Exception {
        f = new Fixture(Fixture.assetsDir(dir.resolve("assets")));
        assertEquals(201, f.createWorkspace("One").status());
        ApiResponse r = f.post("/api/workspaces/" + WS + "/jobs", "kind=validate&target=vocabulary", Fixture.PREFIXES + "ex:a ex:p ex:b .");
        assertEquals(202, r.status());
        jobIri = Graphs.job(r.headers().get("Location").substring("/api/jobs/".length()));
    }

    /** The job's update to {@code status}, as a worker sends it, from the job as the store holds it now. */
    private Command update(Resource status) {
        Model m = ModelFactory.createDefaultModel().add(f.store.graph(jobIri));
        m.removeAll(m.createResource(jobIri), Cst.status, null);
        m.createResource(jobIri).addProperty(Cst.status, status);
        Dataset d = DatasetFactory.create();
        d.addNamedModel(jobIri, m);
        return Command.jobUpdate(WS, jobIri.substring(Graphs.job("").length()), d);
    }

    /** A writer on the fixture's dataset whose first update request is preceded by {@code first}. */
    private Writer lateWriter(Runnable first) {
        boolean[] ran = {false};
        RDFConnection late = (RDFConnection) Proxy.newProxyInstance(RDFConnection.class.getClassLoader(), new Class<?>[] {RDFConnection.class},
            (self, method, args) -> {
                if (method.getName().equals("update") && !ran[0]) {
                    ran[0] = true;
                    first.run();
                }
                try {
                    return method.invoke(f.raw, args);
                } catch (InvocationTargetException e) {
                    throw e.getCause();
                }
            });
        return new Writer(Fixture.textual(late), Fixture.OPS, Fixture.MAINTENANCE, Clock.systemUTC());
    }

    private boolean has(Resource status) {
        Model job = f.store.graph(jobIri);
        return job.contains(job.createResource(jobIri), Cst.status, status);
    }

    @Test
    void aFailureFromAWriterThatReadTheJobBeforeItSucceededIsDropped() {
        Command failed = update(Cst.Failed);
        Command succeeded = update(Cst.Succeeded);
        Writer late = lateWriter(() -> assertEquals(200, f.writes.send(succeeded).status()));
        Reply reply = late.apply(List.of(failed)).get(0);
        assertEquals(200, reply.status(), reply.message());
        assertTrue(has(Cst.Succeeded));
        assertFalse(has(Cst.Failed));
    }

    @Test
    void aFailureFromAWriterThatReadTheJobBeforeItWasDeletedIsNotFound() {
        Command failed = update(Cst.Failed);
        Command delete = Command.deleteJob(WS, jobIri.substring(Graphs.job("").length()));
        Writer late = lateWriter(() -> assertEquals(200, f.writes.send(delete).status()));
        assertEquals(404, late.apply(List.of(failed)).get(0).status());
        assertTrue(f.store.graph(jobIri).isEmpty());
    }

    @Test
    void aFailureWithNoOtherWriterStillApplies() {
        Writer late = lateWriter(() -> { });
        assertEquals(200, late.apply(List.of(update(Cst.Failed))).get(0).status());
        assertTrue(has(Cst.Failed));
    }
}
