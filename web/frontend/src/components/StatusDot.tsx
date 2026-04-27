interface Props {
  active?: boolean;
}

export default function StatusDot({ active }: Props) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${active ? 'bg-green-500' : 'bg-gray-300'}`}
    />
  );
}
