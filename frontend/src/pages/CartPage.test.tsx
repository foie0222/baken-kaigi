import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen } from '../test/utils'
import { fireEvent, act } from '@testing-library/react'
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

    it('「このレースに買い目を追加」ボタンが表示される', () => {
      render(<CartPage />)

      const addMoreBtn = screen.getByRole('button', { name: /このレースに買い目を追加/ })
      expect(addMoreBtn).toBeInTheDocument()
    })

    it('買い目数サマリーがbetCountの合計を表示する', () => {
      render(<CartPage />)

      // betCount=1のアイテム1つ → 合計1点
      expect(screen.getByText('1点')).toBeInTheDocument()
    })
  })

  describe('複数の買い目がある場合', () => {
    beforeEach(() => {
      useCartStore.getState().addItem({
        raceId: 'test-race-1',
        raceName: 'テストレース',
        raceVenue: '東京',
        raceNumber: '1R',
        betType: 'trifecta',
        betMethod: 'box',
        horseNumbers: [1, 3, 7],
        betDisplay: '1-3-7',
        betCount: 6,
        amount: 600,
      })
      useCartStore.getState().addItem({
        raceId: 'test-race-1',
        raceName: 'テストレース',
        raceVenue: '東京',
        raceNumber: '1R',
        betType: 'quinella',
        betMethod: 'box',
        horseNumbers: [2, 4, 6],
        betDisplay: '2-4-6',
        betCount: 3,
        amount: 300,
      })
    })

    it('買い目数サマリーがbetCountの合計を表示する', () => {
      render(<CartPage />)

      // betCount=6 + betCount=3 = 合計9点
      expect(screen.getByText('9点')).toBeInTheDocument()
    })

    it('合計金額が正しく表示される', () => {
      render(<CartPage />)

      const summary = document.querySelector('.cart-summary')
      expect(summary?.textContent).toContain('¥900')
    })
  })

  describe('betCountが未設定のアイテムがある場合', () => {
    beforeEach(() => {
      useCartStore.getState().addItem({
        raceId: 'test-race-1',
        raceName: 'テストレース',
        raceVenue: '東京',
        raceNumber: '1R',
        betType: 'win',
        betMethod: 'normal',
        horseNumbers: [1],
        betDisplay: '1',
        amount: 100,
      })
    })

    it('betCountが未設定の場合は1点として計算される', () => {
      render(<CartPage />)

      expect(screen.getByText('1点')).toBeInTheDocument()
    })
  })

  describe('金額ステッパーUI', () => {
    beforeEach(() => {
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

    it('[+]ボタンで金額が100増える', () => {
      render(<CartPage />)

      const incrementBtn = screen.getByRole('button', { name: '金額を増やす' })
      fireEvent.click(incrementBtn)

      expect(screen.getByRole('button', { name: '金額 1100円 タップで編集' })).toBeInTheDocument()
    })

    it('[−]ボタンで金額が100減る', () => {
      render(<CartPage />)

      const decrementBtn = screen.getByRole('button', { name: '金額を減らす' })
      fireEvent.click(decrementBtn)

      expect(screen.getByRole('button', { name: '金額 900円 タップで編集' })).toBeInTheDocument()
    })

    it('最低金額で[−]ボタンがdisabledになる', () => {
      // amount=100のアイテムに差し替え
      useCartStore.getState().clearCart()
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
        amount: 100,
      })

      render(<CartPage />)

      const decrementBtn = screen.getByRole('button', { name: '金額を減らす' })
      expect(decrementBtn).toBeDisabled()
    })

    it('金額表示をクリックするとinputに切り替わり値を入力してblurで更新される', async () => {
      render(<CartPage />)

      // 金額表示ボタンをクリック
      const amountBtn = screen.getByRole('button', { name: '金額 1000円 タップで編集' })
      fireEvent.click(amountBtn)

      // inputに切り替わる
      const input = screen.getByRole('spinbutton')
      expect(input).toBeInTheDocument()

      // 値を変更してblur
      fireEvent.change(input, { target: { value: '2000' } })
      fireEvent.blur(input)

      // 更新後の金額表示ボタンが表示される
      expect(screen.getByRole('button', { name: '金額 2000円 タップで編集' })).toBeInTheDocument()
    })

    it('Escapeキーで編集をキャンセルして元の金額に戻る', () => {
      render(<CartPage />)

      const amountBtn = screen.getByRole('button', { name: '金額 1000円 タップで編集' })
      fireEvent.click(amountBtn)

      const input = screen.getByRole('spinbutton')
      fireEvent.change(input, { target: { value: '5000' } })
      fireEvent.keyDown(input, { key: 'Escape' })

      // 元の金額のボタンに戻る（5000ではなく1000）
      expect(screen.getByRole('button', { name: '金額 1000円 タップで編集' })).toBeInTheDocument()
    })
  })
})
