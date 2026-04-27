interface Props {
  message: string;
  onRetry?: () => void;
}

export default function ErrorBox({ message, onRetry }: Props) {
  return (
    <div
      role="alert"
      className="flex items-start gap-3 rounded-lg border-2 border-red-600 bg-red-50 px-5 py-4"
    >
      {/* Warning icon — shape-coded, not just colour */}
      <span className="mt-0.5 text-2xl leading-none select-none" aria-hidden>⚠</span>
      <div className="flex-1">
        <p className="text-base font-bold text-red-800">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-2 inline-flex items-center gap-1 rounded border-2 border-red-700 bg-red-700 px-3 py-1 text-sm font-bold text-white hover:bg-red-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500 focus-visible:ring-offset-2"
          >
            ↺ Повторить
          </button>
        )}
      </div>
    </div>
  );
}
