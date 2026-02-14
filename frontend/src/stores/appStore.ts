import { create } from 'zustand';
import type { Race, BetType, PageType } from '../types';

const TOAST_AUTO_HIDE_MS = 2000;

interface AppState {
  // ナビゲーション
  currentPage: PageType;
  setCurrentPage: (page: PageType) => void;

  // レース選択
  selectedRace: Race | null;
  setSelectedRace: (race: Race | null) => void;

  // 馬選択
  selectedHorses: number[];
  toggleHorse: (number: number) => void;
  clearSelectedHorses: () => void;

  // 賭け設定
  betType: BetType;
  setBetType: (type: BetType) => void;
  betAmount: number;
  setBetAmount: (amount: number) => void;

  // トースト
  toastMessage: string | null;
  toastType: 'success' | 'error' | null;
  showToast: (message: string, type?: 'success' | 'error') => void;
  hideToast: () => void;
}

export const useAppStore = create<AppState>((set) => {
  let toastTimerId: ReturnType<typeof setTimeout> | null = null;

  return {
    // ナビゲーション
    currentPage: 'races',
    setCurrentPage: (page) => set({ currentPage: page }),

    // レース選択
    selectedRace: null,
    setSelectedRace: (race) => set({ selectedRace: race, selectedHorses: [] }),

    // 馬選択
    selectedHorses: [],
    toggleHorse: (number) =>
      set((state) => {
        const index = state.selectedHorses.indexOf(number);
        if (index === -1) {
          return { selectedHorses: [...state.selectedHorses, number] };
        } else {
          return {
            selectedHorses: state.selectedHorses.filter((n) => n !== number),
          };
        }
      }),
    clearSelectedHorses: () => set({ selectedHorses: [] }),

    // 賭け設定
    betType: 'quinella',
    setBetType: (type) => set({ betType: type }),
    betAmount: 1000,
    setBetAmount: (amount) => set({ betAmount: amount }),

    // トースト
    toastMessage: null,
    toastType: null,
    showToast: (message, type = 'success') => {
      if (toastTimerId !== null) {
        clearTimeout(toastTimerId);
      }
      set({ toastMessage: message, toastType: type });
      toastTimerId = setTimeout(() => {
        set({ toastMessage: null, toastType: null });
        toastTimerId = null;
      }, TOAST_AUTO_HIDE_MS);
    },
    hideToast: () => {
      if (toastTimerId !== null) {
        clearTimeout(toastTimerId);
        toastTimerId = null;
      }
      set({ toastMessage: null, toastType: null });
    },
  };
});
