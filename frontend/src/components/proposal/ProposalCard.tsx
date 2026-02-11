import type { ProposedBet } from '../../types';
import { BetTypeLabels } from '../../types';

interface ProposalCardProps {
  bet: ProposedBet;
  onAddToCart: () => void;
  isAdded: boolean;
}

const confidenceColors: Record<string, string> = {
  high: '#1a5f2a',
  medium: '#f59e0b',
  low: '#9ca3af',
};

const confidenceLabels: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
};

export function ProposalCard({ bet, onAddToCart, isAdded }: ProposalCardProps) {
  const borderColor = confidenceColors[bet.confidence] || '#9ca3af';

  return (
    <div className="proposal-card" style={{ borderLeftColor: borderColor }}>
      <div className="proposal-card-header">
        <span className="proposal-bet-type">{BetTypeLabels[bet.bet_type]}</span>
        <span
          className="proposal-confidence"
          style={{ color: borderColor }}
        >
          信頼度: {confidenceLabels[bet.confidence]}
        </span>
      </div>
      <div className="proposal-card-body">
        <div className="proposal-bet-display">{bet.bet_display}</div>
        <div className="proposal-details">
          <span className="proposal-detail-item">
            {bet.bet_count}点 / {(bet.amount ?? 0).toLocaleString()}円
          </span>
          <span className="proposal-detail-item">
            推定オッズ: {bet.composite_odds != null && bet.composite_odds >= 1.0 ? `${bet.composite_odds.toFixed(1)}倍` : '未確定'}
          </span>
          <span className="proposal-detail-item">
            期待値: {bet.composite_odds != null && bet.composite_odds >= 1.0 ? (bet.expected_value ?? 0).toFixed(2) : '未確定'}
          </span>
        </div>
        <p className="proposal-reasoning">{bet.reasoning}</p>
      </div>
      <button
        className={`proposal-add-btn ${isAdded ? 'added' : ''}`}
        onClick={onAddToCart}
        disabled={isAdded}
      >
        {isAdded ? '追加済み' : 'カートに追加'}
      </button>
    </div>
  );
}
