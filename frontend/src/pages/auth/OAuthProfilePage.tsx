import { useState, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';

export function OAuthProfilePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const birthdate = (location.state as { birthdate?: string })?.birthdate || '';
  const updateProfile = useAuthStore((state) => state.updateProfile);
  const error = useAuthStore((state) => state.error);
  const isLoading = useAuthStore((state) => state.isLoading);

  const [displayName, setDisplayName] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!displayName.trim()) return;
    await updateProfile(displayName.trim(), birthdate);
    navigate('/', { replace: true });
  };

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <h2 style={{ textAlign: 'center', marginBottom: 24 }}>プロフィール設定</h2>

      <p style={{ textAlign: 'center', color: '#666', marginBottom: 24, fontSize: 14 }}>
        表示名を設定してください。
      </p>

      {error && (
        <div style={{ background: '#ffebee', color: '#c62828', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>表示名</label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="ニックネームを入力"
            maxLength={20}
            style={{
              width: '100%',
              padding: 12,
              border: '1px solid #ddd',
              borderRadius: 8,
              fontSize: 16,
              boxSizing: 'border-box',
            }}
          />
        </div>

        <button
          type="submit"
          disabled={!displayName.trim() || isLoading}
          style={{
            padding: 14,
            background: displayName.trim() && !isLoading ? '#1a73e8' : '#ccc',
            color: 'white',
            border: 'none',
            borderRadius: 8,
            fontSize: 16,
            fontWeight: 600,
            cursor: displayName.trim() && !isLoading ? 'pointer' : 'default',
          }}
        >
          {isLoading ? '設定中...' : '設定完了'}
        </button>
      </form>
    </div>
  );
}
