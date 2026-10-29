import { useCallback, useEffect, useRef, useState } from "react";

import {
  cancelDownload,
  createDownload,
  getErrorMessage,
  jobEventsUrl,
} from "../api/client";
import type { DownloadPayload, JobState, JobStatus } from "../types";

const TERMINAL: ReadonlySet<JobStatus> = new Set(["done", "error", "cancelled"]);

export function useDownload() {
  const [job, setJob] = useState<JobState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const sourceRef = useRef<EventSource | null>(null);
  const jobIdRef = useRef<string | null>(null);

  const closeStream = useCallback(() => {
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
  }, []);

  const connect = useCallback(
    (jobId: string) => {
      closeStream();
      const source = new EventSource(jobEventsUrl(jobId));
      sourceRef.current = source;

      source.onmessage = (event: MessageEvent<string>) => {
        try {
          const next = JSON.parse(event.data) as JobState;
          setJob(next);
          if (TERMINAL.has(next.status)) {
            source.close();
            if (sourceRef.current === source) {
              sourceRef.current = null;
            }
          }
        } catch {
          setError("Received an invalid progress update from the server.");
          source.close();
          if (sourceRef.current === source) {
            sourceRef.current = null;
          }
        }
      };

      source.onerror = () => {
        // EventSource reconnects automatically. The server replays the current
        // snapshot on reconnect, so there is nothing to do unless it is closed.
        if (source.readyState === EventSource.CLOSED) {
          sourceRef.current = null;
        }
      };
    },
    [closeStream],
  );

  useEffect(() => closeStream, [closeStream]);

  const start = useCallback(
    async (payload: DownloadPayload) => {
      closeStream();
      setJob(null);
      setError(null);
      setStarting(true);
      try {
        const accepted = await createDownload(payload);
        jobIdRef.current = accepted.job_id;
        setJob({
          id: accepted.job_id,
          status: "queued",
          percent: 0,
          speed: null,
          eta: null,
          filename: null,
          error: null,
          created_at: new Date().toISOString(),
          playlist: null,
        });
        connect(accepted.job_id);
      } catch (startError) {
        setError(getErrorMessage(startError));
      } finally {
        setStarting(false);
      }
    },
    [closeStream, connect],
  );

  const cancel = useCallback(async () => {
    const jobId = jobIdRef.current;
    if (!jobId) {
      return;
    }
    closeStream();
    try {
      await cancelDownload(jobId);
      setJob((current) =>
        current
          ? {
              ...current,
              status: "cancelled",
              speed: null,
              eta: null,
              error: "Download cancelled.",
            }
          : current,
      );
    } catch (cancelError) {
      setError(getErrorMessage(cancelError));
    }
  }, [closeStream]);

  const reset = useCallback(() => {
    closeStream();
    jobIdRef.current = null;
    setJob(null);
    setError(null);
    setStarting(false);
  }, [closeStream]);

  return { job, error, starting, start, cancel, reset };
}
