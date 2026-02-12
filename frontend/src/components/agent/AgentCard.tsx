import { useNavigate } from 'react-router-dom';
import type { Agent } from '../../types';
import { AGENT_STYLE_MAP } from '../../constants/agentStyles';

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

interface AgentCardProps {
  agent: Agent;
}

export function AgentCard({ agent }: AgentCardProps) {
  const navigate = useNavigate();
  const styleInfo = AGENT_STYLE_MAP[agent.base_style];
  const levelTitle = LEVEL_TITLES[agent.level] || '駆け出し';

  return (
    <button
      type="button"
      onClick={() => navigate('/dashboard')}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        background: 'white',
        borderRadius: 12,
        padding: '14px 16px',
        marginBottom: 12,
        border: 'none',
        width: '100%',
        cursor: 'pointer',
        textAlign: 'left',
      }}
    >
      {/* アイコン */}
      <div style={{
        width: 48,
        height: 48,
        borderRadius: '50%',
        background: `${styleInfo?.color || '#666'}15`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 24,
        flexShrink: 0,
      }}>
        {styleInfo?.icon || '\u{1F916}'}
      </div>

      {/* 名前・レベル */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 15, fontWeight: 600, color: '#111' }}>
            {agent.name}
          </span>
          <span style={{
            fontSize: 11,
            fontWeight: 600,
            color: styleInfo?.color || '#666',
            background: `${styleInfo?.color || '#666'}12`,
            padding: '2px 8px',
            borderRadius: 10,
          }}>
            {styleInfo?.label || agent.base_style}
          </span>
        </div>
        <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>
          Lv.{agent.level} {levelTitle}
          {agent.performance.total_bets > 0 && (
            <span> · {agent.performance.total_bets}戦</span>
          )}
        </div>
      </div>

      {/* 成績 */}
      {agent.performance.total_bets > 0 && (
        <div style={{ textAlign: 'right', flexShrink: 0 }}>
          <div style={{ fontSize: 13, fontWeight: 600, color: agent.profit >= 0 ? '#059669' : '#dc2626' }}>
            {agent.profit >= 0 ? '+' : ''}{agent.profit.toLocaleString()}円
          </div>
          <div style={{ fontSize: 11, color: '#888' }}>
            回収率 {agent.roi.toFixed(1)}%
          </div>
        </div>
      )}

      <span style={{ color: '#ccc', fontSize: 16, flexShrink: 0 }}>&rsaquo;</span>
    </button>
  );
}

export function AgentOnboardingCard() {
  const navigate = useNavigate();

  return (
    <button
      type="button"
      onClick={() => navigate('/onboarding')}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 14,
        background: 'linear-gradient(135deg, #f0f7ff 0%, #e8f0fe 100%)',
        borderRadius: 12,
        padding: '14px 16px',
        marginBottom: 12,
        border: '1px dashed #93b4e8',
        width: '100%',
        cursor: 'pointer',
        textAlign: 'left',
      }}
    >
      <div style={{
        width: 48,
        height: 48,
        borderRadius: '50%',
        background: '#dbeafe',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 24,
        flexShrink: 0,
      }}>
        {'\u{2795}'}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 14, fontWeight: 600, color: '#1a73e8' }}>
          AIエージェントを作成
        </div>
        <div style={{ fontSize: 12, color: '#5f8dc0', marginTop: 2 }}>
          あなた専用の分析パートナーを育てよう
        </div>
      </div>
      <span style={{ color: '#93b4e8', fontSize: 16 }}>&rsaquo;</span>
    </button>
  );
}
