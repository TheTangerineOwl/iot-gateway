import { useState, useEffect, useCallback, useRef } from 'react';

interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useFetch<T>(
  fetcher: () => Promise<T>,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  deps: any[]
): FetchState<T> {
  const [data, setData]       = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const counter               = useRef(0);

  const run = useCallback(() => {
    const id = ++counter.current;
    setLoading(true);
    setError(null);
    fetcher()
      .then(res => { if (counter.current === id) { setData(res); setLoading(false); } })
      .catch(err => { if (counter.current === id) { setError(err?.message ?? 'Ошибка'); setLoading(false); } });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => { run(); }, [run]);

  return { data, loading, error, refetch: run };
}
