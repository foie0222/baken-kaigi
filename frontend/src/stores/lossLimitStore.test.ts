import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useLossLimitStore } from './lossLimitStore';

// apiClient をモック
vi.mock('../api/client', () => ({
  apiClient: {
    getLossLimit: vi.fn(),
    setLossLimit: vi.fn(),
    requestLossLimitChange: vi.fn(),
    checkLossLimit: vi.fn(),
  },
}));

import { apiClient } from '../api/client';

const mockedApiClient = vi.mocked(apiClient);

describe('useLossLimitStore', () => {
  beforeEach(() => {
    // ストアをリセット
    useLossLimitStore.setState({
      lossLimit: null,
      totalLossThisMonth: 0,
      remainingLossLimit: null,
      pendingChange: null,
      isLoading: false,
      error: null,
    });
    vi.clearAllMocks();
  });

  describe('setLossLimit', () => {
    it('設定成功後にfetchLossLimitで最新値を取得できる', async () => {
      mockedApiClient.setLossLimit.mockResolvedValue({ success: true });
      mockedApiClient.getLossLimit.mockResolvedValue({
        success: true,
        data: {
          lossLimit: 50000,
          totalLossThisMonth: 10000,
          remainingLossLimit: 40000,
          pendingChange: null,
        },
      });

      await useLossLimitStore.getState().setLossLimit(50000);

      const state = useLossLimitStore.getState();
      // fetchLossLimitが呼ばれてデータが反映されること
      expect(mockedApiClient.getLossLimit).toHaveBeenCalledTimes(1);
      expect(state.lossLimit).toBe(50000);
      expect(state.remainingLossLimit).toBe(40000);
      expect(state.isLoading).toBe(false);
    });

    it('設定失敗時にisLoadingがfalseに戻りerrorがセットされる', async () => {
      mockedApiClient.setLossLimit.mockResolvedValue({
        success: false,
        error: '設定に失敗しました',
      });

      await useLossLimitStore.getState().setLossLimit(50000);

      const state = useLossLimitStore.getState();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe('設定に失敗しました');
      expect(mockedApiClient.getLossLimit).not.toHaveBeenCalled();
    });

    it('API例外時にisLoadingがfalseに戻りerrorがセットされる', async () => {
      mockedApiClient.setLossLimit.mockRejectedValue(new Error('ネットワークエラー'));

      await useLossLimitStore.getState().setLossLimit(50000);

      const state = useLossLimitStore.getState();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe('ネットワークエラー');
    });
  });

  describe('requestChange', () => {
    it('即時反映（減額）の場合にfetchLossLimitで最新値を取得できる', async () => {
      mockedApiClient.requestLossLimitChange.mockResolvedValue({
        success: true,
        data: {
          changeId: 'change-1',
          changeType: 'decrease',
          status: 'approved',
          effectiveAt: '2026-02-21T00:00:00Z',
          requestedAt: '2026-02-21T00:00:00Z',
          currentLimit: 50000,
          requestedLimit: 30000,
          appliedImmediately: true,
        },
      });
      mockedApiClient.getLossLimit.mockResolvedValue({
        success: true,
        data: {
          lossLimit: 30000,
          totalLossThisMonth: 5000,
          remainingLossLimit: 25000,
          pendingChange: null,
        },
      });

      const result = await useLossLimitStore.getState().requestChange(30000);

      const state = useLossLimitStore.getState();
      // fetchLossLimitが呼ばれてデータが反映されること
      expect(mockedApiClient.getLossLimit).toHaveBeenCalledTimes(1);
      expect(state.lossLimit).toBe(30000);
      expect(state.remainingLossLimit).toBe(25000);
      expect(state.isLoading).toBe(false);
      expect(result).not.toBeNull();
      expect(result?.changeId).toBe('change-1');
    });

    it('変更リクエスト失敗時にisLoadingがfalseに戻りerrorがセットされる', async () => {
      mockedApiClient.requestLossLimitChange.mockResolvedValue({
        success: false,
        error: '変更リクエストに失敗しました',
      });

      const result = await useLossLimitStore.getState().requestChange(30000);

      const state = useLossLimitStore.getState();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe('変更リクエストに失敗しました');
      expect(result).toBeNull();
    });

    it('PENDING（増額）の場合はfetchせずpendingChangeをセットする', async () => {
      mockedApiClient.requestLossLimitChange.mockResolvedValue({
        success: true,
        data: {
          changeId: 'change-2',
          changeType: 'increase',
          status: 'pending',
          effectiveAt: '2026-03-01T00:00:00Z',
          requestedAt: '2026-02-21T00:00:00Z',
          currentLimit: 30000,
          requestedLimit: 50000,
          appliedImmediately: false,
        },
      });

      const result = await useLossLimitStore.getState().requestChange(50000);

      const state = useLossLimitStore.getState();
      expect(mockedApiClient.getLossLimit).not.toHaveBeenCalled();
      expect(state.pendingChange).not.toBeNull();
      expect(state.pendingChange?.changeId).toBe('change-2');
      expect(state.isLoading).toBe(false);
      expect(result?.changeId).toBe('change-2');
    });
  });

  describe('fetchLossLimit', () => {
    it('正常にデータを取得できる', async () => {
      mockedApiClient.getLossLimit.mockResolvedValue({
        success: true,
        data: {
          lossLimit: 100000,
          totalLossThisMonth: 20000,
          remainingLossLimit: 80000,
          pendingChange: null,
        },
      });

      await useLossLimitStore.getState().fetchLossLimit();

      const state = useLossLimitStore.getState();
      expect(state.lossLimit).toBe(100000);
      expect(state.totalLossThisMonth).toBe(20000);
      expect(state.remainingLossLimit).toBe(80000);
      expect(state.isLoading).toBe(false);
    });

    it('API失敗時にisLoadingがfalseに戻りerrorがセットされる', async () => {
      mockedApiClient.getLossLimit.mockResolvedValue({
        success: false,
        error: '取得に失敗しました',
      });

      await useLossLimitStore.getState().fetchLossLimit();

      const state = useLossLimitStore.getState();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe('取得に失敗しました');
    });

    it('isLoading中の重複呼び出しをスキップする', async () => {
      // 手動でisLoadingをtrueに設定
      useLossLimitStore.setState({ isLoading: true });

      await useLossLimitStore.getState().fetchLossLimit();

      // APIが呼ばれないこと
      expect(mockedApiClient.getLossLimit).not.toHaveBeenCalled();
    });
  });
});
