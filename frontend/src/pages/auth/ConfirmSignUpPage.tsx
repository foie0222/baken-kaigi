import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';

export function ConfirmSignUpPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const email = (location.state as { email?: string })?.email || '';
  const { confirmSignUp, isLoading, error, clearError } = useAuthStore();
  const [code, setCode] = useState('');

  // emailがない場合はサインアップ画面にリダイレクト
  useEffect(() => {
    if (!email) {
      navigate('/signup/age', { replace: true });
    }
  }, [email, navigate]);

  if (!email) {
    return null;
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await confirmSignUp(email, code);
      navigate('/login', { state: { message: 'メール確認が完了しました。ログインしてください。' } });
    } catch {
      // error is set in store
    }
  };

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <h2 style={{ textAlign: 'center', marginBottom: 24 }}>メール確認</h2>

      <p style={{ textAlign: 'center', color: '#666', marginBottom: 24, fontSize: 14 }}>
        {email} に確認コードを送信しました。
        <br />
        メールに記載されたコードを入力してください。
      </p>

      {error && (
        <div style={{ background: '#ffebee', color: '#c62828', padding: 12, borderRadius: 8, marginBottom: 16, fontSize: 14 }}>
          {error}
          <button onClick={clearError} style={{ float: 'right', border: 'none', background: 'none', cursor: 'pointer', color: '#c62828' }}>✕</button>
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <div>
          <label style={{ display: 'block', fontSize: 14, marginBottom: 4, color: '#666' }}>確認コード</label>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
            maxLength={6}
            style={{ width: '100%', padding: 12, border: '1px solid #ddd', borderRadius: 8, fontSize: 24, textAlign: 'center', letterSpacing: 8, boxSizing: 'border-box' }}
            placeholder="000000"
          />
        </div>

        <button
          type="submit"
          disabled={isLoading || code.length < 6}
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
          {isLoading ? '確認中...' : '確認'}
        </button>
      </form>
    </div>
  );
}
