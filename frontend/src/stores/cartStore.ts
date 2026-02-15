import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { CartItem, RunnerData } from '../types';
import { BetTypeOrdered } from '../types';
import { MIN_BET_AMOUNT, MAX_BET_AMOUNT } from '../constants/betting';

export type AddItemResult = 'ok' | 'merged' | 'different_race' | 'invalid_amount';

interface CartState {
  cartId: string;
  items: CartItem[];
  currentRunnersData: RunnerData[];
  addItem: (item: Omit<CartItem, 'id'> & { runnersData?: RunnerData[] }) => AddItemResult;
  removeItem: (itemId: string) => void;
  updateItemAmount: (itemId: string, amount: number) => void;
  clearCart: () => void;
  getTotalAmount: () => number;
  getItemCount: () => number;
  getCurrentRaceId: () => string | null;
}

// カートIDを生成（セッション単位）
const generateCartId = () => `cart_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

// アイテムIDを生成
const generateItemId = () => `item_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

export const useCartStore = create<CartState>()(
  persist(
    (set, get) => ({
      cartId: generateCartId(),
      items: [],
      currentRunnersData: [],

      addItem: (item) => {
        // 金額バリデーション
        if (item.amount < MIN_BET_AMOUNT || item.amount > MAX_BET_AMOUNT) {
          return 'invalid_amount';
        }

        const state = get();

        // カートが空でない場合、同一レースかチェック
        if (state.items.length > 0) {
          const existingRaceId = state.items[0].raceId;
          if (item.raceId !== existingRaceId) {
            return 'different_race';
          }
        }

        // 同一券種・同一組み合わせの重複チェック
        const duplicate = state.items.find((existing) => {
          if (existing.betType !== item.betType) return false;
          // betMethod が異なれば別アイテム（BOXと通常を区別）
          if (existing.betMethod !== item.betMethod) return false;
          if (existing.betDisplay && item.betDisplay) {
            return existing.betDisplay === item.betDisplay;
          }
          // 順序依存券種（馬単・三連単）は配列をそのまま比較
          if (BetTypeOrdered[item.betType]) {
            return existing.horseNumbers.length === item.horseNumbers.length &&
              existing.horseNumbers.every((v, i) => v === item.horseNumbers[i]);
          }
          // 順序非依存券種はソートして比較
          const sortedExisting = [...existing.horseNumbers].sort((a, b) => a - b);
          const sortedNew = [...item.horseNumbers].sort((a, b) => a - b);
          return sortedExisting.length === sortedNew.length &&
            sortedExisting.every((v, i) => v === sortedNew[i]);
        });

        // runnersDataはCart単位で保持（CartItemには含めない）
        const { runnersData, ...itemWithoutRunners } = item;
        const runnersUpdate: Partial<CartState> = {};
        if (runnersData && runnersData.length > 0) {
          runnersUpdate.currentRunnersData = runnersData;
        }

        if (duplicate) {
          const mergedAmount = Math.min(duplicate.amount + item.amount, MAX_BET_AMOUNT);
          set((state) => ({
            items: state.items.map((i) => {
              if (i.id !== duplicate.id) return i;
              const merged = { ...i, amount: mergedAmount };
              if (!merged.betDisplay && itemWithoutRunners.betDisplay) {
                merged.betDisplay = itemWithoutRunners.betDisplay;
              }
              if (!merged.betMethod && itemWithoutRunners.betMethod) {
                merged.betMethod = itemWithoutRunners.betMethod;
              }
              if (merged.betCount == null && itemWithoutRunners.betCount != null) {
                merged.betCount = itemWithoutRunners.betCount;
              }
              return merged;
            }),
            ...runnersUpdate,
          }));
          return 'merged';
        }

        const newItem: CartItem = {
          ...itemWithoutRunners,
          id: generateItemId(),
        };
        set((state) => ({
          items: [...state.items, newItem],
          ...runnersUpdate,
        }));
        return 'ok';
      },

      removeItem: (itemId) => {
        set((state) => ({
          items: state.items.filter((item) => item.id !== itemId),
        }));
      },

      updateItemAmount: (itemId, amount) => {
        // バリデーション: 範囲外の金額は無視
        if (amount < MIN_BET_AMOUNT || amount > MAX_BET_AMOUNT) {
          return;
        }
        set((state) => ({
          items: state.items.map((item) =>
            item.id === itemId ? { ...item, amount } : item
          ),
        }));
      },

      clearCart: () => {
        set({
          items: [],
          currentRunnersData: [],
          cartId: generateCartId(),
        });
      },

      getTotalAmount: () => {
        return get().items.reduce((sum, item) => sum + item.amount, 0);
      },

      getItemCount: () => {
        return get().items.length;
      },

      getCurrentRaceId: () => {
        const state = get();
        return state.items.length > 0 ? state.items[0].raceId : null;
      },
    }),
    {
      name: 'baken-kaigi-cart',
    }
  )
);
