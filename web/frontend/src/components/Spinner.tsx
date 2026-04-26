export default function Spinner({ label = 'Загрузка…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-gray-400 py-4">
      <span className="animate-spin border-2 border-gray-300 border-t-gray-600 rounded-full w-4 h-4 inline-block" />
      <span>{label}</span>
    </div>
  );
}
