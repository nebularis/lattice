// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.validation;

import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.shacl.ShaclValidator;
import org.apache.jena.shacl.Shapes;
import org.apache.jena.shacl.ValidationReport;
import org.apache.jena.shacl.validation.ReportEntry;
import org.apache.jena.shacl.validation.Severity;

/** Validates a wording graph against the POC's SHACL shapes (plan \u00a72.3, WA2 Shapes). */
public final class WordingValidator {
    private static final String SHAPES_RESOURCE = "shapes/wording-poc-shapes.ttl";
    private static final Pattern SHAPE_ID_PATTERN = Pattern.compile("shape-(WS\\d{1,2})");
    private static final Pattern ELEMENT_ID_PATTERN = Pattern.compile("/element/([0-9a-f-]{36})");

    private final Shapes shapes;

    public WordingValidator() {
        Model shapesModel = ModelFactory.createDefaultModel();
        try (InputStream in = WordingValidator.class.getClassLoader().getResourceAsStream(SHAPES_RESOURCE)) {
            if (in == null) {
                throw new IllegalStateException("missing classpath resource: " + SHAPES_RESOURCE);
            }
            RDFDataMgr.read(shapesModel, in, Lang.TURTLE);
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        this.shapes = Shapes.parse(shapesModel.getGraph());
    }

    public ValidationReportView validate(Model model) {
        ValidationReport report = ShaclValidator.get().validate(shapes, model.getGraph());
        List<ValidationResult> results = new ArrayList<>();
        boolean conforms = true;
        for (ReportEntry entry : report.getEntries()) {
            String shapeId = shapeId(entry.source().toString());
            String severity = severityOf(entry.severity());
            if ("violation".equals(severity)) {
                conforms = false;
            }
            String focusNode = entry.focusNode().toString();
            results.add(new ValidationResult(shapeId, severity, focusNode, elementId(focusNode), entry.message()));
        }
        return new ValidationReportView(conforms, results);
    }

    private static String severityOf(Severity severity) {
        if (severity.equals(Severity.Violation)) {
            return "violation";
        }
        if (severity.equals(Severity.Warning)) {
            return "warning";
        }
        return "info";
    }

    private static String shapeId(String source) {
        Matcher matcher = SHAPE_ID_PATTERN.matcher(source);
        return matcher.find() ? matcher.group(1) : "WS0";
    }

    private static String elementId(String focusNode) {
        Matcher matcher = ELEMENT_ID_PATTERN.matcher(focusNode);
        return matcher.find() ? matcher.group(1) : null;
    }
}
