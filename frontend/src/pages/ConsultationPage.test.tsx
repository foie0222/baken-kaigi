import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '../test/utils'
import { ConsultationPage } from './ConsultationPage'
import { useCartStore } from '../stores/cartStore'

describe('ConsultationPage', () => {
  beforeEach(() => {
    useCartStore.getState().clearCart()
    // テスト用の買い目を追加
    useCartStore.getState().addItem({
      raceId: 'test-race-1',
      raceName: 'テストレース',
      raceVenue: '東京',
      raceNumber: '1R',
      betType: 'win',
      betMethod: 'normal',
      horseNumbers: [1],
      betDisplay: '1',
      betCount: 1,
      amount: 1000,
    })
  })

  describe('ボタンの優先順位', () => {
    it('「やめておく」ボタンが表示される', async () => {
      render(<ConsultationPage />)

      const stopButton = await screen.findByRole('button', { name: /やめておく/i })
      expect(stopButton).toBeInTheDocument()
      expect(stopButton).toHaveClass('btn-stop')
    })

    it('「購入する」ボタンが表示される', async () => {
      render(<ConsultationPage />)

      const purchaseButton = await screen.findByRole('button', { name: /購入する/i })
      expect(purchaseButton).toBeInTheDocument()
      expect(purchaseButton).toHaveClass('btn-purchase-subtle')
    })

    it('「やめておく」が主アクション（btn-stop）、「購入する」が控えめ（btn-purchase-subtle）', async () => {
      render(<ConsultationPage />)

      const stopButton = await screen.findByRole('button', { name: /やめておく/i })
      const purchaseButton = await screen.findByRole('button', { name: /購入する/i })

      // やめておくボタンが主アクションスタイル
      expect(stopButton).toHaveClass('btn-stop')
      // 購入するボタンが控えめスタイル
      expect(purchaseButton).toHaveClass('btn-purchase-subtle')
    })
  })

  describe('AIヘッダー', () => {
    it('AIのタグラインが表示される', async () => {
      render(<ConsultationPage />)

      expect(await screen.findByText('立ち止まって、考えましょう')).toBeInTheDocument()
    })
  })
})
