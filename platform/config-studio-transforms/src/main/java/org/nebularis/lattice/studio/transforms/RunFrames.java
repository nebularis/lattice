// SPDX-License-Identifier: MPL-2.0
package org.nebularis.lattice.studio.transforms;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import org.apache.jena.atlas.json.JsonObject;

/**
 * The frames of a run (contract Runs, ADR-A154 decision 3). A run's result is cut into parts and each part into frames of at most
 * {@link #MAX_TEXT_BYTES} bytes as UTF-8, never inside a character, and a result that needs more than {@link #MAX_FRAMES} frames is
 * one failed frame instead. The frames are a function of the result alone, so the same result gives the same frames.
 */
final class RunFrames {
    static final int MAX_TEXT_BYTES = 49_152;
    static final int MAX_FRAMES = 128;

    private RunFrames() {
    }

    /** One failed last frame at {@code seq} 0, for a run that cannot start or must stop. */
    static List<JsonObject> failed(String run, String message) {
        JsonObject f = frame(run, 0, true);
        f.put("status", "failed");
        f.put("message", message);
        return List.of(f);
    }

    /** The frames of a {@code sample} run's result, or the one failed frame of a run that failed or is too large. */
    static List<JsonObject> of(String run, TransformRun.Result result) {
        if (result.failure() != null) {
            return failed(run, result.failure());
        }
        List<JsonObject> frames = new ArrayList<>();
        int index = 0;
        index = part(frames, run, index, "report", "text/turtle", null, null, TransformRun.reportTurtle(run, result));
        for (TransformRun.Output o : result.outputs()) {
            index = part(frames, run, index, "artefact", "application/n-triples", o.group(), o.path(), o.ntriples());
            if (frames.size() >= MAX_FRAMES) {
                break;
            }
        }
        if (frames.size() + 1 > MAX_FRAMES) {
            return failed(run, "the result is too large for one run, so narrow what is run");
        }
        JsonObject last = frame(run, frames.size(), true);
        last.put("status", "succeeded");
        last.put("conforms", result.conforms());
        frames.add(last);
        return frames;
    }

    /**
     * The frames of a {@code simulate} step's result, or the one failed frame of a step that could not be run or is too large. The parts keep the
     * order they are given in, which is the step's own, and each is cut into frames as a {@code sample} run's is.
     */
    static List<JsonObject> ofStep(String run, PersistenceStep.Result result) {
        if (result.failure() != null) {
            return failed(run, result.failure());
        }
        List<JsonObject> frames = new ArrayList<>();
        int index = 0;
        for (PersistenceStep.Part p : result.parts()) {
            index = part(frames, run, index, p.role(), p.mediaType(), null, null, p.text());
            if (frames.size() >= MAX_FRAMES) {
                break;
            }
        }
        if (frames.size() + 1 > MAX_FRAMES) {
            return failed(run, "the result is too large for one run, so narrow what is run");
        }
        JsonObject last = frame(run, frames.size(), true);
        last.put("status", "succeeded");
        frames.add(last);
        return frames;
    }

    /** Adds the frames of one part and returns the index of the next. */
    private static int part(List<JsonObject> frames, String run, int index, String role, String mediaType, String group, String path, String text) {
        List<String> pieces = cut(text);
        for (int i = 0; i < pieces.size(); i++) {
            JsonObject f = frame(run, frames.size(), false);
            if (i == 0) {
                JsonObject part = new JsonObject();
                part.put("index", index);
                part.put("role", role);
                part.put("mediaType", mediaType);
                if (path != null) {
                    part.put("path", path);
                }
                if (group != null) {
                    part.put("group", group);
                    part.put("step", 0);
                }
                f.put("part", part);
            }
            if (!pieces.get(i).isEmpty()) {
                f.put("text", pieces.get(i));
            }
            if (i < pieces.size() - 1) {
                f.put("more", true);
            }
            frames.add(f);
        }
        return index + 1;
    }

    /** The text in pieces of at most {@link #MAX_TEXT_BYTES} bytes as UTF-8. A cut never falls inside a character, and the pieces joined are the text. */
    static List<String> cut(String text) {
        byte[] bytes = text.getBytes(StandardCharsets.UTF_8);
        List<String> pieces = new ArrayList<>();
        int from = 0;
        while (from < bytes.length) {
            int to = Math.min(from + MAX_TEXT_BYTES, bytes.length);
            // A byte of the form 10xxxxxx continues a character, so a cut before one would split it. Move the cut back to the start.
            while (to < bytes.length && (bytes[to] & 0xC0) == 0x80) {
                to--;
            }
            pieces.add(new String(bytes, from, to - from, StandardCharsets.UTF_8));
            from = to;
        }
        if (pieces.isEmpty()) {
            pieces.add("");
        }
        return pieces;
    }

    private static JsonObject frame(String run, int seq, boolean last) {
        JsonObject f = new JsonObject();
        f.put("run", run);
        f.put("seq", seq);
        f.put("last", last);
        return f;
    }
}
