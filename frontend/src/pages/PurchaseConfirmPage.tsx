import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCartStore } from '../stores/cartStore';
import { usePurchaseStore } from '../stores/purchaseStore';
import { ConfirmModal } from '../components/common/ConfirmModal';
import { BetTypeLabels, getVenueName } from '../types';

export function PurchaseConfirmPage() {
  const navigate = useNavigate();
  const { cartId, items, getTotalAmount, clearCart } = useCartStore();
  const { balance, purchaseResult, isLoading, error, submitPurchase, fetchBalance, clearError, clearResult } = usePurchaseStore();
  const totalAmount = getTotalAmount();

  const [showConfirmModal, setShowConfirmModal] = useState(false);

  useEffect(() => {
    fetchBalance();
    return () => {
      clearError();
      clearResult();
    };
  }, [fetchBalance, clearError, clearResult]);

  // カートが空の場合はカートページへ
  if (items.length === 0 && !purchaseResult) {
    return (
      <div className="fade-in" style={{ padding: 16, textAlign: 'center' }}>
        <p style={{ marginBottom: 16 }}>カートが空です</p>
        <button
          className="btn-primary"
          style={{ width: '100%' }}
          onClick={() => navigate('/cart')}
        >
          カートに戻る
        </button>
      </div>
    );
  }

  // レース情報をカートアイテムから取得
  const firstItem = items[0];
  const raceDate = firstItem?.raceId?.slice(0, 8) || '';
  const courseCode = firstItem?.raceVenue || '';
  const raceNumber = parseInt(firstItem?.raceNumber?.replace('R', '') || '0', 10);

  const handlePurchase = async () => {
    setShowConfirmModal(false);
    await submitPurchase(cartId, raceDate, courseCode, raceNumber);
    // 成功時のみカートをクリア（purchaseResultがnullの場合はエラーなのでクリアしない）
    const result = usePurchaseStore.getState().purchaseResult;
    if (result && result.status !== 'FAILED') {
      clearCart();
    }
  };

  // 購入結果表示
  if (purchaseResult) {
    const isSuccess = purchaseResult.status !== 'FAILED';
    return (
      <div className="fade-in" style={{ padding: 16 }}>
        <div style={{
          background: 'white',
          borderRadius: 12,
          padding: 24,
          textAlign: 'center',
        }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>
            {isSuccess ? '\u2705' : '\u274C'}
          </div>
          <h2 style={{ marginBottom: 8 }}>
            {isSuccess ? '購入が完了しました' : '購入に失敗しました'}
          </h2>
          <p style={{ color: '#666', fontSize: 14, marginBottom: 16 }}>
            合計金額: ¥{purchaseResult.totalAmount.toLocaleString()}
          </p>
          {!isSuccess && error && (
            <p style={{ color: '#c62828', fontSize: 14, marginBottom: 16 }}>{error}</p>
          )}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <button
              className="btn-primary"
              style={{ width: '100%' }}
              onClick={() => navigate('/purchase/history')}
            >
              購入履歴を見る
            </button>
            <button
              className="btn-primary"
              style={{ width: '100%', background: '#f5f5f5', color: '#333' }}
              onClick={() => navigate('/')}
            >
              レース一覧に戻る
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <button className="back-btn" onClick={() => navigate('/cart')}>
        ← カートに戻る
      </button>

      <h2 style={{ textAlign: 'center', marginBottom: 24 }}>購入確認</h2>

      {error && (
        <div style={{ background: '#fce4ec', color: '#c62828', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {error}
        </div>
      )}

      {/* 残高表示 */}
      <div style={{ background: 'white', borderRadius: 12, padding: 16, marginBottom: 16 }}>
        <div style={{ fontSize: 13, color: '#666', fontWeight: 600, marginBottom: 12 }}>IPAT残高</div>
        {balance ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 14, color: '#666' }}>投票可能残高</span>
              <span style={{ fontSize: 14, fontWeight: 600 }}>¥{balance.betBalance.toLocaleString()}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 14, color: '#666' }}>投票限度額</span>
              <span style={{ fontSize: 14 }}>¥{balance.limitVoteAmount.toLocaleString()}</span>
            </div>
          </div>
        ) : (
          <p style={{ fontSize: 14, color: '#999' }}>
            {isLoading ? '読み込み中...' : '残高を取得できませんでした'}
          </p>
        )}
      </div>

      {/* カート内容 */}
      <div style={{ background: 'white', borderRadius: 12, padding: 16, marginBottom: 16 }}>
        <div style={{ fontSize: 13, color: '#666', fontWeight: 600, marginBottom: 12 }}>購入内容</div>
        {items.map((item) => (
          <div key={item.id} style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
            <div style={{ fontSize: 13, color: '#666' }}>
              {getVenueName(item.raceVenue)} {item.raceNumber} {item.raceName}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
              <span style={{ fontSize: 14 }}>
                {BetTypeLabels[item.betType]} {item.betDisplay || item.horseNumbers.join('-')}
                {item.betCount && item.betCount > 1 && ` (${item.betCount}点)`}
              </span>
              <span style={{ fontSize: 14, fontWeight: 600 }}>¥{item.amount.toLocaleString()}</span>
            </div>
          </div>
        ))}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 12, paddingTop: 12, borderTop: '2px solid #333' }}>
          <span style={{ fontSize: 16, fontWeight: 600 }}>合計</span>
          <span style={{ fontSize: 16, fontWeight: 600 }}>¥{totalAmount.toLocaleString()}</span>
        </div>
      </div>

      {/* 残高不足チェック */}
      {balance && totalAmount > balance.betBalance && (
        <div style={{ background: '#fff3e0', color: '#e65100', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          残高が不足しています。入金してから再度お試しください。
        </div>
      )}

      <button
        className="btn-primary"
        style={{
          width: '100%',
          padding: 14,
          fontSize: 16,
          fontWeight: 600,
          opacity: isLoading ? 0.5 : 1,
        }}
        disabled={isLoading}
        onClick={() => setShowConfirmModal(true)}
      >
        {isLoading ? '処理中...' : '購入する'}
      </button>

      <ConfirmModal
        isOpen={showConfirmModal}
        onClose={() => setShowConfirmModal(false)}
        onConfirm={handlePurchase}
        title="購入確認"
        confirmText="購入する"
      >
        <p>合計 ¥{totalAmount.toLocaleString()} を購入しますか？</p>
        <p style={{ fontSize: 13, color: '#666', marginTop: 8 }}>
          この操作は取り消せません。
        </p>
      </ConfirmModal>
    </div>
  );
}
