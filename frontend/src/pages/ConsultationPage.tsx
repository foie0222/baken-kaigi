import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { useCartStore } from '../stores/cartStore';
import { useAppStore } from '../stores/appStore';
import { BetTypeLabels } from '../types';
import { apiClient } from '../api/client';

interface ChatMessage {
  type: 'ai' | 'user';
  text: string;
}

const quickReplies = ['過去の成績', '騎手', 'オッズ', '直感'];

export function ConsultationPage() {
  const navigate = useNavigate();
  const { items, getTotalAmount, clearCart } = useCartStore();
  const showToast = useAppStore((state) => state.showToast);
  const totalAmount = getTotalAmount();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [showQuickReplies, setShowQuickReplies] = useState(true);
  const [isLoading, setIsLoading] = useState(true); // 初期状態をtrueに
  const [sessionId, setSessionId] = useState<string | undefined>();

  // 初回ロード時に AI からの初期分析を取得
  const fetchInitialAnalysis = useCallback(async () => {
    if (!apiClient.isAgentCoreAvailable()) {
      // AgentCore が利用不可の場合はフォールバック
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
        // エラー時はフォールバック
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
      // AgentCore が利用不可の場合はフォールバック
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
    alert(
      `${items.length}件の馬券を購入しました！\n\n合計: ¥${totalAmount.toLocaleString()}`
    );
    clearCart();
    showToast('購入が完了しました');
    navigate('/');
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

          {items.map((item) => (
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
                <span style={{ marginLeft: 'auto', fontSize: 13, color: '#666' }}>
                  予想オッズ {(Math.random() * 30 + 5).toFixed(1)}倍
                </span>
              </div>
              {item.horseNumbers.map((num) => (
                <div key={num} className="feedback-item" style={{ padding: '10px 12px' }}>
                  <span className="feedback-label">{num}番</span>
                  <span className="feedback-value">{generateMockFeedback()}</span>
                </div>
              ))}
              <div className="feedback-item" style={{ padding: '10px 12px' }}>
                <span className="feedback-label">掛け金</span>
                <span className="feedback-value">¥{item.amount.toLocaleString()}</span>
              </div>
            </div>
          ))}

          <div style={{ marginTop: 16, paddingTop: 16, borderTop: '2px solid #e0e0e0' }}>
            <div className="feedback-item" style={{ fontSize: 16 }}>
              <span className="feedback-label">合計掛け金</span>
              <span className="feedback-value" style={{ fontSize: 18, color: '#1a5f2a' }}>
                ¥{totalAmount.toLocaleString()}
              </span>
            </div>
          </div>
        </div>

        <div className="action-buttons vertical">
          <button className="btn-stop" onClick={() => navigate('/cart')}>
            やめておく
          </button>
          <button className="btn-purchase-subtle" onClick={handlePurchase}>
            購入する
          </button>
        </div>
      </div>
    </div>
  );
}
