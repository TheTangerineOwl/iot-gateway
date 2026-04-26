interface Props {
  ok?: boolean | null;
  size?: 'sm' | 'md';
}

export default function StatusDot({ ok, size = 'sm' }: Props) {
  const sz = size === 'sm' ? 'w-2 h-2' : 'w-3 h-3';
  const color =
    ok == null ? 'bg-gray-300' : ok ? 'bg-green-500' : 'bg-red-500';
  return <span className={`inline-block rounded-full ${sz} ${color} shrink-0`} />;
}
