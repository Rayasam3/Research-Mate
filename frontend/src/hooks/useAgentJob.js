import { useEffect, useRef, useState } from "react";

import { getAgentStatus } from "../api/client";

export function useAgentJob(jobId) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);
  const intervalRef = useRef(null);
  const failureCountRef = useRef(0);


  useEffect(() => {
    if (!jobId) return;

    let cancelled = false;

    async function poll() {
      try {
        const data = await getAgentStatus(jobId);
        if (cancelled) return;
        failureCountRef.current = 0;
        setStatus(data);

        if (data.status === "done" || data.status === "failed") {
          if (intervalRef.current) window.clearInterval(intervalRef.current);
        }
      } catch {
        // A single failed poll shouldn't immediately show an error - the
        // next interval tick will likely succeed. Only surface an error
        // if we've lost the connection for a sustained period.
        failureCountRef.current += 1;
        if (!cancelled && failureCountRef.current >= 5) {
          setError("Lost connection to the server. Please refresh the page.");
        }
      }
    }

    poll();
    intervalRef.current = window.setInterval(poll, 3000);

    return () => {
      cancelled = true;
      if (intervalRef.current) window.clearInterval(intervalRef.current);
    };
  }, [jobId]);

  return { status, error };
}