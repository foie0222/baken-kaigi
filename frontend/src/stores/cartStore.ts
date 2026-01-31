import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { CartItem } from '../types';
import { MIN_BET_AMOUNT, MAX_BET_AMOUNT } from '../constants/betting';

interface CartState {
  cartId: string;
  items: CartItem[];
  addItem: (item: Omit<CartItem, 'id'>) => boolean;
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

      addItem: (item) => {
        const state = get();

        // カートが空でない場合、同一レースかチェック
        if (state.items.length > 0) {
          const existingRaceId = state.items[0].raceId;
          if (item.raceId !== existingRaceId) {
            return false; // 異なるレースは追加不可
          }
        }

        const newItem: CartItem = {
          ...item,
          id: generateItemId(),
        };
        set((state) => ({
          items: [...state.items, newItem],
        }));
        return true;
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
