// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.reasoning;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.stream.Collectors;

import org.semanticweb.HermiT.ReasonerFactory;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.io.FileDocumentSource;
import org.semanticweb.owlapi.model.IRI;
import org.semanticweb.owlapi.model.MissingImportHandlingStrategy;
import org.semanticweb.owlapi.model.OWLDataFactory;
import org.semanticweb.owlapi.model.OWLOntology;
import org.semanticweb.owlapi.model.OWLOntologyCreationException;
import org.semanticweb.owlapi.model.OWLOntologyLoaderConfiguration;
import org.semanticweb.owlapi.model.OWLOntologyManager;
import org.semanticweb.owlapi.reasoner.OWLReasoner;

/**
 * Test-only OWL reasoning (ADR-A83), with HermiT as the engine. Usable as a
 * library from Java tests, and as a CLI from any other test suite:
 *
 * <pre>
 * reasoning-testkit consistent FILE...
 * reasoning-testkit satisfiable CLASS FILE...
 * reasoning-testkit subsumes SUBCLASS SUPERCLASS FILE...
 * reasoning-testkit values OBJECT_PROPERTY FILE...
 * </pre>
 *
 * The files are merged into one ontology and their {@code owl:imports} are
 * ignored, so the caller passes the whole closure. Each file is parsed on its
 * own, so a triple whose property is declared only in another file reads as an
 * annotation: pass one merged file where that matters. Output is one line of JSON.
 * HermiT applies DL-safe SWRL rules but not {@code swrlb} builtins. The OWL API
 * parses a rule only when its {@code swrl:Imp} node is anonymous, so callers
 * anonymise named rules before passing them.
 */
public final class ReasoningTestkit {
    private static final OWLDataFactory DF = OWLManager.getOWLDataFactory();

    private ReasoningTestkit() {}

    /** The files, merged, under a HermiT reasoner. */
    public static OWLReasoner reasoner(List<Path> files) throws OWLOntologyCreationException {
        OWLOntology merged = OWLManager.createOWLOntologyManager().createOntology();
        OWLOntologyLoaderConfiguration config = new OWLOntologyLoaderConfiguration()
                .setMissingImportHandlingStrategy(MissingImportHandlingStrategy.SILENT);
        for (Path file : files) {
            OWLOntologyManager manager = OWLManager.createOWLOntologyManager();
            merged.addAxioms(manager.loadOntologyFromOntologyDocument(new FileDocumentSource(file.toFile()), config).axioms());
        }
        return new ReasonerFactory().createReasoner(merged);
    }

    public static boolean satisfiable(OWLReasoner reasoner, String cls) {
        return reasoner.isSatisfiable(DF.getOWLClass(IRI.create(cls)));
    }

    public static boolean subsumes(OWLReasoner reasoner, String sub, String sup) {
        return reasoner.isEntailed(DF.getOWLSubClassOfAxiom(DF.getOWLClass(IRI.create(sub)), DF.getOWLClass(IRI.create(sup))));
    }

    /** Every entailed (subject, object) pair of a named object property. */
    public static List<String[]> values(OWLReasoner reasoner, String property) {
        List<String[]> pairs = new ArrayList<>();
        var prop = DF.getOWLObjectProperty(IRI.create(property));
        reasoner.getRootOntology().individualsInSignature().sorted().forEach(subject ->
                reasoner.getObjectPropertyValues(subject, prop).entities().sorted().forEach(object ->
                        pairs.add(new String[] {subject.getIRI().toString(), object.getIRI().toString()})));
        return pairs;
    }

    public static void main(String[] args) throws Exception {
        if (args.length < 2) {
            System.err.println("usage: reasoning-testkit consistent|satisfiable|subsumes|values [IRI...] FILE...");
            System.exit(2);
        }
        int iris = switch (args[0]) {
            case "consistent" -> 0;
            case "satisfiable", "values" -> 1;
            case "subsumes" -> 2;
            default -> throw new IllegalArgumentException("unknown command " + args[0]);
        };
        List<Path> files = Arrays.stream(args, 1 + iris, args.length).map(Path::of).toList();
        OWLReasoner reasoner = reasoner(files);
        String result = switch (args[0]) {
            case "consistent" -> String.valueOf(reasoner.isConsistent());
            case "satisfiable" -> String.valueOf(satisfiable(reasoner, args[1]));
            case "subsumes" -> String.valueOf(subsumes(reasoner, args[1], args[2]));
            default -> values(reasoner, args[1]).stream()
                    .map(pair -> "[\"" + pair[0] + "\", \"" + pair[1] + "\"]")
                    .collect(Collectors.joining(", ", "[", "]"));
        };
        System.out.println("{\"result\": " + result + "}");
    }
}
