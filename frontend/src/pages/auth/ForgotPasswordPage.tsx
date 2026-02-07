import { useState, type FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';

export function ForgotPasswordPage() {
  const navigate = useNavigate();
  const { forgotPassword, isLoading, error, clearError } = useAuthStore();
  const [email, setEmail] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await forgotPassword(email);
      navigate('/reset-password', { state: { email } });
    } catch {
      // error is set in store
    }
  };

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <h2 style={{ textAlign: 'center', marginBottom: 24 }}>パスワードリセット</h2>

      <p style={{ textAlign: 'center', color: '#666', marginBottom: 24, fontSize: 14 }}>
        登録済みのメールアドレスを入力してください。
        <br />
        パスワードリセット用のコードを送信します。
      </p>

      {error && (
        <div style={{ background: '#ffebee', color: '#c62828', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {error}
          <button onClick={clearError} style={{ float: 'right', border: 'none', background: 'none', cursor: 'pointer', color: '#c62828' }}>✕</button>
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>メールアドレス</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required
            style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }} />
        </div>
        <button type="submit" disabled={isLoading}
          style={{ padding: 14, background: isLoading ? '#ccc' : '#1a73e8', color: 'white', border: 'none', borderRadius: 8, fontSize: 16, fontWeight: 600, cursor: isLoading ? 'default' : 'pointer' }}>
          {isLoading ? '送信中...' : 'リセットコードを送信'}
        </button>
      </form>

      <div style={{ textAlign: 'center', marginTop: 24 }}>
        <Link to="/login" style={{ color: '#1a73e8', fontSize: 14 }}>ログインに戻る</Link>
      </div>
    </div>
  );
}
