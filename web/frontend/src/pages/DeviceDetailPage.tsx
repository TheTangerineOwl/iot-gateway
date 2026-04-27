import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import { getDevice, sendCommand } from '../api/client';
import Spinner from '../components/Spinner';
import ErrorBox from '../components/ErrorBox';
import StatusDot from '../components/StatusDot';

export default function DeviceDetailPage() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate      = useNavigate();
  const [limit, setLimit] = useState(20);

  const { data, loading, error, refetch } = useFetch(
    () => getDevice(deviceId!, limit),
    [deviceId, limit]
  );

  // Command form
  const [cmd, setCmd]         = useState('');
  const [params, setParams]   = useState('');
  const [cmdRes, setCmdRes]   = useState<string | null>(null);
  const [cmdErr, setCmdErr]   = useState<string | null>(null);
  const [sending, setSending] = useState(false);

  async function handleCommand(e: React.FormEvent) {
    e.preventDefault();
    setCmdRes(null);
    setCmdErr(null);
    setSending(true);
    try {
      let parsed: Record<string, unknown> | undefined;
      if (params.trim()) {
        parsed = JSON.parse(params);
      }
      const res = await sendCommand(deviceId!, { command: cmd, params: parsed });
      setCmdRes(JSON.stringify(res, null, 2));
    } catch (err) {
      setCmdErr(err instanceof Error ? err.message : 'Ошибка');
    } finally {
      setSending(false);
    }
  }

  if (!deviceId) return null;

  return (
    <div className="flex flex-col gap-8">
      {/* Back + title */}
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate('/devices')}
          className="rounded-lg border-2 border-gray-300 px-3 py-1.5 text-sm font-bold text-gray-600 hover:border-blue-400 hover:text-blue-700 focus:outline-none transition-colors"
        >
          ← Назад
        </button>
        <h1 className="text-2xl font-black text-gray-900 font-mono">{deviceId}</h1>
        <button
          onClick={refetch}
          className="ml-auto rounded-lg border-2 border-blue-600 px-4 py-2 text-sm font-bold text-blue-700 hover:bg-blue-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors"
        >
          ↺ Обновить
        </button>
      </div>

      {loading && <Spinner label="Загрузка…" />}
      {error   && <ErrorBox message={error} onRetry={refetch} />}

      {data && (
        <>
          {/* Device info */}
          <section className="rounded-xl border-2 border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-black text-gray-800">Информация об устройстве</h2>
            <dl className="grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-4">
              {[
                { label: 'Имя',               value: data.device.name },
                { label: 'Протокол',          value: data.device.protocol },
                { label: 'Зарегистрирован',   value: data.device.registered_at ? new Date(data.device.registered_at).toLocaleString('ru') : undefined },
                { label: 'Последний визит',   value: data.device.last_seen     ? new Date(data.device.last_seen).toLocaleString('ru') : undefined },
              ].map(({ label, value }) => (
                <div key={label}>
                  <dt className="text-xs font-black uppercase tracking-wide text-gray-500">{label}</dt>
                  <dd className="mt-1 text-base font-bold text-gray-900">
                    {value ?? <span className="text-gray-400">—</span>}
                  </dd>
                </div>
              ))}
            </dl>
            <div className="mt-4 flex items-center gap-2">
              <StatusDot active={!!data.device.last_seen} />
              <span className="text-sm font-bold text-gray-600">
                {data.device.last_seen ? 'Онлайн (последняя активность известна)' : 'Нет данных о последней активности'}
              </span>
            </div>
          </section>

          {/* Telemetry */}
          <section className="rounded-xl border-2 border-gray-200 bg-white p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-black text-gray-800">
                Телеметрия{' '}
                <span className="text-base font-bold text-gray-500">({data.telemetry.total})</span>
              </h2>
              <div className="flex items-center gap-2">
                <label className="text-sm font-bold text-gray-600">Показать:</label>
                <select
                  value={limit}
                  onChange={e => setLimit(Number(e.target.value))}
                  className="rounded-lg border-2 border-gray-300 bg-white px-3 py-1.5 text-sm font-bold text-gray-800 focus:border-blue-600 focus:outline-none"
                >
                  {[10, 20, 50, 100].map(n => (
                    <option key={n} value={n}>{n} записей</option>
                  ))}
                </select>
              </div>
            </div>

            {data.telemetry.records.length === 0 ? (
              <p className="rounded-xl border-2 border-dashed border-gray-300 p-6 text-center text-base font-semibold text-gray-500">
                Нет записей.
              </p>
            ) : (
              <div className="overflow-auto">
                <table className="w-full text-sm">
                  <thead className="border-b-2 border-gray-200 bg-gray-100">
                    <tr>
                      <th className="px-4 py-2.5 text-left text-xs font-black uppercase tracking-wide text-gray-600 whitespace-nowrap">
                        Время
                      </th>
                      <th className="px-4 py-2.5 text-left text-xs font-black uppercase tracking-wide text-gray-600">
                        Данные
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y-2 divide-gray-100">
                    {data.telemetry.records.map((r, i) => (
                      <tr key={i} className="hover:bg-blue-50 transition-colors">
                        <td className="px-4 py-2.5 font-semibold text-gray-700 whitespace-nowrap">
                          {new Date(r.timestamp).toLocaleString('ru')}
                        </td>
                        <td className="px-4 py-2.5">
                          <code className="rounded bg-gray-100 px-2 py-0.5 text-xs font-bold text-gray-900 break-all">
                            {JSON.stringify(r.payload)}
                          </code>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Command */}
          <section className="rounded-xl border-2 border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-lg font-black text-gray-800">Отправить команду</h2>
            <form onSubmit={handleCommand} className="flex flex-col gap-4">
              <label className="flex flex-col gap-1">
                <span className="text-sm font-bold text-gray-700">Команда</span>
                <input
                  type="text"
                  value={cmd}
                  onChange={e => setCmd(e.target.value)}
                  required
                  placeholder="reboot"
                  className="rounded-lg border-2 border-gray-300 bg-white px-4 py-2.5 text-base font-semibold text-gray-900 placeholder-gray-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-sm font-bold text-gray-700">
                  Параметры{' '}
                  <span className="font-normal text-gray-400">(JSON, необязательно)</span>
                </span>
                <input
                  type="text"
                  value={params}
                  onChange={e => setParams(e.target.value)}
                  placeholder='{"key": "value"}'
                  className="rounded-lg border-2 border-gray-300 bg-white px-4 py-2.5 font-mono text-sm font-semibold text-gray-900 placeholder-gray-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-200"
                />
              </label>
              <div>
                <button
                  type="submit"
                  disabled={sending}
                  className="rounded-lg bg-blue-700 px-6 py-2.5 text-base font-black text-white hover:bg-blue-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 disabled:opacity-60 transition-colors"
                >
                  {sending ? 'Отправка…' : '▶ Отправить'}
                </button>
              </div>
            </form>

            {cmdErr && (
              <div className="mt-4">
                <ErrorBox message={cmdErr} />
              </div>
            )}

            {cmdRes && (
              <div className="mt-4 rounded-xl border-2 border-teal-400 bg-gray-900 overflow-auto">
                <pre className="p-4 text-sm font-bold text-teal-300 leading-relaxed whitespace-pre-wrap">
                  {cmdRes}
                </pre>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
