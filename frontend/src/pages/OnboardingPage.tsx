import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAgentStore } from '../stores/agentStore';
import { AGENT_STYLES } from '../constants/agentStyles';
import type { AgentStyleId } from '../types';

export function OnboardingPage() {
  const navigate = useNavigate();
  const { createAgent, isLoading, error, clearError } = useAgentStore();
  const [name, setName] = useState('');
  const [selectedStyle, setSelectedStyle] = useState<AgentStyleId | null>(null);
  const [nameError, setNameError] = useState('');

  const validateName = (value: string): string => {
    const trimmed = value.trim();
    if (trimmed.length === 0) return '名前を入力してください';
    if (trimmed.length > 10) return '10文字以内で入力してください';
    return '';
  };

  const handleSubmit = async () => {
    const validation = validateName(name);
    if (validation) {
      setNameError(validation);
      return;
    }
    if (!selectedStyle) return;

    clearError();
    const success = await createAgent(name.trim(), selectedStyle);
    if (success) {
      navigate('/');
    }
  };

  const canSubmit = name.trim().length > 0 && name.trim().length <= 10 && selectedStyle !== null && !isLoading;

  return (
    <div className="fade-in" style={{ padding: '24px 0' }}>
      {/* ヘッダー */}
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <div style={{ fontSize: 40, marginBottom: 8 }}>{'\u{1F3C7}'}</div>
        <h1 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>あなたの相棒を作ろう</h1>
        <p style={{ fontSize: 14, color: '#666', marginTop: 8, lineHeight: 1.6 }}>
          競馬を一緒に分析するAIエージェントを育てましょう。<br />
          レースを重ねるほど、あなた好みの分析ができるようになります。
        </p>
      </div>

      {/* 名前入力 */}
      <div style={{ background: 'white', borderRadius: 12, padding: 20, marginBottom: 16 }}>
        <label style={{ display: 'block', fontSize: 14, fontWeight: 600, marginBottom: 8 }}>
          エージェントの名前
        </label>
        <input
          type="text"
          value={name}
          onChange={(e) => {
            setName(e.target.value);
            setNameError('');
          }}
          placeholder="例: ハヤテ、タケル"
          maxLength={10}
          style={{
            width: '100%',
            padding: '12px 16px',
            fontSize: 16,
            border: nameError ? '2px solid #ef4444' : '1px solid #ddd',
            borderRadius: 8,
            outline: 'none',
            boxSizing: 'border-box',
          }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
          <span style={{ fontSize: 12, color: nameError ? '#ef4444' : '#999' }}>
            {nameError || '1〜10文字'}
          </span>
          <span style={{ fontSize: 12, color: name.trim().length > 10 ? '#ef4444' : '#999' }}>
            {name.trim().length}/10
          </span>
        </div>
      </div>

      {/* スタイル選択 */}
      <div style={{ background: 'white', borderRadius: 12, padding: 20, marginBottom: 16 }}>
        <label style={{ display: 'block', fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
          分析スタイル
        </label>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {AGENT_STYLES.map((style) => {
            const isSelected = selectedStyle === style.id;
            return (
              <button
                key={style.id}
                type="button"
                onClick={() => setSelectedStyle(style.id)}
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  padding: 16,
                  border: isSelected ? `2px solid ${style.color}` : '2px solid #e5e7eb',
                  borderRadius: 12,
                  background: isSelected ? `${style.color}08` : 'white',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                <span style={{ fontSize: 28, marginBottom: 8 }}>{style.icon}</span>
                <span style={{
                  fontSize: 14,
                  fontWeight: 600,
                  color: isSelected ? style.color : '#333',
                  marginBottom: 4,
                }}>
                  {style.label}
                </span>
                <span style={{ fontSize: 11, color: '#666', textAlign: 'center', lineHeight: 1.4 }}>
                  {style.description}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* エラー表示 */}
      {error && (
        <div style={{
          background: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: 8,
          padding: '12px 16px',
          marginBottom: 16,
          fontSize: 13,
          color: '#dc2626',
        }}>
          {error}
        </div>
      )}

      {/* 作成ボタン */}
      <button
        type="button"
        onClick={handleSubmit}
        disabled={!canSubmit}
        style={{
          width: '100%',
          padding: 16,
          fontSize: 16,
          fontWeight: 600,
          color: 'white',
          background: canSubmit ? '#1a73e8' : '#ccc',
          border: 'none',
          borderRadius: 12,
          cursor: canSubmit ? 'pointer' : 'default',
          opacity: isLoading ? 0.7 : 1,
        }}
      >
        {isLoading ? '作成中...' : 'エージェントを作成'}
      </button>

      <p style={{ fontSize: 12, color: '#999', textAlign: 'center', marginTop: 12 }}>
        スタイルは後から変更できませんが、名前は変更できます
      </p>
    </div>
  );
}
