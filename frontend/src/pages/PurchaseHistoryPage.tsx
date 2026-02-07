import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { usePurchaseStore } from '../stores/purchaseStore';

const statusConfig: Record<string, { label: string; color: string; bg: string }> = {
  COMPLETED: { label: '完了', color: '#2e7d32', bg: '#e8f5e9' },
  FAILED: { label: '失敗', color: '#c62828', bg: '#fce4ec' },
  PENDING: { label: '処理待ち', color: '#666', bg: '#f5f5f5' },
  SUBMITTED: { label: '送信済み', color: '#666', bg: '#f5f5f5' },
};

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  const month = (d.getMonth() + 1).toString().padStart(2, '0');
  const day = d.getDate().toString().padStart(2, '0');
  const hours = d.getHours().toString().padStart(2, '0');
  const minutes = d.getMinutes().toString().padStart(2, '0');
  return `${month}/${day} ${hours}:${minutes}`;
}

export function PurchaseHistoryPage() {
  const navigate = useNavigate();
  const { history, isLoading, error, fetchHistory } = usePurchaseStore();

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <button className="back-btn" onClick={() => navigate('/')}>
        ← レース一覧に戻る
      </button>

      <h2 style={{ textAlign: 'center', marginBottom: 24 }}>購入履歴</h2>

      {error && (
        <div style={{ background: '#fce4ec', color: '#c62828', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {error}
        </div>
      )}

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <p>読み込み中...</p>
        </div>
      ) : history.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
          <p style={{ fontSize: 16 }}>購入履歴はありません</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {history.map((order) => {
            const config = statusConfig[order.status] || statusConfig.PENDING;
            return (
              <div
                key={order.purchaseId}
                style={{
                  background: 'white',
                  borderRadius: 12,
                  padding: 16,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                  <span style={{ fontSize: 13, color: '#666' }}>{formatDate(order.createdAt)}</span>
                  <span style={{
                    fontSize: 12,
                    color: config.color,
                    background: config.bg,
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontWeight: 600,
                  }}>
                    {config.label}
                  </span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: 14 }}>{order.betLineCount}点</span>
                  <span style={{ fontSize: 16, fontWeight: 600 }}>¥{order.totalAmount.toLocaleString()}</span>
                </div>
                {order.errorMessage && (
                  <p style={{ fontSize: 12, color: '#c62828', marginTop: 4 }}>{order.errorMessage}</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
