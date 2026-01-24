import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAppStore } from '../stores/appStore';
import { useCartStore } from '../stores/cartStore';
import type { RaceDetail, BetType, BetMethod, ColumnSelections } from '../types';
import { BetTypeLabels, BetTypeRequiredHorses } from '../types';
import { apiClient } from '../api/client';
import { buildJraShutsubaUrl } from '../utils/jraUrl';
import { getBetMethodLabel } from '../utils/betMethods';
import { BetTypeSheet } from '../components/bet/BetTypeSheet';
import { BetMethodSheet } from '../components/bet/BetMethodSheet';
import { HorseCheckboxList } from '../components/bet/HorseCheckboxList';
import { useBetCalculation } from '../hooks/useBetCalculation';
import './RaceDetailPage.css';

const initialSelections: ColumnSelections = { col1: [], col2: [], col3: [] };

export function RaceDetailPage() {
  const { raceId } = useParams<{ raceId: string }>();
  const navigate = useNavigate();
  const showToast = useAppStore((state) => state.showToast);
  const addItem = useCartStore((state) => state.addItem);
  const itemCount = useCartStore((state) => state.getItemCount());

  const [race, setRace] = useState<RaceDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 券種・買い方・選択状態
  const [betType, setBetType] = useState<BetType>('win');
  const [betMethod, setBetMethod] = useState<BetMethod>('normal');
  const [selections, setSelections] = useState<ColumnSelections>(initialSelections);
  const [betAmount, setBetAmount] = useState(100);

  // ボトムシートの開閉状態
  const [isBetTypeSheetOpen, setIsBetTypeSheetOpen] = useState(false);
  const [isBetMethodSheetOpen, setIsBetMethodSheetOpen] = useState(false);

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
        setError(response.error || 'レース詳細の取得に失敗しました');
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
    setBetAmount(betAmount < 500 ? betAmount + 100 : betAmount + 500);
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

    addItem({
      raceId: race.id,
      raceName: race.name,
      raceVenue: race.venue,
      raceNumber: race.number,
      betType,
      horseNumbers: horseNumbersDisplay,
      amount: betAmount * betCount,
    });

    setSelections(initialSelections);
    setBetAmount(100);
    showToast('カートに追加しました');
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
      const axisText = selections.col1.length > 0 ? `軸:${selections.col1.join(',')}` : '';
      const partnerText = selections.col2.length > 0 ? `→${selections.col2.join(',')}` : '';
      return axisText + partnerText;
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
  if (error) return <div className="error">{error}</div>;
  if (!race) return <div className="no-races">レースが見つかりません</div>;

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
          <span className="race-number">{race.venue} {race.number}</span>
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
                onChange={(e) => setBetAmount(Math.max(100, parseInt(e.target.value) || 100))}
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
          className="ai-consult-btn"
          onClick={handleAddToCart}
          disabled={betCount === 0}
        >
          🛒 カートに追加
        </button>

        {itemCount > 0 && (
          <button
            className="btn-secondary"
            style={{ marginTop: 12, width: '100%' }}
            onClick={() => navigate('/cart')}
          >
            カートを確認する（{itemCount}件）
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
    </div>
  );
}
