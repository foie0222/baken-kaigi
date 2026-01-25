import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { CartItem } from '../types';
import { MIN_BET_AMOUNT, MAX_BET_AMOUNT } from '../constants/betting';

interface CartState {
  cartId: string;
  items: CartItem[];
  addItem: (item: Omit<CartItem, 'id'>) => void;
  removeItem: (itemId: string) => void;
  updateItemAmount: (itemId: string, amount: number) => void;
  clearCart: () => void;
  getTotalAmount: () => number;
  getItemCount: () => number;
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
        const newItem: CartItem = {
          ...item,
          id: generateItemId(),
        };
        set((state) => ({
          items: [...state.items, newItem],
        }));
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
    }),
    {
      name: 'baken-kaigi-cart',
    }
  )
);
