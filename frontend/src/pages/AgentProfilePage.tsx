import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAgentStore } from '../stores/agentStore';
import { AGENT_STYLE_MAP } from '../constants/agentStyles';
import { apiClient } from '../api/client';
import type { AgentReview } from '../types';

const STAT_LABELS: Record<string, string> = {
  data_analysis: 'データ分析',
  pace_reading: '展開読み',
  risk_management: 'リスク管理',
  intuition: '直感',
};

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

function StatBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 12, color: '#555' }}>{label}</span>
        <span style={{ fontSize: 12, fontWeight: 600, color: '#333' }}>{value}</span>
      </div>
      <div style={{ height: 6, background: '#e8e8e8', borderRadius: 3 }}>
        <div style={{
          height: '100%',
          width: `${value}%`,
          background: color,
          borderRadius: 3,
          transition: 'width 0.3s ease',
        }} />
      </div>
    </div>
  );
}

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

      {Object.keys(review.stats_change).length > 0 && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
          {Object.entries(review.stats_change).map(([stat, change]) => (
            <span key={stat} style={{
              fontSize: 10,
              color: '#059669',
              background: '#ecfdf5',
              padding: '2px 6px',
              borderRadius: 6,
            }}>
              {STAT_LABELS[stat] || stat} +{change}
            </span>
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

  const styleInfo = AGENT_STYLE_MAP[agent.base_style];
  const levelTitle = LEVEL_TITLES[agent.level] || '駆け出し';
  const color = styleInfo?.color || '#666';

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
          {styleInfo?.icon || '\u{1F916}'}
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
            {styleInfo?.label || agent.base_style}
          </span>
          <span style={{ fontSize: 13, color: '#666' }}>Lv.{agent.level} {levelTitle}</span>
        </div>

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

      {/* 能力値 */}
      <div style={{
        background: 'white',
        borderRadius: 14,
        padding: '16px',
        marginBottom: 16,
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#333', margin: '0 0 12px' }}>
          能力値
        </h3>
        <StatBar label="データ分析" value={agent.stats.data_analysis} color="#3b82f6" />
        <StatBar label="展開読み" value={agent.stats.pace_reading} color="#8b5cf6" />
        <StatBar label="リスク管理" value={agent.stats.risk_management} color="#059669" />
        <StatBar label="直感" value={agent.stats.intuition} color="#f59e0b" />
      </div>

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
