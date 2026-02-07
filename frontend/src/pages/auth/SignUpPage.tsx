import { useState, type FormEvent } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PasswordStrengthIndicator } from '../../components/auth/PasswordStrengthIndicator';
import { SocialLoginButtons } from '../../components/auth/SocialLoginButtons';

export function SignUpPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { signUp, isLoading, error, clearError } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [displayName, setDisplayName] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (password !== confirmPassword) {
      return;
    }
    try {
      // birthdate は年齢確認ページ (AgeVerificationPage) で入力済み
      // サインアップフロー: /signup/age → /signup/terms → /signup
      // location.state 経由で birthdate を受け取る
      const birthdate = (location.state as { birthdate?: string })?.birthdate || '';
      await signUp(email, password, displayName, birthdate);
      navigate('/signup/confirm', { state: { email } });
    } catch {
      // error is set in store
    }
  };

  const passwordMismatch = confirmPassword && password !== confirmPassword;

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <h2 style={{ textAlign: 'center', marginBottom: 24 }}>新規登録</h2>

      {error && (
        <div style={{ background: '#ffebee', color: '#c62828', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {error}
          <button onClick={clearError} style={{ float: 'right', border: 'none', background: 'none', cursor: 'pointer', color: '#c62828' }}>✕</button>
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>表示名</label>
          <input
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            maxLength={50}
            style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>メールアドレス</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>パスワード（8文字以上、英大小+数字）</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }}
          />
          <PasswordStrengthIndicator password={password} />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>パスワード（確認）</label>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            style={{
              width: '100%', padding: 12,
              border: `1px solid ${passwordMismatch ? '#e53935' : '#ddd'}`,
              borderRadius: 8, fontSize: 16, boxSizing: 'border-box',
            }}
          />
          {passwordMismatch && (
            <span style={{ fontSize: 12, color: '#e53935' }}>パスワードが一致しません</span>
          )}
        </div>

        <button
          type="submit"
          disabled={isLoading || !!passwordMismatch}
          style={{
            padding: 14,
            background: isLoading ? '#ccc' : '#1a73e8',
            color: 'white',
            border: 'none',
            borderRadius: 8,
            fontSize: 16,
            fontWeight: 600,
            cursor: isLoading ? 'default' : 'pointer',
          }}
        >
          {isLoading ? '登録中...' : '新規登録'}
        </button>
      </form>

      <div style={{ textAlign: 'center', margin: '24px 0 16px', color: '#999', fontSize: 13 }}>
        または
      </div>

      <SocialLoginButtons label="登録" />

      <div style={{ textAlign: 'center', marginTop: 24, fontSize: 14 }}>
        既にアカウントをお持ちの方は{' '}
        <Link to="/login" style={{ color: '#1a73e8', fontWeight: 600 }}>
          ログイン
        </Link>
      </div>
    </div>
  );
}
