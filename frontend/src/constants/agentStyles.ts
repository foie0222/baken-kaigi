import type { AgentStyleId } from '../types';

export interface AgentStyleInfo {
  id: AgentStyleId;
  label: string;
  icon: string;
  description: string;
  color: string;
}

export const AGENT_STYLES: AgentStyleInfo[] = [
  {
    id: 'solid',
    label: '堅実型',
    icon: '\u{1F6E1}\u{FE0F}',
    description: 'リスク管理重視で着実に勝つ',
    color: '#2563eb',
  },
  {
    id: 'longshot',
    label: '穴狙い型',
    icon: '\u{1F3B2}',
    description: '大穴を見抜く嗅覚で高配当を狙う',
    color: '#9333ea',
  },
  {
    id: 'data',
    label: 'データ分析型',
    icon: '\u{1F4CA}',
    description: '統計とAI指数をフル活用',
    color: '#059669',
  },
  {
    id: 'pace',
    label: '展開読み型',
    icon: '\u{1F3C7}',
    description: 'レースの流れを読み切る',
    color: '#ea580c',
  },
];

export const AGENT_STYLE_MAP: Record<AgentStyleId, AgentStyleInfo> = Object.fromEntries(
  AGENT_STYLES.map((s) => [s.id, s])
) as Record<AgentStyleId, AgentStyleInfo>;
