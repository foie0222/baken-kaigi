import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';

export function DeleteAccountPage() {
  const navigate = useNavigate();
  const { deleteAccount, isLoading, error, clearError } = useAuthStore();
  const [confirmText, setConfirmText] = useState('');
  const [showConfirm, setShowConfirm] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (confirmText !== '削除する') return;
    try {
      await deleteAccount();
      navigate('/');
    } catch {
      // error is set in store
    }
  };

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <h2 style={{ textAlign: 'center', marginBottom: 24, color: '#c62828' }}>アカウント削除</h2>

      <div style={{ background: '#fff3e0', padding: 16, borderRadius: 8, marginBottom: 24, fontSize: 14, lineHeight: 1.6 }}>
        <strong>注意:</strong>
        <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
          <li>アカウント削除をリクエストすると、30日間の保持期間の後に完全に削除されます。</li>
          <li>保持期間中はログインできません。</li>
          <li>30日以内であれば、サポートに連絡して削除をキャンセルできます。</li>
          <li>削除後はすべてのデータが失われます。</li>
        </ul>
      </div>

      {error && (
        <div style={{ background: '#ffebee', color: '#c62828', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {error}
          <button onClick={clearError} style={{ float: 'right', border: 'none', background: 'none', cursor: 'pointer', color: '#c62828' }}>✕</button>
        </div>
      )}

      {!showConfirm ? (
        <button onClick={() => setShowConfirm(true)}
          style={{ width: '100%', padding: 14, background: '#c62828', color: 'white', border: 'none', borderRadius: 8, fontSize: 16, fontWeight: 600, cursor: 'pointer' }}>
          アカウントを削除する
        </button>
      ) : (
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div>
            <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>
              確認のため「削除する」と入力してください
            </label>
            <input type="text" value={confirmText} onChange={(e) => setConfirmText(e.target.value)}
              style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }}
              placeholder="削除する" />
          </div>
          <button type="submit" disabled={isLoading || confirmText !== '削除する'}
            style={{
              padding: 14,
              background: confirmText === '削除する' ? '#c62828' : '#ccc',
              color: 'white', border: 'none', borderRadius: 8, fontSize: 16, fontWeight: 600,
              cursor: confirmText === '削除する' ? 'pointer' : 'default',
            }}>
            {isLoading ? '削除中...' : '完全に削除する'}
          </button>
          <button type="button" onClick={() => setShowConfirm(false)}
            style={{ padding: 14, background: 'white', color: '#666', border: '1px solid #ddd', borderRadius: 8, fontSize: 16, cursor: 'pointer' }}>
            キャンセル
          </button>
        </form>
      )}
    </div>
  );
}
