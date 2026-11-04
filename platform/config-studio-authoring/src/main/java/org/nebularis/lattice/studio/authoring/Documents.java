// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.authoring;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.regex.Pattern;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import javax.xml.transform.dom.DOMSource;
import javax.xml.validation.Schema;
import javax.xml.validation.SchemaFactory;
import net.sf.saxon.s9api.SaxonApiException;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFParser;
import org.apache.jena.vocabulary.RDF;
import org.apache.jena.vocabulary.RDFS;
import org.apache.jena.shacl.ShaclValidator;
import org.apache.jena.shacl.Shapes;
import org.apache.jena.shacl.validation.ReportEntry;
import org.apache.jena.shacl.vocabulary.SHACLM;
import java.util.List;
import org.nebularis.lattice.studio.store.Cst;
import org.nebularis.lattice.studio.store.Graphs;
import org.w3c.dom.Element;
import org.xml.sax.SAXException;

/**
 * A workspace's documents as the service receives and serves them: markup read with a parser that refuses a DTD,
 * validated against the generated XSD, and mapped to its Wording graph by the document-to-wording kit, with the markup
 * kept beside it (contracts/config-studio/README.md). The service checks all of this itself, whatever the add-in checked
 * (PRI-75). Safe to share across threads.
 */
public final class Documents {
    public static final String NAMESPACE = "https://www.nebularis.org/neuro-semantic/lattice/document/1";
    private static final Pattern KEY = Pattern.compile("[a-z][a-z0-9-]{0,39}");

    private final Schema schema;
    private final DocumentToWording kit = new DocumentToWording();
    private final Model templates;
    private final Shapes shapes;

    public Documents() {
        try {
            SchemaFactory factory = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI);
            factory.setProperty(XMLConstants.ACCESS_EXTERNAL_DTD, "");
            factory.setProperty(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
            schema = factory.newSchema(resource("contracts/document/document.xsd"));
        } catch (SAXException e) {
            throw new IllegalStateException("the document schema does not load", e);
        }
        try (InputStream in = resource("shapes/wording-poc-shapes.ttl").openStream()) {
            shapes = Shapes.parse(RDFParser.create().source(in).lang(Lang.TURTLE).toGraph());
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        // Read as a stream, since Jena cannot open a jar: URL, which the resource is once the module is packaged.
        try (InputStream in = resource("contracts/config-studio/document-templates.ttl").openStream()) {
            templates = RDFParser.create().source(in).lang(Lang.TURTLE).toModel();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    /** What a received document is: its graph, title and template, or why it is refused, with the HTTP status. */
    public record Read(Model graph, String title, String template, int status, String problem) {
        static Read refused(int status, String problem) {
            return new Read(null, null, null, status, problem);
        }
    }

    /** Reads {@code body} as document {@code doc} at revision {@code revision}, the one a successful save makes. */
    public Read read(byte[] body, String doc, long revision) {
        org.w3c.dom.Document dom;
        try {
            dom = builder().parse(new ByteArrayInputStream(body));
        } catch (SAXException | IOException e) {
            return Read.refused(400, "the body is not well-formed XML without a DTD: " + e.getMessage());
        }
        try {
            schema.newValidator().validate(new DOMSource(dom));
        } catch (SAXException e) {
            return Read.refused(422, "the document is not valid markup: " + e.getMessage());
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        Element root = dom.getDocumentElement();
        if (!root.getAttribute("id").equals(doc)) {
            return Read.refused(422, "the document's id is not " + doc);
        }
        String title = child(root, "meta", "title");
        String template = child(root, "meta", "template");
        if (!templateKnown(template)) {
            return Read.refused(422, "no document template has the key " + template);
        }
        String markup = new String(body, StandardCharsets.UTF_8);
        Model graph;
        try {
            graph = RDFParser.fromString(kit.nTriples(markup, Graphs.DOCUMENT_BASE, Math.toIntExact(revision)), Lang.NTRIPLES).toModel();
        } catch (SaxonApiException e) {
            return Read.refused(422, "the document could not be mapped to Wording: " + e.getMessage());
        }
        graph.createResource(Graphs.documentNode(doc)).addProperty(Cst.markup, markup);
        return new Read(graph, title, template, 200, null);
    }

    /**
     * The report on a saved document: its Wording graph against the shapes of the add-in's first service, its markup
     * against its template, and what the detector finds unmarked, as one {@code sh:ValidationReport}. Results are in a
     * fixed order and named under the document's node, so the same document gives the same report.
     */
    public Model report(String doc, String markup, Model wording) {
        Markup structure;
        try {
            structure = Markup.of(builder().parse(new ByteArrayInputStream(markup.getBytes(StandardCharsets.UTF_8))).getDocumentElement());
        } catch (SAXException | IOException e) {
            throw new IllegalStateException("a stored document's markup does not parse", e);
        }
        String node = Graphs.documentNode(doc);
        Report r = new Report(node);
        for (ReportEntry entry : ShaclValidator.get().validate(shapes, wording.getGraph()).getEntries()) {
            String source = entry.source() == null ? "" : entry.source().toString();
            int at = source.lastIndexOf("shape-");
            r.result(severity(entry.severity()), entry.message(), at < 0 ? "shacl" : source.substring(at + 6), "shacl",
                entry.focusNode().isURI() ? entry.focusNode().getURI() : null);
        }
        templateFindings(r, structure, node);
        for (Detector.Detection d : Detector.detect(structure)) {
            Resource result = r.result(SHACLM.Info, "Unmarked " + d.kind() + ": " + d.text(), "detection", "detection", node + "element/" + d.elementId());
            result.addProperty(Cst.detectionKind, d.kind()).addProperty(SHACLM.value, d.text()).addProperty(Cst.action, d.action())
                .addLiteral(Cst.partIndex, (long) d.partIndex()).addLiteral(Cst.start, (long) d.start()).addLiteral(Cst.end, (long) d.end());
            if (d.valueType() != null) {
                result.addProperty(Cst.suggestedValueType, d.valueType()).addProperty(Cst.suggestedKey, d.key());
            }
            if (d.target() != null) {
                result.addProperty(Cst.suggestedTarget, r.model.createResource(node + "element/" + d.target()));
            }
        }
        return r.done();
    }

    /** Required sections left empty, sections the template does not name, elements a section does not allow, and unmarked text. */
    private void templateFindings(Report r, Markup m, String node) {
        Resource template = null;
        String key = templateKeyOf(m);
        for (Resource t : templates.listResourcesWithProperty(Cst.templateKey, key).toList()) {
            if (t.hasProperty(RDF.type, Cst.DocumentTemplate)) {
                template = t;
            }
        }
        if (template == null) {
            return;
        }
        List<Resource> sections = template.listProperties(Cst.section).mapWith(st -> st.getResource()).toList();
        sections.sort(java.util.Comparator.comparingLong(s -> s.getProperty(Cst.order).getLong()));
        java.util.Set<String> known = new java.util.HashSet<>();
        for (Resource ts : sections) {
            String sectionKey = ts.getProperty(Cst.sectionKey).getString();
            String heading = ts.getProperty(RDFS.label).getString();
            known.add(sectionKey);
            Markup.Section found = m.sections().stream().filter(s -> s.key().equals(sectionKey)).findFirst().orElse(null);
            if (ts.getProperty(Cst.required).getBoolean() && (found == null || found.items().isEmpty())) {
                r.result(SHACLM.Warning, "The required section '" + heading + "' has no content.", "required-section-empty", "template", node + "section/" + sectionKey);
            }
            if (found == null) {
                continue;
            }
            java.util.Set<String> kinds = new java.util.HashSet<>();
            ts.listProperties(Cst.elementKind).forEachRemaining(st -> kinds.add(st.getString()));
            int s = m.sections().indexOf(found) + 1;
            for (int e = 0; e < found.items().size(); e++) {
                Markup.Item item = found.items().get(e);
                String kind = item.definition() ? "definition" : "clause";
                if (!kinds.contains(kind)) {
                    r.result(SHACLM.Warning, "Element " + s + "." + (e + 1) + " is a " + kind + ", which the section '" + heading + "' does not allow.",
                        "element-kind-not-allowed", "template", node + "element/" + item.id());
                }
            }
        }
        for (Markup.Section s : m.sections()) {
            if (!known.contains(s.key())) {
                r.result(SHACLM.Warning, "The section '" + s.key() + "' is not in the " + template.getProperty(RDFS.label).getString() + " template.",
                    "unknown-section", "template", node + "section/" + s.key());
            }
        }
        for (String in : m.unmarkedIn()) {
            r.result(SHACLM.Info, in == null ? "Text outside every section is not inside a marked element." : "Text in the section '" + in + "' is not inside a marked element.",
                "unmarked-text", "template", in == null ? node + "wording" : node + "section/" + in);
        }
    }

    private String templateKeyOf(Markup m) {
        return m.templateKey();
    }

    private static Resource severity(org.apache.jena.shacl.validation.Severity s) {
        if (s.equals(org.apache.jena.shacl.validation.Severity.Violation)) {
            return SHACLM.Violation;
        }
        return s.equals(org.apache.jena.shacl.validation.Severity.Warning) ? SHACLM.Warning : SHACLM.Info;
    }

    /** A report under construction, its results numbered in the order they are added. */
    private static final class Report {
        final Model model = ModelFactory.createDefaultModel();
        final Resource node;
        final String prefix;
        int count;
        boolean conforms = true;

        Report(String documentNode) {
            prefix = documentNode + "report";
            node = model.createResource(prefix).addProperty(RDF.type, SHACLM.ValidationReport);
        }

        Resource result(Resource severity, String message, String code, String check, String focus) {
            Resource r = model.createResource(prefix + "/result-" + (++count)).addProperty(RDF.type, SHACLM.ValidationResult)
                .addProperty(SHACLM.resultSeverity, severity).addProperty(SHACLM.resultMessage, message)
                .addProperty(Cst.code, code).addProperty(Cst.check, check);
            if (focus != null) {
                r.addProperty(SHACLM.focusNode, model.createResource(focus));
            }
            node.addProperty(SHACLM.result, r);
            conforms &= !severity.equals(SHACLM.Violation);
            return r;
        }

        Model done() {
            node.addLiteral(SHACLM.conforms, conforms);
            return model;
        }
    }

    /** Every document template, without the samples. */
    public Model templates() {
        Model out = ModelFactory.createDefaultModel();
        templates.listStatements().forEachRemaining(s -> {
            if (!s.getSubject().hasProperty(RDF.type, Cst.DocumentSample)) {
                out.add(s);
            }
        });
        return out.setNsPrefixes(templates.getNsPrefixMap());
    }

    /** Every sample document's entry. */
    public Model samples() {
        Model out = ModelFactory.createDefaultModel();
        templates.listResourcesWithProperty(RDF.type, Cst.DocumentSample).forEachRemaining(r -> out.add(r.listProperties()));
        return out.setNsPrefixes(templates.getNsPrefixMap());
    }

    /** A sample's markup, or null when there is none by that key. */
    public byte[] sample(String key) {
        if (!KEY.matcher(key).matches() || !templates.listResourcesWithProperty(Cst.sampleKey, key).hasNext()) {
            return null;
        }
        try (InputStream in = Documents.class.getClassLoader().getResourceAsStream("contracts/document/samples/" + key + ".xml")) {
            return in == null ? null : in.readAllBytes();
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
    }

    private boolean templateKnown(String key) {
        for (Resource r : templates.listResourcesWithProperty(Cst.templateKey, key).toList()) {
            if (r.hasProperty(RDF.type, Cst.DocumentTemplate)) {
                return true;
            }
        }
        return false;
    }

    private static String child(Element root, String first, String second) {
        Element a = (Element) root.getElementsByTagNameNS(NAMESPACE, first).item(0);
        return a.getElementsByTagNameNS(NAMESPACE, second).item(0).getTextContent();
    }

    /** A namespace-aware parser that refuses a DTD, so a document can declare no entity (ADR-A137 decision 6). */
    private static DocumentBuilder builder() {
        try {
            DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
            factory.setNamespaceAware(true);
            factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
            factory.setFeature("http://xml.org/sax/features/external-general-entities", false);
            factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
            factory.setXIncludeAware(false);
            factory.setExpandEntityReferences(false);
            DocumentBuilder builder = factory.newDocumentBuilder();
            builder.setErrorHandler(null);
            return builder;
        } catch (ParserConfigurationException e) {
            throw new IllegalStateException("no secure XML parser is available", e);
        }
    }

    private static URL resource(String path) {
        URL url = Documents.class.getClassLoader().getResource(path);
        if (url == null) {
            throw new IllegalStateException(path + " is not on the classpath");
        }
        return url;
    }
}
