import { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import { useCartStore } from '../stores/cartStore';
import { useAppStore } from '../stores/appStore';
import { BetTypeLabels, getVenueName } from '../types';
import { apiClient } from '../api/client';
import { ConfirmModal } from '../components/common/ConfirmModal';
import { BottomSheet } from '../components/common/BottomSheet';
import { MIN_BET_AMOUNT, MAX_BET_AMOUNT } from '../constants/betting';
import { ConfidenceBar, RiskReturnChart, type RiskReturnDataPoint } from '../components/charts';

interface ChatMessage {
  type: 'ai' | 'user';
  text: string;
}

const DEFAULT_QUICK_REPLIES = ['過去の成績', '騎手', 'オッズ', '直感'];

export function ConsultationPage() {
  const navigate = useNavigate();
  const { items, getTotalAmount, clearCart, removeItem, updateItemAmount } =
    useCartStore();
  const showToast = useAppStore((state) => state.showToast);
  const totalAmount = getTotalAmount();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [showQuickReplies, setShowQuickReplies] = useState(true);
  const [quickReplies, setQuickReplies] = useState<string[]>(DEFAULT_QUICK_REPLIES);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [aiConfidence, setAiConfidence] = useState(0);

  // リスク/リターンデータをカートアイテムから生成
  const riskReturnData: RiskReturnDataPoint[] = useMemo(() => {
    return items.map((item) => {
      // 買い目の種類に基づいてリスクと期待リターンを算出（モック）
      const betTypeRisk: Record<string, number> = {
        win: 65,
        place: 25,
        quinella: 55,
        quinella_place: 35,
        exacta: 75,
        trio: 70,
        trifecta: 90,
      };
      const betTypeReturn: Record<string, number> = {
        win: 3.5,
        place: 1.5,
        quinella: 5.0,
        quinella_place: 2.5,
        exacta: 8.0,
        trio: 15.0,
        trifecta: 50.0,
      };

      const baseRisk = betTypeRisk[item.betType] || 50;
      const baseReturn = betTypeReturn[item.betType] || 2.0;

      // 選択した馬番による微調整（ランダム要素）
      const riskVariation = ((item.horseNumbers[0] || 1) % 5) * 3 - 6;
      const returnVariation = ((item.horseNumbers[0] || 1) % 3) * 0.3;

      return {
        id: item.id,
        name: `${getVenueName(item.raceVenue)} ${item.raceNumber} ${BetTypeLabels[item.betType]}`,
        risk: Math.max(10, Math.min(95, baseRisk + riskVariation)),
        expectedReturn: Math.max(0.5, baseReturn + returnVariation),
        amount: item.amount,
      };
    });
  }, [items]);

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

  // モック用の自信度計算（バックエンドが実装されるまで）
  const calculateMockConfidence = useCallback(() => {
    // アイテム数と合計金額に基づいて自信度を計算
    const itemCount = items.length;
    const total = getTotalAmount();

    // 少ない買い目で適度な金額の場合は自信度が高い
    let confidence = 70;
    if (itemCount > 5) confidence -= 15;
    if (itemCount > 10) confidence -= 20;
    if (total > 10000) confidence -= 10;
    if (total > 50000) confidence -= 15;

    // ランダム要素
    confidence += Math.floor(Math.random() * 20) - 10;

    return Math.max(20, Math.min(90, confidence));
  }, [items, getTotalAmount]);

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
        // 動的クイックリプライを設定（なければデフォルト）
        if (response.data.suggested_questions && response.data.suggested_questions.length > 0) {
          setQuickReplies(response.data.suggested_questions);
        } else {
          setQuickReplies(DEFAULT_QUICK_REPLIES);
        }
        // AI自信度を設定（バックエンドからconfidenceが来る場合はそれを使用、なければ計算）
        const confidence = response.data.confidence ?? calculateMockConfidence();
        setAiConfidence(confidence);
      } else {
        setMessages([
          {
            type: 'ai',
            text: `${items.length}件の買い目について分析しました。\n以下のデータを参考に、最終判断はあなた自身で行いましょう。`,
          },
        ]);
        setQuickReplies(DEFAULT_QUICK_REPLIES);
        setAiConfidence(calculateMockConfidence());
      }
    } catch {
      setMessages([
        {
          type: 'ai',
          text: `${items.length}件の買い目について分析しました。\n以下のデータを参考に、最終判断はあなた自身で行いましょう。`,
        },
      ]);
      setQuickReplies(DEFAULT_QUICK_REPLIES);
      setAiConfidence(calculateMockConfidence());
    } finally {
      setIsLoading(false);
    }
  }, [items, calculateMockConfidence]);

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
        // 動的クイックリプライを更新（なければデフォルトにフォールバック）
        const nextQuickReplies =
          data.suggested_questions && data.suggested_questions.length > 0
            ? data.suggested_questions
            : DEFAULT_QUICK_REPLIES;
        setQuickReplies(nextQuickReplies);
        setShowQuickReplies(true);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            type: 'ai',
            text: '申し訳ございません。分析中に問題が発生しました。\n\n上記のデータを参考に、ご自身でご判断ください。',
          },
        ]);
        setQuickReplies(DEFAULT_QUICK_REPLIES);
        setShowQuickReplies(true);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          type: 'ai',
          text: '申し訳ございません。通信エラーが発生しました。\n\nしばらく待ってから再度お試しいただくか、上記のデータを参考にご判断ください。',
        },
      ]);
      setQuickReplies(DEFAULT_QUICK_REPLIES);
      setShowQuickReplies(true);
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

        {/* ビジュアル分析ダッシュボード */}
        {!isLoading && items.length > 0 && (
          <div
            className="visual-dashboard"
            style={{
              background: '#fafafa',
              borderRadius: 12,
              padding: 16,
              marginBottom: 16,
            }}
          >
            <div
              style={{
                fontSize: 14,
                fontWeight: 600,
                color: '#333',
                marginBottom: 16,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              <span>📈</span>
              <span>AI分析ダッシュボード</span>
            </div>

            {/* AI自信度バー */}
            <ConfidenceBar confidence={aiConfidence} />

            {/* リスク/リターン散布図 */}
            <RiskReturnChart data={riskReturnData} />
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
                    {getVenueName(item.raceVenue)} {item.raceNumber}
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
