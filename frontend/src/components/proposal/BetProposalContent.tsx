import { useState, useRef, useEffect } from 'react';
import { ProposalCard } from './ProposalCard';
import { apiClient } from '../../api/client';
import { useCartStore, type AddItemResult } from '../../stores/cartStore';
import { useAppStore } from '../../stores/appStore';
import { AI_CHARACTERS, DEFAULT_CHARACTER_ID, STORAGE_KEY_CHARACTER, type CharacterId } from '../../constants/characters';
import { BetTypeLabels, type BetType } from '../../types';
import type { RaceDetail, BetProposalResponse } from '../../types';
import './BetProposalSheet.css';

interface BetProposalContentProps {
  race: RaceDetail;
}

const BUDGET_PRESETS = [1000, 3000, 5000, 10000];
const MAX_BETS_PRESETS = [3, 5, 8] as const;

const BET_TYPE_OPTIONS: { value: BetType; label: string }[] = [
  { value: 'quinella', label: BetTypeLabels.quinella },
  { value: 'quinella_place', label: BetTypeLabels.quinella_place },
  { value: 'exacta', label: BetTypeLabels.exacta },
  { value: 'trio', label: BetTypeLabels.trio },
  { value: 'trifecta', label: BetTypeLabels.trifecta },
  { value: 'win', label: BetTypeLabels.win },
  { value: 'place', label: BetTypeLabels.place },
];

function readCharacterFromStorage(): CharacterId {
  try {
    const stored = localStorage.getItem(STORAGE_KEY_CHARACTER);
    if (stored && AI_CHARACTERS.some((c) => c.id === stored)) {
      return stored as CharacterId;
    }
  } catch { /* ignore */ }
  return DEFAULT_CHARACTER_ID;
}

export function BetProposalContent({ race }: BetProposalContentProps) {
  const addItem = useCartStore((state) => state.addItem);
  const showToast = useAppStore((state) => state.showToast);

  const [characterId, setCharacterId] = useState<CharacterId>(readCharacterFromStorage);
  const [budget, setBudget] = useState(3000);
  const [customBudget, setCustomBudget] = useState('');
  const [isCustomBudget, setIsCustomBudget] = useState(false);
  const [selectedBetTypes, setSelectedBetTypes] = useState<BetType[]>([]);
  const [maxBets, setMaxBets] = useState<number | null>(null);
  const [axisInput, setAxisInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BetProposalResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [addedIndices, setAddedIndices] = useState<Set<number>>(new Set());
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const handleCharacterChange = (id: CharacterId) => {
    setCharacterId(id);
    try {
      localStorage.setItem(STORAGE_KEY_CHARACTER, id);
    } catch { /* ignore */ }
  };

  const handleBetTypeToggle = (betType: BetType) => {
    setSelectedBetTypes((prev) =>
      prev.includes(betType)
        ? prev.filter((t) => t !== betType)
        : [...prev, betType]
    );
  };

  const handleMaxBetsToggle = (value: number) => {
    setMaxBets((prev) => (prev === value ? null : value));
  };

  const handleBudgetPreset = (preset: number) => {
    setBudget(preset);
    setIsCustomBudget(false);
    setCustomBudget('');
  };

  const handleCustomBudgetChange = (value: string) => {
    setCustomBudget(value);
    setIsCustomBudget(true);
    const parsed = parseInt(value, 10);
    if (!isNaN(parsed) && parsed > 0) {
      setBudget(parsed);
    }
  };

  const effectiveBudget = isCustomBudget
    ? (parseInt(customBudget, 10) || 0)
    : budget;

  const resetState = () => {
    setResult(null);
    setError(null);
    setAddedIndices(new Set());
  };

  const handleGenerate = async () => {
    if (loading) return;
    if (effectiveBudget < 100) {
      setError('予算は100円以上を指定してください');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    setAddedIndices(new Set());

    try {
      const runnersData = race.horses.map((h) => ({
        horse_number: h.number,
        horse_name: h.name,
        odds: h.odds,
        popularity: h.popularity,
        frame_number: h.wakuBan,
      }));

      // 出走馬に存在する馬番のみ抽出し、重複を除去
      const validNumbers = new Set(race.horses.map((h) => h.number));
      const axisHorses = [...new Set(
        axisInput
          .split(/[,\s、]+/)
          .map((s) => parseInt(s.trim(), 10))
          .filter((n) => !isNaN(n) && validNumbers.has(n))
      )];

      const options: {
        preferredBetTypes?: BetType[];
        axisHorses?: number[];
        characterType: string;
        maxBets?: number;
      } = { characterType: characterId };

      if (axisHorses.length > 0) options.axisHorses = axisHorses;
      if (selectedBetTypes.length > 0) options.preferredBetTypes = selectedBetTypes;
      if (maxBets !== null) options.maxBets = maxBets;

      const response = await apiClient.requestBetProposal(
        race.id,
        effectiveBudget,
        runnersData,
        options,
      );

      if (!isMountedRef.current) return;

      if (response.success && response.data) {
        setResult(response.data);
      } else {
        setError(response.error || '提案の生成に失敗しました');
      }
    } catch {
      if (!isMountedRef.current) return;
      setError('通信エラーが発生しました。再度お試しください。');
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  };

  const handleAddSingle = (index: number) => {
    if (!result) return;
    const bet = result.proposed_bets[index];

    const addResult = addItem({
      raceId: race.id,
      raceName: race.name,
      raceVenue: race.venue,
      raceNumber: race.number,
      betType: bet.bet_type,
      horseNumbers: bet.horse_numbers,
      betDisplay: bet.bet_display,
      betCount: bet.bet_count,
      amount: bet.amount ?? 0,
      runnersData: race.horses.map((h) => ({
        horse_number: h.number,
        horse_name: h.name,
        odds: h.odds,
        popularity: h.popularity,
        frame_number: h.wakuBan,
      })),
    });

    if (addResult === 'ok') {
      setAddedIndices((prev) => new Set(prev).add(index));
      showToast('カートに追加しました');
    } else {
      const message = addResult === 'different_race'
        ? 'カートには同じレースの買い目のみ追加できます'
        : '金額が範囲外です';
      showToast(message, 'error');
    }
  };

  const handleAddAll = () => {
    if (!result) return;
    let addedCount = 0;
    let firstError: AddItemResult | null = null;
    const newIndices = new Set(addedIndices);

    result.proposed_bets.forEach((bet, index) => {
      if (newIndices.has(index)) return;

      const addResult = addItem({
        raceId: race.id,
        raceName: race.name,
        raceVenue: race.venue,
        raceNumber: race.number,
        betType: bet.bet_type,
        horseNumbers: bet.horse_numbers,
        betDisplay: bet.bet_display,
        betCount: bet.bet_count,
        amount: bet.amount ?? 0,
        runnersData: race.horses.map((h) => ({
          horse_number: h.number,
          horse_name: h.name,
          odds: h.odds,
          popularity: h.popularity,
          frame_number: h.wakuBan,
        })),
      });

      if (addResult === 'ok') {
        addedCount++;
        newIndices.add(index);
      } else if (!firstError) {
        firstError = addResult;
      }
    });

    if (addedCount > 0) {
      setAddedIndices(newIndices);
      showToast(`${addedCount}件をカートに追加しました`);
    } else if (firstError) {
      const message =
        firstError === 'different_race'
          ? 'カートには同じレースの買い目のみ追加できます'
          : '金額が範囲外です';
      showToast(message, 'error');
    }
  };

  const allAdded = result
    ? result.proposed_bets.every((_, i) => addedIndices.has(i))
    : false;

  return (
    <>
      {!result && !loading && (
        <div className="proposal-form">
          {/* ペルソナ選択 */}
          <div className="proposal-form-group">
            <label className="proposal-label">AIキャラクター</label>
            <div className="proposal-character-selector">
              {AI_CHARACTERS.map((char) => (
                <button
                  key={char.id}
                  className={`proposal-character-chip ${characterId === char.id ? 'active' : ''}`}
                  aria-pressed={characterId === char.id}
                  onClick={() => handleCharacterChange(char.id)}
                >
                  <span className="proposal-character-icon">{char.icon}</span>
                  <span className="proposal-character-name">{char.name}</span>
                </button>
              ))}
            </div>
          </div>

          {/* 予算 */}
          <div className="proposal-form-group">
            <label className="proposal-label">予算</label>
            <div className="proposal-budget-presets">
              {BUDGET_PRESETS.map((preset) => (
                <button
                  key={preset}
                  className={`proposal-preset-btn ${!isCustomBudget && budget === preset ? 'active' : ''}`}
                  onClick={() => handleBudgetPreset(preset)}
                >
                  {preset.toLocaleString()}円
                </button>
              ))}
            </div>
            <input
              type="text"
              inputMode="numeric"
              className={`proposal-budget-custom-input ${isCustomBudget ? 'active' : ''}`}
              value={customBudget}
              onChange={(e) => handleCustomBudgetChange(e.target.value.replace(/[^0-9]/g, ''))}
              placeholder="自由入力（円）"
            />
          </div>

          {/* 希望券種 */}
          <div className="proposal-form-group">
            <label className="proposal-label">
              希望券種
              <span className="proposal-label-hint">未選択で自動選定</span>
            </label>
            <div className="proposal-bet-type-chips">
              {BET_TYPE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  className={`proposal-bet-type-chip ${selectedBetTypes.includes(opt.value) ? 'active' : ''}`}
                  aria-pressed={selectedBetTypes.includes(opt.value)}
                  onClick={() => handleBetTypeToggle(opt.value)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* 買い目上限 */}
          <div className="proposal-form-group">
            <label className="proposal-label">
              買い目上限
              <span className="proposal-label-hint">未選択でおまかせ</span>
            </label>
            <div className="proposal-budget-presets">
              {MAX_BETS_PRESETS.map((preset) => (
                <button
                  key={preset}
                  className={`proposal-preset-btn ${maxBets === preset ? 'active' : ''}`}
                  aria-pressed={maxBets === preset}
                  onClick={() => handleMaxBetsToggle(preset)}
                >
                  {preset}点
                </button>
              ))}
            </div>
          </div>

          {/* 注目馬 */}
          <div className="proposal-form-group">
            <label className="proposal-label" htmlFor="axis-horses-input">
              注目馬（任意）
              <span className="proposal-label-hint">カンマ区切りで馬番を入力</span>
            </label>
            <input
              id="axis-horses-input"
              type="text"
              className="proposal-axis-input"
              value={axisInput}
              onChange={(e) => setAxisInput(e.target.value)}
              placeholder="例: 3, 7"
            />
          </div>

          <button
            className="proposal-generate-btn"
            onClick={handleGenerate}
            disabled={loading}
          >
            提案を生成
          </button>
        </div>
      )}

      {loading && (
        <div className="proposal-loading">
          <div className="proposal-spinner" />
          <p>考え中...</p>
        </div>
      )}

      {error && (
        <div className="proposal-error">
          <p>{error}</p>
          <button className="proposal-retry-btn" onClick={handleGenerate}>
            再試行
          </button>
        </div>
      )}

      {result && (
        <div className="proposal-result">
          <div className="proposal-summary-card">
            <div className="proposal-summary-title">{result.race_summary.race_name}</div>
            <div className="proposal-summary-details">
              <span>難易度: {'★'.repeat(result.race_summary.difficulty_stars)}{'☆'.repeat(5 - result.race_summary.difficulty_stars)}</span>
              <span>ペース: {result.race_summary.predicted_pace}</span>
              <span>AI一致度: {result.race_summary.ai_consensus_level}</span>
            </div>
            {result.race_summary.skip_score >= 7 && (
              <div className="proposal-skip-warning">
                {result.race_summary.skip_recommendation}
              </div>
            )}
          </div>

          <div className="proposal-cards">
            {result.proposed_bets.map((bet, index) => (
              <ProposalCard
                key={index}
                bet={bet}
                onAddToCart={() => handleAddSingle(index)}
                isAdded={addedIndices.has(index)}
              />
            ))}
          </div>

          <div className="proposal-total">
            <span>合計: {result.total_amount.toLocaleString()}円</span>
            <span>残り予算: {result.budget_remaining.toLocaleString()}円</span>
          </div>

          {result.analysis_comment && (
            <p className="proposal-analysis-comment">{result.analysis_comment}</p>
          )}

          <button
            className={`proposal-add-all-btn ${allAdded ? 'added' : ''}`}
            onClick={handleAddAll}
            disabled={allAdded}
          >
            {allAdded ? '全て追加済み' : '全てカートに追加'}
          </button>

          <button
            className="proposal-back-btn"
            onClick={resetState}
          >
            条件を変更して再提案
          </button>

          {result.disclaimer && (
            <p className="proposal-disclaimer">{result.disclaimer}</p>
          )}
        </div>
      )}
    </>
  );
}
