import { create } from 'zustand';
import type { Agent, AgentData, BettingPreference } from '../types';
import { apiClient } from '../api/client';

interface AgentState {
  agent: Agent | null;
  isLoading: boolean;
  error: string | null;
  hasFetched: boolean;

  fetchAgent: () => Promise<void>;
  createAgent: (name: string) => Promise<boolean>;
  updateAgent: (bettingPreference?: BettingPreference, customInstructions?: string | null) => Promise<boolean>;
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

  createAgent: async (name: string) => {
    set({ isLoading: true, error: null });
    const result = await apiClient.createAgent(name);

    if (result.success && result.data) {
      set({ agent: result.data, isLoading: false });
      return true;
    }

    set({ isLoading: false, error: result.error || 'エージェントの作成に失敗しました' });
    return false;
  },

  updateAgent: async (bettingPreference?: BettingPreference, customInstructions?: string | null) => {
    set({ isLoading: true, error: null });
    const result = await apiClient.updateAgent(bettingPreference, customInstructions);

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
      betting_preference: agent.betting_preference,
      custom_instructions: agent.custom_instructions,
    };
  },

  clearError: () => set({ error: null }),
  reset: () => set({ agent: null, isLoading: false, error: null, hasFetched: false }),
}));
