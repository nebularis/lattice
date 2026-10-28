// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.authoring;

import java.io.IOException;
import java.io.InputStream;
import java.io.StringReader;
import java.io.StringWriter;
import java.io.UncheckedIOException;
import java.util.Map;
import javax.xml.parsers.ParserConfigurationException;
import javax.xml.parsers.SAXParserFactory;
import javax.xml.transform.sax.SAXSource;
import javax.xml.transform.stream.StreamSource;
import net.sf.saxon.s9api.Processor;
import net.sf.saxon.s9api.QName;
import net.sf.saxon.s9api.SaxonApiException;
import net.sf.saxon.s9api.XdmAtomicValue;
import net.sf.saxon.s9api.XsltExecutable;
import net.sf.saxon.s9api.Xslt30Transformer;
import org.xml.sax.InputSource;
import org.xml.sax.SAXException;
import org.xml.sax.XMLReader;

/**
 * Runs the document-to-wording kit in-process (ADR-A119 decision 3): a document in LATTICE's markup to its Wording
 * graph as canonical sorted N-Triples. The stylesheet is compiled once and is safe to share across threads.
 */
public final class DocumentToWording {
    static final String KIT = "contracts/xml/document-to-wording/1.0.0/document-to-wording.xsl";

    private final Processor processor = new Processor(false);
    private final XsltExecutable stylesheet;

    public DocumentToWording() {
        try (InputStream in = DocumentToWording.class.getClassLoader().getResourceAsStream(KIT)) {
            if (in == null) {
                throw new IllegalStateException("the document-to-wording kit is not on the classpath: " + KIT);
            }
            stylesheet = processor.newXsltCompiler().compile(new StreamSource(in, KIT));
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        } catch (SaxonApiException e) {
            throw new IllegalStateException("the document-to-wording kit does not compile", e);
        }
    }

    /** The document's Wording graph, minted under {@code base}, for its revision {@code revision}. */
    public String nTriples(String document, String base, int revision) throws SaxonApiException {
        Xslt30Transformer transformer = stylesheet.load30();
        transformer.setStylesheetParameters(Map.of(
            new QName("base"), new XdmAtomicValue(base),
            new QName("revision"), new XdmAtomicValue((long) revision)));
        StringWriter out = new StringWriter();
        transformer.transform(new SAXSource(reader(), new InputSource(new StringReader(document))), processor.newSerializer(out));
        return out.toString();
    }

    /** A parser that refuses a DTD, so a document can declare no entity (ADR-A137 decision 6). */
    private static XMLReader reader() {
        try {
            SAXParserFactory factory = SAXParserFactory.newInstance();
            factory.setNamespaceAware(true);
            factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
            factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
            return factory.newSAXParser().getXMLReader();
        } catch (ParserConfigurationException | SAXException e) {
            throw new IllegalStateException("no secure XML parser is available", e);
        }
    }
}
