interface Props {
  label?: string;
}

export default function Spinner({ label }: Props) {
  return (
    <div className="flex items-center gap-2 text-xs text-gray-400">
      <svg
        className="animate-spin h-4 w-4 text-blue-500"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8v8z"
        />
      </svg>
      {label && <span>{label}</span>}
    </div>
  );
}
