import { create } from 'zustand';
import type { CartItem, IpatBalance, PurchaseResult, PurchaseOrder } from '../types';
import { apiClient } from '../api/client';

/** APIの英語エラーメッセージを日本語に変換する */
export function toJapaneseError(error: string | undefined, fallback: string): string {
  if (!error) return fallback;
  if (error === 'Failed to fetch') return '通信エラーが発生しました';
  if (error.includes('IPAT credentials not configured')) return 'IPAT設定が完了していません。設定画面からIPAT情報を登録してください。';
  if (error.includes('IPAT')) return 'IPAT通信エラーが発生しました';
  // 英語/ASCII印刷可能文字のみのメッセージはフォールバックに変換
  if (/^[\x20-\x7E]+$/.test(error)) return fallback;
  return error;
}

/**
 * localStorageのカートアイテムをDynamoDBに同期し、サーバー側のcartIdを返す。
 * 最初のアイテムはcart_idなしで送信（新規カート作成）、
 * 2つ目以降は取得したcart_idに追加する。
 */
export async function syncCartToDynamo(
  items: CartItem[]
): Promise<{ success: true; cartId: string } | { success: false; error?: string }> {
  if (items.length === 0) {
    return { success: false, error: 'カートに商品がありません。' };
  }

  let serverCartId = '';
  for (const item of items) {
    const res = await apiClient.addToCart(serverCartId, {
      raceId: item.raceId,
      raceName: item.raceName,
      betType: item.betType,
      horseNumbers: item.horseNumbers,
      amount: item.amount,
    });
    if (!res.success || !res.data) {
      // 作成済みサーバーカートをbest-effortでクリーンアップ
      if (serverCartId) {
        apiClient.clearCart(serverCartId).catch(e => console.warn('Failed to clear cart:', e));
      }
      return { success: false, error: res.error };
    }
    serverCartId = res.data.cart_id;
  }
  return { success: true, cartId: serverCartId };
}

interface PurchaseState {
  balance: IpatBalance | null;
  purchaseResult: PurchaseResult | null;
  history: PurchaseOrder[];
  isLoading: boolean;
  error: string | null;

  submitPurchase: (cartId: string, raceDate: string, courseCode: string, raceNumber: number, items?: CartItem[]) => Promise<void>;
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

  submitPurchase: async (cartId, raceDate, courseCode, raceNumber, items) => {
    try {
      set({ isLoading: true, error: null, purchaseResult: null });

      // syncCartToDynamo をスキップ - items をそのまま submitPurchase に送信
      // バックエンドが items から直接カートを作成し、bet_method に基づいて展開する
      const response = await apiClient.submitPurchase(cartId, raceDate, courseCode, raceNumber, items);
      if (!response.success || !response.data) {
        set({ isLoading: false, error: toJapaneseError(response.error, '購入に失敗しました') });
        return;
      }
      set({ purchaseResult: response.data, isLoading: false });
    } catch (e) {
      set({
        isLoading: false,
        error: toJapaneseError(e instanceof Error ? e.message : undefined, '購入に失敗しました'),
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
    } catch (e) {
      set({
        isLoading: false,
        error: toJapaneseError(e instanceof Error ? e.message : undefined, '残高取得に失敗しました'),
      });
    }
  },

  fetchHistory: async () => {
    try {
      set({ isLoading: true, error: null });
      const response = await apiClient.getPurchaseHistory();
      if (!response.success || !response.data) {
        set({ isLoading: false, error: toJapaneseError(response.error, '履歴取得に失敗しました') });
        return;
      }
      set({ history: response.data, isLoading: false });
    } catch (e) {
      set({
        isLoading: false,
        error: toJapaneseError(e instanceof Error ? e.message : undefined, '履歴取得に失敗しました'),
      });
    }
  },

  clearError: () => set({ error: null }),
  clearResult: () => set({ purchaseResult: null }),
}));
