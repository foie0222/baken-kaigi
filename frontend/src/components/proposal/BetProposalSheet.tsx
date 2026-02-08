import { useState, useRef } from 'react';
import { BottomSheet } from '../common/BottomSheet';
import { ProposalCard } from './ProposalCard';
import { apiClient } from '../../api/client';
import { useCartStore } from '../../stores/cartStore';
import { useAppStore } from '../../stores/appStore';
import type { RaceDetail, BetProposalResponse } from '../../types';
import './BetProposalSheet.css';

interface BetProposalSheetProps {
  isOpen: boolean;
  onClose: () => void;
  race: RaceDetail;
}

const BUDGET_PRESETS = [1000, 3000, 5000, 10000];

export function BetProposalSheet({ isOpen, onClose, race }: BetProposalSheetProps) {
  const addItem = useCartStore((state) => state.addItem);
  const showToast = useAppStore((state) => state.showToast);

  const [budget, setBudget] = useState(3000);
  const [axisInput, setAxisInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BetProposalResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [addedIndices, setAddedIndices] = useState<Set<number>>(new Set());
  const isMountedRef = useRef(true);

  const resetState = () => {
    setResult(null);
    setError(null);
    setAddedIndices(new Set());
  };

  const handleClose = () => {
    isMountedRef.current = false;
    resetState();
    setLoading(false);
    onClose();
  };

  const handleGenerate = async () => {
    isMountedRef.current = true;
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

      const response = await apiClient.requestBetProposal(
        race.id,
        budget,
        runnersData,
        axisHorses.length > 0 ? { axisHorses } : undefined
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

    const result = addItem({
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

    if (result === 'ok') {
      setAddedIndices((prev) => new Set(prev).add(index));
      showToast('カートに追加しました');
    } else {
      const message = result === 'different_race'
        ? 'カートには同じレースの買い目のみ追加できます'
        : '金額が範囲外です';
      showToast(message, 'error');
    }
  };

  const handleAddAll = () => {
    if (!result) return;
    let addedCount = 0;
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
      }
    });

    if (addedCount > 0) {
      setAddedIndices(newIndices);
      showToast(`${addedCount}件をカートに追加しました`);
    }
  };

  const allAdded = result
    ? result.proposed_bets.every((_, i) => addedIndices.has(i))
    : false;

  return (
    <BottomSheet isOpen={isOpen} onClose={handleClose} title="AI買い目提案">
      {!result && !loading && (
        <div className="proposal-form">
          <div className="proposal-form-group">
            <label className="proposal-label">予算</label>
            <div className="proposal-budget-presets">
              {BUDGET_PRESETS.map((preset) => (
                <button
                  key={preset}
                  className={`proposal-preset-btn ${budget === preset ? 'active' : ''}`}
                  onClick={() => setBudget(preset)}
                >
                  {preset.toLocaleString()}円
                </button>
              ))}
            </div>
          </div>

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
    </BottomSheet>
  );
}
