// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.app;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

/** A container health check: exit 0 when {@code url} answers 200, exit 1 otherwise. */
public final class HealthProbe {
    private static final Duration TIMEOUT = Duration.ofSeconds(3);

    private HealthProbe() {
    }

    public static void main(String[] args) {
        if (args.length != 1) {
            throw new IllegalArgumentException("usage: HealthProbe <url>");
        }
        System.exit(check(args[0]));
    }

    /** Package-visible so a test can read the exit code without exiting the test JVM. */
    static int check(String url) {
        try {
            HttpClient client = HttpClient.newHttpClient();
            HttpRequest request = HttpRequest.newBuilder(URI.create(url)).timeout(TIMEOUT).GET().build();
            HttpResponse<Void> response = client.send(request, HttpResponse.BodyHandlers.discarding());
            return response.statusCode() == 200 ? 0 : 1;
        } catch (IOException | InterruptedException e) {
            return 1;
        }
    }
}
