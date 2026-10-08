// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.app;

import static org.junit.jupiter.api.Assertions.assertEquals;

import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import org.junit.jupiter.api.Test;

class HealthProbeTest {

    /** S5-06: 200 gives 0, 503 gives 1, a closed port gives 1. */
    @Test
    void exitsZeroOn200AndOneOtherwise() throws IOException {
        HttpServer ok = stub(200);
        HttpServer degraded = stub(503);
        try {
            assertEquals(0, HealthProbe.check("http://localhost:" + ok.getAddress().getPort() + "/health"));
            assertEquals(1, HealthProbe.check("http://localhost:" + degraded.getAddress().getPort() + "/health"));
            assertEquals(1, HealthProbe.check("http://localhost:" + closedPort() + "/health"));
        } finally {
            ok.stop(0);
            degraded.stop(0);
        }
    }

    private static HttpServer stub(int status) throws IOException {
        HttpServer server = HttpServer.create(new InetSocketAddress("localhost", 0), 0);
        server.createContext("/health", exchange -> {
            exchange.sendResponseHeaders(status, -1);
            exchange.close();
        });
        server.start();
        return server;
    }

    /** A port nothing is listening on: bound then released immediately. */
    private static int closedPort() throws IOException {
        try (ServerSocket socket = new ServerSocket(0)) {
            return socket.getLocalPort();
        }
    }
}
