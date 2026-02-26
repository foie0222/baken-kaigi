import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAppStore } from '../stores/appStore';
import { useCartStore } from '../stores/cartStore';
import type {
  RaceDetail,
  Horse,
  BetType,
  BetMethod,
  ColumnSelections,
  AiPredictionsResponse,
  SpeedIndicesResponse,
  AiPrediction,
  SpeedIndex,
} from '../types';
import {
  BetTypeLabels,
  BetTypeRequiredHorses,
  BetTypeOrdered,
  extractOdds,
  getVenueName,
} from '../types';
import { apiClient } from '../api/client';
import { toJapaneseError } from '../stores/purchaseStore';
import { buildJraShutsubaUrl } from '../utils/jraUrl';
import { getBetMethodLabel } from '../utils/betMethods';
import { BetTypeSheet } from '../components/bet/BetTypeSheet';
import { BetMethodSheet } from '../components/bet/BetMethodSheet';
import { useBetCalculation } from '../hooks/useBetCalculation';
import { MAX_BET_AMOUNT } from '../constants/betting';
import './RaceDashboardPage.css';

const initialSelections: ColumnSelections = { col1: [], col2: [], col3: [] };

// AI prediction source display names
const AI_SOURCE_NAMES: Record<string, string> = {
  'ai-shisu': 'AI指数',
  'keiba-ai-athena': 'ATHENA',
  'keiba-ai-navi': 'AIナビ',
  'umamax': 'うまmax',
  'muryou-keiba-ai': '無料AI',
};

// Speed index source display names
const SPEED_SOURCE_NAMES: Record<string, string> = {
  'jiro8-speed': 'Jiro8',
  'kichiuma-speed': '吉馬',
  'daily-speed': 'デイリー',
};

/**
 * Score color: gradient from cool (low) to warm (high)
 * low (<50) = bluish, mid = neutral, high (>80) = reddish
 */
function getScoreColor(score: number): string {
  if (score >= 80) return '#e94560';
  if (score >= 70) return '#f07060';
  if (score >= 60) return '#c0a060';
  if (score >= 50) return '#888';
  return '#4a6fa5';
}

function getScoreBg(score: number): string {
  if (score >= 80) return 'rgba(233, 69, 96, 0.15)';
  if (score >= 70) return 'rgba(240, 112, 96, 0.12)';
  if (score >= 60) return 'rgba(192, 160, 96, 0.08)';
  return 'transparent';
}

export function RaceDashboardPage() {
  const { raceId } = useParams<{ raceId: string }>();
  const navigate = useNavigate();
  const showToast = useAppStore((state) => state.showToast);
  const addItem = useCartStore((state) => state.addItem);
  const cartItems = useCartStore((state) => state.items);
  const removeItem = useCartStore((state) => state.removeItem);
  const getTotalAmount = useCartStore((state) => state.getTotalAmount);

  const [race, setRace] = useState<RaceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // AI predictions & speed indices
  const [aiPredictions, setAiPredictions] = useState<AiPredictionsResponse | null>(null);
  const [speedIndices, setSpeedIndices] = useState<SpeedIndicesResponse | null>(null);

  // Betting state
  const [betType, setBetType] = useState<BetType>('win');
  const [betMethod, setBetMethod] = useState<BetMethod>('normal');
  const [selections, setSelections] = useState<ColumnSelections>(initialSelections);
  const [betAmount, setBetAmount] = useState(100);
  const [amountInput, setAmountInput] = useState('100');

  // Bottom sheets
  const [isBetTypeSheetOpen, setIsBetTypeSheetOpen] = useState(false);
  const [isBetMethodSheetOpen, setIsBetMethodSheetOpen] = useState(false);

  // Bet count calculation
  const { betCount } = useBetCalculation(betType, betMethod, selections);

  // Fetch race detail
  useEffect(() => {
    if (!raceId) return;
    let isMounted = true;

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      const response = await apiClient.getRaceDetail(decodeURIComponent(raceId));
      if (!isMounted) return;

      if (response.success && response.data) {
        setRace(response.data);
      } else {
        setError(toJapaneseError(response.error, 'レース詳細の取得に失敗しました'));
      }
      setLoading(false);
    };

    fetchData();
    return () => { isMounted = false; };
  }, [raceId]);

  // Fetch AI predictions & speed indices (non-blocking)
  useEffect(() => {
    if (!raceId) return;
    let isMounted = true;
    const decodedId = decodeURIComponent(raceId);

    apiClient.getAiPredictions(decodedId).then((res) => {
      if (isMounted && res.success && res.data) {
        setAiPredictions(res.data);
      }
    });

    apiClient.getSpeedIndices(decodedId).then((res) => {
      if (isMounted && res.success && res.data) {
        setSpeedIndices(res.data);
      }
    });

    return () => { isMounted = false; };
  }, [raceId]);

  // Handlers
  const handleBetTypeChange = (type: BetType) => {
    setBetType(type);
    setBetMethod('normal');
    setSelections(initialSelections);
  };

  const handleBetMethodChange = (method: BetMethod) => {
    setBetMethod(method);
    setSelections(initialSelections);
  };

  const handleAmountMinus = () => {
    if (betAmount > 100) {
      const newAmount = betAmount <= 500 ? betAmount - 100 : betAmount - 500;
      const clamped = Math.max(100, newAmount);
      setBetAmount(clamped);
      setAmountInput(String(clamped));
    }
  };

  const handleAmountPlus = () => {
    const increment = betAmount < 500 ? 100 : 500;
    const effectiveBetCount = betCount > 0 ? betCount : 1;
    const maxPerBet = Math.floor(MAX_BET_AMOUNT / effectiveBetCount);
    setBetAmount((prev) => {
      const next = Math.min(prev + increment, maxPerBet);
      setAmountInput(String(next));
      return next;
    });
  };

  // Toggle horse selection for betting (simple col1 for normal/box)
  const toggleHorseSelection = useCallback((horseNumber: number) => {
    setSelections((prev) => {
      const col = prev.col1;
      const isSelected = col.includes(horseNumber);
      const required = BetTypeRequiredHorses[betType];

      if (betMethod === 'normal') {
        // Normal mode: toggle, max = required count
        if (isSelected) {
          return { ...prev, col1: col.filter((n) => n !== horseNumber) };
        }
        if (col.length >= required) {
          // Replace last selected
          return { ...prev, col1: [...col.slice(0, required - 1), horseNumber] };
        }
        return { ...prev, col1: [...col, horseNumber] };
      }

      // Box or other modes: just toggle
      if (isSelected) {
        return { ...prev, col1: col.filter((n) => n !== horseNumber) };
      }
      return { ...prev, col1: [...col, horseNumber] };
    });
  }, [betType, betMethod]);

  // Selection display text
  const getSelectionDisplay = () => {
    const hasAny = selections.col1.length > 0 || selections.col2.length > 0 || selections.col3.length > 0;
    if (!hasAny) return null;

    if (betMethod.startsWith('nagashi')) {
      const required = BetTypeRequiredHorses[betType];
      const ordered = BetTypeOrdered[betType];

      if (required === 2 && ordered) {
        if (betMethod === 'nagashi_2') {
          const partnerText = selections.col2.length > 0 ? `1着:${selections.col2.join(',')}` : '';
          const axisText = selections.col1.length > 0 ? `2着軸:${selections.col1.join(',')}` : '';
          return [partnerText, axisText].filter(Boolean).join(' → ');
        }
        const axisText = selections.col1.length > 0 ? `1着軸:${selections.col1.join(',')}` : '';
        const partnerText = selections.col2.length > 0 ? `2着:${selections.col2.join(',')}` : '';
        return [axisText, partnerText].filter(Boolean).join(' → ');
      }

      const axisText = selections.col1.length > 0 ? `軸:${selections.col1.join(',')}` : '';
      const partnerText = selections.col2.length > 0 ? `相手:${selections.col2.join(',')}` : '';
      return [axisText, partnerText].filter(Boolean).join(' → ');
    } else if (betMethod === 'formation') {
      const parts = [
        selections.col1.length > 0 ? selections.col1.join(',') : '-',
        selections.col2.length > 0 ? selections.col2.join(',') : '-',
        selections.col3.length > 0 ? selections.col3.join(',') : '-',
      ];
      const required = BetTypeRequiredHorses[betType];
      return parts.slice(0, required).join(' x ');
    } else {
      const sorted = [...selections.col1].sort((a, b) => a - b);
      return sorted.join(' - ');
    }
  };

  const handleAddToCart = async () => {
    if (!race || betCount === 0) return;

    let horseNumbersDisplay: number[];
    if (betMethod === 'formation' || betMethod.startsWith('nagashi')) {
      const allNumbers = [...new Set([...selections.col1, ...selections.col2, ...selections.col3])];
      horseNumbersDisplay = allNumbers.sort((a, b) => a - b);
    } else {
      horseNumbersDisplay = [...selections.col1].sort((a, b) => a - b);
    }

    const betDisplay = getSelectionDisplay() || horseNumbersDisplay.join('-');

    let odds: number | undefined;
    let oddsMin: number | undefined;
    let oddsMax: number | undefined;
    try {
      const oddsResult = await apiClient.getAllOdds(race.id);
      if (oddsResult.success && oddsResult.data) {
        const extracted = extractOdds(oddsResult.data, betType, horseNumbersDisplay);
        odds = extracted.odds;
        oddsMin = extracted.oddsMin;
        oddsMax = extracted.oddsMax;
      }
    } catch (err: unknown) {
      console.warn('Failed to fetch odds when adding item to cart:', err);
    }

    const result = addItem({
      raceId: race.id,
      raceName: race.name,
      raceVenue: race.venue,
      raceNumber: race.number,
      betType,
      betMethod,
      horseNumbers: horseNumbersDisplay,
      betDisplay,
      betCount,
      columnSelections: { ...selections },
      amount: betAmount * betCount,
      odds,
      oddsMin,
      oddsMax,
    });

    if (result === 'different_race' || result === 'invalid_amount') {
      const message = result === 'different_race'
        ? 'カートには同じレースの買い目のみ追加できます'
        : '金額が範囲外です';
      showToast(message, 'error');
      return;
    }

    setSelections(initialSelections);
    setBetAmount(100);
    setAmountInput('100');
    showToast(result === 'merged' ? '同じ買い目の金額を合算しました' : 'カートに追加しました');
  };

  // Build lookup maps for AI predictions and speed indices
  const aiSourceKeys = aiPredictions ? Object.keys(aiPredictions.predictions) : [];
  const speedSourceKeys = speedIndices ? Object.keys(speedIndices.indices) : [];

  const getAiScore = (horseNumber: number, sourceKey: string): AiPrediction | undefined => {
    if (!aiPredictions) return undefined;
    const preds = aiPredictions.predictions[sourceKey];
    if (!preds) return undefined;
    return preds.find((p) => p.horse_number === horseNumber);
  };

  const getSpeedScore = (horseNumber: number, sourceKey: string): SpeedIndex | undefined => {
    if (!speedIndices) return undefined;
    const idxs = speedIndices.indices[sourceKey];
    if (!idxs) return undefined;
    return idxs.find((s) => s.horse_number === horseNumber);
  };

  // Check if a horse is selected for betting
  const isHorseSelected = (horseNumber: number) => selections.col1.includes(horseNumber);

  // Render
  if (loading) {
    return <div className="dashboard-loading">読み込み中...</div>;
  }

  if (error || !race) {
    return (
      <div className="fade-in">
        <div className="dashboard-error">
          <div className="dashboard-error-icon">!</div>
          <h2 className="dashboard-error-title">レースが見つかりませんでした</h2>
          <p className="dashboard-error-message">
            {error || '指定されたレースは存在しないか、データがまだ公開されていません。'}
          </p>
          <button className="dashboard-error-btn" onClick={() => navigate('/')}>
            レース一覧に戻る
          </button>
        </div>
      </div>
    );
  }

  const jraUrl = buildJraShutsubaUrl(race);
  const required = BetTypeRequiredHorses[betType];
  const canSelectMethod = required > 1;
  const selectionDisplay = getSelectionDisplay();
  const totalAmount = betAmount * betCount;
  const cartTotal = getTotalAmount();

  return (
    <div className="fade-in">
      <button className="dashboard-back-btn" onClick={() => navigate('/')}>
        ← レース一覧に戻る
      </button>

      {/* Race Header */}
      <div className="dashboard-race-header">
        <span className="dashboard-race-number">{getVenueName(race.venue)} {race.number}</span>
        <span className="dashboard-race-name">{race.name}</span>
        <div className="dashboard-race-conditions">
          {race.condition && <span className="condition-tag">馬場: {race.condition}</span>}
          {race.trackType && <span className="condition-tag">{race.trackType}</span>}
          {race.distance && <span className="condition-tag">{race.distance}m</span>}
          {race.time && <span className="condition-tag">{race.time} 発走</span>}
        </div>
        {jraUrl && (
          <div className="dashboard-jra-link">
            <a href={jraUrl} target="_blank" rel="noopener noreferrer" className="jra-link-btn">
              <span>JRA出馬表</span>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                <polyline points="15 3 21 3 21 9" />
                <line x1="10" y1="14" x2="21" y2="3" />
              </svg>
            </a>
          </div>
        )}
      </div>

      {/* Body: Table + Betting Panel */}
      <div className="dashboard-body">
        {/* Main Table */}
        <div className="dashboard-table-area">
          <table className="dashboard-table">
            <thead>
              <tr>
                <th></th>
                <th></th>
                <th>馬番</th>
                <th style={{ textAlign: 'left', paddingLeft: 10 }}>馬名</th>
                <th>着順</th>
                <th>体重</th>
                {aiSourceKeys.map((key) => (
                  <th key={`ai-${key}`} className="col-group-ai">
                    {AI_SOURCE_NAMES[key] || key}
                  </th>
                ))}
                {speedSourceKeys.map((key) => (
                  <th key={`sp-${key}`} className="col-group-speed">
                    {SPEED_SOURCE_NAMES[key] || key}
                  </th>
                ))}
                <th>オッズ</th>
                <th>人気</th>
              </tr>
            </thead>
            <tbody>
              {race.horses.map((horse: Horse) => {
                const selected = isHorseSelected(horse.number);
                return (
                  <tr
                    key={horse.number}
                    className={selected ? 'row-selected' : ''}
                    onClick={() => toggleHorseSelection(horse.number)}
                    style={{ cursor: 'pointer' }}
                  >
                    {/* Checkbox */}
                    <td className="td-checkbox">
                      <input
                        type="checkbox"
                        checked={selected}
                        onChange={() => toggleHorseSelection(horse.number)}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </td>

                    {/* Waku color indicator */}
                    <td className="td-waku">
                      <div
                        className="waku-indicator"
                        style={{ backgroundColor: horse.color }}
                      />
                    </td>

                    {/* Horse number */}
                    <td className="td-horse-number">
                      <span
                        className="horse-num-circle"
                        style={{
                          backgroundColor: horse.color,
                          color: horse.textColor,
                          borderColor: horse.color === '#FFFFFF' ? 'rgba(255,255,255,0.3)' : horse.color,
                        }}
                      >
                        {horse.number}
                      </span>
                    </td>

                    {/* Horse name + jockey */}
                    <td className="td-horse-name">
                      <div className="horse-name-text">{horse.name}</div>
                      <div className="horse-jockey-text">{horse.jockey}</div>
                    </td>

                    {/* Finish position */}
                    <td className="td-finish-position">
                      {horse.finishPosition != null ? (
                        <span className={`finish-badge ${horse.finishPosition <= 3 ? `finish-${horse.finishPosition}` : ''}`}>
                          {horse.finishPosition}
                        </span>
                      ) : (
                        <span className="no-data">-</span>
                      )}
                    </td>

                    {/* Weight */}
                    <td className="td-weight">
                      {horse.weight ? (
                        <>
                          <span className="weight-value">{horse.weight}</span>
                          {horse.weightDiff != null && (
                            <span className={`weight-diff ${horse.weightDiff > 0 ? 'plus' : horse.weightDiff < 0 ? 'minus' : 'zero'}`}>
                              ({horse.weightDiff > 0 ? '+' : ''}{horse.weightDiff})
                            </span>
                          )}
                        </>
                      ) : (
                        <span className="no-data">---</span>
                      )}
                    </td>

                    {/* AI prediction scores */}
                    {aiSourceKeys.map((key) => {
                      const pred = getAiScore(horse.number, key);
                      return (
                        <td
                          key={`ai-${key}`}
                          className="td-ai-score"
                          style={pred ? {
                            color: getScoreColor(pred.score),
                            backgroundColor: getScoreBg(pred.score),
                          } : {}}
                        >
                          {pred ? pred.score : <span className="no-data">-</span>}
                        </td>
                      );
                    })}

                    {/* Speed indices */}
                    {speedSourceKeys.map((key) => {
                      const idx = getSpeedScore(horse.number, key);
                      return (
                        <td
                          key={`sp-${key}`}
                          className="td-speed-index"
                          style={idx ? {
                            color: getScoreColor(idx.speed_index),
                            backgroundColor: getScoreBg(idx.speed_index),
                          } : {}}
                        >
                          {idx ? idx.speed_index : <span className="no-data">-</span>}
                        </td>
                      );
                    })}

                    {/* Odds */}
                    <td className="td-odds">
                      {horse.odds > 0 ? horse.odds.toFixed(1) : <span className="no-data">-</span>}
                    </td>

                    {/* Popularity */}
                    <td className="td-popularity">
                      <span className={`popularity-badge ${horse.popularity <= 3 ? `pop-${horse.popularity}` : ''}`}>
                        {horse.popularity > 0 ? horse.popularity : '-'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Betting Panel */}
        <div className="dashboard-betting-panel">
          <div className="betting-panel-title">馬券購入</div>

          {/* Bet type + method selectors */}
          <div className="panel-selector-row">
            <button
              className="panel-selector"
              onClick={() => setIsBetTypeSheetOpen(true)}
            >
              <span>{BetTypeLabels[betType]}</span>
              <span className="arrow">▼</span>
            </button>
            <button
              className={`panel-selector ${!canSelectMethod ? 'disabled' : ''}`}
              onClick={() => canSelectMethod && setIsBetMethodSheetOpen(true)}
              disabled={!canSelectMethod}
            >
              <span>{getBetMethodLabel(betMethod, betType)}</span>
              <span className="arrow">▼</span>
            </button>
          </div>

          {/* Selection display */}
          <div className={`panel-selection-display ${selectionDisplay ? 'has-selection' : ''}`}>
            {selectionDisplay ? (
              <>
                <span className="panel-selection-numbers">{selectionDisplay}</span>
                {betCount > 0 && <span className="panel-bet-count">{betCount}点</span>}
                <button className="panel-clear-btn" onClick={() => setSelections(initialSelections)}>
                  クリア
                </button>
              </>
            ) : (
              <span>表のチェックボックスから馬を選択</span>
            )}
          </div>

          {/* Amount input */}
          <div className="panel-amount-row">
            <span className="panel-amount-label">金額</span>
            <div className="panel-amount-input-wrapper">
              <button className="panel-stepper-btn" onClick={handleAmountMinus}>-</button>
              <div className="panel-amount-center">
                <span className="panel-currency">¥</span>
                <input
                  type="number"
                  className="panel-amount-input"
                  value={amountInput}
                  onChange={(e) => {
                    const raw = e.target.value;
                    const parsed = parseInt(raw, 10);
                    if (!isNaN(parsed) && parsed > 0) {
                      const effectiveBetCount = betCount > 0 ? betCount : 1;
                      const maxPerBet = Math.floor(MAX_BET_AMOUNT / effectiveBetCount);
                      const clamped = Math.min(maxPerBet, Math.max(100, parsed));
                      setBetAmount(clamped);
                      setAmountInput(String(clamped));
                    } else {
                      setAmountInput(raw);
                    }
                  }}
                  onBlur={() => {
                    const effectiveBetCount = betCount > 0 ? betCount : 1;
                    const maxPerBet = Math.floor(MAX_BET_AMOUNT / effectiveBetCount);
                    const parsed = parseInt(amountInput, 10);
                    const clamped = Math.min(maxPerBet, Math.max(100, isNaN(parsed) ? 100 : parsed));
                    setBetAmount(clamped);
                    setAmountInput(String(clamped));
                  }}
                />
              </div>
              <button className="panel-stepper-btn" onClick={handleAmountPlus}>+</button>
            </div>
          </div>

          <div className="panel-amount-presets">
            {[100, 500, 1000, 5000].map((amount) => (
              <button
                key={amount}
                className="panel-preset-btn"
                onClick={() => { setBetAmount(amount); setAmountInput(String(amount)); }}
              >
                ¥{amount.toLocaleString()}
              </button>
            ))}
          </div>

          {/* Bet summary */}
          {betCount > 0 && (
            <div className="panel-bet-summary">
              <span>{betCount}点</span>
              <span>¥{totalAmount.toLocaleString()}</span>
            </div>
          )}

          {/* Add to cart */}
          <button
            className="panel-add-btn"
            onClick={handleAddToCart}
            disabled={betCount === 0}
          >
            カートに追加
          </button>

          {/* Cart section */}
          <hr className="panel-cart-divider" />
          <div className="panel-cart-title">カート</div>

          {cartItems.length === 0 ? (
            <div className="panel-cart-empty">カートは空です</div>
          ) : (
            <>
              {cartItems.map((item) => (
                <div key={item.id} className="panel-cart-item">
                  <div className="panel-cart-item-info">
                    <span className="panel-cart-bet-type">{BetTypeLabels[item.betType]}</span>
                    <span className="panel-cart-bet-display">
                      {item.betDisplay || item.horseNumbers.join('-')}
                    </span>
                  </div>
                  <span className="panel-cart-item-amount">¥{item.amount.toLocaleString()}</span>
                  <button
                    className="panel-cart-remove"
                    onClick={() => removeItem(item.id)}
                    title="削除"
                  >
                    ×
                  </button>
                </div>
              ))}

              <div className="panel-cart-total">
                <span>合計</span>
                <span>¥{cartTotal.toLocaleString()}</span>
              </div>

              <button
                className="panel-confirm-btn"
                onClick={() => navigate('/cart')}
              >
                購入確認へ →
              </button>
            </>
          )}
        </div>
      </div>

      {/* Bottom sheets (reused from existing) */}
      <BetTypeSheet
        isOpen={isBetTypeSheetOpen}
        onClose={() => setIsBetTypeSheetOpen(false)}
        selectedType={betType}
        onSelect={handleBetTypeChange}
      />
      <BetMethodSheet
        isOpen={isBetMethodSheetOpen}
        onClose={() => setIsBetMethodSheetOpen(false)}
        betType={betType}
        selectedMethod={betMethod}
        onSelect={handleBetMethodChange}
      />
    </div>
  );
}
