// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.api;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.util.Map;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFFormat;
import org.apache.jena.riot.RDFParser;
import org.apache.jena.riot.RDFWriter;
import org.apache.jena.riot.RiotException;

/** Turtle in and out. */
final class Turtle {
    private static final Map<String, String> PREFIXES = Map.of(
        "cst", "https://www.nebularis.org/neuro-semantic/lattice/poc/config-studio#",
        "rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs", "http://www.w3.org/2000/01/rdf-schema#",
        "xsd", "http://www.w3.org/2001/XMLSchema#",
        "sh", "http://www.w3.org/ns/shacl#",
        "dal", "https://www.nebularis.org/neuro-semantic/lattice/persistence#",
        "srf", "https://www.nebularis.org/neuro-semantic/lattice/surface#",
        "skos", "http://www.w3.org/2004/02/skos/core#",
        "owl", "http://www.w3.org/2002/07/owl#");

    private Turtle() {
    }

    /** Parses strictly. Relative IRIs resolve against a fixed base so the result never depends on the host. */
    static Model parse(byte[] body) throws RiotException {
        Model model = ModelFactory.createDefaultModel();
        RDFParser.create().source(new ByteArrayInputStream(body)).lang(Lang.TURTLE)
            .base("urn:lattice:studio:input:").strict(true).parse(model);
        return model;
    }

    static byte[] write(Model model) {
        Model copy = ModelFactory.createDefaultModel().add(model);
        copy.clearNsPrefixMap().setNsPrefixes(PREFIXES);
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        RDFWriter.source(copy).format(RDFFormat.TURTLE_PRETTY).output(out);
        return out.toByteArray();
    }
}
