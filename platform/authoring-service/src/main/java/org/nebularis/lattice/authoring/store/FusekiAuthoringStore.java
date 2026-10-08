// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.store;

import java.io.IOException;
import java.net.Authenticator;
import java.net.PasswordAuthentication;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Optional;
import org.apache.jena.atlas.web.HttpException;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdfconnection.RDFConnection;
import org.apache.jena.rdfconnection.RDFConnectionRemote;
import org.apache.jena.web.HttpSC;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** An {@link AuthoringStore} over a real Fuseki, via the Graph Store Protocol (decision WA-D5). */
public final class FusekiAuthoringStore implements AuthoringStore {
    private static final Logger LOG = LoggerFactory.getLogger(FusekiAuthoringStore.class);
    private static final int READY_ATTEMPTS = 30;
    private static final Duration READY_INTERVAL = Duration.ofSeconds(2);
    private static final Duration ADMIN_TIMEOUT = Duration.ofSeconds(10);

    private final String url;
    private final String dataset;
    private final HttpClient httpClient;
    private final RDFConnection connection;

    public FusekiAuthoringStore(String url, String dataset, String adminUser, String adminPassword) {
        this.url = url.endsWith("/") ? url.substring(0, url.length() - 1) : url;
        this.dataset = dataset;
        this.httpClient = HttpClient.newBuilder()
            .connectTimeout(ADMIN_TIMEOUT)
            .authenticator(new Authenticator() {
                @Override
                protected PasswordAuthentication getPasswordAuthentication() {
                    return new PasswordAuthentication(adminUser, adminPassword.toCharArray());
                }
            })
            .build();
        this.connection = RDFConnectionRemote.service(this.url + "/" + dataset)
            .gspEndpoint("data")
            .httpClient(httpClient)
            .build();
    }

    @Override
    public void ensureReady() {
        IOException lastError = null;
        for (int attempt = 1; attempt <= READY_ATTEMPTS; attempt++) {
            try {
                if (datasetReady()) {
                    LOG.info("Fuseki dataset '{}' at {} is ready", dataset, url);
                    return;
                }
            } catch (IOException e) {
                lastError = e;
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new IllegalStateException("interrupted while waiting for Fuseki", e);
            }
            sleep();
        }
        throw new IllegalStateException(
            "Fuseki at " + url + " was not ready after " + READY_ATTEMPTS + " attempts", lastError);
    }

    /** True once the dataset exists, creating it if Fuseki answers that it does not (yet). */
    private boolean datasetReady() throws IOException, InterruptedException {
        int status = adminGet("/$/datasets/" + dataset);
        if (status == HttpSC.OK_200) {
            return true;
        }
        if (status == HttpSC.NOT_FOUND_404) {
            int created = adminPostForm("/$/datasets", "dbName=" + dataset + "&dbType=tdb2");
            return created / 100 == 2;
        }
        return false;
    }

    @Override
    public boolean ping() {
        try {
            return adminGet("/$/ping") == HttpSC.OK_200;
        } catch (IOException | InterruptedException e) {
            return false;
        }
    }

    @Override
    public void putGraph(String graphIri, Model model) {
        connection.put(graphIri, model);
    }

    @Override
    public Optional<Model> getGraph(String graphIri) {
        try {
            return Optional.of(connection.fetch(graphIri));
        } catch (HttpException e) {
            if (e.getStatusCode() == HttpSC.NOT_FOUND_404) {
                return Optional.empty();
            }
            throw e;
        }
    }

    private int adminGet(String path) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder(URI.create(url + path))
            .timeout(ADMIN_TIMEOUT)
            .GET()
            .build();
        return httpClient.send(request, HttpResponse.BodyHandlers.discarding()).statusCode();
    }

    private int adminPostForm(String path, String form) throws IOException, InterruptedException {
        HttpRequest request = HttpRequest.newBuilder(URI.create(url + path))
            .timeout(ADMIN_TIMEOUT)
            .header("Content-Type", "application/x-www-form-urlencoded")
            .POST(HttpRequest.BodyPublishers.ofString(form))
            .build();
        return httpClient.send(request, HttpResponse.BodyHandlers.discarding()).statusCode();
    }

    private static void sleep() {
        try {
            Thread.sleep(READY_INTERVAL.toMillis());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("interrupted while waiting for Fuseki", e);
        }
    }
}
