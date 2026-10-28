// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.document;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.thaiopensource.relaxng.translate.Driver;
import com.thaiopensource.util.PropertyMapBuilder;
import com.thaiopensource.validate.ValidateProperty;
import com.thaiopensource.validate.ValidationDriver;
import com.thaiopensource.validate.rng.CompactSchemaReader;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.Stream;
import javax.xml.XMLConstants;
import javax.xml.transform.stream.StreamSource;
import javax.xml.validation.Schema;
import javax.xml.validation.SchemaFactory;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.nebularis.lattice.authoring.RepoPaths;
import org.xml.sax.ErrorHandler;
import org.xml.sax.SAXException;
import org.xml.sax.SAXParseException;

/**
 * The document markup's two schemas (ADR-A137 decision 5): the XSD is Trang's output from the RELAX NG source, and the
 * two give the same verdict on every document of the corpus, the valid and invalid fixtures and the samples.
 */
class DocumentSchemaTest {
    private static final Path DOCUMENT = RepoPaths.contracts().resolve("document");

    @Test
    void the_xsd_is_generated_from_the_relax_ng_source(@TempDir Path out) throws IOException {
        Path generated = out.resolve("document.xsd");
        int status = new Driver().run(new String[] {"-I", "rnc", "-O", "xsd",
            DOCUMENT.resolve("document.rnc").toString(), generated.toString()});
        assertEquals(0, status, "Trang could not translate document.rnc");
        assertEquals(Files.readString(generated), Files.readString(DOCUMENT.resolve("document.xsd")),
            "document.xsd is stale: run mise run build:document-schema");
    }

    @Test
    void both_schemas_agree_on_every_document_and_on_its_expected_verdict() throws Exception {
        Schema xsd = SchemaFactory.newInstance(XMLConstants.W3C_XML_SCHEMA_NS_URI).newSchema(DOCUMENT.resolve("document.xsd").toFile());
        List<String> wrong = new ArrayList<>();
        int checked = 0;
        for (Path file : corpus()) {
            boolean expected = !file.getParent().getFileName().toString().equals("invalid");
            boolean byRelaxNg = validByRelaxNg(file);
            boolean byXsd = validByXsd(xsd, file);
            if (byRelaxNg != expected || byXsd != expected) {
                wrong.add(DOCUMENT.relativize(file) + ": expected " + expected + ", RELAX NG " + byRelaxNg + ", XSD " + byXsd);
            }
            checked++;
        }
        assertTrue(checked >= 13, "the corpus holds " + checked + " documents");
        assertTrue(wrong.isEmpty(), String.join("\n", wrong));
    }

    private static List<Path> corpus() throws IOException {
        List<Path> files = new ArrayList<>();
        for (String dir : List.of("fixtures/valid", "fixtures/invalid", "samples")) {
            try (Stream<Path> listed = Files.list(DOCUMENT.resolve(dir))) {
                listed.filter(f -> f.toString().endsWith(".xml")).sorted().forEach(files::add);
            }
        }
        return files;
    }

    private static boolean validByRelaxNg(Path file) throws IOException, SAXException {
        PropertyMapBuilder properties = new PropertyMapBuilder();
        properties.put(ValidateProperty.ERROR_HANDLER, SILENT);
        ValidationDriver driver = new ValidationDriver(properties.toPropertyMap(), CompactSchemaReader.getInstance());
        assertTrue(driver.loadSchema(ValidationDriver.fileInputSource(DOCUMENT.resolve("document.rnc").toFile())));
        return driver.validate(ValidationDriver.fileInputSource(file.toFile()));
    }

    private static boolean validByXsd(Schema xsd, Path file) throws IOException {
        try {
            xsd.newValidator().validate(new StreamSource(file.toFile()));
            return true;
        } catch (SAXException e) {
            return false;
        }
    }

    private static final ErrorHandler SILENT = new ErrorHandler() {
        @Override
        public void warning(SAXParseException e) {
        }

        @Override
        public void error(SAXParseException e) {
        }

        @Override
        public void fatalError(SAXParseException e) throws SAXParseException {
            throw e;
        }
    };
}
