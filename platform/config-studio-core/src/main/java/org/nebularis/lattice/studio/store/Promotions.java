// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.store;

import java.io.ByteArrayInputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.rdf.model.Resource;
import org.apache.jena.rdf.model.Statement;
import org.apache.jena.riot.Lang;
import org.apache.jena.riot.RDFDataMgr;
import org.apache.jena.vocabulary.RDF;
import org.nebularis.lattice.persistence.RequestDigest;
import org.nebularis.lattice.persistence.Payload;

/**
 * The digests of the studio's promotion contracts, which a rebuild records and a start compares (PM-Q3, PM-Q7). A contract's digest is
 * the state digest of its own triples, so a contract that changed in any way has another digest and one that did not has the same.
 */
public final class Promotions {
    /** The target namespace of the studio's promotions, {@code contracts/config-studio/promotions.ttl} (ADR-A149 decision 14). */
    public static final String NS = "https://www.nebularis.org/neuro-semantic/lattice/config-studio/promotion#";
    private static final String SRF = "https://www.nebularis.org/neuro-semantic/lattice/surface#";

    private Promotions() {
    }

    /** Each promotion contract of the staged {@code promotions.ttl}, by IRI, with its digest. Nothing when there is no file. */
    public static Map<String, String> digests(byte[] promotions) {
        Map<String, String> out = new TreeMap<>();
        if (promotions == null) {
            return out;
        }
        Model m = ModelFactory.createDefaultModel();
        RDFDataMgr.read(m, new ByteArrayInputStream(promotions), Lang.TURTLE);
        Resource promotion = m.createResource(SRF + "PromotionContract");
        m.listSubjectsWithProperty(RDF.type, promotion).forEachRemaining(c -> {
            List<org.apache.jena.graph.Triple> own = new ArrayList<>();
            for (Statement st : m.listStatements(c, null, (org.apache.jena.rdf.model.RDFNode) null).toList()) {
                own.add(st.asTriple());
            }
            out.put(c.getURI(), RequestDigest.stateDigest(Payload.ofJena(own)));
        });
        return out;
    }

    /** What the last rebuild recorded, each contract with its digest, from the record graph. */
    public static Map<String, String> recorded(Model record) {
        Map<String, String> out = new TreeMap<>();
        record.listStatements(null, Cst.contractDigest, (org.apache.jena.rdf.model.RDFNode) null)
            .forEachRemaining(st -> out.put(st.getSubject().getURI(), st.getString()));
        return out;
    }

    /** The record of {@code digests}, which a rebuild writes beside the partitions it rebuilt. */
    public static Model record(Map<String, String> digests) {
        Model m = ModelFactory.createDefaultModel();
        digests.forEach((contract, digest) -> m.add(m.createResource(contract), Cst.contractDigest, digest));
        return m;
    }
}
