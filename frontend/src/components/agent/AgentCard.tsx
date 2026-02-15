import { useNavigate } from 'react-router-dom';
import type { Agent } from '../../types';

interface AgentCardProps {
  agent: Agent;
}

export function AgentCard({ agent }: AgentCardProps) {
  const navigate = useNavigate();

  return (
    <button
      type="button"
      onClick={() => navigate('/agent')}
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
        background: '#2563eb15',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: 24,
        flexShrink: 0,
      }}>
        {'\u{1F3C7}'}
      </div>

      {/* 名前 */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <span style={{ fontSize: 15, fontWeight: 600, color: '#111' }}>
          {agent.name}
        </span>
      </div>

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
