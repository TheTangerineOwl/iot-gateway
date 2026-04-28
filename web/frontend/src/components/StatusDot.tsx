interface Props {
  active: boolean;
  label?: string;
}

export default function StatusDot({ active, label }: Props) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        className={[
          'inline-block h-2.5 w-2.5 rounded-full',
          active ? 'bg-teal-500' : 'bg-gray-400',
        ].join(' ')}
        aria-hidden
      />
      {label && (
        <span className={`text-xs font-semibold ${active ? 'text-teal-700' : 'text-gray-500'}`}>
          {label}
        </span>
      )}
    </span>
  );
}
