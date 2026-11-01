// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.morktransforms;

import com.bazaarvoice.jolt.Chainr;
import com.bazaarvoice.jolt.JsonUtils;
import java.io.StringReader;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.Map;
import javax.xml.XMLConstants;
import javax.xml.parsers.SAXParserFactory;
import javax.xml.transform.Source;
import javax.xml.transform.sax.SAXSource;
import javax.xml.transform.stream.StreamSource;
import net.sf.saxon.s9api.Processor;
import net.sf.saxon.s9api.Serializer;
import net.sf.saxon.s9api.XsltExecutable;
import net.sf.saxon.s9api.XsltTransformer;
import org.xml.sax.InputSource;
import org.xml.sax.XMLReader;

/** The two transform backends (ADR-A148). Each validates what it receives and wraps engine errors in one exception. */
public final class Transforms {
    private Transforms() {}

    /** Compiled stylesheets and chains, the costly part of a run, keyed by the SHA-256 of their text, which is all that changes them. */
    private static final int CACHED = 64;
    private static final Processor PROCESSOR = new Processor(false);
    private static final Map<String, XsltExecutable> STYLESHEETS = lru();
    private static final Map<String, Chainr> CHAINS = lru();

    private static <V> Map<String, V> lru() {
        return java.util.Collections.synchronizedMap(new LinkedHashMap<>(16, 0.75f, true) {
            @Override
            protected boolean removeEldestEntry(Map.Entry<String, V> eldest) {
                return size() > CACHED;
            }
        });
    }

    static String digest(String text) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(text.getBytes(StandardCharsets.UTF_8)));
        } catch (java.security.NoSuchAlgorithmException e) {
            throw new IllegalStateException(e);
        }
    }

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
            String key = digest(stylesheet);
            XsltExecutable compiled = STYLESHEETS.get(key);
            if (compiled == null) {
                compiled = PROCESSOR.newXsltCompiler().compile(new StreamSource(new StringReader(stylesheet)));
                STYLESHEETS.put(key, compiled);
            }
            XsltTransformer t = compiled.load();
            StringWriter out = new StringWriter();
            Serializer ser = PROCESSOR.newSerializer(out);
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
        String key = digest(chain);
        Chainr chainr = CHAINS.get(key);
        if (chainr == null) try {
            chainr = Chainr.fromSpec(JsonUtils.jsonToList(chain));
            CHAINS.put(key, chainr);
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
