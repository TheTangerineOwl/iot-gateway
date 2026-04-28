import { useState, useEffect, useCallback, useRef, DependencyList } from 'react';
import { UnauthorizedError, clearToken } from '../api/client';

interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  unauthorized: boolean;
}

interface UseFetchResult<T> extends FetchState<T> {
  refetch: () => void;
}

export function useFetch<T>(
  fetcher: () => Promise<T>,
  deps: DependencyList
): UseFetchResult<T> {
  const [state, setState] = useState<FetchState<T>>({
    data: null,
    loading: true,
    error: null,
    unauthorized: false,
  });

  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const run = useCallback(async () => {
    setState(prev => ({ ...prev, loading: true, error: null, unauthorized: false }));
    try {
      const data = await fetcherRef.current();
      setState({ data, loading: false, error: null, unauthorized: false });
    } catch (e: unknown) {
      if (e instanceof UnauthorizedError) {
        clearToken();
        setState({ data: null, loading: false, error: null, unauthorized: true });
      } else {
        const msg = e instanceof Error ? e.message : String(e);
        setState(prev => ({ ...prev, loading: false, error: msg }));
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    run();
  }, [run]);

  return { ...state, refetch: run };
}
