// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.reasoning;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.semanticweb.HermiT.ReasonerFactory;
import org.semanticweb.owlapi.apibinding.OWLManager;
import org.semanticweb.owlapi.io.StringDocumentSource;
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
 * reasoning-testkit serve
 * </pre>
 *
 * The files are merged into one ontology and their {@code owl:imports} are
 * ignored, so the caller passes the whole closure. Each file is parsed on its
 * own, so a triple whose property is declared only in another file reads as an
 * annotation: pass one merged file where that matters. Output is one line of JSON.
 * HermiT applies DL-safe SWRL rules but not {@code swrlb} builtins. The OWL API
 * parses a rule only when its {@code swrl:Imp} node is anonymous, so callers
 * anonymise named rules before passing them.
 *
 * <p>{@code serve} keeps one JVM for many requests, so that a caller pays for starting it and
 * loading the OWL API and HermiT once. Each line on standard input is a request, the command and
 * its arguments separated by tabs, as the other commands take them. Each request is answered by one
 * line on standard output, {@code {"result": ...}} or {@code {"error": "..."}}. A request that fails does
 * not end the server. It ends when standard input does. Reasoners for the last few distinct closures
 * are kept, by the content of their files, so that several questions about one closure load and
 * classify it once. Anything the libraries print goes to standard error.
 */
public final class ReasoningTestkit {
    private static final OWLDataFactory DF = OWLManager.getOWLDataFactory();

    private ReasoningTestkit() {}

    /** The files, merged, under a HermiT reasoner. */
    public static OWLReasoner reasoner(List<Path> files) throws OWLOntologyCreationException, java.io.IOException {
        OWLOntology merged = OWLManager.createOWLOntologyManager().createOntology();
        OWLOntologyLoaderConfiguration config = new OWLOntologyLoaderConfiguration()
                .setMissingImportHandlingStrategy(MissingImportHandlingStrategy.SILENT);
        for (Path file : files) {
            OWLOntologyManager manager = OWLManager.createOWLOntologyManager();
            // Imports are ignored, since the caller passes the whole closure. SILENT alone still
            // fetches each import and has no bound on a stalled connection, so send every import
            // to a document that cannot load, which SILENT then skips without touching the network.
            manager.getIRIMappers().add(iri -> IRI.create("file:/lattice-import-ignored"));
            String content = Files.readString(file);
            merged.addAxioms(manager.loadOntologyFromOntologyDocument(new StringDocumentSource(content), config).axioms());
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

    /** Reasoners by the content of the files they were built from, least recently used out first. */
    static final class ReasonerCache {
        private final Map<String, OWLReasoner> byContent;

        ReasonerCache(int capacity) {
            this.byContent = new LinkedHashMap<>(16, 0.75f, true) {
                @Override
                protected boolean removeEldestEntry(Map.Entry<String, OWLReasoner> eldest) {
                    if (size() <= capacity) {
                        return false;
                    }
                    eldest.getValue().dispose();
                    return true;
                }
            };
        }

        OWLReasoner reasonerFor(List<Path> files) throws Exception {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            for (Path file : files) {
                digest.update(Files.readAllBytes(file));
                digest.update((byte) 0);
            }
            String key = HexFormat.of().formatHex(digest.digest());
            OWLReasoner cached = byContent.get(key);
            if (cached == null) {
                cached = reasoner(files);
                byContent.put(key, cached);
            }
            return cached;
        }

        int size() {
            return byContent.size();
        }
    }

    /** The IRI arguments a command takes before its files, or -1 for a command that does not exist. */
    private static int irisOf(String command) {
        return switch (command) {
            case "consistent" -> 0;
            case "satisfiable", "values" -> 1;
            case "subsumes" -> 2;
            default -> -1;
        };
    }

    /** The JSON text of the answer to one command, given as the command line gives it. */
    static String execute(String[] args, ReasonerCache cache) throws Exception {
        int iris = args.length == 0 ? -1 : irisOf(args[0]);
        if (iris < 0) {
            throw new IllegalArgumentException("unknown command " + (args.length == 0 ? "" : args[0]));
        }
        if (args.length < 2 + iris) {
            throw new IllegalArgumentException(args[0] + " takes " + iris + " IRI(s) and at least one file");
        }
        List<Path> files = Arrays.stream(args, 1 + iris, args.length).map(Path::of).toList();
        OWLReasoner reasoner = cache == null ? reasoner(files) : cache.reasonerFor(files);
        return switch (args[0]) {
            case "consistent" -> String.valueOf(reasoner.isConsistent());
            case "satisfiable" -> String.valueOf(satisfiable(reasoner, args[1]));
            case "subsumes" -> String.valueOf(subsumes(reasoner, args[1], args[2]));
            default -> values(reasoner, args[1]).stream()
                    .map(pair -> "[\"" + pair[0] + "\", \"" + pair[1] + "\"]")
                    .collect(Collectors.joining(", ", "[", "]"));
        };
    }

    static String jsonString(String text) {
        StringBuilder out = new StringBuilder("\"");
        for (char c : text.toCharArray()) {
            switch (c) {
                case '"' -> out.append("\\\"");
                case '\\' -> out.append("\\\\");
                case '\n' -> out.append("\\n");
                case '\r' -> out.append("\\r");
                case '\t' -> out.append("\\t");
                default -> {
                    if (c < 0x20) {
                        out.append(String.format("\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
                }
            }
        }
        return out.append('"').toString();
    }

    /** Answers each line of {@code in} on {@code out} until {@code in} ends. */
    static void serve(BufferedReader in, PrintStream out, ReasonerCache cache) throws IOException {
        String line;
        while ((line = in.readLine()) != null) {
            if (line.isBlank()) {
                continue;
            }
            String answer;
            try {
                answer = "{\"result\": " + execute(line.split("\t", -1), cache) + "}";
            } catch (Exception | StackOverflowError failure) {
                String message = failure.getMessage() == null ? failure.getClass().getName() : failure.getMessage();
                answer = "{\"error\": " + jsonString(failure.getClass().getSimpleName() + ": " + message) + "}";
            }
            // One line is one answer, in every host's reading, never println's platform
            // separator: on Windows that is "\r\n", and a reader splitting on "\n" alone
            // (any consumer, Java or Python) is then left with a trailing "\r" on every
            // line but the last.
            out.print(answer);
            out.print('\n');
            out.flush();
        }
    }

    public static void main(String[] args) throws Exception {
        if (args.length == 1 && args[0].equals("serve")) {
            // The protocol owns standard output, so a library that prints cannot corrupt an answer.
            PrintStream protocol = System.out;
            System.setOut(System.err);
            int capacity = Integer.getInteger("lattice.reasoning.cache", 4);
            serve(new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8)), protocol, new ReasonerCache(capacity));
            return;
        }
        if (args.length < 2) {
            System.err.println("usage: reasoning-testkit consistent|satisfiable|subsumes|values [IRI...] FILE... | serve");
            System.exit(2);
        }
        System.out.print("{\"result\": " + execute(args, null) + "}");
        System.out.print('\n');
    }
}
