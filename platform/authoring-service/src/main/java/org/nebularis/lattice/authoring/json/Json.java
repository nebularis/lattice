// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.authoring.json;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;

/** One shared Jackson mapper for the word authoring POC service. */
public final class Json {
    public static final ObjectMapper MAPPER = new ObjectMapper()
        .configure(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES, true)
        .setSerializationInclusion(JsonInclude.Include.ALWAYS);

    private Json() {
    }
}
