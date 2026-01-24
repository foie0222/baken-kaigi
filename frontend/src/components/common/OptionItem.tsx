import type { ReactNode } from 'react';
import './OptionItem.css';

interface OptionItemProps {
  title: string;
  description: string;
  selected: boolean;
  disabled?: boolean;
  badge?: string;
  onClick: () => void;
}

export function OptionItem({
  title,
  description,
  selected,
  disabled = false,
  badge,
  onClick,
}: OptionItemProps) {
  return (
    <button
      type="button"
      className={`option-item ${selected ? 'selected' : ''} ${disabled ? 'disabled' : ''}`}
      onClick={onClick}
      disabled={disabled}
      aria-pressed={selected}
    >
      <div className="option-check">✓</div>
      <div className="option-info">
        <div className="option-title">{title}</div>
        <div className="option-desc">{description}</div>
      </div>
      {badge && <span className="option-badge">{badge}</span>}
    </button>
  );
}

interface OptionSectionProps {
  title: string;
  children: ReactNode;
}

export function OptionSection({ title, children }: OptionSectionProps) {
  return (
    <div className="option-section">
      <div className="option-section-title">{title}</div>
      {children}
    </div>
  );
}
