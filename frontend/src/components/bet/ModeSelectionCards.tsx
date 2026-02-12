import './ModeSelectionCards.css';

interface ModeSelectionCardsProps {
  onSelectAi: () => void;
  onSelectManual: () => void;
}

export function ModeSelectionCards({ onSelectAi, onSelectManual }: ModeSelectionCardsProps) {
  return (
    <div className="mode-selection-cards">
      <button className="mode-card mode-card-ai" onClick={onSelectAi}>
        <div className="mode-card-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z" />
            <line x1="9" y1="21" x2="15" y2="21" />
          </svg>
        </div>
        <div className="mode-card-text">
          <span className="mode-card-title">AIにおまかせ</span>
          <span className="mode-card-desc">予算と好みを伝えてAIに買い目を提案してもらう</span>
        </div>
        <span className="mode-card-arrow">→</span>
      </button>

      <button className="mode-card mode-card-manual" onClick={onSelectManual}>
        <div className="mode-card-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
          </svg>
        </div>
        <div className="mode-card-text">
          <span className="mode-card-title">自分で選ぶ</span>
          <span className="mode-card-desc">券種・馬・金額を自分で組み立てる</span>
        </div>
        <span className="mode-card-arrow">→</span>
      </button>
    </div>
  );
}
