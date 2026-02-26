interface Props {
  position: number | undefined;
}

export function FinishPositionBadge({ position }: Props) {
  if (position == null) {
    return <span className="no-data">-</span>;
  }
  const badgeClass = position >= 1 && position <= 3 ? `finish-${position}` : '';
  return (
    <span className={`finish-badge ${badgeClass}`.trim()}>
      {position}
    </span>
  );
}
