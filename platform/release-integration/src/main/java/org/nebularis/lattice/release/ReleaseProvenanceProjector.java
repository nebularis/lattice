package org.nebularis.lattice.release;

import java.util.List;

/** Projects LATTICE-owned release evidence to deterministic N-Triples for an RDF provenance graph. */
public final class ReleaseProvenanceProjector {
    private static final String PROV = "http://www.w3.org/ns/prov#";
    private static final String RELEASE = "https://www.nebularis.org/neuro-semantic/lattice/release#";

    public String project(ReleaseIntent intent, ReleaseReceipt receipt, List<ReleaseLedgerEvent> events) {
        String release = iri(RELEASE + "releases/" + intent.releaseId());
        StringBuilder triples = new StringBuilder();
        triple(triples, release, iri("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), iri(RELEASE + "SemanticRelease"));
        triple(triples, release, iri(RELEASE + "correlationId"), literal(intent.correlationId()));
        triple(triples, release, iri(RELEASE + "profileId"), literal(intent.requirements().profileId()));
        triple(triples, release, iri(RELEASE + "profileRevisionHash"), literal(intent.requirements().profileRevisionHash()));
        triple(triples, release, iri(RELEASE + "approvalEvidenceDigest"), literal(intent.requirements().approvalEvidenceDigest()));
        triple(triples, release, iri(RELEASE + "impactEvidenceDigest"), literal(intent.requirements().impactEvidenceDigest()));
        for (var graph : intent.graphReferences()) {
            triple(triples, release, iri(RELEASE + "usesGraphRevision"), iri(graph.graphIri() + "#" + graph.revisionHash()));
        }
        if (receipt != null) {
            triple(triples, release, iri(PROV + "generated"), iri(receipt.artifactUri().toString()));
            triple(triples, release, iri(RELEASE + "artifactDigest"), literal(receipt.artifactDigest()));
        }
        for (var event : events.stream().sorted(java.util.Comparator.comparing(ReleaseLedgerEvent::recordedAt)).toList()) {
            String eventIri = iri(RELEASE + "events/" + event.releaseId() + "/" + event.kind() + "/" + event.recordedAt().toEpochMilli());
            triple(triples, eventIri, iri("http://www.w3.org/1999/02/22-rdf-syntax-ns#type"), iri(RELEASE + event.kind()));
            triple(triples, eventIri, iri(PROV + "generatedAtTime"), literal(event.recordedAt().toString()));
            triple(triples, eventIri, iri(RELEASE + "evidenceReference"), literal(event.evidenceReference()));
            triple(triples, release, iri(RELEASE + "hasEvent"), eventIri);
        }
        return triples.toString();
    }

    private static void triple(StringBuilder triples, String subject, String predicate, String object) {
        triples.append(subject).append(' ').append(predicate).append(' ').append(object).append(" .\n");
    }

    private static String iri(String value) {
        return "<" + value.replace(" ", "%20") + ">";
    }

    private static String literal(String value) {
        return "\"" + value.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n") + "\"";
    }
}
