import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { useCartStore } from '../stores/cartStore';
import { useAppStore } from '../stores/appStore';
import { BetTypeLabels } from '../types';
import { apiClient } from '../api/client';
import { ConfirmModal } from '../components/common/ConfirmModal';
import { BottomSheet } from '../components/common/BottomSheet';
import {
  calculateTrigaramiRisk,
  getTrigaramiRiskLabel,
} from '../utils/betAnalysis';
import { MIN_BET_AMOUNT, MAX_BET_AMOUNT, MOCK_ODDS } from '../constants/betting';

interface ChatMessage {
  type: 'ai' | 'user';
  text: string;
}

const quickReplies = ['過去の成績', '騎手', 'オッズ', '直感'];

/**
 * アイテムごとの暫定オッズを生成
 * 注: 将来的にはJRA-VAN APIからリアルオッズを取得予定
 */
const generateMockOdds = (itemId: string): number => {
  // itemIdをシードとして一貫した値を返す
  const hash = itemId.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return Number(((hash % MOCK_ODDS.MODULO) / MOCK_ODDS.DIVISOR + MOCK_ODDS.MIN_ODDS).toFixed(1));
};

export function ConsultationPage() {
  const navigate = useNavigate();
  const { items, getTotalAmount, clearCart, removeItem, updateItemAmount } =
    useCartStore();
  const showToast = useAppStore((state) => state.showToast);
  const totalAmount = getTotalAmount();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [showQuickReplies, setShowQuickReplies] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionId, setSessionId] = useState<string | undefined>();

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

  // アイテムごとのオッズをメモ化
  const itemOdds = useMemo(() => {
    const odds: Record<string, number> = {};
    items.forEach((item) => {
      odds[item.id] = generateMockOdds(item.id);
    });
    return odds;
  }, [items]);

  // 初回ロード時に AI からの初期分析を取得
  const fetchInitialAnalysis = useCallback(async () => {
    if (!apiClient.isAgentCoreAvailable()) {
      setMessages([
        {
          type: 'ai',
          text: `${items.length}件の買い目について分析しました。\n以下のデータを参考に、最終判断はあなた自身で行いましょう。`,
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
            text: `${items.length}件の買い目について分析しました。\n以下のデータを参考に、最終判断はあなた自身で行いましょう。`,
          },
        ]);
      }
    } catch {
      setMessages([
        {
          type: 'ai',
          text: `${items.length}件の買い目について分析しました。\n以下のデータを参考に、最終判断はあなた自身で行いましょう。`,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }, [items]);

  useEffect(() => {
    fetchInitialAnalysis();
  }, [fetchInitialAnalysis]);

  const handleQuickReply = async (reply: string) => {
    setMessages((prev) => [...prev, { type: 'user', text: reply }]);
    setShowQuickReplies(false);

    if (!apiClient.isAgentCoreAvailable()) {
      setMessages((prev) => [
        ...prev,
        {
          type: 'ai',
          text: `なるほど、「${reply}」ですね。\n\n以下のデータを参考にしてください。最終判断はあなた自身で行いましょう。`,
        },
      ]);
      return;
    }

    setIsLoading(true);
    try {
      const response = await apiClient.consultWithAgent({
        prompt: reply,
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
            text: '申し訳ございません。分析中に問題が発生しました。\n\n上記のデータを参考に、ご自身でご判断ください。',
          },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          type: 'ai',
          text: '申し訳ございません。通信エラーが発生しました。\n\nしばらく待ってから再度お試しいただくか、上記のデータを参考にご判断ください。',
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
    if (editTarget && editAmount >= MIN_BET_AMOUNT && editAmount <= MAX_BET_AMOUNT) {
      updateItemAmount(editTarget.id, editAmount);
      setEditTarget(null);
      showToast('金額を変更しました');
    }
  };

  const adjustEditAmount = (delta: number) => {
    setEditAmount((prev) => Math.max(MIN_BET_AMOUNT, Math.min(MAX_BET_AMOUNT, prev + delta)));
  };

  // モックデータフィードバック生成
  const generateMockFeedback = () => {
    const analyses = [
      '前走1着 / コース◎',
      '前走3着 / 長距離○',
      '前走5着 / 休み明け△',
      '前走2着 / 騎手◎',
      '前走4着 / 馬場△',
    ];
    return analyses[Math.floor(Math.random() * analyses.length)];
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

        {showQuickReplies && !isLoading && (
          <div className="quick-replies">
            {quickReplies.map((reply) => (
              <button
                key={reply}
                className="quick-reply-btn"
                onClick={() => handleQuickReply(reply)}
                disabled={isLoading}
              >
                {reply}
              </button>
            ))}
          </div>
        )}

        <div className="data-feedback">
          <div className="feedback-title">📊 買い目データフィードバック</div>

          {items.map((item) => {
            const odds = itemOdds[item.id];
            // betCountが存在する場合はそれを使用（券種・買い方により正確な点数）
            const betCount = item.betCount ?? item.horseNumbers.length;
            const risk = calculateTrigaramiRisk(odds, betCount);
            const riskLabel = getTrigaramiRiskLabel(risk);

            return (
              <div
                key={item.id}
                style={{
                  background: 'white',
                  border: '1px solid #e0e0e0',
                  borderRadius: 10,
                  marginBottom: 12,
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    background: '#f8f8f8',
                    padding: 12,
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: 8,
                    alignItems: 'center',
                    borderBottom: '1px solid #e0e0e0',
                  }}
                >
                  <span style={{ fontWeight: 700, color: '#1a5f2a' }}>
                    {item.raceVenue} {item.raceNumber}
                  </span>
                  <span
                    style={{
                      background: '#1a5f2a',
                      color: 'white',
                      padding: '2px 8px',
                      borderRadius: 4,
                      fontSize: 12,
                      fontWeight: 600,
                    }}
                  >
                    {BetTypeLabels[item.betType]} {item.horseNumbers.join('-')}
                  </span>
                  <span
                    className="risk-badge"
                    style={{
                      background: riskLabel.color,
                      color: 'white',
                      padding: '2px 8px',
                      borderRadius: 4,
                      fontSize: 11,
                      fontWeight: 600,
                    }}
                  >
                    {riskLabel.label}
                  </span>
                  <span
                    style={{ marginLeft: 'auto', fontSize: 13, color: '#666' }}
                  >
                    予想オッズ {odds}倍
                  </span>
                </div>
                {item.horseNumbers.map((num) => (
                  <div
                    key={num}
                    className="feedback-item"
                    style={{ padding: '10px 12px' }}
                  >
                    <span className="feedback-label">{num}番</span>
                    <span className="feedback-value">
                      {generateMockFeedback()}
                    </span>
                  </div>
                ))}
                <div
                  className="feedback-item"
                  style={{
                    padding: '10px 12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div>
                    <span className="feedback-label">掛け金</span>
                    <span className="feedback-value">
                      ¥{item.amount.toLocaleString()}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <button
                      className="item-action-btn"
                      onClick={() => handleEditAmount(item.id, item.amount)}
                      style={{
                        background: '#f5f5f5',
                        border: 'none',
                        borderRadius: 6,
                        padding: '6px 12px',
                        fontSize: 12,
                        color: '#666',
                        cursor: 'pointer',
                      }}
                    >
                      金額変更
                    </button>
                    <button
                      className="item-action-btn delete"
                      onClick={() => handleDeleteItem(item.id)}
                      style={{
                        background: '#ffebee',
                        border: 'none',
                        borderRadius: 6,
                        padding: '6px 12px',
                        fontSize: 12,
                        color: '#d32f2f',
                        cursor: 'pointer',
                      }}
                    >
                      削除
                    </button>
                  </div>
                </div>
              </div>
            );
          })}

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

        <div className="action-buttons">
          <button
            className="btn-primary"
            onClick={handlePurchase}
            disabled={items.length === 0}
          >
            購入する
          </button>
          <button className="btn-secondary" onClick={() => navigate('/cart')}>
            やめておく
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
                {deleteTargetItem.raceVenue} {deleteTargetItem.raceNumber}
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
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 16,
              marginBottom: 24,
            }}
          >
            <button
              onClick={() => adjustEditAmount(-100)}
              disabled={editAmount <= 100}
              style={{
                width: 44,
                height: 44,
                borderRadius: '50%',
                border: 'none',
                background: editAmount <= 100 ? '#e0e0e0' : '#1a5f2a',
                color: 'white',
                fontSize: 24,
                cursor: editAmount <= 100 ? 'not-allowed' : 'pointer',
              }}
            >
              −
            </button>
            <div
              style={{
                fontSize: 28,
                fontWeight: 700,
                minWidth: 150,
                textAlign: 'center',
              }}
            >
              ¥{editAmount.toLocaleString()}
            </div>
            <button
              onClick={() => adjustEditAmount(100)}
              style={{
                width: 44,
                height: 44,
                borderRadius: '50%',
                border: 'none',
                background: '#1a5f2a',
                color: 'white',
                fontSize: 24,
                cursor: 'pointer',
              }}
            >
              +
            </button>
          </div>
          <div
            style={{
              display: 'flex',
              gap: 8,
              justifyContent: 'center',
              marginBottom: 24,
            }}
          >
            {[500, 1000, 5000, 10000].map((amount) => (
              <button
                key={amount}
                onClick={() => setEditAmount(amount)}
                style={{
                  padding: '8px 16px',
                  borderRadius: 20,
                  border:
                    editAmount === amount
                      ? '2px solid #1a5f2a'
                      : '1px solid #ddd',
                  background: editAmount === amount ? '#e8f5e9' : 'white',
                  fontSize: 13,
                  cursor: 'pointer',
                }}
              >
                ¥{amount.toLocaleString()}
              </button>
            ))}
          </div>
          <button
            onClick={confirmEditAmount}
            style={{
              width: '100%',
              padding: 14,
              borderRadius: 10,
              border: 'none',
              background: '#1a5f2a',
              color: 'white',
              fontSize: 16,
              fontWeight: 600,
              cursor: 'pointer',
            }}
          >
            変更を確定
          </button>
        </div>
      </BottomSheet>
    </div>
  );
}
