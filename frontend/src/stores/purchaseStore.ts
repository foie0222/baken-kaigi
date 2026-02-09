import { create } from 'zustand';
import type { IpatBalance, PurchaseResult, PurchaseOrder } from '../types';
import { apiClient } from '../api/client';

/** APIの英語エラーメッセージを日本語に変換する */
function toJapaneseError(error: string | undefined, fallback: string): string {
  if (!error) return fallback;
  if (error === 'Failed to fetch') return '通信エラーが発生しました';
  if (error.includes('IPAT credentials not configured')) return 'IPAT設定が完了していません。設定画面からIPAT情報を登録してください。';
  if (error.includes('IPAT')) return 'IPAT通信エラーが発生しました';
  // 英語のみのメッセージはフォールバックに変換
  if (/^[a-zA-Z0-9\s.:_-]+$/.test(error)) return fallback;
  return error;
}

interface PurchaseState {
  balance: IpatBalance | null;
  purchaseResult: PurchaseResult | null;
  history: PurchaseOrder[];
  isLoading: boolean;
  error: string | null;

  submitPurchase: (cartId: string, raceDate: string, courseCode: string, raceNumber: number) => Promise<void>;
  fetchBalance: () => Promise<void>;
  fetchHistory: () => Promise<void>;
  clearError: () => void;
  clearResult: () => void;
}

export const usePurchaseStore = create<PurchaseState>()((set) => ({
  balance: null,
  purchaseResult: null,
  history: [],
  isLoading: false,
  error: null,

  submitPurchase: async (cartId, raceDate, courseCode, raceNumber) => {
    try {
      set({ isLoading: true, error: null, purchaseResult: null });
      const response = await apiClient.submitPurchase(cartId, raceDate, courseCode, raceNumber);
      if (!response.success || !response.data) {
        set({ isLoading: false, error: toJapaneseError(response.error, '購入に失敗しました') });
        return;
      }
      set({ purchaseResult: response.data, isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: '購入に失敗しました',
      });
    }
  },

  fetchBalance: async () => {
    try {
      set({ isLoading: true, error: null });
      const response = await apiClient.getIpatBalance();
      if (!response.success || !response.data) {
        set({ isLoading: false, error: toJapaneseError(response.error, '残高取得に失敗しました') });
        return;
      }
      set({ balance: response.data, isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: '残高取得に失敗しました',
      });
    }
  },

  fetchHistory: async () => {
    try {
      set({ isLoading: true, error: null });
      const response = await apiClient.getPurchaseHistory();
      if (!response.success || !response.data) {
        set({ isLoading: false, error: response.error || '履歴取得に失敗しました' });
        return;
      }
      set({ history: response.data, isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : '履歴取得に失敗しました',
      });
    }
  },

  clearError: () => set({ error: null }),
  clearResult: () => set({ purchaseResult: null }),
}));
