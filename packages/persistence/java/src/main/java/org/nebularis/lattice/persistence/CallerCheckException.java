// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.List;
import java.util.stream.Collectors;

/** A request the caller check refuses (ADR-A132 decision 2). {@link #refusals()} holds every reason, in a stable order, and the message names them all. */
public class CallerCheckException extends IllegalArgumentException {
    private static final long serialVersionUID = 1L;

    private final transient List<Refusal> refusals;

    public CallerCheckException(OperationContract operation, List<Refusal> refusals) {
        super(operation.templateId() + " refused before sending: " + refusals.stream().map(Refusal::toString).collect(Collectors.joining("; ")));
        this.refusals = List.copyOf(refusals);
    }

    public List<Refusal> refusals() { return refusals; }
}
