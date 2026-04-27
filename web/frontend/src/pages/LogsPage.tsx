import { useState, useRef, useEffect } from 'react';
import {
  getLogFiles, getLogFile,
  LogFile, LogLines,
} from '../api/client';
import { useFetch } from '../hooks/useFetch';

// ─── LiveStream ──────────────────────────────────────────────────────────────

function LiveStream() {
  const [streamLevel, setStreamLevel] = useState('INFO');
  const [active, setActive]           = useState(false);
  const [lines, setLines]             = useState<string[]>([]);
  const abortRef  = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [lines]);

  async function start() {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
  
    const token = localStorage.getItem('token') ?? '';
    const base  = import.meta.env.VITE_API_BASE ?? '';
  
    setLines([]);
    setActive(true);
  
    try {
      const res = await fetch(
        `${base}/web/api/logs/stream?level=${streamLevel}`,
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
  
        // SSE-события разделяются двойным переносом строки
        const parts = buf.split('\n\n');          // ← '\n\n', не '\\n'
        buf = parts.pop() ?? '';                  // неполное событие — обратно в буфер
  
        for (const part of parts) {
          for (const line of part.split('\n')) {  // ← '\n', не '\\n'
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

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-3 flex-wrap">
        <label className="text-sm">
          Уровень:{' '}
          <select
            value={streamLevel}
            onChange={e => setStreamLevel(e.target.value)}
            disabled={active}
            className="ml-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
          >
            {['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].map(l => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </label>

        {active
          ? <button onClick={stop}  className="px-3 py-1 rounded bg-red-700 hover:bg-red-600 text-sm">⏹ Стоп</button>
          : <button onClick={start} className="px-3 py-1 rounded bg-green-700 hover:bg-green-600 text-sm">▶ Старт</button>
        }
        {active && <span className="text-green-400 text-xs animate-pulse">● live</span>}
        {lines.length > 0 && (
          <button onClick={() => setLines([])} className="ml-auto text-xs text-gray-500 hover:text-gray-300">
            Очистить
          </button>
        )}
      </div>

      <div className="bg-black rounded border border-gray-800 h-96 overflow-y-auto p-3 font-mono text-xs">
        {lines.length === 0 ? (
          <p className="text-gray-600">
            {active ? 'Ожидание сообщений…' : 'Нажмите ▶ для запуска стрима.'}
          </p>
        ) : (
          lines.map((line, i) => <div key={i}>{line}</div>)
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

// ─── FileViewer ──────────────────────────────────────────────────────────────

interface FileViewerProps { filename: string }

function FileViewer({ filename }: FileViewerProps) {
  const [level, setLevel]   = useState('');
  const [search, setSearch] = useState('');
  const [lines, setLines]   = useState(100);

  const { data, loading, error, refetch } = useFetch<LogLines>(
    () => getLogFile(filename, { level: level || undefined, search: search || undefined, lines }),
    [filename, level, search, lines]
  );

  return (
    <div className="space-y-3">
      <div className="flex gap-2 flex-wrap">
        <select
          value={level}
          onChange={e => setLevel(e.target.value)}
          className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
        >
          <option value="">Все уровни</option>
          {['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].map(l => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Поиск…"
          className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm flex-1 min-w-0"
        />
        <select
          value={lines}
          onChange={e => setLines(Number(e.target.value))}
          className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
        >
          {[50, 100, 200, 500].map(n => (
            <option key={n} value={n}>Последние {n}</option>
          ))}
        </select>
        <button onClick={refetch} className="px-3 py-1 bg-gray-700 hover:bg-gray-600 rounded text-sm">
          ↻
        </button>
      </div>

      {loading && <p className="text-gray-500 text-sm">Загрузка…</p>}
      {error   && <p className="text-red-400 text-sm">{error}</p>}

      {data && (
        <>
          <p className="text-xs text-gray-500">
            Показано {data.filtered_lines} / {data.total_lines} строк
          </p>
          <div className="bg-black rounded border border-gray-800 h-96 overflow-y-auto p-3 font-mono text-xs">
            {data.lines.map((line, i) => <div key={i}>{line}</div>)}
          </div>
        </>
      )}
    </div>
  );
}

// ─── FileList ────────────────────────────────────────────────────────────────

interface FileListProps {
  files: LogFile[];
  selected: string | null;
  onSelect: (f: string) => void;
}

function FileList({ files, selected, onSelect }: FileListProps) {
  function fmt(bytes: number) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  return (
    <ul className="space-y-1">
      {files.length === 0 && <li className="text-gray-500 text-sm">Файлы не найдены.</li>}
      {files.map(f => (
        <li key={f.filename}>
          <button
            onClick={() => onSelect(f.filename)}
            className={`w-full text-left px-3 py-2 rounded text-xs transition-colors ${
              selected === f.filename
                ? 'bg-blue-900/50 text-blue-300'
                : 'hover:bg-gray-800 text-gray-300'
            }`}
          >
            <div className="flex justify-between gap-2">
              <span className="truncate font-mono">{f.filename}</span>
              <span className="text-gray-500 shrink-0">{fmt(f.size_bytes)}</span>
            </div>
            {f.is_active && (
              <span className="text-green-400 text-xs">● активный</span>
            )}
          </button>
        </li>
      ))}
    </ul>
  );
}

// ─── LogsPage ────────────────────────────────────────────────────────────────

export default function LogsPage() {
  const { data, loading, error, refetch } = useFetch(() => getLogFiles(), []);
  const [selected, setSelected] = useState<string | null>(null);
  const [tab, setTab]           = useState<'file' | 'live'>('file');

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Логи</h1>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-800">
        {(['file', 'live'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm border-b-2 -mb-px transition-colors ${
              tab === t
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-300'
            }`}
          >
            {t === 'file' ? 'Файл' : 'Live'}
          </button>
        ))}
      </div>

      {tab === 'live' && <LiveStream />}

      {tab === 'file' && (
        <div className="grid grid-cols-[260px_1fr] gap-4">
          {/* Sidebar */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-400">Файлы</span>
              <button onClick={refetch} className="text-xs text-gray-600 hover:text-gray-400">↻</button>
            </div>
            {loading && <p className="text-gray-500 text-sm">Загрузка…</p>}
            {error   && <p className="text-red-400 text-sm">{error}</p>}
            {data    && <FileList files={data.files} selected={selected} onSelect={setSelected} />}
          </div>

          {/* Content */}
          <div>
            {selected
              ? <FileViewer filename={selected} />
              : <p className="text-gray-500 text-sm mt-2">Выберите файл из списка слева.</p>
            }
          </div>
        </div>
      )}
    </div>
  );
}