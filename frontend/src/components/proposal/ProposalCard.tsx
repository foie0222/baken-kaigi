import type { ProposedBet } from '../../types';
import { BetTypeLabels } from '../../types';

interface ProposalCardProps {
  bet: ProposedBet;
  onAddToCart: () => void;
  isAdded: boolean;
}

const MIN_CONFIRMED_ODDS = 1.0;

export function ProposalCard({ bet, onAddToCart, isAdded }: ProposalCardProps) {
  const isOddsConfirmed = bet.composite_odds >= MIN_CONFIRMED_ODDS;

  return (
    <div className="proposal-card">
      <div className="proposal-card-header">
        <span className="proposal-bet-type">{BetTypeLabels[bet.bet_type]}</span>
      </div>
      <div className="proposal-card-body">
        <div className="proposal-bet-display">{bet.bet_display}</div>
        <div className="proposal-details">
          <span className="proposal-detail-item">
            {bet.bet_count}点 / {bet.amount.toLocaleString()}円
          </span>
          <span className="proposal-detail-item">
            推定オッズ: {isOddsConfirmed ? `${bet.composite_odds.toFixed(1)}倍` : '未確定'}
          </span>
          <span className="proposal-detail-item">
            期待値: {isOddsConfirmed ? bet.expected_value.toFixed(2) : '未確定'}
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
