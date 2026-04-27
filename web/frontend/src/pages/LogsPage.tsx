import { useState, useEffect, useRef } from 'react';
import { getLogFiles, getLogFile, LogFile, LogLines } from '../api/client';
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

// ─── File viewer ──────────────────────────────────────────────────────────────

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
        >
          ↺
        </button>
        {data && (
          <span className="text-gray-400 ml-auto">{data.filtered_lines} строк</span>
        )}
      </div>

      {loading && <Spinner label="Загрузка лого…" />}
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

// ─── Live stream ──────────────────────────────────────────────────────────────

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
            {LOG_LEVELS.map(l => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </label>
        <button
          onClick={active ? stop : start}
          className="px-3 py-1 rounded border border-gray-200 bg-white text-gray-600 hover:border-gray-400"
        >
          {active ? '■ Стоп' : '▶ Старт'}
        </button>
        {active && <span className="text-green-600 animate-pulse">● live</span>}
        {lines.length > 0 && (
          <button
            onClick={() => setLines([])}
            className="text-gray-400 hover:text-gray-600 ml-auto"
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

// ─── File list ────────────────────────────────────────────────────────────────

interface FileListProps {
  files: LogFile[];
  selected: string | null;
  onSelect: (filename: string) => void;
}

function FileList({ files, selected, onSelect }: FileListProps) {
  function formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  return (
    <div className="flex flex-col border border-gray-200 rounded bg-white overflow-hidden w-56 shrink-0">
      {files.length === 0 && (
        <p className="text-xs text-gray-400 px-3 py-2">Файлы не найдены.</p>
      )}
      {files.map(file => (
        <button
          key={file.filename}
          onClick={() => onSelect(file.filename)}  // ✅ передаём file.filename (string), не file (object)
          className={`text-left px-3 py-2 text-xs border-b border-gray-100 last:border-0 flex flex-col gap-0.5 hover:bg-blue-50 transition-colors ${
            selected === file.filename ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
          }`}
        >
          <span className="font-mono truncate flex items-center gap-1">
            {file.is_active && (
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-green-500 shrink-0" title="активный" />
            )}
            {file.filename}  {/* ✅ рендерим file.filename (string), не file (object) */}
          </span>
          <span className="text-gray-400 text-[10px]">
            {formatSize(file.size_bytes)} · {new Date(file.modified_at).toLocaleDateString('ru')}
          </span>
        </button>
      ))}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function LogsPage() {
  const { data, loading, error, refetch } = useFetch(() => getLogFiles(), []);
  const [selected, setSelected] = useState<string | null>(null);  // ✅ string | null, не LogFile | null
  const [tab, setTab] = useState<'file' | 'live'>('file');

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-gray-800">Логи</h2>
        <div className="flex gap-1">
          {(['file', 'live'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1 rounded text-xs border ${
                tab === t
                  ? 'bg-gray-800 text-white border-gray-800'
                  : 'bg-white text-gray-500 border-gray-200 hover:border-gray-400'
              }`}
            >
              {t === 'file' ? 'Файл' : 'Live'}
            </button>
          ))}
        </div>
      </div>

      {tab === 'live' && <LiveStream />}

      {tab === 'file' && (
        <div className="flex gap-4">
          {/* File list */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">Файлы</span>
              <button onClick={refetch} className="text-xs text-gray-400 hover:text-gray-700">↺</button>
            </div>
            {loading && <Spinner />}
            {error && <ErrorBox message={error} onRetry={refetch} />}
            {data && (
              <FileList
                files={data.files}
                selected={selected}
                onSelect={setSelected}  // ✅ setSelected принимает string
              />
            )}
          </div>

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
