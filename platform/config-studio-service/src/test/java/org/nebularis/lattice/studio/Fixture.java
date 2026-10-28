// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio;

import java.io.IOException;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.atomic.AtomicLong;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.nebularis.lattice.studio.api.ApiRequest;
import org.nebularis.lattice.studio.api.ApiResponse;
import org.nebularis.lattice.studio.api.StudioApi;
import org.nebularis.lattice.studio.jobs.JobBus;
import org.nebularis.lattice.studio.jobs.RecordingJobBus;
import org.nebularis.lattice.studio.store.StudioStore;

/** An in-memory store, a recording bus, a fixed clock and counting ids. */
final class Fixture {
    static final String PREFIXES = "@prefix cst: <https://www.nebularis.org/neuro-semantic/lattice/config-studio#> .\n"
        + "@prefix ex: <https://example.org/> .\n";
    static final String TURTLE = "text/turtle; charset=utf-8";

    final StudioStore store = StudioStore.inMemory();
    final RecordingJobBus bus = new RecordingJobBus();
    final Path assets;
    final StudioApi api;
    private final AtomicLong counter = new AtomicLong();

    Fixture(Path assets) {
        this(assets, null);
    }

    Fixture(Path assets, JobBus busOverride) {
        this.assets = assets;
        Clock clock = Clock.fixed(Instant.parse("2026-10-27T10:00:00Z"), ZoneOffset.UTC);
        this.api = new StudioApi(store, busOverride == null ? bus : busOverride, clock,
            () -> new UUID(0, counter.incrementAndGet()), assets);
    }

    static String id(long n) {
        return new UUID(0, n).toString();
    }

    ApiResponse send(String method, String path, Map<String, String> headers, String body) {
        return send(method, path, null, headers, body == null ? new byte[0] : body.getBytes(StandardCharsets.UTF_8));
    }

    ApiResponse send(String method, String path, String query, Map<String, String> headers, byte[] body) {
        return api.handle(new ApiRequest(method, path, query, headers, body));
    }

    ApiResponse get(String path) {
        return send("GET", path, Map.of(), null);
    }

    ApiResponse post(String path, String query, String body) {
        return send("POST", path, query, Map.of("content-type", TURTLE), body.getBytes(StandardCharsets.UTF_8));
    }

    /** Creates workspace 1 from a one-triple baseline. */
    ApiResponse createWorkspace(String slug) {
        Map<String, String> headers = new HashMap<>(Map.of("content-type", TURTLE));
        if (slug != null) {
            headers.put("slug", slug);
        }
        return send("POST", "/api/workspaces", null, headers, (PREFIXES + "ex:a ex:p ex:b .").getBytes(StandardCharsets.UTF_8));
    }

    ApiResponse put(String path, String ifMatch, String body) {
        Map<String, String> headers = new HashMap<>(Map.of("content-type", TURTLE));
        if (ifMatch != null) {
            headers.put("if-match", ifMatch);
        }
        return send("PUT", path, null, headers, body.getBytes(StandardCharsets.UTF_8));
    }

    static Model model(ApiResponse r) {
        return model(new String(r.body(), StandardCharsets.UTF_8));
    }

    static Model model(String turtle) {
        Model m = ModelFactory.createDefaultModel();
        RDFDataMgr.read(m, new StringReader(turtle), "urn:test:", Lang.TURTLE);
        return m;
    }

    static Path assetsDir(Path dir) throws IOException {
        Files.createDirectories(dir.resolve("samples"));
        Files.writeString(dir.resolve("vocabulary.ttl"), "@prefix ex: <https://example.org/> .\nex:v ex:p ex:o .\n");
        Files.writeString(dir.resolve("samples.ttl"), PREFIXES
            + "<urn:lattice:studio:sample:lending> a cst:Sample ; <http://www.w3.org/2000/01/rdf-schema#label> \"Lending\" .\n");
        Files.writeString(dir.resolve("samples/lending.ttl"), "@prefix ex: <https://example.org/> .\nex:loan ex:p ex:o .\n");
        return dir;
    }
}
