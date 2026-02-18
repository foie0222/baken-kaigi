import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAgentStore } from '../stores/agentStore';
import { BET_TYPE_PREFERENCE_OPTIONS } from '../constants/bettingPreferences';
import { apiClient } from '../api/client';
import type { Agent, AgentReview, BetTypePreference } from '../types';

function ReviewCard({ review }: { review: AgentReview }) {
  return (
    <div style={{
      background: 'white',
      borderRadius: 10,
      padding: '14px 16px',
      marginBottom: 10,
      border: '1px solid #eee',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div>
          <span style={{ fontSize: 14, fontWeight: 600, color: '#111' }}>{review.race_name}</span>
          <span style={{ fontSize: 11, color: '#888', marginLeft: 8 }}>{review.race_date}</span>
        </div>
        <span style={{
          fontSize: 12,
          fontWeight: 600,
          color: review.has_win ? '#059669' : '#dc2626',
          background: review.has_win ? '#ecfdf5' : '#fef2f2',
          padding: '2px 8px',
          borderRadius: 8,
        }}>
          {review.has_win ? (review.profit > 0 ? 'WIN' : 'トリガミ') : 'LOSE'}
        </span>
      </div>

      <div style={{ display: 'flex', gap: 16, marginBottom: 10, fontSize: 12, color: '#555' }}>
        <span>投資: {review.total_invested.toLocaleString()}円</span>
        <span>回収: {review.total_return.toLocaleString()}円</span>
        <span style={{ fontWeight: 600, color: review.profit >= 0 ? '#059669' : '#dc2626' }}>
          {review.profit >= 0 ? '+' : ''}{review.profit.toLocaleString()}円
        </span>
      </div>

      <p style={{ fontSize: 13, color: '#333', lineHeight: 1.6, margin: '0 0 8px' }}>
        {review.review_text}
      </p>

      {review.learnings.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {review.learnings.map((learning, i) => (
            <div key={i} style={{ fontSize: 12, color: '#666', padding: '2px 0' }}>
              - {learning}
            </div>
          ))}
        </div>
      )}

    </div>
  );
}

export function AgentProfilePage() {
  const navigate = useNavigate();
  const { agent, fetchAgent } = useAgentStore();
  const [reviews, setReviews] = useState<AgentReview[]>([]);
  const [isLoadingReviews, setIsLoadingReviews] = useState(true);

  useEffect(() => {
    fetchAgent();
  }, [fetchAgent]);

  useEffect(() => {
    const loadReviews = async () => {
      setIsLoadingReviews(true);
      const result = await apiClient.getAgentReviews();
      if (result.success && result.data) {
        setReviews(result.data);
      }
      setIsLoadingReviews(false);
    };
    loadReviews();
  }, []);

  if (!agent) {
    return (
      <div className="fade-in" style={{ padding: '20px 0' }}>
        <button className="back-btn" onClick={() => navigate('/')}>
          &larr; 戻る
        </button>
        <div style={{ textAlign: 'center', padding: '40px 0', color: '#888' }}>
          エージェントが見つかりません
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in" style={{ padding: '0 0 20px' }}>
      <button className="back-btn" onClick={() => navigate('/')}>
        &larr; 戻る
      </button>

      {/* ヘッダー */}
      <div style={{
        background: 'white',
        borderRadius: 14,
        padding: '20px 16px',
        marginBottom: 16,
        textAlign: 'center',
      }}>
        <div style={{
          width: 64,
          height: 64,
          borderRadius: '50%',
          background: '#2563eb15',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 32,
          margin: '0 auto 10px',
        }}>
          {'\u{1F3C7}'}
        </div>
        <div style={{ fontSize: 20, fontWeight: 700, color: '#111' }}>{agent.name}</div>
      </div>

      {/* 好み設定 - keyでagent変更時に再マウントし初期値をリセット */}
      {agent && (
        <BettingPreferenceForm key={agent.agent_id} agent={agent} />
      )}

      {/* 振り返り履歴 */}
      <div style={{ marginBottom: 16 }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#333', margin: '0 0 12px', padding: '0 4px' }}>
          振り返り履歴
        </h3>
        {isLoadingReviews ? (
          <div style={{ textAlign: 'center', padding: '20px 0', color: '#888', fontSize: 13 }}>
            読み込み中...
          </div>
        ) : reviews.length === 0 ? (
          <div style={{
            background: 'white',
            borderRadius: 10,
            padding: '24px 16px',
            textAlign: 'center',
            color: '#888',
            fontSize: 13,
          }}>
            まだ振り返りがありません
          </div>
        ) : (
          reviews.map((review) => (
            <ReviewCard key={review.review_id} review={review} />
          ))
        )}
      </div>
    </div>
  );
}


function RangeSlider({
  label,
  minValue,
  maxValue,
  rangeMin,
  rangeMax,
  step,
  formatValue,
  onMinChange,
  onMaxChange,
}: {
  label: string;
  minValue: number;
  maxValue: number;
  rangeMin: number;
  rangeMax: number;
  step: number;
  formatValue: (v: number) => string;
  onMinChange: (v: number) => void;
  onMaxChange: (v: number) => void;
}) {
  const minDisplay = formatValue(minValue);
  const maxDisplay = maxValue >= rangeMax ? 'なし' : formatValue(maxValue);
  const minPercent = ((minValue - rangeMin) / (rangeMax - rangeMin)) * 100;
  const maxPercent = ((maxValue - rangeMin) / (rangeMax - rangeMin)) * 100;

  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div style={{ fontSize: 12, color: '#666' }}>{label}</div>
        <div style={{ fontSize: 12, color: '#1a73e8', fontWeight: 600 }}>
          {minDisplay} 〜 {maxDisplay}
        </div>
      </div>
      <div style={{ position: 'relative', height: 36 }}>
        {/* トラック背景 */}
        <div style={{
          position: 'absolute',
          top: 16,
          left: 0,
          right: 0,
          height: 4,
          borderRadius: 2,
          background: '#e5e7eb',
        }} />
        {/* 選択範囲ハイライト */}
        <div style={{
          position: 'absolute',
          top: 16,
          left: `${minPercent}%`,
          width: `${maxPercent - minPercent}%`,
          height: 4,
          borderRadius: 2,
          background: '#1a73e8',
        }} />
        {/* 下限スライダー */}
        <input
          type="range"
          min={rangeMin}
          max={rangeMax}
          step={step}
          value={minValue}
          aria-label={`${label}の下限`}
          onChange={(e) => {
            const val = Number(e.target.value);
            if (val <= maxValue) onMinChange(val);
          }}
          className="range-slider-thumb"
          style={{
            position: 'absolute',
            top: 0,
            width: '100%',
            height: 36,
            zIndex: minValue > rangeMax - step ? 5 : 3,
          }}
        />
        {/* 上限スライダー */}
        <input
          type="range"
          min={rangeMin}
          max={rangeMax}
          step={step}
          value={maxValue}
          aria-label={`${label}の上限`}
          onChange={(e) => {
            const val = Number(e.target.value);
            if (val >= minValue) onMaxChange(val);
          }}
          className="range-slider-thumb"
          style={{
            position: 'absolute',
            top: 0,
            width: '100%',
            height: 36,
            zIndex: 4,
          }}
        />
      </div>
    </div>
  );
}

function BettingPreferenceForm({ agent }: { agent: Agent }) {
  const { updateAgent } = useAgentStore();

  const [betTypePref, setBetTypePref] = useState<BetTypePreference>(agent.betting_preference?.bet_type_preference ?? 'auto');
  const [customInstructions, setCustomInstructions] = useState<string>(agent.custom_instructions ?? '');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [minProb, setMinProb] = useState<number>((agent.betting_preference?.min_probability ?? 0) * 100);
  const [maxProb, setMaxProb] = useState<number>(
    agent.betting_preference?.max_probability != null ? agent.betting_preference.max_probability * 100 : 50,
  );
  const [minEv, setMinEv] = useState<number>(agent.betting_preference?.min_ev ?? 0);
  const [maxEv, setMaxEv] = useState<number>(agent.betting_preference?.max_ev ?? 10.0);
  const [raceBudget, setRaceBudget] = useState<number>(agent.betting_preference?.race_budget ?? 0);

  return (
    <div style={{
      background: 'white',
      borderRadius: 14,
      padding: '20px 16px',
      marginBottom: 16,
    }}>
      <h3 style={{ fontSize: 14, fontWeight: 600, color: '#333', margin: '0 0 16px' }}>
        好み設定
      </h3>

      {/* 券種の好み */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>券種の好み</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {BET_TYPE_PREFERENCE_OPTIONS.map((opt) => {
            const isSelected = betTypePref === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => setBetTypePref(opt.value)}
                aria-pressed={isSelected}
                style={{
                  fontSize: 13,
                  fontWeight: isSelected ? 600 : 400,
                  color: isSelected ? '#1a73e8' : '#555',
                  background: isSelected ? '#e8f0fe' : '#f5f5f5',
                  border: isSelected ? '1.5px solid #1a73e8' : '1.5px solid transparent',
                  borderRadius: 20,
                  padding: '6px 14px',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* 確率フィルター */}
      <RangeSlider
        label="確率フィルター"
        minValue={minProb}
        maxValue={maxProb}
        rangeMin={0}
        rangeMax={50}
        step={1}
        formatValue={(v) => `${v}%`}
        onMinChange={setMinProb}
        onMaxChange={setMaxProb}
      />

      {/* 期待値フィルター */}
      <RangeSlider
        label="期待値フィルター"
        minValue={minEv}
        maxValue={maxEv}
        rangeMin={0}
        rangeMax={10.0}
        step={0.5}
        formatValue={(v) => `${v.toFixed(1)}`}
        onMinChange={setMinEv}
        onMaxChange={setMaxEv}
      />

      {/* 1レースあたりの予算 */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>1レースあたりの予算</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 8 }}>
          {[1000, 3000, 5000, 10000].map((amount) => {
            const isSelected = raceBudget === amount;
            return (
              <button
                key={amount}
                type="button"
                onClick={() => setRaceBudget(amount)}
                aria-pressed={isSelected}
                style={{
                  fontSize: 13,
                  fontWeight: isSelected ? 600 : 400,
                  color: isSelected ? '#1a73e8' : '#555',
                  background: isSelected ? '#e8f0fe' : '#f5f5f5',
                  border: isSelected ? '1.5px solid #1a73e8' : '1.5px solid transparent',
                  borderRadius: 20,
                  padding: '6px 14px',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                {amount.toLocaleString()}円
              </button>
            );
          })}
        </div>
        <input
          type="number"
          min={0}
          max={1000000}
          step={100}
          value={raceBudget || ''}
          placeholder="自由入力（円）"
          onChange={(e) => {
            const val = e.target.value === '' ? 0 : parseInt(e.target.value, 10);
            if (!isNaN(val) && val >= 0 && val <= 1000000) {
              setRaceBudget(val);
            }
          }}
          style={{
            width: '100%',
            padding: '8px 12px',
            fontSize: 13,
            border: '1px solid #e5e7eb',
            borderRadius: 8,
            boxSizing: 'border-box',
          }}
        />
      </div>

      {/* 追加指示 */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
          <div style={{ fontSize: 12, color: '#666' }}>追加指示</div>
          <div style={{ fontSize: 11, color: customInstructions.length > 200 ? '#dc2626' : '#999' }}>
            {customInstructions.length}/200
          </div>
        </div>
        <textarea
          value={customInstructions}
          onChange={(e) => {
            if (e.target.value.length <= 200) {
              setCustomInstructions(e.target.value);
            }
          }}
          placeholder="例: 三連単の1着固定が好き、逃げ馬を軸にしたい"
          style={{
            width: '100%',
            minHeight: 80,
            padding: '10px 12px',
            fontSize: 13,
            border: '1px solid #e5e7eb',
            borderRadius: 8,
            resize: 'vertical',
            fontFamily: 'inherit',
            boxSizing: 'border-box',
          }}
        />
      </div>

      {/* 保存ボタン */}
      <button
        type="button"
        disabled={isSaving}
        onClick={async () => {
          setError(null);
          setSaved(false);
          setIsSaving(true);
          const success = await updateAgent(
            {
              bet_type_preference: betTypePref,
              min_probability: minProb / 100,
              min_ev: minEv,
              max_probability: maxProb >= 50 ? null : maxProb / 100,
              max_ev: maxEv >= 10.0 ? null : maxEv,
              race_budget: raceBudget > 0 ? raceBudget : undefined,
            },
            customInstructions === '' ? null : customInstructions,
          );
          if (success) {
            setSaved(true);
            setTimeout(() => setSaved(false), 2000);
          } else {
            const { error: storeError } = useAgentStore.getState();
            setError(storeError || '好み設定の保存に失敗しました');
          }
          setIsSaving(false);
        }}
        style={{
          width: '100%',
          padding: '10px 0',
          fontSize: 14,
          fontWeight: 600,
          color: 'white',
          background: isSaving ? '#93c5fd' : '#1a73e8',
          border: 'none',
          borderRadius: 10,
          cursor: isSaving ? 'default' : 'pointer',
          transition: 'background 0.15s',
        }}
      >
        {isSaving ? '保存中...' : '好み設定を保存'}
      </button>

      {error && (
        <div style={{ marginTop: 10, fontSize: 12, color: '#dc2626', textAlign: 'center' }}>
          {error}
        </div>
      )}
      {saved && (
        <div style={{ marginTop: 10, fontSize: 12, color: '#059669', textAlign: 'center' }}>
          保存しました
        </div>
      )}
    </div>
  );
}
