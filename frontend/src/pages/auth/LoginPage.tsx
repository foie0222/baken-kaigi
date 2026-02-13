import { useState, type FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { SocialLoginButtons } from '../../components/auth/SocialLoginButtons';

const EMAIL_REGEX = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;

export function LoginPage() {
  const navigate = useNavigate();
  const { signIn, isLoading, error, clearError } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const isValidEmail = EMAIL_REGEX.test(email);
  const canSubmit = isValidEmail && password.length > 0 && !isLoading;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!canSubmit) return;
    try {
      await signIn(email, password);
      navigate('/');
    } catch {
      // error is set in store
    }
  };

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <h2 style={{ textAlign: 'center', marginBottom: 24 }}>ログイン</h2>

      {error && (
        <div style={{ background: '#ffebee', color: '#c62828', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {error}
          <button onClick={clearError} style={{ float: 'right', border: 'none', background: 'none', cursor: 'pointer', color: '#c62828' }}>✕</button>
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>メールアドレス</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }}
            placeholder="example@email.com"
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>パスワード</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 16, boxSizing: 'border-box' }}
          />
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
          {isLoading ? 'ログイン中...' : 'ログイン'}
        </button>
      </form>

      <div style={{ textAlign: 'center', margin: '16px 0' }}>
        <Link to="/forgot-password" style={{ color: '#1a73e8', fontSize: 14 }}>
          パスワードを忘れた方
        </Link>
      </div>

      <div style={{ textAlign: 'center', margin: '24px 0 16px', color: '#999', fontSize: 13 }}>
        または
      </div>

      <SocialLoginButtons />

      <div style={{ textAlign: 'center', marginTop: 24, fontSize: 14 }}>
        アカウントをお持ちでない方は{' '}
        <Link to="/signup/age" style={{ color: '#1a73e8', fontWeight: 600 }}>
          新規登録
        </Link>
      </div>
    </div>
  );
}
