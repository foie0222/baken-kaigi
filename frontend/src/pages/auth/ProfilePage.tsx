import { useState, useMemo, type FormEvent } from 'react';
import { useAuthStore } from '../../stores/authStore';

export function ProfilePage() {
  const { user, isLoading } = useAuthStore();
  const initialDisplayName = useMemo(() => user?.displayName || '', [user]);
  const [displayName, setDisplayName] = useState(initialDisplayName);
  const [saved, setSaved] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    // TODO: API call to update profile (未実装)
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <h2 style={{ textAlign: 'center', marginBottom: 24 }}>プロフィール</h2>

      {saved && (
        <div style={{ background: '#fff3e0', color: '#e65100', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          プロフィール更新機能は現在準備中です
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>表示名</label>
          <input type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)}
            maxLength={50}
            style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }} />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>メールアドレス</label>
          <input type="email" value={user?.email || ''} disabled
            style={{ width: '100%', padding: 12, border: '1px solid #eee', borderRadius: 8, fontSize: 16, background: '#f5f5f5', color: '#999', boxSizing: 'border-box' }} />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>生年月日</label>
          <input type="text" value="変更できません" disabled
            style={{ width: '100%', padding: 12, border: '1px solid #eee', borderRadius: 8, fontSize: 16, background: '#f5f5f5', color: '#999', boxSizing: 'border-box' }} />
        </div>

        <button type="submit" disabled={isLoading}
          style={{ padding: 14, background: '#1a73e8', color: 'white', border: 'none', borderRadius: 8, fontSize: 16, fontWeight: 600, cursor: 'pointer' }}>
          保存
        </button>
      </form>
    </div>
  );
}
