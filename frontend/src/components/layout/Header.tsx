import { useNavigate } from 'react-router-dom';
import { useCartStore } from '../../stores/cartStore';
import { useAuthStore } from '../../stores/authStore';

export function Header() {
  const navigate = useNavigate();
  const itemCount = useCartStore((state) => state.getItemCount());
  const { isAuthenticated, user, signOut } = useAuthStore();

  return (
    <header className="app-header">
      <h1 className="app-title" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>馬券会議</h1>
      <div className="header-actions">
        <button className="header-pill cart-btn" onClick={() => navigate('/cart')} aria-label="カートへ移動" type="button">
          <span className="cart-icon">🛒</span>
          {itemCount > 0 && <span className="cart-badge">{itemCount}</span>}
        </button>
        {isAuthenticated ? (
          <div className="header-pill header-pill-user">
            <button
              className="header-pill-name"
              onClick={() => navigate('/profile')}
              type="button"
            >
              {user?.displayName || user?.email?.split('@')[0] || ''}
            </button>
            <span className="header-pill-divider" />
            <button
              className="header-pill-logout"
              onClick={() => signOut()}
              type="button"
            >
              ログアウト
            </button>
          </div>
        ) : (
          <button
            className="header-pill"
            onClick={() => navigate('/login')}
            type="button"
          >
            ログイン
          </button>
        )}
      </div>
    </header>
  );
}
