import { useState, useEffect, useRef } from 'react';
import { getLogFiles, getLogFile, LogLines } from '../api/client';
import { useFetch } from '../hooks/useFetch';
import Spinner from '../components/Spinner';
import ErrorBox from '../components/ErrorBox';

const LOG_LEVELS = ['', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];

const LEVEL_COLORS: Record<string, string> = {
  DEBUG: 'text-gray-400',
  INFO: 'text-blue-600',
  WARNING: 'text-yellow-600',
  ERROR: 'text-red-600',
  CRITICAL: 'text-red-800 font-bold',
};

function levelClass(line: string): string {
  for (const [lvl, cls] of Object.entries(LEVEL_COLORS)) {
    if (line.includes(`│ ${lvl}`) || line.includes(lvl)) return cls;
  }
  return 'text-gray-700';
}

function LogLine({ line }: { line: string }) {
  return (
    <div className={`whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed ${levelClass(line)}`}>
      {line}
    </div>
  );
}

interface FileViewerProps {
  filename: string;
}

function FileViewer({ filename }: FileViewerProps) {
  const [level, setLevel] = useState('');
  const [search, setSearch] = useState('');
  const [lines, setLines] = useState(100);
  const [query, setQuery] = useState({ level: '', search: '', lines: 100 });
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data, loading, error, refetch } = useFetch<LogLines>(
    () => getLogFile(filename, { level: query.level || undefined, search: query.search || undefined, lines: query.lines }),
    [filename, query]
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [data]);

  function applyFilter() {
    setQuery({ level, search, lines });
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Filter bar */}
      <div className="flex flex-wrap items-end gap-2 text-xs">
        <label className="flex flex-col gap-0.5 text-gray-500">
          Уровень
          <select
            value={level}
            onChange={e => setLevel(e.target.value)}
            className="border border-gray-200 rounded px-2 py-1 bg-white"
          >
            {LOG_LEVELS.map(l => <option key={l} value={l}>{l || 'Все'}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-0.5 text-gray-500 flex-1 min-w-[120px]">
          Поиск
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="текст…"
            className="border border-gray-200 rounded px-2 py-1 bg-white font-mono"
            onKeyDown={e => e.key === 'Enter' && applyFilter()}
          />
        </label>
        <label className="flex flex-col gap-0.5 text-gray-500">
          Строк
          <select
            value={lines}
            onChange={e => setLines(Number(e.target.value))}
            className="border border-gray-200 rounded px-2 py-1 bg-white"
          >
            {[50, 100, 200, 500].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
        <button
          onClick={applyFilter}
          className="px-3 py-1 rounded border border-gray-200 bg-white text-gray-600 hover:border-gray-400"
        >
          Применить
        </button>
        <button
          onClick={refetch}
          className="px-3 py-1 rounded border border-gray-200 bg-white text-gray-500 hover:border-gray-400"
          title="Обновить"
        >↻</button>
        {data && (
          <span className="text-gray-400 ml-auto">{data.total} строк</span>
        )}
      </div>

      {loading && <Spinner label="Загрузка логов…" />}
      {error && <ErrorBox message={error} onRetry={refetch} />}

      {data && (
        <div className="border border-gray-200 rounded bg-gray-900 p-3 max-h-[60vh] overflow-y-auto">
          {data.lines.length === 0 ? (
            <span className="text-gray-500 font-mono text-[11px]">Нет строк по фильтру.</span>
          ) : (
            data.lines.map((line, i) => <LogLine key={i} line={line} />)
          )}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
}

// ─── Live stream ─────────────────────────────────────────────────────────────

function LiveStream() {
  const [streamLevel, setStreamLevel] = useState('INFO');
  const [active, setActive] = useState(false);
  const [lines, setLines] = useState<string[]>([]);
  const esRef = useRef<EventSource | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [lines]);

  function start() {
    if (esRef.current) esRef.current.close();
    const token = localStorage.getItem('token') ?? '';
    const base = import.meta.env.VITE_API_BASE ?? '';
    const es = new EventSource(
      `${base}/web/api/logs/stream?level=${streamLevel}${token ? `&token=${encodeURIComponent(token)}` : ''}`
    );
    es.onmessage = (e) => {
      setLines(prev => [...prev.slice(-500), e.data]);
    };
    es.onerror = () => {
      setActive(false);
    };
    esRef.current = es;
    setLines([]);
    setActive(true);
  }

  function stop() {
    esRef.current?.close();
    setActive(false);
  }

  useEffect(() => () => { esRef.current?.close(); }, []);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2 text-xs">
        <label className="flex items-center gap-1 text-gray-500">
          Уровень:
          <select
            value={streamLevel}
            onChange={e => setStreamLevel(e.target.value)}
            className="border border-gray-200 rounded px-2 py-1 bg-white"
          >
            {LOG_LEVELS.slice(1).map(l => <option key={l} value={l}>{l}</option>)}
          </select>
        </label>
        <button
          onClick={active ? stop : start}
          className={`px-3 py-1 rounded border text-xs ${
            active
              ? 'border-red-300 bg-red-50 text-red-600 hover:bg-red-100'
              : 'border-green-300 bg-green-50 text-green-700 hover:bg-green-100'
          }`}
        >
          {active ? '⏹ Остановить' : '▶ Запустить'}
        </button>
        {active && <span className="text-green-600 animate-pulse">● live</span>}
        {lines.length > 0 && (
          <button
            onClick={() => setLines([])}
            className="text-gray-400 hover:text-gray-700 ml-auto"
          >
            Очистить
          </button>
        )}
      </div>

      <div className="border border-gray-200 rounded bg-gray-900 p-3 h-[50vh] overflow-y-auto">
        {lines.length === 0 ? (
          <span className="text-gray-500 font-mono text-[11px]">
            {active ? 'Ожидание сообщений…' : 'Нажмите ▶ для запуска стрима.'}
          </span>
        ) : (
          lines.map((line, i) => <LogLine key={i} line={line} />)
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LogsPage() {
  const { data, loading, error, refetch } = useFetch(() => getLogFiles(), []);
  const [selected, setSelected] = useState<string | null>(null);
  const [tab, setTab] = useState<'file' | 'live'>('file');

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="font-semibold text-gray-800">Логи</h1>
        <div className="flex gap-1">
          {(['file', 'live'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`text-xs px-3 py-1 rounded border transition-colors ${
                tab === t
                  ? 'bg-gray-800 text-white border-gray-800'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
              }`}
            >
              {t === 'file' ? 'Файлы' : 'Live'}
            </button>
          ))}
        </div>
      </div>

      {tab === 'live' && <LiveStream />}

      {tab === 'file' && (
        <div className="flex gap-4">
          {/* File list */}
          <aside className="w-48 shrink-0">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] uppercase tracking-widest text-gray-400 font-semibold">Файлы</span>
              <button onClick={refetch} className="text-gray-400 hover:text-gray-700 text-xs">↻</button>
            </div>
            {loading && <Spinner label="" />}
            {error && <ErrorBox message={error} />}
            {data && (
              <ul className="border border-gray-200 rounded bg-white divide-y divide-gray-100 max-h-[70vh] overflow-y-auto">
                {data.files.length === 0 && (
                  <li className="px-3 py-2 text-xs text-gray-400">Нет файлов</li>
                )}
                {data.files.map(f => (
                  <li key={f}>
                    <button
                      onClick={() => setSelected(f)}
                      className={`w-full text-left px-3 py-1.5 text-xs truncate hover:bg-gray-50 ${
                        selected === f ? 'bg-blue-50 text-blue-700 font-medium' : 'text-gray-700'
                      }`}
                      title={f}
                    >
                      {f}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </aside>

          {/* File content */}
          <div className="flex-1 min-w-0">
            {selected ? (
              <>
                <p className="text-xs text-gray-500 mb-2 font-mono">{selected}</p>
                <FileViewer filename={selected} />
              </>
            ) : (
              <p className="text-xs text-gray-400">Выберите файл из списка слева.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
