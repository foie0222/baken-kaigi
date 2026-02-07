import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useCookieConsentStore } from '../../stores/cookieConsentStore';

export function CookieConsentBanner() {
  const { consent, acceptAll, rejectOptional, updateConsent } = useCookieConsentStore();
  const [showDetails, setShowDetails] = useState(false);
  const [analytics, setAnalytics] = useState(false);
  const [marketing, setMarketing] = useState(false);

  if (consent !== null) {
    return null;
  }

  const handleSaveDetails = () => {
    updateConsent({ analytics, marketing });
  };

  return (
    <div className="cookie-consent-banner">
      <div className="cookie-consent-content">
        <p className="cookie-consent-text">
          本サービスではCookieを使用しています。
          <Link to="/cookie-policy" className="cookie-consent-link">Cookieポリシー</Link>
          をご確認ください。
        </p>

        {showDetails && (
          <div className="cookie-details-panel">
            <div className="cookie-toggle-row">
              <span className="cookie-toggle-label">必須Cookie</span>
              <label className="cookie-toggle disabled">
                <input type="checkbox" checked disabled aria-label="必須Cookie" />
                <span className="cookie-toggle-slider" />
              </label>
            </div>
            <div className="cookie-toggle-row">
              <span className="cookie-toggle-label">分析Cookie</span>
              <label className="cookie-toggle">
                <input
                  type="checkbox"
                  checked={analytics}
                  onChange={(e) => setAnalytics(e.target.checked)}
                  aria-label="分析Cookie"
                />
                <span className="cookie-toggle-slider" />
              </label>
            </div>
            <div className="cookie-toggle-row">
              <span className="cookie-toggle-label">マーケティングCookie</span>
              <label className="cookie-toggle">
                <input
                  type="checkbox"
                  checked={marketing}
                  onChange={(e) => setMarketing(e.target.checked)}
                  aria-label="マーケティングCookie"
                />
                <span className="cookie-toggle-slider" />
              </label>
            </div>
            <button type="button" className="cookie-btn cookie-btn-save" onClick={handleSaveDetails}>
              保存
            </button>
          </div>
        )}

        <div className="cookie-consent-buttons">
          <button type="button" className="cookie-btn cookie-btn-details" onClick={() => setShowDetails(!showDetails)}>
            {showDetails ? '閉じる' : '詳細設定'}
          </button>
          <button type="button" className="cookie-btn cookie-btn-reject" onClick={rejectOptional}>
            必要なもののみ
          </button>
          <button type="button" className="cookie-btn cookie-btn-accept" onClick={acceptAll}>
            すべて許可
          </button>
        </div>
      </div>
    </div>
  );
}
