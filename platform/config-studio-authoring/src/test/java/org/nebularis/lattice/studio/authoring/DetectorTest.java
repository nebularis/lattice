// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.authoring;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import javax.xml.parsers.DocumentBuilderFactory;
import org.junit.jupiter.api.Test;

/** The detector, and its suggested keys, which the add-in computes too from the same fixture. */
class DetectorTest {

    @Test
    void suggestedKeysMatchTheSharedFixture() throws Exception {
        String json = Files.readString(Paths.CONTRACTS.resolve("document/fixtures/suggested-keys.json"));
        Matcher m = Pattern.compile("\\{\"text\": \"([^\"]*)\", \"valueType\": \"([^\"]*)\", \"suggestedKey\": \"([^\"]*)\"\\}").matcher(json);
        int checked = 0;
        while (m.find()) {
            assertEquals(m.group(3), Detector.suggestedKey(m.group(1), m.group(2)), m.group(1));
            checked++;
        }
        assertTrue(checked >= 5, "the fixture holds " + checked + " cases");
    }

    @Test
    void findsWhatIsUnmarkedAndLetsTheLongerMatchWin() throws Exception {
        String xml = """
            <document xmlns="https://www.nebularis.org/neuro-semantic/lattice/document/1" id="00000009-0000-4000-8000-000000000000">
              <meta><title>T</title><template>facility-agreement</template></meta>
              <body><section key="commitment">
                <definition id="00000009-0000-4000-8000-000000000001" term="Borrower">“Borrower” means the company.</definition>
                <clause id="00000009-0000-4000-8000-000000000002">The Borrower shall pay <var key="fee">GBP 250</var> within 30 days and GBP 1,000 by 1 March 2027 under clause 4.2(a), see [Agent].</clause>
              </section></body>
            </document>""";
        var factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        Markup markup = Markup.of(factory.newDocumentBuilder().parse(new ByteArrayInputStream(xml.getBytes(StandardCharsets.UTF_8))).getDocumentElement());
        List<Detector.Detection> found = Detector.detect(markup);
        List<String> kinds = found.stream().map(Detector.Detection::kind).toList();
        assertEquals(List.of("defined-term", "duration", "money", "date", "cross-reference", "placeholder"), kinds);
        Detector.Detection term = found.getFirst();
        assertEquals("00000009-0000-4000-8000-000000000001", term.target());
        assertEquals(0, term.partIndex());
        Detector.Detection money = found.get(2);
        assertEquals("GBP 1,000", money.text());
        assertEquals(2, money.partIndex(), "the literal after the variable");
        String text = markup.sections().getFirst().items().get(1).text();
        assertEquals("GBP 1,000", text.substring(money.start(), money.end()), "offsets are into the element's text");
        assertTrue(found.stream().noneMatch(d -> d.text().equals("Borrower") && d.elementId().endsWith("01")), "a definition does not detect its own term");
    }
}
