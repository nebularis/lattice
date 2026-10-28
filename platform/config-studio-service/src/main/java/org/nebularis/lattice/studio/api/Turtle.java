// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.api;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.util.Map;
import javax.xml.stream.XMLInputFactory;
import javax.xml.stream.XMLStreamConstants;
import javax.xml.stream.XMLStreamException;
import javax.xml.stream.XMLStreamReader;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFFormat;
import org.apache.jena.riot.RDFParser;
import org.apache.jena.riot.RDFWriter;
import org.apache.jena.riot.RiotException;

/** RDF in and out: Turtle, and RDF/XML where a client asks for it (CS10). */
final class Turtle {
    static final String RDF_XML = "application/rdf+xml";

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
        return parse(body, Lang.TURTLE);
    }

    static Model parse(byte[] body, Lang lang) throws RiotException {
        if (lang.equals(Lang.RDFXML)) {
            refuseDtd(body);
        }
        Model model = ModelFactory.createDefaultModel();
        RDFParser.create().source(new ByteArrayInputStream(body)).lang(lang)
            .base("urn:lattice:studio:input:").strict(true).parse(model);
        return model;
    }

    /**
     * Refuses an XML document that declares a DTD. Jena's RDF/XML reader does not fetch an external entity, but it reads
     * one as empty text and so stores a value nobody wrote. RDF/XML never needs a DTD, so a body with one is refused.
     */
    private static void refuseDtd(byte[] body) {
        XMLInputFactory factory = XMLInputFactory.newFactory();
        factory.setProperty(XMLInputFactory.SUPPORT_DTD, false);
        factory.setProperty(XMLInputFactory.IS_SUPPORTING_EXTERNAL_ENTITIES, false);
        factory.setProperty(XMLInputFactory.IS_REPLACING_ENTITY_REFERENCES, false);
        try {
            XMLStreamReader reader = factory.createXMLStreamReader(new ByteArrayInputStream(body));
            try {
                while (reader.hasNext()) {
                    if (reader.next() == XMLStreamConstants.DTD) {
                        throw new RiotException("a DTD is not allowed in RDF/XML");
                    }
                }
            } finally {
                reader.close();
            }
        } catch (XMLStreamException e) {
            throw new RiotException(e.getMessage());
        }
    }

    static byte[] write(Model model) {
        return write(model, RDFFormat.TURTLE_PRETTY);
    }

    /** Plain RDF/XML, one description per subject and no abbreviation, so an XSLT reads one regular shape. */
    static byte[] writeXml(Model model) {
        return write(model, RDFFormat.RDFXML_PLAIN);
    }

    private static byte[] write(Model model, RDFFormat format) {
        Model copy = ModelFactory.createDefaultModel().add(model);
        copy.clearNsPrefixMap().setNsPrefixes(PREFIXES);
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        RDFWriter.source(copy).format(format).output(out);
        return out.toByteArray();
    }

    /**
     * Whether {@code accept} ranks RDF/XML above Turtle. A media range without a {@code q} counts 1, and {@code *}/{@code *}
     * or {@code application}/{@code *} lend their weight to a type they cover, so an absent header or a browser's default
     * keeps Turtle.
     */
    static boolean prefersXml(String accept) {
        if (accept == null) {
            return false;
        }
        double xml = 0;
        double turtle = 0;
        for (String range : accept.split(",")) {
            String[] parts = range.trim().split(";");
            String media = parts[0].trim().toLowerCase(java.util.Locale.ROOT);
            double q = 1;
            for (int i = 1; i < parts.length; i++) {
                String param = parts[i].trim();
                if (param.startsWith("q=")) {
                    try {
                        q = Double.parseDouble(param.substring(2));
                    } catch (NumberFormatException e) {
                        q = 0;
                    }
                }
            }
            if (media.equals(RDF_XML) || media.equals("application/*")) {
                xml = Math.max(xml, q);
            }
            if (media.equals("text/turtle") || media.equals("text/*")) {
                turtle = Math.max(turtle, q);
            }
            if (media.equals("*/*")) {
                xml = Math.max(xml, q / 2);
                turtle = Math.max(turtle, q);
            }
        }
        return xml > turtle;
    }
}
