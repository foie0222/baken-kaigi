import { useNavigate } from 'react-router-dom';
import { useCartStore } from '../../stores/cartStore';

export function Header() {
  const navigate = useNavigate();
  const itemCount = useCartStore((state) => state.getItemCount());

  return (
    <header className="app-header">
      <h1 className="app-title">馬券会議</h1>
      <div className="header-actions">
        <button className="cart-btn" onClick={() => navigate('/cart')}>
          <span className="cart-icon">🛒</span>
          {itemCount > 0 && <span className="cart-badge">{itemCount}</span>}
        </button>
      </div>
    </header>
  );
}
