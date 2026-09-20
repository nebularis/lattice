package org.nebularis.lattice.release;

final class ReleaseEvidenceJson {
    private ReleaseEvidenceJson() { }

    static String intent(ReleaseIntent intent) {
        String graphs = intent.graphReferences().stream().map(graph -> "{\"graphIri\":\"" + escape(graph.graphIri()) + "\",\"revisionHash\":\"" + escape(graph.revisionHash()) + "\"}").reduce((left, right) -> left + "," + right).orElse("");
        String gates = intent.semanticGates().stream().map(gate -> "{\"gate\":\"" + escape(gate.gate()) + "\",\"evidenceDigest\":\"" + escape(gate.evidenceDigest()) + "\"}").reduce((left, right) -> left + "," + right).orElse("");
        return "{\"releaseId\":\"" + escape(intent.releaseId()) + "\",\"correlationId\":\"" + escape(intent.correlationId()) + "\",\"profileRevisionHash\":\"" + escape(intent.requirements().profileRevisionHash()) + "\",\"graphReferences\":[" + graphs + "],\"semanticGates\":[" + gates + "]}";
    }

    static String receipt(ReleaseReceipt receipt) {
        return "{\"releaseId\":\"" + escape(receipt.releaseId()) + "\",\"adapterId\":\"" + escape(receipt.adapterId()) + "\",\"state\":\"" + receipt.state() + "\",\"artifactDigest\":\"" + escape(receipt.artifactDigest()) + "\"}";
    }

    private static String escape(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
