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
      <div className="header-actions" style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <button className="cart-btn" onClick={() => navigate('/cart')}>
          <span className="cart-icon">🛒</span>
          {itemCount > 0 && <span className="cart-badge">{itemCount}</span>}
        </button>
        {isAuthenticated ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span
              style={{ fontSize: 13, color: '#666', cursor: 'pointer' }}
              onClick={() => navigate('/profile')}
            >
              {user?.displayName || user?.email?.split('@')[0] || ''}
            </span>
            <button
              onClick={() => signOut()}
              style={{
                padding: '6px 12px',
                border: '1px solid #ddd',
                borderRadius: 6,
                background: 'white',
                fontSize: 12,
                cursor: 'pointer',
              }}
            >
              ログアウト
            </button>
          </div>
        ) : (
          <button
            onClick={() => navigate('/login')}
            style={{
              padding: '6px 12px',
              border: 'none',
              borderRadius: 6,
              background: '#1a73e8',
              color: 'white',
              fontSize: 12,
              cursor: 'pointer',
            }}
          >
            ログイン
          </button>
        )}
      </div>
    </header>
  );
}
