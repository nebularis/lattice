// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.api;

import java.io.IOException;
import java.net.URI;
import java.net.URISyntaxException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Map;
import java.util.TreeMap;
import java.util.regex.Pattern;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.Property;
import org.apache.jena.rdf.model.ResourceFactory;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.vocabulary.OWL;
import org.apache.jena.vocabulary.RDF;
import org.nebularis.lattice.studio.store.Cst;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The LATTICE ontology documents the staged folder holds, served by the ontology IRI or version IRI an index names (SVA-B2b,
 * ADR-A88). The index, {@code ontologies/index.ttl}, is read once at start. A document is found through it only, so no
 * part of a request becomes a path, and nothing is fetched from anywhere. The staged file's name never leaves the service.
 */
final class StagedOntologies {
    private static final Logger LOG = LoggerFactory.getLogger(StagedOntologies.class);
    private static final Property STAGED_AS = ResourceFactory.createProperty(Cst.NS + "stagedAs");
    /** What staging names a copy: the SHA-256 of its content, then {@code .ttl}. Anything else in the index is not trusted. */
    private static final Pattern STAGED_NAME = Pattern.compile("[0-9a-f]{64}\\.ttl");
    private static final Pattern ABSOLUTE_IRI = Pattern.compile("[A-Za-z][A-Za-z0-9+.-]*:[^\\s<>\"{}|\\\\^`]+");

    private final Path folder;
    private final Map<String, String> fileByIri = new TreeMap<>();
    private final byte[] listing;
    private final String etag;

    /** Reads the index under {@code assets}. A folder with no index holds none, so {@link #present()} is false. */
    StagedOntologies(Path assets) {
        this.folder = assets.resolve("ontologies").normalize();
        byte[] indexBytes = null;
        byte[] shown = null;
        try {
            Path index = folder.resolve("index.ttl");
            if (Files.isRegularFile(index)) {
                indexBytes = Files.readAllBytes(index);
                Model model = Turtle.parse(indexBytes);
                java.util.List<org.apache.jena.rdf.model.Resource> unusable = new java.util.ArrayList<>();
                for (Statement s : model.listStatements(null, STAGED_AS, (org.apache.jena.rdf.model.RDFNode) null).toList()) {
                    String name = s.getObject().isLiteral() ? s.getObject().asLiteral().getLexicalForm() : "";
                    if (!s.getSubject().isURIResource() || !model.contains(s.getSubject(), RDF.type, OWL.Ontology)
                        || !STAGED_NAME.matcher(name).matches() || !Files.isRegularFile(folder.resolve(name))) {
                        LOG.warn("the staged ontology index names no usable copy for {}", s.getSubject());
                        unusable.add(s.getSubject());
                        continue;
                    }
                    fileByIri.putIfAbsent(s.getSubject().getURI(), name);
                    for (Statement v : model.listStatements(s.getSubject(), OWL.versionIRI, (org.apache.jena.rdf.model.RDFNode) null).toList()) {
                        if (v.getObject().isURIResource()) {
                            fileByIri.putIfAbsent(v.getObject().asResource().getURI(), name);
                        }
                    }
                }
                // An entry with no usable copy would be listed and never served, so it is not listed.
                unusable.forEach(subject -> model.removeAll(subject, null, null));
                model.removeAll(null, STAGED_AS, null);
                shown = Turtle.write(model);
            }
        } catch (IOException | RuntimeException e) {
            LOG.warn("cannot read the staged ontology index, so no ontology is served", e);
            fileByIri.clear();
            indexBytes = null;
        }
        this.listing = shown;
        this.etag = indexBytes == null ? null : "\"" + sha256(indexBytes).substring(0, 32) + "\"";
    }

    boolean present() {
        return listing != null;
    }

    /** The index as Turtle, without the staged file of each document. */
    byte[] listing() {
        return listing;
    }

    String etag() {
        return etag;
    }

    /** Whether {@code value} is an absolute IRI, the only thing a request may ask a document by. */
    static boolean isAbsoluteIri(String value) {
        if (value == null || !ABSOLUTE_IRI.matcher(value).matches()) {
            return false;
        }
        try {
            return new URI(value).isAbsolute();
        } catch (URISyntaxException e) {
            return false;
        }
    }

    /** The document whose ontology IRI or version IRI is {@code iri}, or null when the index holds none. */
    byte[] document(String iri) {
        String name = fileByIri.get(iri);
        if (name == null) {
            return null;
        }
        try {
            return Files.readAllBytes(folder.resolve(name));
        } catch (IOException e) {
            LOG.warn("cannot read the staged copy of {}", iri, e);
            return null;
        }
    }

    private static String sha256(byte[] bytes) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }
}
