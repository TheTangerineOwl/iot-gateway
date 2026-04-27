interface Props {
  label?: string;
}

export default function Spinner({ label }: Props) {
  return (
    <div className="flex items-center gap-3 py-4 text-blue-700 font-semibold text-base">
      <svg
        className="animate-spin h-6 w-6 text-blue-700"
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          className="opacity-25"
          cx="12" cy="12" r="10"
          stroke="currentColor"
          strokeWidth="4"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
        />
      </svg>
      {label && <span>{label}</span>}
    </div>
  );
}
