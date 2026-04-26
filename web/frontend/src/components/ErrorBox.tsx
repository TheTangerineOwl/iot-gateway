interface Props {
  message: string;
  onRetry?: () => void;
}

export default function ErrorBox({ message, onRetry }: Props) {
  return (
    <div className="border border-red-300 bg-red-50 text-red-700 rounded px-3 py-2 text-xs flex items-start gap-3">
      <span className="flex-1">{message}</span>
      {onRetry && (
        <button onClick={onRetry} className="underline shrink-0 hover:text-red-900">
          Повторить
        </button>
      )}
    </div>
  );
}
