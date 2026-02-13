import { create } from 'zustand';
import type { Agent, AgentData, AgentStyleId } from '../types';
import { apiClient } from '../api/client';

interface AgentState {
  agent: Agent | null;
  isLoading: boolean;
  error: string | null;
  hasFetched: boolean;

  fetchAgent: () => Promise<void>;
  createAgent: (name: string, baseStyle: AgentStyleId) => Promise<boolean>;
  updateAgent: (baseStyle: AgentStyleId) => Promise<boolean>;
  getAgentData: () => AgentData | null;
  clearError: () => void;
  reset: () => void;
}

export const useAgentStore = create<AgentState>()((set, get) => ({
  agent: null,
  isLoading: false,
  error: null,
  hasFetched: false,

  fetchAgent: async () => {
    set({ isLoading: true, error: null });
    const result = await apiClient.getMyAgent();

    if (result.success && result.data) {
      set({ agent: result.data, isLoading: false, hasFetched: true });
    } else {
      // 404 = エージェント未作成（正常ケース）
      set({ agent: null, isLoading: false, hasFetched: true, error: null });
    }
  },

  createAgent: async (name: string, baseStyle: AgentStyleId) => {
    set({ isLoading: true, error: null });
    const result = await apiClient.createAgent(name, baseStyle);

    if (result.success && result.data) {
      set({ agent: result.data, isLoading: false });
      return true;
    }

    set({ isLoading: false, error: result.error || 'エージェントの作成に失敗しました' });
    return false;
  },

  updateAgent: async (baseStyle: AgentStyleId) => {
    set({ isLoading: true, error: null });
    const result = await apiClient.updateAgent(baseStyle);

    if (result.success && result.data) {
      set({ agent: result.data, isLoading: false });
      return true;
    }

    set({ isLoading: false, error: result.error || 'エージェントの更新に失敗しました' });
    return false;
  },

  getAgentData: (): AgentData | null => {
    const { agent } = get();
    if (!agent) return null;

    return {
      name: agent.name,
      base_style: agent.base_style,
      performance: agent.performance,
      level: agent.level,
    };
  },

  clearError: () => set({ error: null }),
  reset: () => set({ agent: null, isLoading: false, error: null, hasFetched: false }),
}));
