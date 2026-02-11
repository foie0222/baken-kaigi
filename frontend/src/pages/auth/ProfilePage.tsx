import { useState, useMemo, type FormEvent } from 'react';
import { useAuthStore } from '../../stores/authStore';
import { useAppStore } from '../../stores/appStore';

export function ProfilePage() {
  const { user, isLoading, updateProfile, error, clearError } = useAuthStore();
  const showToast = useAppStore((state) => state.showToast);
  const initialDisplayName = useMemo(() => user?.displayName || '', [user]);
  const [displayName, setDisplayName] = useState(initialDisplayName);
  const [isSaving, setIsSaving] = useState(false);

  const hasChanges = displayName !== initialDisplayName;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!hasChanges || isSaving) return;

    clearError();
    setIsSaving(true);
    try {
      await updateProfile(displayName);
      showToast('プロフィールを更新しました');
    } catch {
      showToast('プロフィールの更新に失敗しました', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <h2 style={{ textAlign: 'center', marginBottom: 24 }}>プロフィール</h2>

      {error && (
        <div style={{ background: '#ffebee', color: '#c62828', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {error}
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

        <button type="submit" disabled={isLoading || isSaving || !hasChanges}
          style={{
            padding: 14,
            background: hasChanges && !isSaving ? '#1a73e8' : '#ccc',
            color: 'white', border: 'none', borderRadius: 8, fontSize: 16, fontWeight: 600,
            cursor: hasChanges && !isSaving ? 'pointer' : 'default',
          }}>
          {isSaving ? '保存中...' : '保存'}
        </button>
      </form>
    </div>
  );
}
