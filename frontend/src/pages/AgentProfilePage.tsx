import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAgentStore } from '../stores/agentStore';
import { AGENT_STYLES, AGENT_STYLE_MAP } from '../constants/agentStyles';
import { BET_TYPE_PREFERENCE_OPTIONS } from '../constants/bettingPreferences';
import { apiClient } from '../api/client';
import type { Agent, AgentReview, BetTypePreference } from '../types';

const LEVEL_TITLES: Record<number, string> = {
  1: '駆け出し',
  2: '見習い',
  3: '一人前',
  4: 'ベテラン',
  5: '熟練',
  6: '達人',
  7: '名人',
  8: '鉄人',
  9: '伝説',
  10: '神',
};

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
  const { agent, fetchAgent, updateAgent } = useAgentStore();
  const [reviews, setReviews] = useState<AgentReview[]>([]);
  const [isLoadingReviews, setIsLoadingReviews] = useState(true);
  const [isEditingStyle, setIsEditingStyle] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [styleError, setStyleError] = useState<string | null>(null);

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

  const styleInfo = AGENT_STYLE_MAP[agent.base_style];
  const levelTitle = LEVEL_TITLES[agent.level];
  const color = styleInfo.color;

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
          background: `${color}15`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 32,
          margin: '0 auto 10px',
        }}>
          {styleInfo.icon}
        </div>
        <div style={{ fontSize: 20, fontWeight: 700, color: '#111' }}>{agent.name}</div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginTop: 4 }}>
          <span style={{
            fontSize: 12,
            fontWeight: 600,
            color,
            background: `${color}12`,
            padding: '2px 10px',
            borderRadius: 10,
          }}>
            {styleInfo.label}
          </span>
          <span style={{ fontSize: 13, color: '#666' }}>Lv.{agent.level} {levelTitle}</span>
          <button
            type="button"
            onClick={() => setIsEditingStyle(!isEditingStyle)}
            style={{
              fontSize: 12,
              color: '#1a73e8',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: 0,
            }}
          >
            {isEditingStyle ? '閉じる' : '変更'}
          </button>
        </div>

        {isEditingStyle && (
          <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            {AGENT_STYLES.map((style) => {
              const isSelected = agent.base_style === style.id;
              return (
                <button
                  key={style.id}
                  type="button"
                  disabled={isUpdating}
                  aria-label={`${style.label}スタイルを選択${isSelected ? '（選択中）' : ''}`}
                  onClick={async () => {
                    if (style.id === agent.base_style) return;
                    setStyleError(null);
                    setIsUpdating(true);
                    const success = await updateAgent(style.id);
                    if (success) {
                      setIsEditingStyle(false);
                    } else {
                      const { error } = useAgentStore.getState();
                      setStyleError(error || 'スタイルの変更に失敗しました');
                    }
                    setIsUpdating(false);
                  }}
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    padding: 12,
                    border: isSelected ? `2px solid ${style.color}` : '2px solid #e5e7eb',
                    borderRadius: 10,
                    background: isSelected ? `${style.color}08` : 'white',
                    cursor: isSelected ? 'default' : 'pointer',
                    opacity: isUpdating ? 0.5 : 1,
                  }}
                >
                  <span style={{ fontSize: 24, marginBottom: 4 }}>{style.icon}</span>
                  <span style={{ fontSize: 12, fontWeight: 600, color: isSelected ? style.color : '#333' }}>
                    {style.label}
                  </span>
                </button>
              );
            })}
          </div>
        )}

        {styleError && (
          <div style={{ marginTop: 10, fontSize: 12, color: '#dc2626' }}>
            {styleError}
          </div>
        )}

        {/* 成績サマリー */}
        {agent.performance.total_bets > 0 && (
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            gap: 24,
            marginTop: 16,
            paddingTop: 16,
            borderTop: '1px solid #f0f0f0',
          }}>
            <div>
              <div style={{ fontSize: 11, color: '#888' }}>戦績</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#333' }}>
                {agent.performance.total_bets}戦{agent.performance.wins}勝
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#888' }}>収支</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: agent.profit >= 0 ? '#059669' : '#dc2626' }}>
                {agent.profit >= 0 ? '+' : ''}{agent.profit.toLocaleString()}円
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: '#888' }}>回収率</div>
              <div style={{ fontSize: 14, fontWeight: 600, color: '#333' }}>
                {agent.roi.toFixed(1)}%
              </div>
            </div>
          </div>
        )}
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


function BettingPreferenceForm({ agent }: { agent: Agent }) {
  const { updateAgent } = useAgentStore();

  const [betTypePref, setBetTypePref] = useState<BetTypePreference>(agent.betting_preference?.bet_type_preference ?? 'auto');
  const [customInstructions, setCustomInstructions] = useState<string>(agent.custom_instructions ?? '');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

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
            undefined,
            {
              bet_type_preference: betTypePref,
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
