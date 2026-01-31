import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { useCartStore } from '../stores/cartStore';
import { useAppStore } from '../stores/appStore';
import { BetTypeLabels, getVenueName } from '../types';
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
        prompt: 'カートの買い目を分析してください',
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

  const handleEditAmount = (itemId: string, currentAmount: number) => {
    setEditTarget({ id: itemId, amount: currentAmount });
    setEditAmount(currentAmount);
  };

  const confirmEditAmount = () => {
    if (!editTarget) {
      return;
    }

    if (editAmount < MIN_BET_AMOUNT || editAmount > MAX_BET_AMOUNT) {
      showToast(
        `金額は${MIN_BET_AMOUNT.toLocaleString()}〜${MAX_BET_AMOUNT.toLocaleString()}円の範囲で入力してください`
      );
      return;
    }

    updateItemAmount(editTarget.id, editAmount);
    setEditTarget(null);
    showToast('金額を変更しました');
  };

  const isEditAmountValid = editAmount >= MIN_BET_AMOUNT && editAmount <= MAX_BET_AMOUNT;

  const adjustEditAmount = (delta: number) => {
    setEditAmount((prev) => Math.max(MIN_BET_AMOUNT, Math.min(MAX_BET_AMOUNT, prev + delta)));
  };

  // 削除対象のアイテム情報
  const deleteTargetItem = deleteTarget
    ? items.find((item) => item.id === deleteTarget)
    : null;

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
            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
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

        {/* 買い目カード（簡素化） */}
        <div className="data-feedback">
          <div className="feedback-title">買い目一覧</div>

          {items.map((item) => (
            <div key={item.id} className="bet-card-simple">
              <div className="bet-card-header">
                <span className="bet-venue">
                  {getVenueName(item.raceVenue)} {item.raceNumber}R
                </span>
                <span className="bet-type">{BetTypeLabels[item.betType]}</span>
                <span className="bet-numbers">{item.horseNumbers.join('-')}</span>
              </div>
              <div className="bet-card-footer">
                <span className="bet-amount">¥{item.amount.toLocaleString()}</span>
                <div className="bet-actions">
                  <button
                    className="bet-action-btn"
                    onClick={() => handleEditAmount(item.id, item.amount)}
                  >
                    金額変更
                  </button>
                  <button
                    className="bet-action-btn delete"
                    onClick={() => handleDeleteItem(item.id)}
                  >
                    削除
                  </button>
                </div>
              </div>
            </div>
          ))}

          <div
            style={{
              marginTop: 16,
              paddingTop: 16,
              borderTop: '2px solid #e0e0e0',
            }}
          >
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
        title="掛け金の変更"
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
              disabled={editAmount >= MAX_BET_AMOUNT}
              style={{
                width: 44,
                height: 44,
                border: 'none',
                background: '#e8e8e8',
                fontSize: 20,
                fontWeight: 600,
                color: editAmount >= MAX_BET_AMOUNT ? '#999' : '#333',
                cursor: editAmount >= MAX_BET_AMOUNT ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              ＋
            </button>
          </div>
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
