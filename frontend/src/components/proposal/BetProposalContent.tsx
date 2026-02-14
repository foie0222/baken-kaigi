import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ProposalCard } from './ProposalCard';
import { apiClient, type UsageInfo } from '../../api/client';
import { useCartStore, type AddItemResult } from '../../stores/cartStore';
import { useAppStore } from '../../stores/appStore';
import { useAuthStore } from '../../stores/authStore';
import { AI_CHARACTERS, DEFAULT_CHARACTER_ID, STORAGE_KEY_CHARACTER, type CharacterId } from '../../constants/characters';
import { MIN_BET_AMOUNT, MAX_BET_AMOUNT } from '../../constants/betting';
import { BetTypeLabels, BetTypeToApiName, type BetType } from '../../types';
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
  const navigate = useNavigate();
  const addItem = useCartStore((state) => state.addItem);
  const showToast = useAppStore((state) => state.showToast);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

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
  const [usage, setUsage] = useState<UsageInfo | null>(null);
  const [rateLimited, setRateLimited] = useState(false);
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
    setError(null);
    setRateLimited(false);
    if (effectiveBudget < MIN_BET_AMOUNT) {
      setError(`予算は${MIN_BET_AMOUNT.toLocaleString()}円以上を指定してください`);
      return;
    }
    if (effectiveBudget > MAX_BET_AMOUNT) {
      setError(`予算は${MAX_BET_AMOUNT.toLocaleString()}円以下を指定してください`);
      return;
    }
    setLoading(true);
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
        // 429 利用制限の場合は usage 情報を取得
        const responseData = response.data as unknown as { usage?: UsageInfo } | undefined;
        if (responseData?.usage) {
          setUsage(responseData.usage);
          setRateLimited(true);
        }
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

  const handleAddSingle = async (index: number) => {
    if (!result) return;
    const bet = result.proposed_bets[index];

    // オッズ取得（失敗してもカート追加はブロックしない）
    let odds: number | undefined;
    let oddsMin: number | undefined;
    let oddsMax: number | undefined;
    try {
      const apiName = BetTypeToApiName[bet.bet_type];
      const oddsResult = await apiClient.getBetOdds(race.id, apiName, bet.horse_numbers);
      if (oddsResult.success && oddsResult.data) {
        odds = oddsResult.data.odds ?? undefined;
        oddsMin = oddsResult.data.odds_min ?? undefined;
        oddsMax = oddsResult.data.odds_max ?? undefined;
      }
    } catch {
      // オッズ取得失敗はカート追加をブロックしない
    }

    const addResult = addItem({
      raceId: race.id,
      raceName: race.name,
      raceVenue: race.venue,
      raceNumber: race.number,
      betType: bet.bet_type,
      horseNumbers: bet.horse_numbers,
      betDisplay: bet.bet_display,
      betCount: bet.bet_count ?? 1,
      amount: bet.amount ?? 0,
      odds,
      oddsMin,
      oddsMax,
      runnersData: race.horses.map((h) => ({
        horse_number: h.number,
        horse_name: h.name,
        odds: h.odds,
        popularity: h.popularity,
        frame_number: h.wakuBan,
      })),
    });

    if (addResult === 'ok' || addResult === 'merged') {
      setAddedIndices((prev) => new Set(prev).add(index));
      showToast(addResult === 'merged' ? '同じ買い目の金額を合算しました' : 'カートに追加しました');
    } else {
      const message = addResult === 'different_race'
        ? 'カートには同じレースの買い目のみ追加できます'
        : '金額が範囲外です';
      showToast(message, 'error');
    }
  };

  const handleAddAll = async () => {
    if (!result) return;
    let addedCount = 0;
    let firstError: AddItemResult | null = null;
    const newIndices = new Set(addedIndices);

    // 未追加の買い目のみ処理
    const betsToAdd = result.proposed_bets
      .map((bet, index) => ({ bet, index }))
      .filter(({ index }) => !newIndices.has(index));

    // 全買い目のオッズを並列取得（失敗してもカート追加はブロックしない）
    const oddsResults = await Promise.allSettled(
      betsToAdd.map(async ({ bet }) => {
        try {
          const apiName = BetTypeToApiName[bet.bet_type];
          const oddsResult = await apiClient.getBetOdds(race.id, apiName, bet.horse_numbers);
          if (oddsResult.success && oddsResult.data) {
            return {
              odds: oddsResult.data.odds ?? undefined,
              oddsMin: oddsResult.data.odds_min ?? undefined,
              oddsMax: oddsResult.data.odds_max ?? undefined,
            };
          }
        } catch {
          // オッズ取得失敗はカート追加をブロックしない
        }
        return { odds: undefined, oddsMin: undefined, oddsMax: undefined };
      })
    );

    betsToAdd.forEach(({ bet, index }, i) => {
      const oddsData = oddsResults[i].status === 'fulfilled'
        ? oddsResults[i].value
        : { odds: undefined, oddsMin: undefined, oddsMax: undefined };

      const addResult = addItem({
        raceId: race.id,
        raceName: race.name,
        raceVenue: race.venue,
        raceNumber: race.number,
        betType: bet.bet_type,
        horseNumbers: bet.horse_numbers,
        betDisplay: bet.bet_display,
        betCount: bet.bet_count ?? 1,
        amount: bet.amount ?? 0,
        odds: oddsData.odds,
        oddsMin: oddsData.oddsMin,
        oddsMax: oddsData.oddsMax,
        runnersData: race.horses.map((h) => ({
          horse_number: h.number,
          horse_name: h.name,
          odds: h.odds,
          popularity: h.popularity,
          frame_number: h.wakuBan,
        })),
      });

      if (addResult === 'ok' || addResult === 'merged') {
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
          {rateLimited ? (
            <div className="proposal-rate-limit">
              {usage && (
                <p className="proposal-usage-badge">
                  本日 {usage.consulted_races}/{usage.max_races} レース利用済み
                </p>
              )}
              {!isAuthenticated ? (
                <button className="proposal-cta-btn" onClick={() => navigate('/signup/age')}>
                  会員登録（無料）で1日3レースまで予想可能
                </button>
              ) : (
                <p className="proposal-limit-message">明日になると予想枠がリセットされます</p>
              )}
            </div>
          ) : (
            <button className="proposal-retry-btn" onClick={handleGenerate}>
              再試行
            </button>
          )}
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

          {result.proposal_reasoning && (
            <div className="proposal-reasoning-section">
              <div className="proposal-reasoning-title">提案の根拠</div>
              <div className="proposal-reasoning-body">
                {result.proposal_reasoning.split('\n').map((line, i) => {
                  const headingMatch = line.match(/^【(.+?)】(.*)$/);
                  if (headingMatch) {
                    return (
                      <p key={i}>
                        <strong>【{headingMatch[1]}】</strong>{headingMatch[2]}
                      </p>
                    );
                  }
                  return line ? <p key={i}>{line}</p> : null;
                })}
              </div>
            </div>
          )}

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
