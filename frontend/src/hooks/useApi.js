import { useCallback, useEffect, useRef, useState } from "react";
import { errorMessage } from "../services/api";

/**
 * Load data from the API, optionally re-fetching on an interval.
 * `interval` may change between renders (e.g. poll only while a workflow is running).
 */
export function useApi(fetcher, deps = [], { interval = null, enabled = true } = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(enabled);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const result = await fetcherRef.current();
      setData(result);
      setError(null);
      return result;
    } catch (err) {
      setError(errorMessage(err));
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }
    load(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, load, ...deps]);

  useEffect(() => {
    if (!interval || !enabled) return undefined;
    const timer = setInterval(() => load(true), interval);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interval, enabled, load, ...deps]);

  const reload = useCallback(() => load(true), [load]);
  return { data, error, loading, reload, setData };
}
