import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '../test/utils'
import { CartPage } from './CartPage'
import { useCartStore } from '../stores/cartStore'

describe('CartPage', () => {
  beforeEach(() => {
    // カートをリセット
    useCartStore.getState().clearCart()
  })

  describe('カートが空の場合', () => {
    it('空のカートメッセージが表示される', () => {
      render(<CartPage />)

      expect(screen.getByText('カートに馬券がありません')).toBeInTheDocument()
    })

    it('spending-statusは表示されない', () => {
      render(<CartPage />)

      expect(screen.queryByText('今月の状況')).not.toBeInTheDocument()
    })
  })

  describe('カートに商品がある場合', () => {
    beforeEach(() => {
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

    it('spending-statusセクションが表示される', () => {
      render(<CartPage />)

      expect(screen.getByText('今月の状況')).toBeInTheDocument()
    })

    it('使用済み金額が表示される', () => {
      render(<CartPage />)

      expect(screen.getByText('使用済み')).toBeInTheDocument()
      expect(screen.getByText('¥0')).toBeInTheDocument()
    })

    it('今回の購入金額が表示される', () => {
      render(<CartPage />)

      expect(screen.getByText('今回の購入')).toBeInTheDocument()
      // spending-statusセクション内に金額が表示されていることを確認
      const spendingStatus = document.querySelector('.spending-status')
      expect(spendingStatus).not.toBeNull()
      expect(spendingStatus?.textContent).toContain('¥1,000')
    })

    it('残り許容負け額（未ログイン状態）が表示される', () => {
      render(<CartPage />)

      expect(screen.getByText('残り許容負け額')).toBeInTheDocument()
      expect(screen.getByText('ログインして設定')).toBeInTheDocument()
    })

    it('AI買い目レビューボタンが表示される', () => {
      render(<CartPage />)

      const aiButton = screen.getByRole('button', { name: /AI 買い目レビュー/i })
      expect(aiButton).toBeInTheDocument()
    })

    it('「このレースに買い目を追加」ボタンが表示される', () => {
      render(<CartPage />)

      const addMoreBtn = screen.getByRole('button', { name: /このレースに買い目を追加/ })
      expect(addMoreBtn).toBeInTheDocument()
    })
  })
})
