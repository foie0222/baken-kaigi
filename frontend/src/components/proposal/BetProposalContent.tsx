import { useState, useRef, useEffect } from 'react';
import { ProposalCard } from './ProposalCard';
import { apiClient } from '../../api/client';
import { useCartStore, type AddItemResult } from '../../stores/cartStore';
import { useAppStore } from '../../stores/appStore';
import { useAuthStore } from '../../stores/authStore';
import { useAgentStore } from '../../stores/agentStore';
import { extractOdds, type BetType, type AllOddsResponse } from '../../types';
import type { RaceDetail, BetProposalResponse } from '../../types';
import './BetProposalSheet.css';

interface BetProposalContentProps {
  race: RaceDetail;
}

export function BetProposalContent({ race }: BetProposalContentProps) {
  const addItem = useCartStore((state) => state.addItem);
  const showToast = useAppStore((state) => state.showToast);
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const agent = useAgentStore((state) => state.agent);
  const hasFetched = useAgentStore((state) => state.hasFetched);
  const fetchAgent = useAgentStore((state) => state.fetchAgent);
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

  useEffect(() => {
    if (isAuthenticated && !hasFetched) {
      fetchAgent();
    }
  }, [isAuthenticated, hasFetched, fetchAgent]);

  const resetState = () => {
    setResult(null);
    setError(null);
    setAddedIndices(new Set());
  };

  const handleGenerate = async () => {
    if (loading) return;
    setError(null);
    setLoading(true);
    setResult(null);
    setAddedIndices(new Set());

    try {
      const response = await apiClient.requestBetProposal(race.id);

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

  const handleAddSingle = async (index: number) => {
    if (!result) return;
    const bet = result.proposed_bets[index];

    // オッズ取得（失敗してもカート追加はブロックしない）
    let odds: number | undefined;
    let oddsMin: number | undefined;
    let oddsMax: number | undefined;
    try {
      const oddsResult = await apiClient.getAllOdds(race.id);
      if (oddsResult.success && oddsResult.data) {
        const extracted = extractOdds(oddsResult.data, bet.bet_type as BetType, bet.horse_numbers);
        odds = extracted.odds;
        oddsMin = extracted.oddsMin;
        oddsMax = extracted.oddsMax;
      }
    } catch (error: unknown) {
      console.warn('Failed to fetch odds in handleAddSingle:', error);
    }

    const addResult = addItem({
      raceId: race.id,
      raceName: race.name,
      raceVenue: race.venue,
      raceNumber: race.number,
      betType: bet.bet_type,
      betMethod: 'normal',
      horseNumbers: bet.horse_numbers,
      betDisplay: bet.bet_display,
      betCount: bet.bet_count,
      amount: bet.amount,
      odds,
      oddsMin,
      oddsMax,
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

    // 全券種オッズを1回で取得（失敗してもカート追加はブロックしない）
    let allOddsData: AllOddsResponse | undefined;
    try {
      const oddsResult = await apiClient.getAllOdds(race.id);
      if (oddsResult.success && oddsResult.data) {
        allOddsData = oddsResult.data;
      }
    } catch (error) {
      console.warn('Failed to fetch all odds:', error);
    }

    betsToAdd.forEach(({ bet, index }) => {
      const oddsData = allOddsData
        ? extractOdds(allOddsData, bet.bet_type as BetType, bet.horse_numbers)
        : { odds: undefined, oddsMin: undefined, oddsMax: undefined };

      const addResult = addItem({
        raceId: race.id,
        raceName: race.name,
        raceVenue: race.venue,
        raceNumber: race.number,
        betType: bet.bet_type,
        betMethod: 'normal',
        horseNumbers: bet.horse_numbers,
        betDisplay: bet.bet_display,
        betCount: bet.bet_count,
        amount: bet.amount,
        odds: oddsData.odds,
        oddsMin: oddsData.oddsMin,
        oddsMax: oddsData.oddsMax,
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
          {agent ? (
            <button
              className="proposal-generate-btn"
              onClick={handleGenerate}
              disabled={loading}
            >
              {agent.name}に提案してもらう
            </button>
          ) : (
            <p className="proposal-no-agent-message">
              エージェントを設定すると買い目提案を利用できます
            </p>
          )}
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
              <span>AI一致度: {result.race_summary.ai_consensus_level}</span>
            </div>
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
            再提案
          </button>

          {result.disclaimer && (
            <p className="proposal-disclaimer">{result.disclaimer}</p>
          )}
        </div>
      )}
    </>
  );
}
