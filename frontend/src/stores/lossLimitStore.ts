import { create } from 'zustand';
import type { LossLimit, PendingLossLimitChange, LossLimitCheckResult } from '../types';
import { apiClient } from '../api/client';

interface LossLimitState {
  lossLimit: number | null;
  totalLossThisMonth: number;
  remainingLossLimit: number | null;
  pendingChange: PendingLossLimitChange | null;
  isLoading: boolean;
  error: string | null;

  fetchLossLimit: () => Promise<void>;
  setLossLimit: (amount: number) => Promise<void>;
  requestChange: (amount: number) => Promise<PendingLossLimitChange | null>;
  checkLimit: (amount: number) => Promise<LossLimitCheckResult | null>;
  clearError: () => void;
}

export const useLossLimitStore = create<LossLimitState>()((set, get) => ({
  lossLimit: null,
  totalLossThisMonth: 0,
  remainingLossLimit: null,
  pendingChange: null,
  isLoading: false,
  error: null,

  fetchLossLimit: async () => {
    try {
      set({ isLoading: true, error: null });
      const response = await apiClient.getLossLimit();
      if (!response.success || !response.data) {
        set({ isLoading: false, error: response.error || '限度額の取得に失敗しました' });
        return;
      }
      const data = response.data as LossLimit;
      set({
        lossLimit: data.lossLimit,
        totalLossThisMonth: data.totalLossThisMonth,
        remainingLossLimit: data.remainingLossLimit,
        pendingChange: data.pendingChange,
        isLoading: false,
      });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : '限度額の取得に失敗しました',
      });
    }
  },

  setLossLimit: async (amount) => {
    try {
      set({ isLoading: true, error: null });
      const response = await apiClient.setLossLimit(amount);
      if (!response.success) {
        set({ isLoading: false, error: response.error || '限度額の設定に失敗しました' });
        return;
      }
      // サーバーから最新値を取得
      await get().fetchLossLimit();
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : '限度額の設定に失敗しました',
      });
    }
  },

  requestChange: async (amount) => {
    try {
      set({ isLoading: true, error: null });
      const response = await apiClient.requestLossLimitChange(amount);
      if (!response.success || !response.data) {
        set({ isLoading: false, error: response.error || '限度額の変更リクエストに失敗しました' });
        return null;
      }
      const { appliedImmediately, ...changeData } = response.data;
      if (appliedImmediately) {
        // 即時反映（減額）の場合、サーバーから最新値を取得
        await get().fetchLossLimit();
        return changeData;
      }
      // PENDING（増額）の場合、pendingChangeをセット
      set({ pendingChange: changeData, isLoading: false });
      return changeData;
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : '限度額の変更リクエストに失敗しました',
      });
      return null;
    }
  },

  checkLimit: async (amount) => {
    try {
      const response = await apiClient.checkLossLimit(amount);
      if (!response.success || !response.data) {
        return null;
      }
      return response.data;
    } catch {
      return null;
    }
  },

  clearError: () => set({ error: null }),
}));
