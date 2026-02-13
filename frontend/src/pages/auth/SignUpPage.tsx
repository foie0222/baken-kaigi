import { useState, type FormEvent } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { PasswordStrengthIndicator } from '../../components/auth/PasswordStrengthIndicator';
import { SocialLoginButtons } from '../../components/auth/SocialLoginButtons';
import { EMAIL_REGEX } from '../../utils/validation';

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

  const isValidEmail = EMAIL_REGEX.test(email);
  const passwordMismatch = confirmPassword && password !== confirmPassword;
  const canSubmit = displayName.length > 0 && isValidEmail && password.length >= 8 && confirmPassword.length > 0 && !passwordMismatch && !isLoading;

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <h2 style={{ textAlign: 'center', marginBottom: 24 }}>新規登録</h2>

      {error && (
        <div style={{ background: '#ffebee', color: '#c62828', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {error}
          <button onClick={clearError} style={{ float: 'right', border: 'none', background: 'none', cursor: 'pointer', color: '#c62828' }}>✕</button>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <label htmlFor="signup-displayname" style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>表示名</label>
          <input
            id="signup-displayname"
            type="text"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            maxLength={50}
            style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }}
          />
        </div>

        <div>
          <label htmlFor="signup-email" style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>メールアドレス</label>
          <input
            id="signup-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }}
            placeholder="example@email.com"
          />
        </div>

        <div>
          <label htmlFor="signup-password" style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>パスワード（8文字以上、英大小+数字）</label>
          <input
            id="signup-password"
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
          <label htmlFor="signup-confirm-password" style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>パスワード（確認）</label>
          <input
            id="signup-confirm-password"
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
          disabled={!canSubmit}
          style={{
            padding: 14,
            background: !canSubmit ? '#ccc' : '#1a73e8',
            color: 'white',
            border: 'none',
            borderRadius: 8,
            fontSize: 16,
            fontWeight: 600,
            cursor: !canSubmit ? 'default' : 'pointer',
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
