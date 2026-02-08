import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '../test/utils'
import { IpatSettingsPage } from './IpatSettingsPage'
import { useIpatSettingsStore } from '../stores/ipatSettingsStore'

// apiClientをモック
vi.mock('../api/client', () => ({
  apiClient: {
    getIpatStatus: vi.fn(),
    saveIpatCredentials: vi.fn(),
    deleteIpatCredentials: vi.fn(),
  },
}))

// checkStatusのno-opモック（useEffect内の自動実行を抑制）
const mockCheckStatus = vi.fn()

describe('IpatSettingsPage', () => {
  beforeEach(() => {
    mockCheckStatus.mockReset()
    // ストアをリセット（checkStatusをno-opにして自動実行を抑制）
    useIpatSettingsStore.setState({
      status: null,
      isLoading: false,
      error: null,
      checkStatus: mockCheckStatus,
    })
  })

  describe('ローディング状態', () => {
    it('ステータス未取得時に読み込み中と表示される', () => {
      render(<IpatSettingsPage />)

      expect(screen.getByText('読み込み中...')).toBeInTheDocument()
    })
  })

  describe('API失敗時のエラー表示', () => {
    it('エラー時にエラーメッセージが表示される', () => {
      useIpatSettingsStore.setState({
        status: null,
        isLoading: false,
        error: 'IPAT状態の取得に失敗しました',
        checkStatus: mockCheckStatus,
      })

      render(<IpatSettingsPage />)

      expect(screen.getByText('IPAT状態の取得に失敗しました')).toBeInTheDocument()
      expect(screen.queryByText('読み込み中...')).not.toBeInTheDocument()
    })

    it('エラー時に再読み込みボタンが表示される', () => {
      useIpatSettingsStore.setState({
        status: null,
        isLoading: false,
        error: 'エラーが発生しました',
        checkStatus: mockCheckStatus,
      })

      render(<IpatSettingsPage />)

      expect(screen.getByRole('button', { name: '再読み込み' })).toBeInTheDocument()
    })

    it('再読み込みボタンクリックでcheckStatusが再実行される', async () => {
      useIpatSettingsStore.setState({
        status: null,
        isLoading: false,
        error: 'エラーが発生しました',
        checkStatus: mockCheckStatus,
      })

      const { user } = render(<IpatSettingsPage />)

      // useEffectでの初回呼び出しをリセット
      mockCheckStatus.mockClear()

      const retryButton = screen.getByRole('button', { name: '再読み込み' })
      await user.click(retryButton)

      expect(mockCheckStatus).toHaveBeenCalled()
    })

    it('再読み込み中はボタンが無効化される', () => {
      useIpatSettingsStore.setState({
        status: null,
        isLoading: true,
        error: 'エラーが発生しました',
        checkStatus: mockCheckStatus,
      })

      render(<IpatSettingsPage />)

      const retryButton = screen.getByRole('button', { name: '読み込み中...' })
      expect(retryButton).toBeDisabled()
    })
  })

  describe('正常表示', () => {
    it('設定済みの場合に設定済みメッセージが表示される', () => {
      useIpatSettingsStore.setState({
        status: { configured: true },
        isLoading: false,
        error: null,
        checkStatus: mockCheckStatus,
      })

      render(<IpatSettingsPage />)

      expect(screen.getByText('IPAT認証情報は設定済みです')).toBeInTheDocument()
    })

    it('未設定の場合に入力フォームが表示される', () => {
      useIpatSettingsStore.setState({
        status: { configured: false },
        isLoading: false,
        error: null,
        checkStatus: mockCheckStatus,
      })

      render(<IpatSettingsPage />)

      expect(screen.getByPlaceholderText('8桁の英数字')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: '保存' })).toBeInTheDocument()
    })
  })
})
