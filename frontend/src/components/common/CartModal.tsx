import { useNavigate } from 'react-router-dom';
import { useCartStore } from '../../stores/cartStore';
import { BetTypeLabels, getVenueName } from '../../types';
import './CartModal.css';

interface CartModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CartModal({ isOpen, onClose }: CartModalProps) {
  const navigate = useNavigate();
  const { items, removeItem, clearCart, getTotalAmount } = useCartStore();
  const totalAmount = getTotalAmount();

  if (!isOpen) return null;

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleClearCart = () => {
    if (window.confirm('カートの中身をすべて削除しますか？')) {
      clearCart();
    }
  };

  const handleConfirm = () => {
    onClose();
    navigate('/purchase/confirm');
  };

  return (
    <div className="cart-modal-overlay" onClick={handleOverlayClick}>
      <div className="cart-modal">
        {/* Header */}
        <div className="cart-modal-header">
          <span className="cart-modal-title">カート ({items.length}件)</span>
          <button className="cart-modal-close" onClick={onClose} type="button">
            ×
          </button>
        </div>

        {/* Body */}
        <div className="cart-modal-body">
          {items.length === 0 ? (
            <div className="cart-modal-empty">
              <div className="cart-modal-empty-icon">🛒</div>
              <p>カートに馬券がありません</p>
              <p style={{ fontSize: 12, marginTop: 8 }}>
                馬を選んで買い目を追加しましょう
              </p>
            </div>
          ) : (
            items.map((item) => (
              <div key={item.id} className="cart-modal-item">
                <div className="cart-modal-item-header">
                  <span className="cart-modal-item-race">
                    {getVenueName(item.raceVenue)} {item.raceNumber}R {item.raceName}
                  </span>
                  <button
                    className="cart-modal-item-remove"
                    onClick={() => removeItem(item.id)}
                    type="button"
                    title="削除"
                  >
                    ×
                  </button>
                </div>
                <div className="cart-modal-item-bet">
                  <span className="cart-modal-item-type">
                    {BetTypeLabels[item.betType]}
                  </span>
                  <span className="cart-modal-item-display">
                    {item.betDisplay || item.horseNumbers.join('-')}
                  </span>
                </div>
                <div className="cart-modal-item-amount">
                  ¥{item.amount.toLocaleString()}
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        {items.length > 0 && (
          <div className="cart-modal-footer">
            <div className="cart-modal-total">
              <span>合計</span>
              <span className="cart-modal-total-amount">
                ¥{totalAmount.toLocaleString()}
              </span>
            </div>
            <div className="cart-modal-actions">
              <button
                className="cart-modal-clear-btn"
                onClick={handleClearCart}
                type="button"
              >
                全削除
              </button>
              <button
                className="cart-modal-confirm-btn"
                onClick={handleConfirm}
                type="button"
              >
                購入確認へ
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
