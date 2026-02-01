import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen } from '../test/utils'
import { ConsultationPage } from './ConsultationPage'
import { useCartStore } from '../stores/cartStore'

// APIクライアントをモック
vi.mock('../api/client', () => ({
  apiClient: {
    isAgentCoreAvailable: vi.fn(() => false),
    consultWithAgent: vi.fn(),
  },
}))

describe('ConsultationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
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

  describe('テキスト入力欄', () => {
    it('テキスト入力欄と送信ボタンが表示される', async () => {
      render(<ConsultationPage />)

      // テキスト入力欄が表示される
      const input = await screen.findByPlaceholderText('AIに質問する...')
      expect(input).toBeInTheDocument()

      // 送信ボタンが表示される
      const sendButton = await screen.findByRole('button', { name: '送信' })
      expect(sendButton).toBeInTheDocument()
    })
  })

  describe('買い目グルーピング表示', () => {
    it('買い目一覧のタイトルとレース情報が表示される', async () => {
      render(<ConsultationPage />)

      // 「買い目一覧」というタイトルが表示される
      expect(await screen.findByText('買い目一覧')).toBeInTheDocument()

      // レース情報が表示される（東京 1R）
      expect(await screen.findByText('東京 1R')).toBeInTheDocument()
    })

    it('同一レースの複数買い目がグループ内にまとめて表示される', async () => {
      // 同一レースに追加の買い目を追加
      useCartStore.getState().addItem({
        raceId: 'test-race-1',
        raceName: 'テストレース',
        raceVenue: '東京',
        raceNumber: '1R',
        betType: 'quinella',
        betMethod: 'normal',
        horseNumbers: [1, 2],
        betDisplay: '1-2',
        betCount: 1,
        amount: 500,
      })

      render(<ConsultationPage />)

      // 「買い目一覧」は1つだけ表示される（同一レースなのでグループは1つ）
      const titles = await screen.findAllByText('買い目一覧')
      expect(titles).toHaveLength(1)

      // 2つの買い目が表示される
      expect(await screen.findByText('単勝')).toBeInTheDocument()
      expect(await screen.findByText('馬連')).toBeInTheDocument()
      expect(await screen.findByText('1')).toBeInTheDocument()
      expect(await screen.findByText('1-2')).toBeInTheDocument()
    })

    it('削除ボタンにアクセシビリティ属性が設定されている', async () => {
      render(<ConsultationPage />)

      const deleteButton = await screen.findByRole('button', { name: '買い目を削除' })
      expect(deleteButton).toBeInTheDocument()
      expect(deleteButton).toHaveAttribute('title', '買い目を削除')
    })
  })

  describe('買い方バッジと点数表示', () => {
    it('BOX買いの場合にBOXバッジが表示される', async () => {
      useCartStore.getState().clearCart()
      useCartStore.getState().addItem({
        raceId: 'test-race-1',
        raceName: 'テストレース',
        raceVenue: '05',
        raceNumber: '1R',
        betType: 'quinella',
        betMethod: 'box',
        horseNumbers: [1, 2, 3, 4],
        betDisplay: '1,2,3,4',
        betCount: 6,
        amount: 600,
      })

      render(<ConsultationPage />)

      // BOXバッジが表示される
      expect(await screen.findByText('BOX')).toBeInTheDocument()
      // betDisplayの内容が表示される
      expect(await screen.findByText('1,2,3,4')).toBeInTheDocument()
    })

    it('流し買いの場合に流しバッジが表示される', async () => {
      useCartStore.getState().clearCart()
      useCartStore.getState().addItem({
        raceId: 'test-race-1',
        raceName: 'テストレース',
        raceVenue: '05',
        raceNumber: '1R',
        betType: 'quinella',
        betMethod: 'nagashi',
        horseNumbers: [3, 1, 5, 7],
        betDisplay: '軸:3 → 相手:1,5,7',
        betCount: 3,
        amount: 300,
      })

      render(<ConsultationPage />)

      // 流しバッジが表示される
      expect(await screen.findByText('流し')).toBeInTheDocument()
      // betDisplayの内容が表示される
      expect(await screen.findByText('軸:3 → 相手:1,5,7')).toBeInTheDocument()
    })

    it('通常買いの場合はバッジが表示されない', async () => {
      useCartStore.getState().clearCart()
      useCartStore.getState().addItem({
        raceId: 'test-race-1',
        raceName: 'テストレース',
        raceVenue: '05',
        raceNumber: '1R',
        betType: 'quinella',
        betMethod: 'normal',
        horseNumbers: [1, 2],
        betDisplay: '1-2',
        betCount: 1,
        amount: 100,
      })

      render(<ConsultationPage />)

      // 買い目は表示される
      expect(await screen.findByText('1-2')).toBeInTheDocument()
      // BOXや流しバッジは表示されない
      expect(screen.queryByText('BOX')).not.toBeInTheDocument()
      expect(screen.queryByText('流し')).not.toBeInTheDocument()
    })

    it('複数点の買い目で点数詳細が表示される', async () => {
      useCartStore.getState().clearCart()
      useCartStore.getState().addItem({
        raceId: 'test-race-1',
        raceName: 'テストレース',
        raceVenue: '05',
        raceNumber: '1R',
        betType: 'quinella',
        betMethod: 'box',
        horseNumbers: [1, 2, 3, 4],
        betDisplay: '1,2,3,4',
        betCount: 6,
        amount: 600,
      })

      render(<ConsultationPage />)

      // 点数詳細が表示される（6点 @¥100）
      expect(await screen.findByText('6点 @¥100')).toBeInTheDocument()
    })

    it('1点の買い目では点数詳細が表示されない', async () => {
      useCartStore.getState().clearCart()
      useCartStore.getState().addItem({
        raceId: 'test-race-1',
        raceName: 'テストレース',
        raceVenue: '05',
        raceNumber: '1R',
        betType: 'quinella',
        betMethod: 'normal',
        horseNumbers: [1, 2],
        betDisplay: '1-2',
        betCount: 1,
        amount: 100,
      })

      render(<ConsultationPage />)

      // 買い目は表示される
      expect(await screen.findByText('1-2')).toBeInTheDocument()
      // 1点の場合は点数詳細が表示されない
      expect(screen.queryByText(/点 @¥/)).not.toBeInTheDocument()
    })

    it('betCountが0の場合は点数詳細が表示されない（除算ゼロ防止）', async () => {
      useCartStore.getState().clearCart()
      useCartStore.getState().addItem({
        raceId: 'test-race-1',
        raceName: 'テストレース',
        raceVenue: '05',
        raceNumber: '1R',
        betType: 'quinella',
        betMethod: 'normal',
        horseNumbers: [1, 2],
        betDisplay: '1-2',
        betCount: 0,
        amount: 100,
      })

      render(<ConsultationPage />)

      // 買い目は表示される
      expect(await screen.findByText('1-2')).toBeInTheDocument()
      // betCountが0の場合は点数詳細が表示されない
      expect(screen.queryByText(/点 @¥/)).not.toBeInTheDocument()
    })
  })

  describe('金額編集（1点あたり金額）', () => {
    it('単勝（1点）の場合は「掛け金の変更」タイトルで表示される', async () => {
      useCartStore.getState().clearCart()
      useCartStore.getState().addItem({
        raceId: 'test-race-1',
        raceName: 'テストレース',
        raceVenue: '05',
        raceNumber: '1R',
        betType: 'win',
        betMethod: 'normal',
        horseNumbers: [1],
        betDisplay: '1',
        betCount: 1,
        amount: 500,
      })

      const { user } = render(<ConsultationPage />)

      // 変更ボタンをクリック
      const editButton = await screen.findByRole('button', { name: '変更' })
      await user.click(editButton)

      // 「掛け金の変更」タイトルが表示される
      expect(await screen.findByText('掛け金の変更')).toBeInTheDocument()
      // 合計金額プレビューは表示されない
      expect(screen.queryByText(/合計:/)).not.toBeInTheDocument()
    })

    it('複数点買い目の場合は「1点あたりの金額」タイトルで表示される', async () => {
      useCartStore.getState().clearCart()
      useCartStore.getState().addItem({
        raceId: 'test-race-1',
        raceName: 'テストレース',
        raceVenue: '05',
        raceNumber: '1R',
        betType: 'quinella',
        betMethod: 'box',
        horseNumbers: [1, 2, 3, 4],
        betDisplay: '1,2,3,4',
        betCount: 6,
        amount: 600,
      })

      const { user } = render(<ConsultationPage />)

      // 変更ボタンをクリック
      const editButton = await screen.findByRole('button', { name: '変更' })
      await user.click(editButton)

      // 「1点あたりの金額」タイトルが表示される
      expect(await screen.findByText('1点あたりの金額')).toBeInTheDocument()
      // 合計金額プレビューが表示される
      expect(await screen.findByText(/合計:/)).toBeInTheDocument()
    })

    it('複数点買い目で合計金額プレビューが表示される', async () => {
      useCartStore.getState().clearCart()
      useCartStore.getState().addItem({
        raceId: 'test-race-1',
        raceName: 'テストレース',
        raceVenue: '05',
        raceNumber: '1R',
        betType: 'quinella',
        betMethod: 'box',
        horseNumbers: [1, 2, 3, 4],
        betDisplay: '1,2,3,4',
        betCount: 6,
        amount: 600,
      })

      const { user } = render(<ConsultationPage />)

      // 変更ボタンをクリック
      const editButton = await screen.findByRole('button', { name: '変更' })
      await user.click(editButton)

      // 初期値は1点あたり100円なので、合計600円と表示される（amount-previewクラス内）
      const preview = await screen.findByText(/合計: ¥600/)
      expect(preview).toBeInTheDocument()
      expect(preview).toHaveClass('amount-preview')
    })
  })
})
