import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCartStore } from '../stores/cartStore';
import { useAuthStore } from '../stores/authStore';
import { useIpatSettingsStore } from '../stores/ipatSettingsStore';
import { useLossLimitStore } from '../stores/lossLimitStore';
import { BetTypeLabels, getVenueName } from '../types';

export function CartPage() {
  const navigate = useNavigate();
  const { items, removeItem, clearCart, getTotalAmount } = useCartStore();
  const { isAuthenticated } = useAuthStore();
  const { status: ipatStatus, checkStatus: checkIpatStatus } = useIpatSettingsStore();
  const { lossLimit, remainingLossLimit } = useLossLimitStore();
  const totalAmount = getTotalAmount();
  const isLossLimitReached = lossLimit !== null && remainingLossLimit !== null && remainingLossLimit <= 0;

  useEffect(() => {
    if (isAuthenticated) {
      checkIpatStatus();
    }
  }, [isAuthenticated, checkIpatStatus]);

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
          {/* 今月の状況（モック - 将来的にはログイン時のみ表示） */}
          <div className="spending-status" role="region" aria-label="今月の使用状況">
            <div className="spending-status-title">
              <span aria-hidden="true">📊</span>
              <span>今月の状況</span>
            </div>
            <div className="spending-status-row">
              <span>使用済み</span>
              <span>¥0</span>
            </div>
            <div className="spending-status-row">
              <span>今回の購入</span>
              <span>¥{totalAmount.toLocaleString()}</span>
            </div>
            <div className="spending-status-row highlight">
              <span>残り許容負け額</span>
              <span>ログインして設定</span>
            </div>
          </div>

          {isLossLimitReached && (
            <div style={{
              background: '#fef2f2',
              color: '#c62828',
              padding: 12,
              borderRadius: 8,
              marginBottom: 12,
              fontSize: 14,
              fontWeight: 600,
              textAlign: 'center',
            }}>
              月間の負け額限度額に達しているため、購入操作はできません
            </div>
          )}

          <button className="add-more-btn" onClick={() => navigate('/')}>
            ＋ 別のレースの買い目を追加
          </button>
          <button
            className="btn-ai-confirm"
            onClick={handleConsult}
            disabled={isLossLimitReached}
            style={isLossLimitReached ? { opacity: 0.5, cursor: 'not-allowed' } : undefined}
          >
            AIと一緒に確認する →
          </button>
          <p className="ai-guide-text">
            ※ 購入前にAIが買い目を一緒に確認します
          </p>

          {/* IPAT購入ボタン */}
          {isAuthenticated && ipatStatus?.configured && items.length > 0 && (
            <button
              className="btn-primary"
              style={{
                width: '100%',
                marginTop: 12,
                background: isLossLimitReached ? '#9e9e9e' : '#2e7d32',
                cursor: isLossLimitReached ? 'not-allowed' : 'pointer',
              }}
              onClick={() => navigate('/purchase/confirm')}
              disabled={isLossLimitReached}
            >
              IPATで購入する
            </button>
          )}
          {isAuthenticated && !ipatStatus?.configured && (
            <div style={{ textAlign: 'center', marginTop: 12 }}>
              <span style={{ fontSize: 13, color: '#666' }}>IPAT設定が必要です </span>
              <button
                type="button"
                onClick={() => navigate('/settings/ipat')}
                style={{ fontSize: 13, color: '#1a73e8', background: 'none', border: 'none', cursor: 'pointer', textDecoration: 'underline', padding: 0 }}
              >
                設定する
              </button>
            </div>
          )}
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
