import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { useCartStore } from '../stores/cartStore';
import { useAppStore } from '../stores/appStore';
import { BetTypeLabels, BetMethodLabels, getVenueName } from '../types';
import type { CartItem } from '../types';
import { apiClient } from '../api/client';
import { ConfirmModal } from '../components/common/ConfirmModal';
import { BottomSheet } from '../components/common/BottomSheet';
import { MIN_BET_AMOUNT, MAX_BET_AMOUNT } from '../constants/betting';

interface ChatMessage {
  type: 'ai' | 'user';
  text: string;
}

export function ConsultationPage() {
  const navigate = useNavigate();
  const { items, getTotalAmount, clearCart, removeItem, updateItemAmount } =
    useCartStore();
  const showToast = useAppStore((state) => state.showToast);
  const totalAmount = getTotalAmount();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [inputText, setInputText] = useState('');

  // 購入確認モーダル
  const [showPurchaseModal, setShowPurchaseModal] = useState(false);

  // 削除確認モーダル
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  // 金額編集シート
  const [editTarget, setEditTarget] = useState<{
    id: string;
    amount: number;
    betCount?: number;
  } | null>(null);
  const [editAmount, setEditAmount] = useState(0);

  // 初回ロード時に AI からの初期分析を取得
  const fetchInitialAnalysis = useCallback(async () => {
    if (!apiClient.isAgentCoreAvailable()) {
      setMessages([
        {
          type: 'ai',
          text: '買い目の分析準備ができました。\n何か質問があればお聞きください。',
        },
      ]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const response = await apiClient.consultWithAgent({
        prompt: 'カートの買い目についてAI指数と照らし合わせて分析し、リスクや弱点を指摘してください。',
        cart_items: items.map((item) => ({
          raceId: item.raceId,
          raceName: item.raceName,
          betType: item.betType,
          horseNumbers: item.horseNumbers,
          amount: item.amount,
        })),
      });

      if (response.success && response.data) {
        setMessages([{ type: 'ai', text: response.data.message }]);
        setSessionId(response.data.session_id);
      } else {
        setMessages([
          {
            type: 'ai',
            text: '買い目の分析準備ができました。\n何か質問があればお聞きください。',
          },
        ]);
      }
    } catch {
      setMessages([
        {
          type: 'ai',
          text: '買い目の分析準備ができました。\n何か質問があればお聞きください。',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [items]);

  useEffect(() => {
    fetchInitialAnalysis();
  }, [fetchInitialAnalysis]);

  // ユーザーメッセージ送信
  const handleSendMessage = async () => {
    const message = inputText.trim();
    if (!message || isLoading) return;

    setInputText('');
    setMessages((prev) => [...prev, { type: 'user', text: message }]);

    if (!apiClient.isAgentCoreAvailable()) {
      setMessages((prev) => [
        ...prev,
        {
          type: 'ai',
          text: '申し訳ございません。現在AI分析機能は利用できません。',
        },
      ]);
      return;
    }

    setIsLoading(true);
    try {
      const response = await apiClient.consultWithAgent({
        prompt: message,
        cart_items: items.map((item) => ({
          raceId: item.raceId,
          raceName: item.raceName,
          betType: item.betType,
          horseNumbers: item.horseNumbers,
          amount: item.amount,
        })),
        session_id: sessionId,
      });

      if (response.success && response.data) {
        const data = response.data;
        setMessages((prev) => [...prev, { type: 'ai', text: data.message }]);
        setSessionId(data.session_id);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            type: 'ai',
            text: '申し訳ございません。分析中に問題が発生しました。',
          },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          type: 'ai',
          text: '申し訳ございません。通信エラーが発生しました。',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handlePurchase = () => {
    setShowPurchaseModal(true);
  };

  const confirmPurchase = () => {
    setShowPurchaseModal(false);
    clearCart();
    showToast('購入が完了しました');
    navigate('/');
  };

  const handleDeleteItem = (itemId: string) => {
    setDeleteTarget(itemId);
  };

  const confirmDelete = () => {
    if (!deleteTarget) {
      return;
    }

    // 削除前の状態で最後の1件かどうかを判定
    const isLastItem = items.length === 1;

    removeItem(deleteTarget);
    setDeleteTarget(null);
    showToast('買い目を削除しました');

    // 全て削除した場合はカートに戻る
    if (isLastItem) {
      navigate('/cart');
    }
  };

  const handleEditAmount = (item: CartItem) => {
    // 複数点の場合は1点あたり金額をセット
    const amountPerBet = item.betCount && item.betCount > 1
      ? Math.floor(item.amount / item.betCount)
      : item.amount;
    setEditTarget({ id: item.id, amount: item.amount, betCount: item.betCount });
    setEditAmount(amountPerBet);
  };

  const confirmEditAmount = () => {
    if (!editTarget) {
      return;
    }

    // 1点あたり金額のバリデーション（100円単位）
    if (editAmount < MIN_BET_AMOUNT || editAmount % 100 !== 0) {
      showToast('金額は100円単位で入力してください');
      return;
    }

    // 合計金額の計算と上限チェック
    const itemTotalAmount = editTarget.betCount && editTarget.betCount > 1
      ? editAmount * editTarget.betCount
      : editAmount;

    if (itemTotalAmount > MAX_BET_AMOUNT) {
      showToast(`合計金額が${MAX_BET_AMOUNT.toLocaleString()}円を超えています`);
      return;
    }

    updateItemAmount(editTarget.id, itemTotalAmount);
    setEditTarget(null);
    showToast('金額を変更しました');
  };

  // 1点あたり金額の上限（複数点の場合は合計金額の上限を考慮）
  const maxAmountPerBet = useMemo(() => {
    return editTarget?.betCount && editTarget.betCount > 1
      ? Math.floor(MAX_BET_AMOUNT / editTarget.betCount)
      : MAX_BET_AMOUNT;
  }, [editTarget]);

  // 1点あたり金額の検証
  const isEditAmountValid = useMemo(() => {
    if (editAmount < MIN_BET_AMOUNT || editAmount % 100 !== 0) return false;
    // 複数点の場合は合計金額の上限チェック
    const itemTotalAmount = editTarget?.betCount && editTarget.betCount > 1
      ? editAmount * editTarget.betCount
      : editAmount;
    return itemTotalAmount <= MAX_BET_AMOUNT;
  }, [editAmount, editTarget]);

  const adjustEditAmount = (delta: number) => {
    setEditAmount((prev) => Math.max(MIN_BET_AMOUNT, Math.min(maxAmountPerBet, prev + delta)));
  };

  // 削除対象のアイテム情報
  const deleteTargetItem = deleteTarget
    ? items.find((item) => item.id === deleteTarget)
    : null;

  // レースごとにグループ化
  const groupedItems = useMemo(() => {
    const groups: Record<string, CartItem[]> = {};
    items.forEach((item) => {
      const key = `${item.raceVenue}-${item.raceNumber}`;
      if (!groups[key]) groups[key] = [];
      groups[key].push(item);
    });
    return groups;
  }, [items]);

  return (
    <div className="fade-in">
      <button className="back-btn" onClick={() => navigate('/cart')}>
        ← カートに戻る
      </button>

      <div className="ai-chat-container">
        <div className="ai-chat-header">
          <div className="ai-avatar">🤖</div>
          <div className="ai-chat-header-text">
            <h3>馬券会議 AI</h3>
            <p>立ち止まって、考えましょう</p>
          </div>
        </div>

        <div className="chat-messages">
          {messages.map((msg, index) => (
            <div key={index} className={`chat-message ${msg.type}`}>
              <div className="message-bubble markdown-content">
                <ReactMarkdown>{msg.text}</ReactMarkdown>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="chat-message ai">
              <div className="message-bubble loading-bubble">
                <span className="loading-dots">
                  <span>考</span>
                  <span>え</span>
                  <span>中</span>
                  <span className="dot">.</span>
                  <span className="dot">.</span>
                  <span className="dot">.</span>
                </span>
              </div>
            </div>
          )}
        </div>

        {/* テキスト入力欄 */}
        <div className="chat-input-container">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                handleSendMessage();
              }
            }}
            placeholder="AIに質問する..."
            disabled={isLoading}
            className="chat-input"
          />
          <button
            onClick={handleSendMessage}
            disabled={!inputText.trim() || isLoading}
            className="chat-send-btn"
          >
            送信
          </button>
        </div>

        {/* 買い目リスト（レースごとにグループ化） */}
        {Object.entries(groupedItems).map(([key, raceItems]) => (
          <div className="bet-list" key={key}>
            <div className="bet-list-header">
              <span className="bet-list-title">買い目一覧</span>
              <span className="bet-list-race">
                {getVenueName(raceItems[0].raceVenue)} {raceItems[0].raceNumber}
              </span>
            </div>
            <div className="bet-table">
              {raceItems.map((item) => (
                <div className="bet-row" key={item.id}>
                  <span className="bet-card-type">{BetTypeLabels[item.betType]}</span>
                  <div className="bet-numbers-wrap">
                    <span className="bet-numbers">
                      {item.betDisplay || item.horseNumbers.join('-')}
                    </span>
                    {item.betMethod && item.betMethod !== 'normal' && (
                      <span className="bet-style">{BetMethodLabels[item.betMethod]}</span>
                    )}
                  </div>
                  <div className="bet-price-c">
                    <span className="bet-amount">¥{item.amount.toLocaleString()}</span>
                    {item.betCount && item.betCount > 1 && (
                      <span className="bet-detail">{item.betCount}点 @¥{Math.floor(item.amount / item.betCount).toLocaleString()}</span>
                    )}
                  </div>
                  <div className="bet-actions">
                    <button className="btn-edit" onClick={() => handleEditAmount(item)}>変更</button>
                    <button
                      className="btn-delete"
                      onClick={() => handleDeleteItem(item.id)}
                      aria-label="買い目を削除"
                      title="買い目を削除"
                    >
                      ×
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* 合計金額 */}
        <div className="data-feedback">
          <div className="feedback-item" style={{ fontSize: 16 }}>
            <span className="feedback-label">合計掛け金</span>
            <span
              className="feedback-value"
              style={{ fontSize: 18, color: '#1a5f2a' }}
            >
              ¥{totalAmount.toLocaleString()}
            </span>
          </div>
        </div>

        <div className="action-buttons vertical">
          <button className="btn-stop" onClick={() => navigate('/cart')}>
            やめておく
          </button>
          <button
            className="btn-purchase-subtle"
            onClick={handlePurchase}
            disabled={items.length === 0}
          >
            購入する
          </button>
        </div>
      </div>

      {/* 購入確認モーダル */}
      <ConfirmModal
        isOpen={showPurchaseModal}
        onClose={() => setShowPurchaseModal(false)}
        onConfirm={confirmPurchase}
        title="購入確認"
        confirmText="購入する"
        cancelText="キャンセル"
      >
        <div className="purchase-summary">
          <p style={{ marginBottom: 16 }}>
            以下の内容で馬券を購入します。よろしいですか？
          </p>
          <div
            style={{
              background: '#f8f8f8',
              padding: 16,
              borderRadius: 8,
              marginBottom: 16,
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginBottom: 8,
              }}
            >
              <span>買い目数</span>
              <span style={{ fontWeight: 600 }}>{items.length}件</span>
            </div>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                fontSize: 18,
                fontWeight: 700,
                color: '#1a5f2a',
              }}
            >
              <span>合計金額</span>
              <span>¥{totalAmount.toLocaleString()}</span>
            </div>
          </div>
        </div>
      </ConfirmModal>

      {/* 削除確認モーダル */}
      <ConfirmModal
        isOpen={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        onConfirm={confirmDelete}
        title="削除確認"
        confirmText="削除する"
        cancelText="キャンセル"
        confirmVariant="danger"
      >
        <p>
          {deleteTargetItem && (
            <>
              <strong>
                {getVenueName(deleteTargetItem.raceVenue)} {deleteTargetItem.raceNumber}
              </strong>
              <br />
              {BetTypeLabels[deleteTargetItem.betType]}{' '}
              {deleteTargetItem.horseNumbers.join('-')}
              <br />
              <br />
            </>
          )}
          この買い目を削除しますか？
        </p>
      </ConfirmModal>

      {/* 金額編集シート */}
      <BottomSheet
        isOpen={editTarget !== null}
        onClose={() => setEditTarget(null)}
        title={editTarget?.betCount && editTarget.betCount > 1 ? '1点あたりの金額' : '掛け金の変更'}
      >
        <div style={{ padding: '8px 0' }}>
          {/* 金額入力 - RaceDetailPageと同じスタイル */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              background: '#f8f9fa',
              border: '2px solid #e8e8e8',
              borderRadius: 8,
              overflow: 'hidden',
              marginBottom: 8,
            }}
          >
            <button
              onClick={() => adjustEditAmount(-100)}
              disabled={editAmount <= MIN_BET_AMOUNT}
              style={{
                width: 44,
                height: 44,
                border: 'none',
                background: '#e8e8e8',
                fontSize: 20,
                fontWeight: 600,
                color: editAmount <= MIN_BET_AMOUNT ? '#999' : '#333',
                cursor: editAmount <= MIN_BET_AMOUNT ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              −
            </button>
            <div
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '0 8px',
                gap: 2,
              }}
            >
              <span style={{ fontSize: 16, fontWeight: 600, color: '#666' }}>¥</span>
              <input
                type="number"
                value={editAmount}
                onChange={(e) => setEditAmount(Math.max(MIN_BET_AMOUNT, parseInt(e.target.value) || MIN_BET_AMOUNT))}
                style={{
                  width: 80,
                  border: 'none',
                  background: 'none',
                  padding: '12px 4px',
                  fontSize: 18,
                  fontWeight: 600,
                  outline: 'none',
                  textAlign: 'center',
                }}
              />
            </div>
            <button
              onClick={() => adjustEditAmount(100)}
              disabled={editAmount >= maxAmountPerBet}
              style={{
                width: 44,
                height: 44,
                border: 'none',
                background: '#e8e8e8',
                fontSize: 20,
                fontWeight: 600,
                color: editAmount >= maxAmountPerBet ? '#999' : '#333',
                cursor: editAmount >= maxAmountPerBet ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              ＋
            </button>
          </div>

          {/* 複数点の場合は合計金額をプレビュー */}
          {editTarget?.betCount && editTarget.betCount > 1 && (
            <div className="amount-preview">
              合計: ¥{(editAmount * editTarget.betCount).toLocaleString()}
              （{editTarget.betCount}点 × ¥{editAmount.toLocaleString()}）
            </div>
          )}

          {/* プリセットボタン */}
          <div
            style={{
              display: 'flex',
              gap: 8,
              marginBottom: 16,
            }}
          >
            {[100, 500, 1000, 5000].map((amount) => (
              <button
                key={amount}
                onClick={() => setEditAmount(amount)}
                style={{
                  flex: 1,
                  padding: 8,
                  border: '1px solid #ddd',
                  background: 'white',
                  borderRadius: 6,
                  fontSize: 12,
                  cursor: 'pointer',
                }}
              >
                ¥{amount.toLocaleString()}
              </button>
            ))}
          </div>
          <button
            onClick={confirmEditAmount}
            disabled={!isEditAmountValid}
            style={{
              width: '100%',
              padding: 14,
              borderRadius: 10,
              border: 'none',
              background: isEditAmountValid ? '#1a5f2a' : '#ccc',
              color: 'white',
              fontSize: 16,
              fontWeight: 600,
              cursor: isEditAmountValid ? 'pointer' : 'not-allowed',
            }}
          >
            変更を確定
          </button>
        </div>
      </BottomSheet>
    </div>
  );
}
