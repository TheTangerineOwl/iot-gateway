import { useState } from 'react';
import { Navigate, useParams, useNavigate } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import { getDevice, sendCommand } from '../api/client';
import Spinner from '../components/Spinner';
import ErrorBox from '../components/ErrorBox';
import StatusDot from '../components/StatusDot';

export default function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  const [limit, setLimit] = useState(20);
  const [cmdText, setCmdText] = useState('');
  const [cmdResult, setCmdResult] = useState<string | null>(null);
  const [cmdError, setCmdError] = useState<string | null>(null);
  const [cmdLoading, setCmdLoading] = useState(false);

  const { data, loading, error, unauthorized, refetch } = useFetch(
    () => getDevice(deviceId!, limit),
    [deviceId, limit]
  );

  if (unauthorized) return <Navigate to="/login" replace />;

  const isOnline = (lastSeen?: string) => {
    if (!lastSeen) return false;
    return Date.now() - new Date(lastSeen).getTime() < 60_000;
  };

  async function handleSendCommand() {
    if (!deviceId || !cmdText.trim()) return;
    setCmdResult(null);
    setCmdError(null);
    setCmdLoading(true);
    try {
      let parsed: { command: string; params?: Record<string, unknown> };
      try {
        parsed = JSON.parse(cmdText);
      } catch {
        parsed = { command: cmdText.trim() };
      }
      const res = await sendCommand(deviceId, parsed);
      setCmdResult(JSON.stringify(res, null, 2));
    } catch (e) {
      setCmdError(e instanceof Error ? e.message : 'Ошибка');
    } finally {
      setCmdLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/devices')}
          className="text-sm font-bold text-gray-500 hover:text-blue-600 transition-colors"
        >
          ← Назад
        </button>
        <h1 className="text-2xl font-black text-gray-900 truncate">
          {deviceId}
        </h1>
      </div>

      {loading && <Spinner label="Загрузка данных устройства…" />}
      {error && <ErrorBox message={error} onRetry={refetch} />}

      {data && (
        <>
          {/* Device info */}
          <section className="bg-white rounded-xl border-2 border-gray-200 p-5">
            <h2 className="text-lg font-black text-gray-800 mb-4 border-b border-gray-100 pb-2">Информация</h2>
            <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4">
              <div>
                <dt className="text-xs font-black uppercase tracking-wide text-gray-400 mb-1">Статус</dt>
                <dd><StatusDot active={isOnline(data.device.last_seen)} label={isOnline(data.device.last_seen) ? 'Онлайн' : 'Офлайн'} /></dd>
              </div>
              <div>
                <dt className="text-xs font-black uppercase tracking-wide text-gray-400 mb-1">Имя</dt>
                <dd className="font-semibold text-gray-800">{data.device.name ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-xs font-black uppercase tracking-wide text-gray-400 mb-1">Протокол</dt>
                <dd>
                  {data.device.protocol ? (
                    <span className="inline-block rounded-full bg-blue-100 text-blue-800 border border-blue-300 px-2.5 py-0.5 text-xs font-black">
                      {data.device.protocol}
                    </span>
                  ) : '—'}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-black uppercase tracking-wide text-gray-400 mb-1">Зарегистрировано</dt>
                <dd className="font-semibold text-gray-700">
                  {data.device.registered_at ? new Date(data.device.registered_at).toLocaleString('ru') : '—'}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-black uppercase tracking-wide text-gray-400 mb-1">Последнее обновление</dt>
                <dd className="font-semibold text-gray-700">
                  {data.device.last_seen ? new Date(data.device.last_seen).toLocaleString('ru') : '—'}
                </dd>
              </div>
            </dl>

            {data.device.metadata && Object.keys(data.device.metadata).length > 0 && (
              <div className="mt-4">
                <dt className="text-xs font-black uppercase tracking-wide text-gray-400 mb-2">Метаданные</dt>
                <pre className="bg-gray-900 text-gray-100 rounded-lg p-3 text-xs font-mono whitespace-pre-wrap overflow-auto max-h-40">
                  {JSON.stringify(data.device.metadata, null, 2)}
                </pre>
              </div>
            )}
          </section>

          {/* Send command */}
          <section className="bg-white rounded-xl border-2 border-gray-200 p-5">
            <h2 className="text-lg font-black text-gray-800 mb-4 border-b border-gray-100 pb-2">Отправить команду</h2>
            <div className="flex gap-2">
              <input
                type="text"
                value={cmdText}
                onChange={e => setCmdText(e.target.value)}
                placeholder='Команда или JSON: {"command":"ping"}'
                className="flex-1 rounded-lg border-2 border-gray-200 px-3 py-2 text-sm font-semibold text-gray-900 focus:outline-none focus:border-blue-500 transition-colors font-mono"
              />
              <button
                onClick={handleSendCommand}
                disabled={cmdLoading || !cmdText.trim()}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-black text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {cmdLoading ? '…' : 'Отправить'}
              </button>
            </div>
            {cmdResult && (
              <pre className="mt-3 bg-teal-900 text-teal-100 rounded-lg p-3 text-xs font-mono whitespace-pre-wrap">
                {cmdResult}
              </pre>
            )}
            {cmdError && <ErrorBox message={cmdError} />}
          </section>

          {/* Telemetry */}
          <section className="bg-white rounded-xl border-2 border-gray-200 p-5">
            <div className="flex items-center justify-between mb-4 border-b border-gray-100 pb-2">
              <h2 className="text-lg font-black text-gray-800">
                Телеметрия{' '}
                <span className="text-sm font-semibold text-gray-400">({data.telemetry.total})</span>
              </h2>
              <div className="flex items-center gap-2">
                <label className="text-xs font-bold text-gray-500">Записей:</label>
                <select
                  value={limit}
                  onChange={e => setLimit(Number(e.target.value))}
                  className="rounded border border-gray-200 text-xs font-bold px-2 py-1"
                >
                  {[10, 20, 50, 100].map(n => (
                    <option key={n} value={n}>{n}</option>
                  ))}
                </select>
                <button
                  onClick={refetch}
                  className="text-xs font-bold text-blue-600 hover:text-blue-800 transition-colors"
                >
                  ↺
                </button>
              </div>
            </div>

            {data.telemetry.records.length === 0 ? (
              <p className="text-gray-400 font-semibold text-sm py-4 text-center">Нет данных телеметрии</p>
            ) : (
              <div className="flex flex-col gap-2 max-h-[32rem] overflow-auto">
                {data.telemetry.records.map((rec, i) => (
                  <div key={i} className="rounded-lg border border-gray-200 bg-gray-50 p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-gray-400">
                        {new Date(rec.timestamp).toLocaleString('ru')}
                      </span>
                    </div>
                    <pre className="text-xs font-mono font-semibold text-gray-800 whitespace-pre-wrap">
                      {JSON.stringify(rec.payload, null, 2)}
                    </pre>
                  </div>
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
