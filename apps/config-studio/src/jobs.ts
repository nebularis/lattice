// SPDX-License-Identifier: MPL-2.0
// Jobs a view started and that are still running when the view goes (plan studio-worker-liveness, WL-Q5).
//
// A job that takes minutes belongs to the store, which holds its state, and not to the closure of the component that submitted it. A view
// therefore does two things. It ends its waiting when it unmounts, with an abort signal, so no old closure goes on reading a job nobody
// shows. And when it opens it reads the workspace's unfinished jobs and, for one of the kind it submits, waits for that job as it
// would for one it had just submitted, and applies its result the same way.

import { useCallback, useEffect, useRef } from "react";
import { api, awaitJob, jobId } from "./api";
import type { Job } from "./rdf/report";

/** A getter for a signal that aborts when the component unmounts, a new one for each mount, which a strict-mode remount needs. */
export function useUnmountSignal(): () => AbortSignal {
  const controller = useRef<AbortController>(undefined);
  useEffect(() => {
    controller.current = new AbortController();
    return () => controller.current?.abort();
  }, []);
  return useCallback(() => controller.current?.signal ?? new AbortController().signal, []);
}

export function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

/**
 * When the workspace `id` opens, finds its unfinished job that `wanted` picks and waits for it. `onRunning` is called with the job as
 * soon as one is found, and `onDone` with the finished job, unless the view has gone by then. A job that fails to be read is left for
 * the view to find the next time it opens.
 */
export function useAttach(id: string, wanted: (job: Job) => boolean, onRunning: (job: Job) => void, onDone: (job: Job) => void): void {
  const handlers = useRef({ wanted, onRunning, onDone });
  handlers.current = { wanted, onRunning, onDone };
  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const job = (await api.unfinishedJobs(id)).find((j) => handlers.current.wanted(j));
        if (!job || controller.signal.aborted) return;
        handlers.current.onRunning(job);
        const done = await awaitJob(jobId(job.iri), controller.signal);
        if (!controller.signal.aborted) handlers.current.onDone(done);
      } catch {
        // aborted when the view went, or the service did not answer, and the next opening looks again
      }
    })();
    return () => controller.abort();
  }, [id]);
}
