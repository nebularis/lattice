// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.Set;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;

/** The odrl proposer is offered only when the deployment's features name it, and validates what it receives. */
class OdrlImportTest {
    private static final String WS = Fixture.id(1);
    private static final String PATH = "/api/workspaces/" + WS + "/jobs";
    private static final String DOC = "ex:d a cst:ImportDocument ; cst:documentContent \"{}\" ; cst:documentMediaType \"application/ld+json\" .\n";

    @TempDir Path dir;

    private Fixture fixture(Set<String> features) throws IOException {
        Fixture f = new Fixture(Fixture.assetsDir(dir), null, features);
        assertEquals(201, f.createWorkspace("Odrl").status());
        return f;
    }

    private static String text(ApiResponse r) {
        return new String(r.body(), StandardCharsets.UTF_8);
    }

    @Test
    void isNotFoundWithoutTheFlag() throws IOException {
        Fixture f = fixture(Set.of());
        assertEquals(404, f.post(PATH, "kind=propose&target=odrl", Fixture.PREFIXES + DOC).status());
        assertEquals("{\"features\":[]}", text(f.get("/api/features")));
    }

    @Test
    void isAcceptedWithTheFlag() throws IOException {
        Fixture f = fixture(Set.of("odrl"));
        ApiResponse job = f.post(PATH, "kind=propose&target=odrl", Fixture.PREFIXES + DOC);
        assertEquals(202, job.status(), () -> text(job));
        String id = job.headers().get("Location").substring("/api/jobs/".length());
        assertTrue(f.store.graph(Graphs.job(id)).contains(null, Cst.target, Cst.OdrlProposer));
        assertEquals("{\"features\":[\"odrl\"]}", text(f.get("/api/features")));
    }

    @Test
    void refusesABodyWithoutExactlyOneImportDocument() throws IOException {
        Fixture f = fixture(Set.of("odrl"));
        assertEquals(422, f.post(PATH, "kind=propose&target=odrl", Fixture.PREFIXES + "ex:a ex:p ex:b .\n").status());
        assertEquals(422, f.post(PATH, "kind=propose&target=odrl", Fixture.PREFIXES + DOC + DOC.replace("ex:d", "ex:e")).status());
        assertEquals(422, f.post(PATH, "kind=propose&target=odrl",
            Fixture.PREFIXES + "ex:d a cst:ImportDocument ; cst:documentContent \"{}\" .\n").status());
    }
}
