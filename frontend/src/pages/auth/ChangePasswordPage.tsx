import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PasswordStrengthIndicator } from '../../components/auth/PasswordStrengthIndicator';

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const { changePassword, isLoading, error, clearError } = useAuthStore();
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) return;
    try {
      await changePassword(oldPassword, newPassword);
      navigate('/settings', { state: { message: 'パスワードを変更しました' } });
    } catch {
      // error is set in store
    }
  };

  const passwordMismatch = confirmPassword && newPassword !== confirmPassword;

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <h2 style={{ textAlign: 'center', marginBottom: 24 }}>パスワード変更</h2>

      {error && (
        <div style={{ background: '#ffebee', color: '#c62828', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {error}
          <button onClick={clearError} style={{ float: 'right', border: 'none', background: 'none', cursor: 'pointer', color: '#c62828' }}>✕</button>
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>現在のパスワード</label>
          <input type="password" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} required
            style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>新しいパスワード</label>
          <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={8}
            style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }} />
          <PasswordStrengthIndicator password={newPassword} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>新しいパスワード（確認）</label>
          <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} required
            style={{
              width: '100%', padding: 12,
              border: `1px solid ${passwordMismatch ? '#e53935' : '#ddd'}`,
              borderRadius: 8, fontSize: 16, boxSizing: 'border-box',
            }} />
          {passwordMismatch && <span style={{ fontSize: 12, color: '#e53935' }}>パスワードが一致しません</span>}
        </div>
        <button type="submit" disabled={isLoading || !!passwordMismatch}
          style={{ padding: 14, background: isLoading ? '#ccc' : '#1a73e8', color: 'white', border: 'none', borderRadius: 8, fontSize: 16, fontWeight: 600, cursor: isLoading ? 'default' : 'pointer' }}>
          {isLoading ? '変更中...' : 'パスワードを変更'}
        </button>
      </form>
    </div>
  );
}
