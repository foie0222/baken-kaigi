import { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useCartStore } from '../stores/cartStore';
import { useAuthStore } from '../stores/authStore';
import { useIpatSettingsStore } from '../stores/ipatSettingsStore';
import { useAppStore } from '../stores/appStore';
import { BetTypeLabels, BetMethodLabels, getVenueName } from '../types';
import type { CartItem, RunnerData } from '../types';
import { apiClient, type BetAction } from '../api/client';
import { ConfirmModal } from '../components/common/ConfirmModal';
import { BottomSheet } from '../components/common/BottomSheet';
import { MIN_BET_AMOUNT, MAX_BET_AMOUNT } from '../constants/betting';
import { AI_CHARACTERS, DEFAULT_CHARACTER_ID, STORAGE_KEY_CHARACTER, type CharacterId } from '../constants/characters';

// レース難易度・人気集中度の算出閾値
// オッズの絶対値で人気集中度を判定（2倍未満=集中、4倍未満=普通、それ以上=混戦）
const ODDS_CONCENTRATION_HIGH = 2.0;
const ODDS_CONCENTRATION_MEDIUM = 4.0;
// 上位3頭のオッズ差で難易度を判定（差が小さいほど難しい＝予想が困難）
const ODDS_SPREAD_TIGHT = 3;
const ODDS_SPREAD_MEDIUM = 6;
const ODDS_SPREAD_WIDE = 10;
const MAX_DIFFICULTY_STARS = 4;

function RaceSummaryCard({ runnersData }: { runnersData: RunnerData[] }) {
  if (!runnersData || runnersData.length === 0) return null;

  const topOdds = runnersData
    .filter((r) => r.odds)
    .sort((a, b) => (a.odds ?? 99) - (b.odds ?? 99))
    .slice(0, 3);

  const hasOddsData = topOdds.length > 0;

  const favoriteOdds = topOdds[0]?.odds ?? 0;
  const concentrationLevel =
    favoriteOdds < ODDS_CONCENTRATION_HIGH ? 'high' : favoriteOdds < ODDS_CONCENTRATION_MEDIUM ? 'medium' : 'low';

  const oddsSpread =
    topOdds.length >= 3
      ? (topOdds[2]?.odds ?? 0) - (topOdds[0]?.odds ?? 0)
      : 0;
  const difficultyStars =
    oddsSpread < ODDS_SPREAD_TIGHT ? MAX_DIFFICULTY_STARS :
    oddsSpread < ODDS_SPREAD_MEDIUM ? 3 :
    oddsSpread < ODDS_SPREAD_WIDE ? 2 : 1;

  return (
    <div className="race-summary-card">
      <div className="race-summary-header">
        <h3>レース概要</h3>
      </div>
      <div className="race-summary-metrics">
        <div className="metric">
          <span className="metric-label">難易度</span>
          <span className="metric-value">
            {hasOddsData
              ? '★'.repeat(difficultyStars) + '☆'.repeat(MAX_DIFFICULTY_STARS - difficultyStars)
              : '—'}
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">人気集中</span>
          <span className={`metric-value${hasOddsData ? ` concentration-${concentrationLevel}` : ''}`}>
            {hasOddsData
              ? concentrationLevel === 'high'
                ? '集中'
                : concentrationLevel === 'medium'
                  ? '普通'
                  : '混戦'
              : '—'}
          </span>
        </div>
        <div className="metric">
          <span className="metric-label">出走頭数</span>
          <span className="metric-value">{runnersData.length}頭</span>
        </div>
      </div>
      {topOdds.length > 0 && (
        <div className="race-summary-favorites">
          <span className="favorites-label">上位人気</span>
          <div className="favorites-list">
            {topOdds.map((r) => (
              <span key={r.horse_number} className="favorite-chip">
                {r.horse_number}番 {r.horse_name} ({r.odds}倍)
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface ChatMessage {
  type: 'ai' | 'user';
  text: string;
  suggestedQuestions?: string[];
  betActions?: BetAction[];
}

export function BetReviewPage() {
  const navigate = useNavigate();
  const { items, currentRunnersData, getTotalAmount, removeItem, updateItemAmount } =
    useCartStore();
  const { isAuthenticated } = useAuthStore();
  const { status: ipatStatus, checkStatus: checkIpatStatus } = useIpatSettingsStore();
  const showToast = useAppStore((state) => state.showToast);
  // IPAT設定状態（true: 設定済み, false: 未設定, null: ステータス未取得）
  const isIpatConfigured = ipatStatus?.configured ?? null;
  const totalAmount = getTotalAmount();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [inputText, setInputText] = useState('');
  const [characterId, setCharacterId] = useState<CharacterId>(() => {
    const stored = localStorage.getItem(STORAGE_KEY_CHARACTER);
    return stored && AI_CHARACTERS.some((c) => c.id === stored) ? (stored as CharacterId) : DEFAULT_CHARACTER_ID;
  });
  const selectedCharacter = AI_CHARACTERS.find((c) => c.id === characterId) || AI_CHARACTERS[0];


  const [isBetListExpanded, setIsBetListExpanded] = useState(false);

  // 削除確認モーダル
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  // 金額編集シート
  const [editTarget, setEditTarget] = useState<{
    id: string;
    amount: number;
    betCount?: number;
  } | null>(null);
  const [editAmount, setEditAmount] = useState(0);

  // 初回マウント時のカートデータをキャプチャ（カート変更でAPI再呼び出しを防止）
  const initialItemsRef = useRef(items);
  const initialRunnersRef = useRef(currentRunnersData);

  const handleCharacterChange = (newCharacterId: CharacterId) => {
    setCharacterId(newCharacterId);
    localStorage.setItem(STORAGE_KEY_CHARACTER, newCharacterId);
  };

  // ログイン時にIPAT設定を取得
  useEffect(() => {
    if (isAuthenticated) {
      checkIpatStatus();
    }
  }, [isAuthenticated, checkIpatStatus]);

  // 初回ロード時に AI からの初期分析を取得（マウント時のみ実行）
  useEffect(() => {
    if (!apiClient.isAgentCoreAvailable()) {
      setMessages([
        {
          type: 'ai',
          text: 'AI分析機能は現在利用できません。\n買い目一覧をご確認の上、ご判断ください。',
        },
      ]);
      setIsLoading(false);
      return;
    }

    let isMounted = true;
    setIsLoading(true);

    const fetchInitialAnalysis = async () => {
      try {
        const capturedItems = initialItemsRef.current;
        const capturedRunners = initialRunnersRef.current;
        const runnersData = capturedRunners.length > 0 ? capturedRunners : undefined;
        const response = await apiClient.consultWithAgent({
          prompt: 'カートの買い目をレビューしてください。AI指数と照らし合わせてリスクや弱点を指摘し、改善案があれば提案してください。',
          cart_items: capturedItems.map((item) => ({
            raceId: item.raceId,
            raceName: item.raceName,
            betType: item.betType,
            horseNumbers: item.horseNumbers,
            amount: item.amount,
          })),
          runners_data: runnersData,
          character_type: characterId,
        });

        if (!isMounted) return;

        if (response.success && response.data) {
          setMessages([{
            type: 'ai',
            text: response.data.message,
            suggestedQuestions: response.data.suggested_questions,
            betActions: response.data.bet_actions,
          }]);
          setSessionId(response.data.session_id);
        } else {
          setMessages([
            {
              type: 'ai',
              text: '分析中に問題が発生しました。\n再度お試しいただくか、買い目一覧をご確認ください。',
            },
          ]);
        }
      } catch {
        if (!isMounted) return;
        setMessages([
          {
            type: 'ai',
            text: '通信エラーが発生しました。\n再度お試しいただくか、買い目一覧をご確認ください。',
          },
        ]);
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    fetchInitialAnalysis();

    return () => {
      isMounted = false;
    };
  }, []);

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
      const runnersData = currentRunnersData.length > 0 ? currentRunnersData : undefined;
      const response = await apiClient.consultWithAgent({
        prompt: message,
        cart_items: items.map((item) => ({
          raceId: item.raceId,
          raceName: item.raceName,
          betType: item.betType,
          horseNumbers: item.horseNumbers,
          amount: item.amount,
        })),
        runners_data: runnersData,
        session_id: sessionId,
        character_type: characterId,
      });

      if (response.success && response.data) {
        const data = response.data;
        setMessages((prev) => [...prev, {
          type: 'ai',
          text: data.message,
          suggestedQuestions: data.suggested_questions,
          betActions: data.bet_actions,
        }]);
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

  const handleSuggestedQuestion = (question: string) => {
    setInputText(question);
  };

  const handleBetAction = (action: BetAction) => {
    switch (action.type) {
      case 'remove_horse': {
        const horseNum = action.params.horse_number as number;
        const targetItems = items.filter((item) =>
          item.horseNumbers.includes(horseNum)
        );
        if (targetItems.length > 0) {
          targetItems.forEach((targetItem) => {
            removeItem(targetItem.id);
          });
          showToast(`${horseNum}番を削除しました`);
          if (items.length === targetItems.length) {
            navigate('/cart');
          }
        } else {
          showToast('該当する買い目が見つかりませんでした');
        }
        break;
      }
      case 'add_horse': {
        showToast('馬の追加はレース詳細画面から行ってください');
        break;
      }
      case 'change_amount': {
        const amount = action.params.amount as number;
        if (amount >= MIN_BET_AMOUNT && amount <= MAX_BET_AMOUNT && amount % 100 === 0) {
          useCartStore.setState((state) => ({
            items: state.items.map((item) => ({ ...item, amount })),
          }));
          showToast(`金額を${amount.toLocaleString()}円に変更しました`);
        } else {
          showToast('金額は100円単位で指定してください');
        }
        break;
      }
      case 'replace_bet': {
        showToast('買い目の置き換えはレース詳細画面から行ってください');
        break;
      }
    }
  };

  const handlePurchase = () => {
    if (isIpatConfigured === false) {
      showToast('IPAT設定が必要です');
      navigate('/settings/ipat');
      return;
    }
    navigate('/purchase/confirm');
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
          <div className="ai-avatar">{selectedCharacter.icon}</div>
          <div className="ai-chat-header-text">
            <h3>AI 買い目レビュー</h3>
            <p>{selectedCharacter.description}</p>
          </div>
        </div>

        <div className="character-selector">
          {AI_CHARACTERS.map((char) => (
            <button
              key={char.id}
              type="button"
              className={`character-chip${char.id === characterId ? ' active' : ''}`}
              aria-pressed={char.id === characterId}
              aria-label={`キャラクター選択: ${char.name}`}
              onClick={() => handleCharacterChange(char.id)}
            >
              <span className="character-chip-icon">{char.icon}</span>
              <span className="character-chip-name">{char.name}</span>
            </button>
          ))}
        </div>

        <RaceSummaryCard runnersData={initialRunnersRef.current} />

        <div className="chat-messages">
          {messages.map((msg, index) => (
            <div key={index} className={`chat-message ${msg.type}`}>
              <div className="message-bubble markdown-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
              </div>
              {msg.betActions && msg.betActions.length > 0 && index === messages.length - 1 && !isLoading && (
                <div className="bet-action-buttons">
                  {msg.betActions.map((action) => (
                    <button
                      key={`${action.type}-${action.label}`}
                      type="button"
                      className="bet-action-btn"
                      onClick={() => handleBetAction(action)}
                    >
                      {action.label}
                    </button>
                  ))}
                </div>
              )}
              {msg.suggestedQuestions && msg.suggestedQuestions.length > 0 && index === messages.length - 1 && !isLoading && (
                <div className="suggested-questions">
                  {msg.suggestedQuestions.map((q, i) => (
                    <button
                      key={i}
                      type="button"
                      className="suggested-question-btn"
                      onClick={() => handleSuggestedQuestion(q)}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              )}
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
            placeholder="レビューについて質問..."
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

        {/* 買い目リスト（折りたたみ式） */}
        <div className="bet-list-section">
          <button
            type="button"
            className="bet-list-toggle"
            onClick={() => setIsBetListExpanded((prev) => !prev)}
            aria-expanded={isBetListExpanded}
            aria-controls="bet-list-content"
          >
            <span>買い目一覧（{items.length}点）</span>
            <span className="toggle-amount">¥{totalAmount.toLocaleString()}</span>
            <span className={`toggle-icon ${isBetListExpanded ? 'expanded' : ''}`} aria-hidden="true">▼</span>
          </button>
          {isBetListExpanded && (
            <div className="bet-list-content" id="bet-list-content">
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
            </div>
          )}
        </div>

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
            disabled={items.length === 0 || !isAuthenticated || isIpatConfigured === null}
          >
            {!isAuthenticated ? 'ログインして購入' : isIpatConfigured === null ? '確認中...' : isIpatConfigured === false ? 'IPAT設定して購入' : '購入する'}
          </button>
        </div>
      </div>

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
