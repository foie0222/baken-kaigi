import { useNavigate, useLocation } from 'react-router-dom';
import type { PageType } from '../../types';

interface NavItem {
  page: PageType;
  icon: string;
  label: string;
  path: string;
}

const navItems: NavItem[] = [
  { page: 'races', icon: '🏇', label: 'レース', path: '/' },
  { page: 'dashboard', icon: '📊', label: '損益', path: '/dashboard' },
  { page: 'history', icon: '📋', label: '履歴', path: '/history' },
  { page: 'settings', icon: '⚙', label: '設定', path: '/settings' },
];

export function BottomNav() {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === '/') {
      return location.pathname === '/' || location.pathname.startsWith('/races');
    }
    return location.pathname.startsWith(path);
  };

  return (
    <nav className="bottom-nav">
      {navItems.map((item) => (
        <button
          key={item.page}
          className={`nav-item ${isActive(item.path) ? 'active' : ''}`}
          onClick={() => navigate(item.path)}
        >
          <span className="nav-icon">{item.icon}</span>
          <span className="nav-label">{item.label}</span>
        </button>
      ))}
    </nav>
  );
}
