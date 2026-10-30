// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Resource;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.jobs.JobBus;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;

/** {@code POST /api/workspaces/{ws}/transforms}, with a bus that stands in for the transforms worker (ADR-A148). */
class TransformsRouteTest {
    private static final String WS = "/api/workspaces/" + Fixture.id(1);

    @TempDir Path dir;
    Fixture f;
    final AtomicReference<String[]> asked = new AtomicReference<>();
    /** What the stand-in worker answers: the run described, or nothing, as when no worker runs. */
    boolean answers = true;

    @BeforeEach
    void setUp() throws IOException {
        f = new Fixture(Fixture.assetsDir(dir), new JobBus() {
            @Override
            public void publish(String jobIri) {
            }

            @Override
            public byte[] transform(String id, String jobIri, String mediaType, byte[] sample, Duration timeout) {
                asked.set(new String[] {jobIri, mediaType, new String(sample, StandardCharsets.UTF_8)});
                return answers ? (Fixture.PREFIXES + "<urn:lattice:studio:transform:" + id + "> a cst:Transform ; cst:status cst:Succeeded .")
                    .getBytes(StandardCharsets.UTF_8) : null;
            }
        });
        f.createWorkspace("One");
    }

    private String compileJob(boolean finished) {
        f.post(WS + "/jobs", "kind=compile&target=mapping", Fixture.PREFIXES + "ex:a ex:p ex:b .");
        String job = Graphs.job(Fixture.id(2));
        if (finished) {
            Model done = f.store.graph(job);
            Resource j = done.getResource(job);
            done.removeAll(j, Cst.status, null);
            j.addProperty(Cst.status, Cst.Succeeded);
            f.store.write(List.of(), Map.of(job, done));
        }
        return job;
    }

    private ApiResponse transform(String job, String media, String sample) {
        return f.send("POST", WS + "/transforms", "job=" + job.substring(Graphs.JOB_PREFIX.length()),
            Map.of("content-type", media), sample.getBytes(StandardCharsets.UTF_8));
    }

    @Test
    void aSampleGoesToTheWorkerWithItsJobAndTheReplyIsAnswered() {
        String job = compileJob(true);
        ApiResponse r = transform(job, "application/xml; charset=utf-8", "<a/>");
        assertEquals(200, r.status());
        assertEquals(List.of(job, "application/xml", "<a/>"), List.of(asked.get()));
        assertTrue(Fixture.model(r).contains(null, Cst.status, Cst.Succeeded));
    }

    @Test
    void anUnfinishedJobAnotherMediaTypeAndNoWorkerAreRefused() {
        String job = compileJob(false);
        assertEquals(409, transform(job, "application/xml", "<a/>").status());
        Model done = f.store.graph(job);
        done.removeAll(done.getResource(job), Cst.status, null);
        done.getResource(job).addProperty(Cst.status, Cst.Succeeded);
        f.store.write(List.of(), Map.of(job, done));
        assertEquals(415, transform(job, "text/turtle", "").status());
        assertEquals(404, f.send("POST", WS + "/transforms", "job=" + Fixture.id(99), Map.of("content-type", "application/json"), new byte[0]).status());
        answers = false;
        assertEquals(504, transform(job, "application/json", "{}").status());
    }
}
