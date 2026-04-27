interface Props {
  message: string;
  onRetry?: () => void;
}

export default function ErrorBox({ message, onRetry }: Props) {
  return (
    <div className="rounded-xl border-2 border-red-300 bg-red-50 p-4 flex items-start gap-3" role="alert">
      <div className="flex-1">
        <p className="text-sm font-bold text-red-800">{message}</p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="shrink-0 text-xs font-bold text-red-700 border border-red-400 rounded px-2 py-1 hover:bg-red-100 transition-colors"
        >
          Повторить
        </button>
      )}
    </div>
  );
}
