// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.morktransforms;

import com.bazaarvoice.jolt.Chainr;
import com.bazaarvoice.jolt.JsonUtils;
import java.io.StringReader;
import java.io.StringWriter;
import javax.xml.XMLConstants;
import javax.xml.parsers.SAXParserFactory;
import javax.xml.transform.Source;
import javax.xml.transform.sax.SAXSource;
import javax.xml.transform.stream.StreamSource;
import net.sf.saxon.s9api.Processor;
import net.sf.saxon.s9api.Serializer;
import net.sf.saxon.s9api.XsltTransformer;
import org.xml.sax.InputSource;
import org.xml.sax.XMLReader;

/** The two transform backends (ADR-A148). Each validates what it receives and wraps engine errors in one exception. */
public final class Transforms {
    private Transforms() {}

    /** Runs an XSLT 3.0 stylesheet on a source document and returns the text output. DTDs and external entities are refused. */
    public static String xslt(String stylesheet, String xml) throws TransformException {
        Source source;
        try {
            SAXParserFactory f = SAXParserFactory.newInstance();
            f.setNamespaceAware(true);
            f.setFeature(XMLConstants.FEATURE_SECURE_PROCESSING, true);
            f.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            f.setFeature("http://xml.org/sax/features/external-general-entities", false);
            f.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
            XMLReader reader = f.newSAXParser().getXMLReader();
            source = new SAXSource(reader, new InputSource(new StringReader(xml)));
        } catch (Exception e) {
            throw new TransformException("xslt: could not set up a secure XML parser", e);
        }
        try {
            Processor processor = new Processor(false);
            XsltTransformer t = processor.newXsltCompiler()
                    .compile(new StreamSource(new StringReader(stylesheet)))
                    .load();
            StringWriter out = new StringWriter();
            Serializer ser = processor.newSerializer(out);
            ser.setOutputProperty(Serializer.Property.METHOD, "text");
            t.setSource(source);
            t.setDestination(ser);
            t.transform();
            return out.toString();
        } catch (Exception e) {
            throw new TransformException("xslt: stylesheet compile, source parse or transform failed (" + e.getClass().getSimpleName() + ")", e);
        }
    }

    /** Runs a JOLT chain on a JSON document and returns the JSON result. */
    public static String jolt(String chain, String json) throws TransformException {
        Chainr chainr;
        try {
            chainr = Chainr.fromSpec(JsonUtils.jsonToList(chain));
        } catch (Exception e) {
            throw new TransformException("jolt: the chain is not a valid JOLT chain", e);
        }
        try {
            return JsonUtils.toJsonString(chainr.transform(JsonUtils.jsonToObject(json)));
        } catch (Exception e) {
            throw new TransformException("jolt: the input is not valid JSON or the transform failed", e);
        }
    }
}
