// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.rdf;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HexFormat;
import java.util.List;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.RDFNode;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.rdf.model.StmtIterator;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;

/** A content hash independent of triple insertion order or blank node labelling (plan \u00a72.3). */
public final class CanonicalHash {
    private CanonicalHash() {
    }

    public static String of(Model model) {
        return "sha256:" + sha256Hex(canonicalText(model));
    }

    /** The bytes the hash is taken over, and the content of a generated {@code .nt} fixture. */
    public static String canonicalText(Model model) {
        return String.join("\n", sortedNTriplesLines(model)) + "\n";
    }

    public static List<String> sortedNTriplesLines(Model model) {
        requireNoBlankNodes(model);
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        RDFDataMgr.write(out, model, Lang.NTRIPLES);
        String text = out.toString(StandardCharsets.UTF_8);
        List<String> lines = new ArrayList<>();
        for (String line : text.split("\n")) {
            String trimmed = line.strip();
            if (!trimmed.isEmpty()) {
                lines.add(trimmed);
            }
        }
        Collections.sort(lines);
        return lines;
    }

    private static void requireNoBlankNodes(Model model) {
        StmtIterator statements = model.listStatements();
        while (statements.hasNext()) {
            Statement statement = statements.next();
            if (statement.getSubject().isAnon()) {
                throw new IllegalStateException("model contains a blank node subject: " + statement);
            }
            RDFNode object = statement.getObject();
            if (object.isAnon()) {
                throw new IllegalStateException("model contains a blank node object: " + statement);
            }
        }
    }

    private static String sha256Hex(String text) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(text.getBytes(StandardCharsets.UTF_8));
            return HexFormat.of().formatHex(hash);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 not available", e);
        }
    }
}
