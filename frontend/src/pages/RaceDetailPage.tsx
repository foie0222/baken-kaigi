import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAppStore } from '../stores/appStore';
import { useCartStore } from '../stores/cartStore';
import type { RaceDetail, BetType, BetMethod, ColumnSelections } from '../types';
import { BetTypeLabels, BetTypeRequiredHorses, BetTypeOrdered, getVenueName } from '../types';
import { apiClient } from '../api/client';
import { toJapaneseError } from '../stores/purchaseStore';
import { buildJraShutsubaUrl } from '../utils/jraUrl';
import { getBetMethodLabel } from '../utils/betMethods';
import { BetTypeSheet } from '../components/bet/BetTypeSheet';
import { BetMethodSheet } from '../components/bet/BetMethodSheet';
import { HorseCheckboxList } from '../components/bet/HorseCheckboxList';
import { ModeSelectionCards } from '../components/bet/ModeSelectionCards';
import { BetProposalContent } from '../components/proposal/BetProposalContent';
import { BetProposalSheet } from '../components/proposal/BetProposalSheet';
import { useBetCalculation } from '../hooks/useBetCalculation';
import { MAX_BET_AMOUNT } from '../constants/betting';
import './RaceDetailPage.css';

const initialSelections: ColumnSelections = { col1: [], col2: [], col3: [] };

type RaceDetailMode = 'select' | 'ai' | 'manual';

export function RaceDetailPage() {
  const { raceId } = useParams<{ raceId: string }>();
  const navigate = useNavigate();
  const showToast = useAppStore((state) => state.showToast);
  const addItem = useCartStore((state) => state.addItem);
  const itemCount = useCartStore((state) => state.getItemCount());

  const [race, setRace] = useState<RaceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<RaceDetailMode>('ai');

  // 券種・買い方・選択状態
  const [betType, setBetType] = useState<BetType>('win');
  const [betMethod, setBetMethod] = useState<BetMethod>('normal');
  const [selections, setSelections] = useState<ColumnSelections>(initialSelections);
  const [betAmount, setBetAmount] = useState(100);

  // ボトムシートの開閉状態
  const [isBetTypeSheetOpen, setIsBetTypeSheetOpen] = useState(false);
  const [isBetMethodSheetOpen, setIsBetMethodSheetOpen] = useState(false);
  const [isProposalSheetOpen, setIsProposalSheetOpen] = useState(false);

  // AI提案リマウント用key
  const [aiContentKey, setAiContentKey] = useState(0);

  // 点数計算
  const { betCount } = useBetCalculation(betType, betMethod, selections);

  useEffect(() => {
    if (!raceId) return;

    let isMounted = true;

    const fetchRaceDetail = async () => {
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

    fetchRaceDetail();

    return () => {
      isMounted = false;
    };
  }, [raceId]);

  const handleBetTypeChange = (type: BetType) => {
    setBetType(type);
    setBetMethod('normal');
    setSelections(initialSelections);
  };

  const handleBetMethodChange = (method: BetMethod) => {
    setBetMethod(method);
    setSelections(initialSelections);
  };

  const clearSelection = () => setSelections(initialSelections);

  const handleAmountMinus = () => {
    if (betAmount > 100) {
      const newAmount = betAmount <= 500 ? betAmount - 100 : betAmount - 500;
      setBetAmount(Math.max(100, newAmount));
    }
  };

  const handleAmountPlus = () => {
    const increment = betAmount < 500 ? 100 : 500;
    const effectiveBetCount = betCount > 0 ? betCount : 1;
    const maxPerBet = Math.floor(MAX_BET_AMOUNT / effectiveBetCount);
    setBetAmount((prev) => Math.min(prev + increment, maxPerBet));
  };

  const handleAddToCart = () => {
    if (!race || betCount === 0) return;

    // 馬番表示を生成
    let horseNumbersDisplay: number[];
    if (betMethod === 'formation' || betMethod.startsWith('nagashi')) {
      // 複数列の場合は全ての選択を結合
      const allNumbers = [...new Set([...selections.col1, ...selections.col2, ...selections.col3])];
      horseNumbersDisplay = allNumbers.sort((a, b) => a - b);
    } else {
      horseNumbersDisplay = [...selections.col1].sort((a, b) => a - b);
    }

    // 表示用文字列を生成
    const betDisplay = getSelectionDisplay() || horseNumbersDisplay.join('-');

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
      amount: betAmount * betCount,
      runnersData: race.horses.map((h) => ({
        horse_number: h.number,
        horse_name: h.name,
        odds: h.odds,
        popularity: h.popularity,
        frame_number: h.wakuBan,
      })),
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
    showToast(result === 'merged' ? '同じ買い目の金額を合算しました' : 'カートに追加しました');
  };

  // 選択ヒントのラベル生成
  const getSelectionLabel = () => {
    const methodLabel = getBetMethodLabel(betMethod, betType);
    if (methodLabel === '通常') {
      return BetTypeLabels[betType];
    }
    return `${BetTypeLabels[betType]} × ${methodLabel}`;
  };

  // 選択馬番の表示テキスト生成
  const getSelectionDisplay = () => {
    const hasAny = selections.col1.length > 0 || selections.col2.length > 0 || selections.col3.length > 0;
    if (!hasAny) return null;

    if (betMethod.startsWith('nagashi')) {
      const required = BetTypeRequiredHorses[betType];
      const ordered = BetTypeOrdered[betType];

      // 馬単の場合
      if (required === 2 && ordered) {
        if (betMethod === 'nagashi_2') {
          // 2着流し: 1着 → 2着軸 の順
          const partnerText = selections.col2.length > 0 ? `1着:${selections.col2.join(',')}` : '';
          const axisText = selections.col1.length > 0 ? `2着軸:${selections.col1.join(',')}` : '';
          return [partnerText, axisText].filter(Boolean).join(' → ');
        }
        // 1着流し: 1着軸 → 2着 の順
        const axisText = selections.col1.length > 0 ? `1着軸:${selections.col1.join(',')}` : '';
        const partnerText = selections.col2.length > 0 ? `2着:${selections.col2.join(',')}` : '';
        return [axisText, partnerText].filter(Boolean).join(' → ');
      }

      // 三連単の場合
      if (required === 3 && ordered) {
        if (betMethod === 'nagashi_1') {
          // 1着流し: 1着軸 → 2-3着
          const axisText = selections.col1.length > 0 ? `1着軸:${selections.col1.join(',')}` : '';
          const partnerText = selections.col2.length > 0 ? `2-3着:${selections.col2.join(',')}` : '';
          return [axisText, partnerText].filter(Boolean).join(' → ');
        } else if (betMethod === 'nagashi_2') {
          // 2着流し: 1,3着 → 2着軸
          const partnerText = selections.col2.length > 0 ? `1,3着:${selections.col2.join(',')}` : '';
          const axisText = selections.col1.length > 0 ? `2着軸:${selections.col1.join(',')}` : '';
          return [partnerText, axisText].filter(Boolean).join(' → ');
        } else if (betMethod === 'nagashi_3') {
          // 3着流し: 1-2着 → 3着軸
          const partnerText = selections.col2.length > 0 ? `1-2着:${selections.col2.join(',')}` : '';
          const axisText = selections.col1.length > 0 ? `3着軸:${selections.col1.join(',')}` : '';
          return [partnerText, axisText].filter(Boolean).join(' → ');
        } else if (betMethod === 'nagashi_12') {
          // 軸2頭 1-2着流し: 1着軸 → 2着軸 → 3着
          const axis1 = selections.col1.length > 0 ? `1着軸:${selections.col1.join(',')}` : '';
          const axis2 = selections.col3.length > 0 ? `2着軸:${selections.col3.join(',')}` : '';
          const partner = selections.col2.length > 0 ? `3着:${selections.col2.join(',')}` : '';
          return [axis1, axis2, partner].filter(Boolean).join(' → ');
        } else if (betMethod === 'nagashi_13') {
          // 軸2頭 1-3着流し: 1着軸 → 2着 → 3着軸
          const axis1 = selections.col1.length > 0 ? `1着軸:${selections.col1.join(',')}` : '';
          const partner = selections.col2.length > 0 ? `2着:${selections.col2.join(',')}` : '';
          const axis3 = selections.col3.length > 0 ? `3着軸:${selections.col3.join(',')}` : '';
          return [axis1, partner, axis3].filter(Boolean).join(' → ');
        } else if (betMethod === 'nagashi_23') {
          // 軸2頭 2-3着流し: 1着 → 2着軸 → 3着軸
          const partner = selections.col2.length > 0 ? `1着:${selections.col2.join(',')}` : '';
          const axis2 = selections.col1.length > 0 ? `2着軸:${selections.col1.join(',')}` : '';
          const axis3 = selections.col3.length > 0 ? `3着軸:${selections.col3.join(',')}` : '';
          return [partner, axis2, axis3].filter(Boolean).join(' → ');
        }
        // マルチ
        const axisText = selections.col1.length > 0 ? `軸:${selections.col1.join(',')}` : '';
        const partnerText = selections.col2.length > 0 ? `相手:${selections.col2.join(',')}` : '';
        return [axisText, partnerText].filter(Boolean).join(' → ');
      }

      // 馬連・ワイド・三連複（順不同）
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
      return parts.slice(0, required).join(' × ');
    } else {
      const sorted = [...selections.col1].sort((a, b) => a - b);
      return sorted.join(' - ');
    }
  };

  if (loading) return <div className="loading">読み込み中...</div>;
  if (error || !race) return (
    <div className="fade-in">
      <div className="race-not-found">
        <div className="race-not-found-icon">!</div>
        <h2 className="race-not-found-title">レースが見つかりませんでした</h2>
        <p className="race-not-found-message">
          {error || '指定されたレースは存在しないか、データがまだ公開されていません。'}
        </p>
        <button className="race-not-found-btn" onClick={() => navigate('/')}>
          レース一覧に戻る
        </button>
      </div>
    </div>
  );

  const required = BetTypeRequiredHorses[betType];
  const canSelectMethod = required > 1;
  const selectionDisplay = getSelectionDisplay();
  const totalAmount = betAmount * betCount;

  return (
    <div className="fade-in">
      <button className="back-btn" onClick={() => navigate('/')}>
        ← レース一覧に戻る
      </button>

      <div className="race-detail-header">
        <div className="race-header-top">
          <span className="race-number">{getVenueName(race.venue)} {race.number}</span>
          {(() => {
            const jraUrl = buildJraShutsubaUrl(race);
            return jraUrl && (
              <a
                href={jraUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="jra-link-btn"
              >
                <span>出馬表</span>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                  <polyline points="15 3 21 3 21 9" />
                  <line x1="10" y1="14" x2="21" y2="3" />
                </svg>
              </a>
            );
          })()}
        </div>
        <div className="race-name">{race.name}</div>
        <div className="race-conditions">
          {race.course && <span className="condition-tag">{race.course}</span>}
          {race.condition && <span className="condition-tag">馬場: {race.condition}</span>}
          {race.time && <span className="condition-tag">{race.time} 発走</span>}
        </div>
      </div>

      {mode === 'select' && (
        <ModeSelectionCards
          onSelectAi={() => setMode('ai')}
          onSelectManual={() => setMode('manual')}
        />
      )}

      {mode === 'ai' && (
        <>
          <div className="mode-switch-link">
            <button className="text-link-btn" onClick={() => setMode('manual')}>
              手動で買い目を選ぶ
            </button>
          </div>

          <div className="ai-proposal-section">
            <BetProposalContent key={aiContentKey} race={race} />
          </div>

          {itemCount > 0 && (
            <button
              className="btn-ai-confirm mt-3"
              onClick={() => navigate('/cart')}
            >
              カートを確認する（{itemCount}件） →
            </button>
          )}
        </>
      )}

      {mode === 'manual' && (
        <>
          <button className="back-to-select-btn" onClick={() => { setAiContentKey((k) => k + 1); setMode('ai'); }}>
            ← AI提案に戻る
          </button>

          {/* 券種・買い方セレクター */}
          <div className="selector-area">
            <button
              className="selector-badge bet-type"
              onClick={() => setIsBetTypeSheetOpen(true)}
            >
              <span className="label">{BetTypeLabels[betType]}</span>
              <span className="arrow">▼</span>
            </button>
            <button
              className={`selector-badge bet-method ${!canSelectMethod ? 'disabled' : ''}`}
              onClick={() => canSelectMethod && setIsBetMethodSheetOpen(true)}
              disabled={!canSelectMethod}
            >
              <span className="label">{getBetMethodLabel(betMethod, betType)}</span>
              <span className="arrow">▼</span>
            </button>
            {selectionDisplay && (
              <button className="clear-selection-btn" onClick={clearSelection}>
                ✕ クリア
              </button>
            )}
          </div>

          {/* 馬リスト */}
          <HorseCheckboxList
            horses={race.horses}
            betType={betType}
            method={betMethod}
            selections={selections}
            onSelectionChange={setSelections}
          />

          {/* 買い目入力セクション */}
          <div className="bet-section">
            <div className="bet-input-group">
              <label>
                選択した馬番
                <span className="selection-label">{getSelectionLabel()}</span>
              </label>
              <div className={`selected-horses-display ${selectionDisplay ? 'has-selection' : ''}`}>
                {selectionDisplay ? (
                  <>
                    <span className="selected-numbers">{selectionDisplay}</span>
                    {betCount > 0 && (
                      <span className="inline-bet-count">{betCount}点</span>
                    )}
                    <button className="clear-selection-btn" onClick={clearSelection}>
                      クリア
                    </button>
                  </>
                ) : (
                  <span className="no-selection">上のリストから馬を選択してください</span>
                )}
              </div>
            </div>

            <div className="bet-input-group">
              <label>金額</label>
              <div className="amount-input-wrapper">
                <button className="amount-stepper-btn" onClick={handleAmountMinus}>−</button>
                <div className="amount-center">
                  <span className="currency-symbol">¥</span>
                  <input
                    type="number"
                    className="amount-input"
                    value={betAmount}
                    onChange={(e) => {
                      const effectiveBetCount = betCount > 0 ? betCount : 1;
                      const maxPerBet = Math.floor(MAX_BET_AMOUNT / effectiveBetCount);
                      setBetAmount(Math.min(maxPerBet, Math.max(100, parseInt(e.target.value, 10) || 100)));
                    }}
                  />
                </div>
                <button className="amount-stepper-btn" onClick={handleAmountPlus}>＋</button>
              </div>
              <div className="amount-presets">
                {[100, 500, 1000, 5000].map((amount) => (
                  <button
                    key={amount}
                    className="preset-btn"
                    onClick={() => setBetAmount(amount)}
                  >
                    ¥{amount.toLocaleString()}
                  </button>
                ))}
              </div>
            </div>

            {betCount > 0 && (
              <div className="bet-summary">
                <span>{betCount}点</span>
                <span>¥{totalAmount.toLocaleString()}</span>
              </div>
            )}

            <button
              className="btn-proposal"
              onClick={() => setIsProposalSheetOpen(true)}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z" />
                <line x1="9" y1="21" x2="15" y2="21" />
              </svg>
              AI分析提案
            </button>

            <button
              className="btn-add-cart-subtle"
              onClick={handleAddToCart}
              disabled={betCount === 0}
            >
              カートに追加
            </button>
            <p className="ai-guide-text">
              ※ カートに追加後、購入確認へ進めます
            </p>

            {itemCount > 0 && (
              <button
                className="btn-ai-confirm mt-3"
                onClick={() => navigate('/cart')}
              >
                カートを確認する（{itemCount}件） →
              </button>
            )}
          </div>

          {/* ボトムシート */}
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
          <BetProposalSheet
            isOpen={isProposalSheetOpen}
            onClose={() => setIsProposalSheetOpen(false)}
            race={race}
          />
        </>
      )}
    </div>
  );
}
