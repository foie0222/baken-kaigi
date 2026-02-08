import { create } from 'zustand';
import type { BettingRecord, BettingSummary, BettingRecordFilter } from '../types';
import { apiClient } from '../api/client';

interface BettingState {
  records: BettingRecord[];
  summary: BettingSummary | null;
  thisMonthSummary: BettingSummary | null;
  lastMonthSummary: BettingSummary | null;
  isLoading: boolean;
  error: string | null;

  fetchRecords: (filters?: BettingRecordFilter) => Promise<void>;
  fetchSummary: (period: 'this_month' | 'last_month' | 'all_time') => Promise<void>;
  fetchAllSummaries: () => Promise<void>;
  clearError: () => void;
}

export const useBettingStore = create<BettingState>()((set) => ({
  records: [],
  summary: null,
  thisMonthSummary: null,
  lastMonthSummary: null,
  isLoading: false,
  error: null,

  fetchRecords: async (filters?: BettingRecordFilter) => {
    try {
      set({ isLoading: true, error: null });
      const response = await apiClient.getBettingRecords(filters);
      if (!response.success || !response.data) {
        set({ isLoading: false, error: response.error || '履歴取得に失敗しました' });
        return;
      }
      set({ records: response.data, isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : '履歴取得に失敗しました',
      });
    }
  },

  fetchSummary: async (period) => {
    try {
      set({ isLoading: true, error: null });
      const response = await apiClient.getBettingSummary(period);
      if (!response.success || !response.data) {
        set({ isLoading: false, error: response.error || 'サマリー取得に失敗しました' });
        return;
      }
      if (period === 'this_month') {
        set({ thisMonthSummary: response.data, isLoading: false });
      } else if (period === 'last_month') {
        set({ lastMonthSummary: response.data, isLoading: false });
      } else {
        set({ summary: response.data, isLoading: false });
      }
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'サマリー取得に失敗しました',
      });
    }
  },

  fetchAllSummaries: async () => {
    try {
      set({ isLoading: true, error: null });
      const [thisMonth, lastMonth, allTime] = await Promise.all([
        apiClient.getBettingSummary('this_month'),
        apiClient.getBettingSummary('last_month'),
        apiClient.getBettingSummary('all_time'),
      ]);
      set({
        thisMonthSummary: thisMonth.success ? thisMonth.data ?? null : null,
        lastMonthSummary: lastMonth.success ? lastMonth.data ?? null : null,
        summary: allTime.success ? allTime.data ?? null : null,
        isLoading: false,
      });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'サマリー取得に失敗しました',
      });
    }
  },

  clearError: () => set({ error: null }),
}));
