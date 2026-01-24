import { useNavigate } from 'react-router-dom';
import { useCartStore } from '../stores/cartStore';
import { BetTypeLabels, getVenueName } from '../types';

export function CartPage() {
  const navigate = useNavigate();
  const { items, removeItem, clearCart, getTotalAmount } = useCartStore();
  const totalAmount = getTotalAmount();

  const handleClearCart = () => {
    if (window.confirm('カートの中身をすべて削除しますか？')) {
      clearCart();
    }
  };

  const handleConsult = () => {
    navigate('/consultation');
  };

  return (
    <div className="fade-in">
      <button className="back-btn" onClick={() => navigate('/')}>
        ← レース一覧に戻る
      </button>

      <div className="cart-container">
        <div className="cart-header">
          <h3>🛒 カート</h3>
          {items.length > 0 && (
            <button className="cart-clear-btn" onClick={handleClearCart}>
              すべて削除
            </button>
          )}
        </div>

        {items.length === 0 ? (
          <div className="cart-empty">
            <div className="cart-empty-icon">🛒</div>
            <p>カートに馬券がありません</p>
            <p style={{ fontSize: 12, marginTop: 8 }}>
              レースを選んで買い目を追加しましょう
            </p>
          </div>
        ) : (
          <>
            {items.map((item) => (
              <div key={item.id} className="cart-item">
                <div className="cart-item-info">
                  <div className="cart-item-race">
                    {getVenueName(item.raceVenue)} {item.raceNumber} {item.raceName}
                  </div>
                  <div className="cart-item-bet">
                    <span className="cart-item-bet-type">{BetTypeLabels[item.betType]}</span>
                    <span className="cart-item-bet-display">
                      {item.betDisplay || item.horseNumbers.join('-')}
                    </span>
                    {item.betCount && item.betCount > 1 && (
                      <span className="cart-item-bet-count">{item.betCount}点</span>
                    )}
                  </div>
                  <div className="cart-item-amount">
                    ¥{item.amount.toLocaleString()}
                  </div>
                </div>
                <button
                  className="cart-item-delete"
                  onClick={() => removeItem(item.id)}
                >
                  ×
                </button>
              </div>
            ))}

            <div className="cart-summary">
              <div className="cart-summary-row">
                <span>買い目数</span>
                <span>{items.length}点</span>
              </div>
              <div className="cart-summary-row total">
                <span>合計金額</span>
                <span>¥{totalAmount.toLocaleString()}</span>
              </div>
            </div>
          </>
        )}
      </div>

      {items.length > 0 ? (
        <>
          <button className="add-more-btn" onClick={() => navigate('/')}>
            ＋ 別のレースの買い目を追加
          </button>
          <button className="ai-consult-btn" onClick={handleConsult}>
            🤖 まとめてAIに相談する
          </button>
        </>
      ) : (
        <button
          className="btn-primary"
          style={{ width: '100%' }}
          onClick={() => navigate('/')}
        >
          レースを選ぶ
        </button>
      )}
    </div>
  );
}
