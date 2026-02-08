import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { BottomNav } from './BottomNav';
import { Toast } from '../common/Toast';
import { CookieConsentBanner } from '../common/CookieConsentBanner';
import { LossLimitAlert } from '../loss-limit/LossLimitAlert';
import { useAuthStore } from '../../stores/authStore';
import { useLossLimitStore } from '../../stores/lossLimitStore';

function HelpLink() {
  return (
    <div className="help-link-section">
      <a
        href="https://www.gaprsc.or.jp/index.html"
        target="_blank"
        rel="noopener noreferrer"
        aria-label="ギャンブル依存症の相談窓口へ（新しいタブで開く）"
      >
        困ったときは｜ギャンブル依存症相談窓口 →
      </a>
    </div>
  );
}

export function Layout() {
  const { isAuthenticated } = useAuthStore();
  const { fetchLossLimit } = useLossLimitStore();

  useEffect(() => {
    if (isAuthenticated) {
      fetchLossLimit();
    }
  }, [isAuthenticated, fetchLossLimit]);

  return (
    <>
      <Header />
      <LossLimitAlert />
      <main>
        <Outlet />
      </main>
      <HelpLink />
      <BottomNav />
      <CookieConsentBanner />
      <Toast />
    </>
  );
}
