// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.morktransforms;

/** A transform step failed. The message names the step and never carries the input's content. */
public class TransformException extends Exception {
    public TransformException(String message, Throwable cause) {
        super(message, cause);
    }
}
