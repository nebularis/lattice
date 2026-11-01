// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.authoring;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import net.sf.saxon.s9api.SaxonApiException;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFParser;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/** The document-to-wording kit gives the graph the Java mapper of the Word add-in's first service gave for the same document, kept as the kit's expected outputs (ADR-A137 consequences). */
class DocumentToWordingTest {
    private static final String BASE = "https://example.org/lattice/authoring/";
    private static final DocumentToWording KIT = new DocumentToWording();

    @ParameterizedTest
    @ValueSource(strings = {"facility-agreement", "software-licence"})
    void each_sample_maps_to_the_kit_s_expected_output(String sampleId) throws Exception {
        String document = Files.readString(Paths.CONTRACTS.resolve("document").resolve("samples").resolve(sampleId + ".xml"));
        String output = KIT.nTriples(document, BASE, 1);

        Path fixture = Paths.CONTRACTS.resolve("xml/document-to-wording/1.0.0/expected").resolve(sampleId + ".nt");
        List<String> expected = Files.readAllLines(fixture).stream().filter(line -> !line.isBlank()).sorted().toList();
        assertEquals(expected, sorted(parse(output)));
        assertEquals(output, KIT.nTriples(document, BASE, 1), "the same document gives the same output");
        List<String> lines = output.lines().toList();
        assertEquals(lines.stream().sorted().toList(), lines, "the output is sorted");
    }

    @Test
    void text_that_n_triples_must_escape_survives() throws Exception {
        String document = """
            <document xmlns="https://www.nebularis.org/neuro-semantic/lattice/document/1" id="00000009-0000-4000-8000-000000000000">
              <meta><title>A "quoted" \\ title</title><template>facility-agreement</template></meta>
              <body><section key="commitment"><clause id="00000009-0000-4000-8000-000000000002">Line one,
            then	a tab and a \\ backslash.</clause></section></body>
            </document>""";
        Model model = parse(KIT.nTriples(document, BASE, 3));
        String text = "Line one,\nthen\ta tab and a \\ backslash.";
        assertTrue(model.listObjects().toList().stream().anyMatch(o -> o.isLiteral() && o.asLiteral().getString().equals(text)));
        assertTrue(model.listObjects().toList().stream().anyMatch(o -> o.isLiteral() && o.asLiteral().getString().equals("A \"quoted\" \\ title")));
    }

    @Test
    void a_document_declaring_a_dtd_is_refused() {
        String document = """
            <?xml version="1.0"?>
            <!DOCTYPE document [<!ENTITY x SYSTEM "file:///etc/passwd">]>
            <document xmlns="https://www.nebularis.org/neuro-semantic/lattice/document/1" id="00000009-0000-4000-8000-000000000000">
              <meta><title>&x;</title><template>t</template></meta><body/>
            </document>""";
        assertThrows(SaxonApiException.class, () -> KIT.nTriples(document, BASE, 1));
    }

    @Test
    void a_base_without_a_trailing_slash_is_refused() {
        assertThrows(SaxonApiException.class, () -> KIT.nTriples("<document xmlns=\"https://www.nebularis.org/neuro-semantic/lattice/document/1\" id=\"x\"/>", "https://example.org", 1));
    }

    /** The graph as N-Triples lines, sorted, as the expected files are. */
    private static List<String> sorted(Model model) {
        java.io.StringWriter out = new java.io.StringWriter();
        org.apache.jena.riot.RDFDataMgr.write(out, model, Lang.NTRIPLES);
        return out.toString().lines().filter(line -> !line.isBlank()).sorted().toList();
    }

    private static Model parse(String nTriples) {
        return RDFParser.fromString(nTriples, Lang.NTRIPLES).toModel();
    }
}
