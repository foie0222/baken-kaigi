import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor, within } from '../test/utils'
import { PurchaseConfirmPage } from './PurchaseConfirmPage'
import { useCartStore } from '../stores/cartStore'
import { usePurchaseStore } from '../stores/purchaseStore'
import { apiClient } from '../api/client'

// APIクライアントをモック
vi.mock('../api/client', () => ({
  apiClient: {
    submitPurchase: vi.fn(),
    getIpatBalance: vi.fn(() => Promise.resolve({
      success: true,
      data: { betBalance: 100000, limitVoteAmount: 200000 },
    })),
    getPurchaseHistory: vi.fn(),
  },
}))

function addTestCartItem() {
  useCartStore.getState().addItem({
    raceId: '20260208050101',
    raceName: 'テストレース',
    raceVenue: '05',
    raceNumber: '1R',
    betType: 'win',
    betMethod: 'normal',
    horseNumbers: [1],
    betDisplay: '1',
    betCount: 1,
    amount: 1000,
  })
}

/** モーダルを開いて確認ボタンをクリックするヘルパー */
async function clickPurchaseAndConfirm(user: ReturnType<typeof import('@testing-library/user-event')['default']['setup']>) {
  // fetchBalanceが完了して購入ボタンが有効になるのを待つ
  const purchaseButton = await screen.findByRole('button', { name: '購入する' })
  await user.click(purchaseButton)

  // モーダルが表示されるのを待つ
  const dialog = await screen.findByRole('dialog')
  // モーダル内の確認ボタンをクリック
  const confirmBtn = within(dialog).getByText('購入する')
  await user.click(confirmBtn)
}

describe('PurchaseConfirmPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useCartStore.getState().clearCart()
    usePurchaseStore.setState({
      balance: null,
      purchaseResult: null,
      history: [],
      isLoading: false,
      error: null,
    })
  })

  describe('購入エラー時のカートクリア防止', () => {
    it('API通信エラー時にカートがクリアされない', async () => {
      addTestCartItem()
      expect(useCartStore.getState().items).toHaveLength(1)

      // submitPurchaseがエラーを返す（purchaseResultはnullのまま）
      vi.mocked(apiClient.submitPurchase).mockResolvedValue({
        success: false,
        error: '通信エラーが発生しました',
      })

      const { user } = render(<PurchaseConfirmPage />)
      await clickPurchaseAndConfirm(user)

      // storeのsubmitPurchaseが完了するまで待つ
      await waitFor(() => {
        expect(usePurchaseStore.getState().isLoading).toBe(false)
      })

      // カートがクリアされていないことを確認
      expect(useCartStore.getState().items).toHaveLength(1)
    })

    it('API例外スロー時にカートがクリアされない', async () => {
      addTestCartItem()
      expect(useCartStore.getState().items).toHaveLength(1)

      // submitPurchaseが例外をスロー（purchaseResultはnullのまま）
      vi.mocked(apiClient.submitPurchase).mockRejectedValue(
        new Error('Network Error'),
      )

      const { user } = render(<PurchaseConfirmPage />)
      await clickPurchaseAndConfirm(user)

      await waitFor(() => {
        expect(usePurchaseStore.getState().isLoading).toBe(false)
      })

      // カートがクリアされていないことを確認
      expect(useCartStore.getState().items).toHaveLength(1)
    })

    it('購入失敗（status=FAILED）時にカートがクリアされない', async () => {
      addTestCartItem()
      expect(useCartStore.getState().items).toHaveLength(1)

      // submitPurchaseがFAILED statusを返す
      vi.mocked(apiClient.submitPurchase).mockResolvedValue({
        success: true,
        data: {
          purchaseId: 'purchase-123',
          status: 'FAILED',
          totalAmount: 1000,
          createdAt: '2026-02-08T00:00:00Z',
        },
      })

      const { user } = render(<PurchaseConfirmPage />)
      await clickPurchaseAndConfirm(user)

      await waitFor(() => {
        expect(usePurchaseStore.getState().isLoading).toBe(false)
      })

      // FAILED時はカートがクリアされない
      expect(useCartStore.getState().items).toHaveLength(1)
    })

    it('購入成功時にはカートがクリアされる', async () => {
      addTestCartItem()
      expect(useCartStore.getState().items).toHaveLength(1)

      vi.mocked(apiClient.submitPurchase).mockResolvedValue({
        success: true,
        data: {
          purchaseId: 'purchase-123',
          status: 'COMPLETED',
          totalAmount: 1000,
          createdAt: '2026-02-08T00:00:00Z',
        },
      })

      const { user } = render(<PurchaseConfirmPage />)
      await clickPurchaseAndConfirm(user)

      await waitFor(() => {
        expect(usePurchaseStore.getState().isLoading).toBe(false)
      })

      // 成功時はカートがクリアされる
      expect(useCartStore.getState().items).toHaveLength(0)
    })
  })
})
