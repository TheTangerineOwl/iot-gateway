import { useState } from 'react';
import { Navigate } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import { getLogFiles, getLogFile, LogLines } from '../api/client';
import Spinner from '../components/Spinner';
import ErrorBox from '../components/ErrorBox';

const LEVEL_COLORS: Record<string, string> = {
  ERROR:    'text-red-600 font-black',
  CRITICAL: 'text-red-700 font-black',
  WARNING:  'text-orange-500 font-bold',
  WARN:     'text-orange-500 font-bold',
  INFO:     'text-blue-600 font-semibold',
  DEBUG:    'text-gray-400 font-semibold',
};

function colorLine(line: string): string {
  for (const level of Object.keys(LEVEL_COLORS)) {
    if (line.includes(level)) return LEVEL_COLORS[level];
  }
  return 'text-gray-700 font-semibold';
}

export default function LogsPage() {
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [levelFilter, setLevelFilter] = useState('');
  const [searchFilter, setSearchFilter] = useState('');
  const [linesLimit, setLinesLimit] = useState(200);

  const { data: fileList, loading: flLoading, error: flError, unauthorized: flUnauth, refetch: flRefetch } =
    useFetch(() => getLogFiles(), []);

  const { data: logLines, loading: llLoading, error: llError, unauthorized: llUnauth, refetch: llRefetch } =
    useFetch(
      () => selectedFile
        ? getLogFile(selectedFile, {
            level: levelFilter || undefined,
            search: searchFilter || undefined,
            lines: linesLimit,
          })
        : Promise.resolve(null as unknown as LogLines),
      [selectedFile, levelFilter, searchFilter, linesLimit]
    );

  if (flUnauth || llUnauth) return <Navigate to="/login" replace />;

  function fmt(bytes: number) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-black text-gray-900">Логи</h1>
        <button
          onClick={() => { flRefetch(); if (selectedFile) llRefetch(); }}
          className="flex items-center gap-2 rounded-lg border-2 border-blue-600 px-4 py-2 text-sm font-bold text-blue-700 hover:bg-blue-50 transition-colors focus:outline-none"
        >
          ↺ Обновить
        </button>
      </div>

      {flLoading && <Spinner label="Загрузка списка файлов…" />}
      {flError && <ErrorBox message={flError} onRetry={flRefetch} />}

      {fileList && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* File list */}
          <div className="lg:col-span-1">
            <h2 className="text-sm font-black uppercase tracking-wide text-gray-400 mb-2">Файлы ({fileList.total})</h2>
            <div className="flex flex-col gap-1">
              {fileList.files.map(f => (
                <button
                  key={f.filename}
                  onClick={() => setSelectedFile(f.filename)}
                  className={[
                    'flex items-start justify-between rounded-lg border-2 px-3 py-2 text-left transition-colors',
                    selectedFile === f.filename
                      ? 'border-blue-600 bg-blue-50'
                      : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50',
                  ].join(' ')}
                >
                  <div className="min-w-0">
                    <p className="text-xs font-black text-gray-800 truncate">{f.filename}</p>
                    <p className="text-xs font-semibold text-gray-400">{fmt(f.size_bytes)}</p>
                  </div>
                  {f.is_active && (
                    <span className="shrink-0 ml-2 inline-block rounded-full bg-teal-100 text-teal-700 border border-teal-300 px-1.5 py-0.5 text-xs font-black">
                      live
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Log viewer */}
          <div className="lg:col-span-3 flex flex-col gap-4">
            {selectedFile && (
              <>
                {/* Filters */}
                <div className="flex flex-wrap gap-3 items-end">
                  <div>
                    <label className="block text-xs font-black text-gray-500 uppercase mb-1">Уровень</label>
                    <select
                      value={levelFilter}
                      onChange={e => setLevelFilter(e.target.value)}
                      className="rounded-lg border-2 border-gray-200 text-sm font-bold px-2 py-1.5 focus:outline-none focus:border-blue-500"
                    >
                      <option value="">Все</option>
                      {['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].map(l => (
                        <option key={l} value={l}>{l}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-black text-gray-500 uppercase mb-1">Поиск</label>
                    <input
                      type="text"
                      value={searchFilter}
                      onChange={e => setSearchFilter(e.target.value)}
                      placeholder="Поиск по тексту…"
                      className="rounded-lg border-2 border-gray-200 text-sm font-semibold px-3 py-1.5 focus:outline-none focus:border-blue-500 w-52"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-black text-gray-500 uppercase mb-1">Строк</label>
                    <select
                      value={linesLimit}
                      onChange={e => setLinesLimit(Number(e.target.value))}
                      className="rounded-lg border-2 border-gray-200 text-sm font-bold px-2 py-1.5 focus:outline-none focus:border-blue-500"
                    >
                      {[50, 100, 200, 500, 1000].map(n => (
                        <option key={n} value={n}>{n}</option>
                      ))}
                    </select>
                  </div>
                </div>

                {llLoading && <Spinner label="Загрузка логов…" />}
                {llError && <ErrorBox message={llError} onRetry={llRefetch} />}

                {logLines && (
                  <div>
                    <p className="text-xs font-bold text-gray-400 mb-2">
                      Показано {logLines.filtered_lines} из {logLines.total_lines} строк
                    </p>
                    <div className="bg-gray-950 rounded-xl border-2 border-gray-800 overflow-auto max-h-[60vh] p-4">
                      <code className="block text-xs leading-relaxed font-mono">
                        {logLines.lines.map((line, i) => (
                          <span key={i} className={`block ${colorLine(line)}`}>
                            {line}
                          </span>
                        ))}
                      </code>
                    </div>
                  </div>
                )}
              </>
            )}

            {!selectedFile && (
              <div className="flex items-center justify-center h-48 text-gray-400 font-semibold">
                Выберите файл лога слева
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
