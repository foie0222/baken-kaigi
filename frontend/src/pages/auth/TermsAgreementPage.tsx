import { useState, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export function TermsAgreementPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const birthdate = (location.state as { birthdate?: string })?.birthdate || '';
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (termsAccepted && privacyAccepted) {
      navigate('/signup', { state: { birthdate } });
    }
  };

  return (
    <div className="fade-in" style={{ padding: 16 }}>
      <h2 style={{ textAlign: 'center', marginBottom: 24 }}>利用規約への同意</h2>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <label style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: 16, background: 'white', borderRadius: 8, cursor: 'pointer' }}>
          <input type="checkbox" checked={termsAccepted} onChange={(e) => setTermsAccepted(e.target.checked)}
            style={{ marginTop: 2, width: 20, height: 20 }} />
          <span style={{ fontSize: 14 }}>
            <span style={{ color: '#1a73e8', textDecoration: 'underline', cursor: 'default' }}>利用規約</span>
            {' '}に同意します
            <br />
            <span style={{ fontSize: 12, color: '#999' }}>※ 利用規約は準備中です</span>
          </span>
        </label>

        <label style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: 16, background: 'white', borderRadius: 8, cursor: 'pointer' }}>
          <input type="checkbox" checked={privacyAccepted} onChange={(e) => setPrivacyAccepted(e.target.checked)}
            style={{ marginTop: 2, width: 20, height: 20 }} />
          <span style={{ fontSize: 14 }}>
            <span style={{ color: '#1a73e8', textDecoration: 'underline', cursor: 'default' }}>プライバシーポリシー</span>
            {' '}に同意します
            <br />
            <span style={{ fontSize: 12, color: '#999' }}>※ プライバシーポリシーは準備中です</span>
          </span>
        </label>

        <button type="submit" disabled={!termsAccepted || !privacyAccepted}
          style={{
            padding: 14,
            background: termsAccepted && privacyAccepted ? '#1a73e8' : '#ccc',
            color: 'white', border: 'none', borderRadius: 8,
            fontSize: 16, fontWeight: 600,
            cursor: termsAccepted && privacyAccepted ? 'pointer' : 'default',
          }}>
          同意して次へ
        </button>
      </form>
    </div>
  );
}
