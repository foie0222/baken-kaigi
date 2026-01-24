import { Outlet } from 'react-router-dom';
import { Header } from './Header';
import { BottomNav } from './BottomNav';
import { Toast } from '../common/Toast';

function HelpLink() {
  return (
    <div className="help-link-section">
      <a
        href="https://www.mhlw.go.jp/stf/seisakunitsuite/bunya/0000070789.html"
        target="_blank"
        rel="noopener noreferrer"
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
      <Toast />
    </>
  );
}
