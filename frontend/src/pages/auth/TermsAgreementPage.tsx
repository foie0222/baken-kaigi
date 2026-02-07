import { useState, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { TERMS_VERSION, PRIVACY_VERSION } from '../../constants/legal';

export function TermsAgreementPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const state = location.state as { birthdate?: string; oauthUser?: boolean } | null;
  const birthdate = state?.birthdate || '';
  const oauthUser = state?.oauthUser || false;
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (termsAccepted && privacyAccepted) {
      if (oauthUser) {
        navigate('/oauth/complete', {
          state: {
            birthdate,
            termsVersion: TERMS_VERSION.version,
            privacyVersion: PRIVACY_VERSION.version,
          },
        });
      } else {
        navigate('/signup', {
          state: {
            birthdate,
            termsVersion: TERMS_VERSION.version,
            privacyVersion: PRIVACY_VERSION.version,
          },
        });
      }
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
            <a href="/terms" target="_blank" rel="noopener noreferrer"
              style={{ color: '#1a73e8', textDecoration: 'underline' }}
              onClick={(e) => e.stopPropagation()}>
              利用規約
            </a>
            {' '}に同意します
          </span>
        </label>

        <label style={{ display: 'flex', alignItems: 'flex-start', gap: 12, padding: 16, background: 'white', borderRadius: 8, cursor: 'pointer' }}>
          <input type="checkbox" checked={privacyAccepted} onChange={(e) => setPrivacyAccepted(e.target.checked)}
            style={{ marginTop: 2, width: 20, height: 20 }} />
          <span style={{ fontSize: 14 }}>
            <a href="/privacy" target="_blank" rel="noopener noreferrer"
              style={{ color: '#1a73e8', textDecoration: 'underline' }}
              onClick={(e) => e.stopPropagation()}>
              プライバシーポリシー
            </a>
            {' '}に同意します
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
