import { useState, useRef, useEffect } from 'react';
import { useFetch } from '../hooks/useFetch';
import { getLogFiles, getLogFile } from '../api/client';
import type { LogFile } from '../api/client';
import Spinner from '../components/Spinner';
import ErrorBox from '../components/ErrorBox';

// ─── Log level helpers ────────────────────────────────────────────────────────

/**
 * Returns a CSS class for the log level extracted from the line text.
 * Coloring is based on colorblind-safe palette on a dark background.
 */
function logLineClass(line: string): string {
  const u = line.toUpperCase();
  if (u.includes('CRITICAL') || u.includes('FATAL'))  return 'log-level-critical';
  if (u.includes('ERROR'))                             return 'log-level-error';
  if (u.includes('WARNING') || u.includes('WARN'))    return 'log-level-warning';
  if (u.includes('INFO'))                              return 'log-level-info';
  if (u.includes('DEBUG'))                             return 'log-level-debug';
  return 'text-gray-200'; // default — near-white on dark bg
}

// ─── LiveViewer ───────────────────────────────────────────────────────────────

function LiveViewer() {
  const [streamLevel, setStreamLevel] = useState('');
  const [lines, setLines]             = useState<string[]>([]);
  const [active, setActive]           = useState(false);
  const abortRef  = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [lines]);

  async function start() {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    const token = localStorage.getItem('token') ?? '';
    const base  = (import.meta.env.VITE_API_BASE as string | undefined) ?? '';

    setLines([]);
    setActive(true);

    try {
      const res = await fetch(
        `${base}/web/api/logs/stream${streamLevel ? `?level=${streamLevel}` : ''}`,
        {
          headers: { Authorization: `Bearer ${token}` },
          signal: ctrl.signal,
        }
      );

      if (!res.ok || !res.body) {
        setActive(false);
        return;
      }

      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buf += decoder.decode(value, { stream: true });

        const parts = buf.split('\n\n');
        buf = parts.pop() ?? '';

        for (const part of parts) {
          for (const line of part.split('\n')) {
            if (line.startsWith('data: ')) {
              const text = line.slice(6);
              if (text) setLines(prev => [...prev.slice(-500), text]);
            }
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== 'AbortError') {
        console.error('SSE stream error:', err);
      }
    } finally {
      setActive(false);
    }
  }

  function stop() {
    abortRef.current?.abort();
    setActive(false);
  }

  useEffect(() => () => { abortRef.current?.abort(); }, []);

  const LEVELS = ['', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];

  return (
    <div className="flex flex-col gap-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm font-bold text-gray-700">
          Уровень:
          <select
            value={streamLevel}
            onChange={e => setStreamLevel(e.target.value)}
            disabled={active}
            className="rounded-lg border-2 border-gray-300 bg-white px-3 py-1.5 text-sm font-bold text-gray-900 focus:border-blue-600 focus:outline-none disabled:opacity-50"
          >
            {LEVELS.map(l => (
              <option key={l} value={l}>{l || 'Все'}</option>
            ))}
          </select>
        </label>

        {active ? (
          <button
            onClick={stop}
            className="rounded-lg border-2 border-orange-500 bg-orange-500 px-5 py-2 text-sm font-black text-white hover:bg-orange-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-orange-400 transition-colors"
          >
            ■ Стоп
          </button>
        ) : (
          <button
            onClick={start}
            className="rounded-lg border-2 border-teal-600 bg-teal-600 px-5 py-2 text-sm font-black text-white hover:bg-teal-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400 transition-colors"
          >
            ▶ Старт
          </button>
        )}

        {active && (
          <span className="flex items-center gap-1.5 rounded-full border-2 border-teal-500 bg-teal-50 px-3 py-1 text-xs font-black text-teal-700">
            <span className="animate-pulse">●</span> live
          </span>
        )}

        {lines.length > 0 && (
          <button
            onClick={() => setLines([])}
            className="ml-auto text-sm font-bold text-gray-500 hover:text-gray-800 underline underline-offset-2"
          >
            Очистить
          </button>
        )}
      </div>

      {/* Terminal window */}
      <div className="log-terminal rounded-xl border-2 border-gray-700 min-h-64 max-h-[65vh] overflow-y-auto p-4">
        {lines.length === 0 ? (
          <p className="text-gray-500 font-semibold italic">
            {active ? 'Ожидание сообщений…' : 'Нажмите ▶ для запуска стрима.'}
          </p>
        ) : (
          lines.map((line, i) => (
            <div key={i} className={`${logLineClass(line)} break-all`}>
              {line}
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

// ─── FileViewer ───────────────────────────────────────────────────────────────

interface FileViewerProps { filename: string }

function FileViewer({ filename }: FileViewerProps) {
  const [level, setLevel]   = useState('');
  const [search, setSearch] = useState('');
  const [lines, setLines]   = useState(100);

  const { data, loading, error, refetch } = useFetch(
    () => getLogFile(filename, { level: level || undefined, search: search || undefined, lines }),
    [filename, level, search, lines]
  );

  const LEVELS = ['', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];

  return (
    <div className="flex flex-col gap-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Поиск…"
          className="flex-1 min-w-40 rounded-lg border-2 border-gray-300 bg-white px-4 py-2 text-base font-semibold text-gray-900 placeholder-gray-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-200"
        />
        <select
          value={level}
          onChange={e => setLevel(e.target.value)}
          className="rounded-lg border-2 border-gray-300 bg-white px-3 py-2 text-sm font-bold text-gray-900 focus:border-blue-600 focus:outline-none"
        >
          {LEVELS.map(l => (
            <option key={l} value={l}>{l || 'Все уровни'}</option>
          ))}
        </select>
        <select
          value={lines}
          onChange={e => setLines(Number(e.target.value))}
          className="rounded-lg border-2 border-gray-300 bg-white px-3 py-2 text-sm font-bold text-gray-900 focus:border-blue-600 focus:outline-none"
        >
          {[50, 100, 250, 500, 1000].map(n => (
            <option key={n} value={n}>{n} строк</option>
          ))}
        </select>
        <button
          onClick={refetch}
          className="rounded-lg border-2 border-blue-600 px-4 py-2 text-sm font-bold text-blue-700 hover:bg-blue-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors"
        >
          ↺ Обновить
        </button>
      </div>

      {loading && <Spinner label="Загрузка…" />}
      {error   && <ErrorBox message={error} onRetry={refetch} />}

      {data && (
        <>
          <p className="text-sm font-bold text-gray-600">
            Показано{' '}
            <span className="text-blue-700">{data.filtered_lines}</span>
            {' '}из{' '}
            <span className="text-blue-700">{data.total_lines}</span>
            {' '}строк
          </p>

          {/* Terminal window */}
          <div className="log-terminal rounded-xl border-2 border-gray-700 max-h-[60vh] overflow-y-auto p-4">
            {data.lines.length === 0 ? (
              <p className="text-gray-500 italic font-semibold">Нет строк для отображения.</p>
            ) : (
              data.lines.map((line, i) => (
                <div key={i} className={`${logLineClass(line)} break-all`}>
                  {line}
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ─── FileList ─────────────────────────────────────────────────────────────────

interface FileListProps {
  files: LogFile[];
  selected: string | null;
  onSelect: (f: string) => void;
}

function FileList({ files, selected, onSelect }: FileListProps) {
  function fmt(bytes: number) {
    if (bytes < 1024)             return `${bytes} B`;
    if (bytes < 1024 * 1024)      return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  if (files.length === 0) {
    return (
      <p className="py-4 text-sm font-semibold text-gray-500 italic text-center">
        Файлы не найдены.
      </p>
    );
  }

  return (
    <ul className="flex flex-col gap-1">
      {files.map(f => (
        <li key={f.filename}>
          <button
            onClick={() => onSelect(f.filename)}
            className={[
              'w-full rounded-lg border-2 px-4 py-3 text-left transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
              selected === f.filename
                ? 'border-blue-600 bg-blue-50 text-blue-900'
                : 'border-transparent bg-white text-gray-800 hover:border-gray-300 hover:bg-gray-50',
            ].join(' ')}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-sm font-bold truncate">{f.filename}</span>
              {f.is_active && (
                <span className="flex-shrink-0 rounded-full border border-teal-500 bg-teal-50 px-2 py-0.5 text-xs font-black text-teal-700">
                  active
                </span>
              )}
            </div>
            <div className="mt-1 flex items-center gap-3 text-xs font-semibold text-gray-500">
              <span>{fmt(f.size_bytes)}</span>
              <span>·</span>
              <span>{new Date(f.modified_at).toLocaleString('ru')}</span>
            </div>
          </button>
        </li>
      ))}
    </ul>
  );
}

// ─── LogsPage ─────────────────────────────────────────────────────────────────

export default function LogsPage() {
  const { data, loading, error, refetch } = useFetch(() => getLogFiles(), []);
  const [selected, setSelected] = useState<string | null>(null);
  const [tab, setTab]           = useState<'file' | 'live'>('file');

  const tabs: { key: 'file' | 'live'; label: string }[] = [
    { key: 'file', label: '📄 Файлы логов' },
    { key: 'live', label: '📡 Live стрим'  },
  ];

  return (
    <div className="flex flex-col gap-6">
      {/* Page title */}
      <h1 className="text-3xl font-black text-gray-900">Логи</h1>

      {/* Tabs */}
      <div className="flex gap-2 border-b-2 border-gray-200 pb-0">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={[
              'rounded-t-lg border-2 border-b-0 px-6 py-2.5 text-sm font-black transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
              tab === t.key
                ? 'border-gray-200 border-b-white bg-white text-blue-800 -mb-0.5'
                : 'border-transparent text-gray-500 hover:text-gray-800',
            ].join(' ')}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Live */}
      {tab === 'live' && (
        <div className="rounded-xl border-2 border-gray-200 bg-white p-6">
          <LiveViewer />
        </div>
      )}

      {/* File */}
      {tab === 'file' && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[280px_1fr]">
          {/* Sidebar */}
          <aside className="rounded-xl border-2 border-gray-200 bg-white p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-black text-gray-800">Файлы</h2>
              <button
                onClick={refetch}
                className="text-sm font-bold text-gray-500 hover:text-gray-800 underline underline-offset-2"
              >
                ↺
              </button>
            </div>
            {loading && <Spinner label="Загрузка…" />}
            {error   && <ErrorBox message={error} onRetry={refetch} />}
            {data    && (
              <FileList
                files={data.files}
                selected={selected}
                onSelect={setSelected}
              />
            )}
          </aside>

          {/* Content */}
          <div className="rounded-xl border-2 border-gray-200 bg-white p-6 min-h-64">
            {selected ? (
              <FileViewer filename={selected} />
            ) : (
              <div className="flex h-full min-h-48 items-center justify-center text-base font-semibold text-gray-400">
                ← Выберите файл из списка слева
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
