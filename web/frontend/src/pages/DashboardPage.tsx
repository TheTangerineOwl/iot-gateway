import { Navigate } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import { getGatewayStatus, getGatewayConfig } from '../api/client';
import Spinner from '../components/Spinner';
import ErrorBox from '../components/ErrorBox';

// ─── Stat card ────────────────────────────────────────────────────────────────
function StatCard({
  label,
  value,
  accent = 'blue',
}: {
  label: string;
  value: string | number | undefined;
  accent?: 'blue' | 'teal' | 'orange' | 'slate';
}) {
  const accentMap = {
    blue:   'border-blue-500 bg-blue-50 text-blue-600',
    teal:   'border-teal-500 bg-teal-50 text-teal-600',
    orange: 'border-orange-500 bg-orange-50 text-orange-600',
    slate:  'border-slate-500 bg-slate-50 text-slate-600',
  };
  return (
    <div className={`rounded-xl border-2 p-5 ${accentMap[accent]}`}>
      <div className="flex items-center gap-3 mb-2">
        <span className="text-sm font-bold uppercase tracking-wide opacity-70">{label}</span>
      </div>
      <p className="text-3xl font-black">{value ?? '—'}</p>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h2 className="mb-4 text-xl font-black text-gray-800 border-b-2 border-gray-200 pb-2">{title}</h2>
      {children}
    </section>
  );
}

// ─── DashboardPage ────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { data: status, loading: sl, error: se, unauthorized: su, refetch: sr } = useFetch(() => getGatewayStatus(), []);
  const { data: config, loading: cl, error: ce, unauthorized: cu, refetch: cr } = useFetch(() => getGatewayConfig(), []);

  if (su || cu) return <Navigate to="/login" replace />;

  const loading = sl || cl;

  function fmtUptime(s?: number) {
    if (s == null) return undefined;
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = Math.floor(s % 60);
    return `${h}ч ${m}м ${sec}с`;
  }

  return (
    <div className="flex flex-col gap-10">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-black text-gray-900">Статус шлюза</h1>
        <button
          onClick={() => { sr(); cr(); }}
          className="flex items-center gap-2 rounded-lg border-2 border-blue-600 px-4 py-2 text-sm font-bold text-blue-700 hover:bg-blue-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 transition-colors"
        >
          ↺ Обновить
        </button>
      </div>

      {loading && <Spinner label="Загрузка…" />}
      {se && <ErrorBox message={se} onRetry={sr} />}
      {ce && <ErrorBox message={ce} onRetry={cr} />}

      {status && (
        <>
          <Section title="Общие сведения">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <StatCard label="Имя" value={status.general?.name} accent="blue" />
              <StatCard label="Статус" value={status.general?.running ? 'Работает' : 'Остановлен'} accent={status.general?.running ? 'teal' : 'orange'} />
              <StatCard label="Аптайм" value={fmtUptime(status.uptime)} accent="slate" />
              <StatCard label="Устройств" value={status.devices?.total} accent="blue" />
            </div>
          </Section>

          {status.adapters && Object.keys(status.adapters).length > 0 && (
            <Section title="Адаптеры">
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {Object.entries(status.adapters).map(([name, a]) => (
                  <div
                    key={name}
                    className="flex items-start justify-between rounded-xl border-2 border-gray-200 bg-white p-4"
                  >
                    <div>
                      <p className="text-base font-black text-gray-900">{name}</p>
                      <p className="text-sm font-semibold text-gray-500">{a.protocol ?? '—'}</p>
                      {a.broker && (
                        <p className="mt-1 text-xs font-mono font-semibold text-gray-500">{a.broker}</p>
                      )}
                    </div>
                    <div className="text-right">
                      <span
                        className={[
                          'inline-block rounded-full px-3 py-1 text-xs font-black',
                          (a.running || a.connected)
                            ? 'bg-teal-100 text-teal-800 border border-teal-400'
                            : 'bg-orange-100 text-orange-800 border border-orange-400',
                        ].join(' ')}
                      >
                        {(a.running || a.connected) ? '● Активен' : '○ Стоп'}
                      </span>
                      {a.connections != null && (
                        <p className="mt-2 text-sm font-bold text-gray-600">
                          {a.connections} соедин.
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {status.bus && (
            <Section title="Шина сообщений">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
                <StatCard label="Опубликовано" value={status.bus.published} accent="blue" />
                <StatCard label="Доставлено"   value={status.bus.delivered} accent="teal" />
                <StatCard label="Ошибки"        value={status.bus.errors} accent="orange" />
                <StatCard label="Очередь"       value={status.bus.queue_size != null ? `${status.bus.queue_size} / ${status.bus.max_queue ?? '?'}` : undefined} accent="slate" />
                <StatCard label="Подписчики"    value={status.bus.subscribers} accent="slate" />
              </div>
            </Section>
          )}

          {status.pipeline && (
            <Section title="Пайплайн">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <StatCard label="Стадий"       value={status.pipeline.stages} accent="blue" />
                <StatCard label="Обработано"   value={status.pipeline.processed} accent="teal" />
                <StatCard label="Отфильтровано" value={status.pipeline.filtered} accent="slate" />
                <StatCard label="Ошибки"        value={status.pipeline.errors} accent="orange" />
              </div>
            </Section>
          )}
        </>
      )}

      {config && (
        <Section title="Конфигурация">
          <div className="rounded-xl border-2 border-gray-300 bg-gray-900 overflow-auto max-h-96">
            <pre className="p-5 text-sm font-semibold text-gray-100 leading-relaxed whitespace-pre-wrap">
              {JSON.stringify(config, null, 2)}
            </pre>
          </div>
        </Section>
      )}
    </div>
  );
}
