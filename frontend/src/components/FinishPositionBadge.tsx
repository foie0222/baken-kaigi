const PODIUM_MAX = 3;

interface Props {
  position: number | null | undefined;
}

export function FinishPositionBadge({ position }: Props) {
  if (position == null) {
    return <span className="no-data">-</span>;
  }
  const badgeClass = position >= 1 && position <= PODIUM_MAX ? `finish-${position}` : '';
  return (
    <span className={`finish-badge ${badgeClass}`.trim()}>
      {position}
    </span>
  );
}
