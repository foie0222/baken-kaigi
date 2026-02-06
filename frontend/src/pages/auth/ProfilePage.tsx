import { useState, useEffect, type FormEvent } from 'react';
import { useAuthStore } from '../../stores/authStore';

export function ProfilePage() {
  const { user, isLoading } = useAuthStore();
  const [displayName, setDisplayName] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (user?.displayName) {
      setDisplayName(user.displayName);
    }
  }, [user]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    // API call to update profile would go here
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <h2 style={{ textAlign: 'center', marginBottom: 24 }}>プロフィール</h2>

      {saved && (
        <div style={{ background: '#e8f5e9', color: '#2e7d32', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          プロフィールを更新しました
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
