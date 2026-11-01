// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.persistence;

import java.util.Comparator;

/** A declared parameter of an operation (ADR-A123 decision 5). {@code kind} is one of {@code Iri}, {@code Long}, {@code Position}, {@code Digest}, {@code String}, {@code LangString}, {@code Literal}, {@code IriOrLiteral}, {@code Payload}, {@code Rows} and {@code RegistryList}. */
public record ParameterContract(String name, String kind, boolean required, boolean equalsGraphName, boolean sourcedFromRegistry)
    implements Comparable<ParameterContract> {
    private static final Comparator<ParameterContract> ORDER = Comparator.comparing(ParameterContract::name, Text.ORDER)
        .thenComparing(ParameterContract::kind, Text.ORDER).thenComparing(ParameterContract::required)
        .thenComparing(ParameterContract::equalsGraphName).thenComparing(ParameterContract::sourcedFromRegistry);

    public ParameterContract(String name, String kind, boolean required) { this(name, kind, required, false, false); }

    @Override public int compareTo(ParameterContract o) { return ORDER.compare(this, o); }
}
