import { create } from 'zustand';
import type { Race, BetType, PageType } from '../types';

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

  // 相談セッション
  consultationSessionId: string | null;
  setConsultationSessionId: (id: string | null) => void;

  // トースト
  toastMessage: string | null;
  showToast: (message: string) => void;
  hideToast: () => void;
}

export const useAppStore = create<AppState>((set) => ({
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

  // 相談セッション
  consultationSessionId: null,
  setConsultationSessionId: (id) => set({ consultationSessionId: id }),

  // トースト
  toastMessage: null,
  showToast: (message) => {
    set({ toastMessage: message });
    setTimeout(() => set({ toastMessage: null }), 2000);
  },
  hideToast: () => set({ toastMessage: null }),
}));
