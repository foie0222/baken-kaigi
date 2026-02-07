import { create } from 'zustand';
import type { IpatStatus, IpatCredentialsInput } from '../types';
import { apiClient } from '../api/client';

interface IpatSettingsState {
  status: IpatStatus | null;
  isLoading: boolean;
  error: string | null;

  checkStatus: () => Promise<void>;
  saveCredentials: (credentials: IpatCredentialsInput) => Promise<void>;
  deleteCredentials: () => Promise<void>;
  clearError: () => void;
}

export const useIpatSettingsStore = create<IpatSettingsState>()((set) => ({
  status: null,
  isLoading: false,
  error: null,

  checkStatus: async () => {
    try {
      set({ isLoading: true, error: null });
      const response = await apiClient.getIpatStatus();
      if (!response.success || !response.data) {
        set({ isLoading: false, error: response.error || 'IPAT状態の取得に失敗しました' });
        return;
      }
      set({ status: response.data, isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'IPAT状態の取得に失敗しました',
      });
    }
  },

  saveCredentials: async (credentials) => {
    try {
      set({ isLoading: true, error: null });
      const response = await apiClient.saveIpatCredentials(credentials);
      if (!response.success) {
        set({ isLoading: false, error: response.error || 'IPAT認証情報の保存に失敗しました' });
        return;
      }
      set({ status: { configured: true }, isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'IPAT認証情報の保存に失敗しました',
      });
    }
  },

  deleteCredentials: async () => {
    try {
      set({ isLoading: true, error: null });
      const response = await apiClient.deleteIpatCredentials();
      if (!response.success) {
        set({ isLoading: false, error: response.error || 'IPAT認証情報の削除に失敗しました' });
        return;
      }
      set({ status: { configured: false }, isLoading: false });
    } catch (error) {
      set({
        isLoading: false,
        error: error instanceof Error ? error.message : 'IPAT認証情報の削除に失敗しました',
      });
    }
  },

  clearError: () => set({ error: null }),
}));
