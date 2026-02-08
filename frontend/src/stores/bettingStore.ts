import { create } from 'zustand';
import type { BettingRecord, BettingSummary, BettingRecordFilter } from '../types';
import { apiClient } from '../api/client';

interface BettingState {
  records: BettingRecord[];
  summary: BettingSummary | null;
  thisMonthSummary: BettingSummary | null;
  lastMonthSummary: BettingSummary | null;
  isLoadingRecords: boolean;
  isLoadingSummary: boolean;
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
  isLoadingRecords: false,
  isLoadingSummary: false,
  error: null,

  fetchRecords: async (filters?: BettingRecordFilter) => {
    try {
      set({ isLoadingRecords: true, error: null });
      const response = await apiClient.getBettingRecords(filters);
      if (!response.success || !response.data) {
        set({ isLoadingRecords: false, error: response.error || '履歴取得に失敗しました' });
        return;
      }
      set({ records: response.data, isLoadingRecords: false });
    } catch (error) {
      set({
        isLoadingRecords: false,
        error: error instanceof Error ? error.message : '履歴取得に失敗しました',
      });
    }
  },

  fetchSummary: async (period) => {
    try {
      set({ isLoadingSummary: true, error: null });
      const response = await apiClient.getBettingSummary(period);
      if (!response.success || !response.data) {
        set({ isLoadingSummary: false, error: response.error || 'サマリー取得に失敗しました' });
        return;
      }
      if (period === 'this_month') {
        set({ thisMonthSummary: response.data, isLoadingSummary: false });
      } else if (period === 'last_month') {
        set({ lastMonthSummary: response.data, isLoadingSummary: false });
      } else {
        set({ summary: response.data, isLoadingSummary: false });
      }
    } catch (error) {
      set({
        isLoadingSummary: false,
        error: error instanceof Error ? error.message : 'サマリー取得に失敗しました',
      });
    }
  },

  fetchAllSummaries: async () => {
    try {
      set({ isLoadingSummary: true, error: null });
      const [thisMonth, lastMonth, allTime] = await Promise.all([
        apiClient.getBettingSummary('this_month'),
        apiClient.getBettingSummary('last_month'),
        apiClient.getBettingSummary('all_time'),
      ]);
      set({
        thisMonthSummary: thisMonth.success ? thisMonth.data ?? null : null,
        lastMonthSummary: lastMonth.success ? lastMonth.data ?? null : null,
        summary: allTime.success ? allTime.data ?? null : null,
        isLoadingSummary: false,
      });
    } catch (error) {
      set({
        isLoadingSummary: false,
        error: error instanceof Error ? error.message : 'サマリー取得に失敗しました',
      });
    }
  },

  clearError: () => set({ error: null }),
}));
