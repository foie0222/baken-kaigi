import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PasswordStrengthIndicator } from '../../components/auth/PasswordStrengthIndicator';

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const email = (location.state as { email?: string })?.email || '';
  const { confirmResetPassword, isLoading, error, clearError } = useAuthStore();
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');

  // emailがない場合はパスワードリセット要求画面にリダイレクト
  useEffect(() => {
    if (!email) {
      navigate('/forgot-password', { replace: true });
    }
  }, [email, navigate]);

  if (!email) {
    return null;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await confirmResetPassword(email, code, newPassword);
      navigate('/login', { state: { message: 'パスワードがリセットされました。新しいパスワードでログインしてください。' } });
    } catch {
      // error is set in store
    }
  };

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <h2 style={{ textAlign: 'center', marginBottom: 24 }}>新しいパスワード</h2>

      {error && (
        <div style={{ background: '#ffebee', color: '#c62828', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {error}
          <button onClick={clearError} style={{ float: 'right', border: 'none', background: 'none', cursor: 'pointer', color: '#c62828' }}>✕</button>
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>確認コード</label>
          <input type="text" value={code} onChange={(e) => setCode(e.target.value)} required maxLength={6}
            style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 24, textAlign: 'center', letterSpacing: 8, boxSizing: 'border-box' }} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>新しいパスワード</label>
          <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} required minLength={8}
            style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }} />
          <PasswordStrengthIndicator password={newPassword} />
        </div>
        <button type="submit" disabled={isLoading}
          style={{ padding: 14, background: isLoading ? '#ccc' : '#1a73e8', color: 'white', border: 'none', borderRadius: 8, fontSize: 16, fontWeight: 600, cursor: isLoading ? 'default' : 'pointer' }}>
          {isLoading ? 'リセット中...' : 'パスワードをリセット'}
        </button>
      </form>
    </div>
  );
}
