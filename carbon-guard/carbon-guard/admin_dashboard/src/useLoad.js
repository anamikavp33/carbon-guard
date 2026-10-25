import { useCallback, useEffect, useRef, useState } from "react";

// Runs an async function and gives back { data, error, loading, reload }.
// When `deps` change (e.g. a new filter) the old data is cleared, so a stale list is never shown.
// reload() fetches again but keeps showing the current data until the new data arrives.
export function useLoad(fn, deps = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [tick, setTick] = useState(0);
  const depsKey = JSON.stringify(deps);
  const lastKey = useRef(depsKey);

  useEffect(() => {
    let alive = true;
    if (lastKey.current !== depsKey) {
      lastKey.current = depsKey;
      setData(null);
    }
    setLoading(true);
    setError("");
    fn()
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e.message))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [depsKey, tick]);

  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { data, error, loading, reload };
}
