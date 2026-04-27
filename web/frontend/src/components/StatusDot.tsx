interface Props {
  active?: boolean;
}

/**
 * Colorblind-safe status indicator:
 * - Uses both colour AND shape/symbol so it is never colour-only.
 * - Active:   teal filled circle  ●  (#008B8B)
 * - Inactive: orange outline circle ○ (#E87722)
 */
export default function StatusDot({ active }: Props) {
  return (
    <span
      aria-label={active ? 'Онлайн' : 'Оффлайн'}
      title={active ? 'Онлайн' : 'Оффлайн'}
      className={[
        'inline-block h-3 w-3 rounded-full border-2 flex-shrink-0',
        active
          ? 'bg-teal-600 border-teal-700'          // teal fill
          : 'bg-transparent border-orange-500',    // orange outline
      ].join(' ')}
    />
  );
}
