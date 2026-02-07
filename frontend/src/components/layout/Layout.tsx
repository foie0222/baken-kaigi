import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { BottomNav } from './BottomNav';
import { Toast } from '../common/Toast';
import { CookieConsentBanner } from '../common/CookieConsentBanner';

function HelpLink() {
  return (
    <div className="help-link-section">
      <a
        href="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000070789.html"
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
  return (
    <>
      <Header />
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
