interface Props {
  label?: string;
}

export default function Spinner({ label }: Props) {
  return (
    <div className="flex items-center gap-2 text-xs text-gray-400 py-2">
      <div className="w-3 h-3 border border-gray-300 border-t-gray-600 rounded-full animate-spin" />
      {label && <span>{label}</span>}
    </div>
  );
}
