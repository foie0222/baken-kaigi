import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '../test/utils'
import { ConsultationPage } from './ConsultationPage'
import { useCartStore } from '../stores/cartStore'
import { useAuthStore } from '../stores/authStore'
import { useIpatSettingsStore } from '../stores/ipatSettingsStore'
import { apiClient } from '../api/client'

// react-router-domのuseNavigateをモック
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// APIクライアントをモック
vi.mock('../api/client', () => ({
  apiClient: {
    isAgentCoreAvailable: vi.fn(() => false),
    consultWithAgent: vi.fn(),
    getIpatStatus: vi.fn(() => Promise.resolve({ success: true, data: { configured: true } })),
  },
}))

const testRunnersData = [
  { horse_number: 1, horse_name: 'テスト馬1', odds: 5.0, popularity: 2, frame_number: 1 },
  { horse_number: 2, horse_name: 'テスト馬2', odds: 3.0, popularity: 1, frame_number: 1 },
]

describe('ConsultationPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockNavigate.mockClear()
    useCartStore.getState().clearCart()
    useAuthStore.setState({ isAuthenticated: true })
    useIpatSettingsStore.setState({ status: { configured: true }, isLoading: false, error: null })
    // テスト用の買い目を追加（runnersData付き）
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
      runnersData: testRunnersData,
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

  describe('購入ボタンの遷移', () => {
    it('購入ボタンクリックで購入確認ページへ遷移する', async () => {
      const { user } = render(<ConsultationPage />)

      const purchaseButton = await screen.findByRole('button', { name: /購入する/i })
      await user.click(purchaseButton)

      expect(mockNavigate).toHaveBeenCalledWith('/purchase/confirm')
    })

    it('未認証時は購入ボタンが無効化され「ログインして購入」と表示される', async () => {
      useAuthStore.setState({ isAuthenticated: false })

      render(<ConsultationPage />)

      const purchaseButton = await screen.findByRole('button', { name: /ログインして購入/i })
      expect(purchaseButton).toBeInTheDocument()
      expect(purchaseButton).toBeDisabled()
    })

    it('IPAT未設定時は「IPAT設定して購入」と表示され、クリックでIPAT設定ページへ遷移する', async () => {
      vi.mocked(apiClient.getIpatStatus).mockResolvedValue({ success: true, data: { configured: false } })
      useIpatSettingsStore.setState({ status: { configured: false }, isLoading: false, error: null })

      const { user } = render(<ConsultationPage />)

      const purchaseButton = await screen.findByRole('button', { name: /IPAT設定して購入/i })
      expect(purchaseButton).toBeInTheDocument()

      await user.click(purchaseButton)
      expect(mockNavigate).toHaveBeenCalledWith('/settings/ipat')
    })

    it('IPATステータス未取得時は「確認中...」と表示されボタンが無効化される', async () => {
      // getIpatStatusが解決しないようにして未取得状態を維持
      vi.mocked(apiClient.getIpatStatus).mockReturnValue(new Promise(() => {}))
      useIpatSettingsStore.setState({ status: null, isLoading: true, error: null })

      render(<ConsultationPage />)

      const purchaseButton = await screen.findByRole('button', { name: /確認中/i })
      expect(purchaseButton).toBeInTheDocument()
      expect(purchaseButton).toBeDisabled()
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

    it('複数点買い目の初期値が1点あたり金額になっている', async () => {
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
        amount: 1200, // 6点で1200円 = 1点あたり200円
      })

      const { user } = render(<ConsultationPage />)

      // 変更ボタンをクリック
      const editButton = await screen.findByRole('button', { name: '変更' })
      await user.click(editButton)

      // 入力欄の値が1点あたり200円になっている
      const input = await screen.findByRole('spinbutton')
      expect(input).toHaveValue(200)
    })

    it('複数点買い目で＋ボタンが上限に達すると無効化される', async () => {
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
        // MAX_BET_AMOUNT = 100000なので、6点の場合1点あたり上限は16666円（切り捨て）
        amount: 99996, // 6点 × 16666円
      })

      const { user } = render(<ConsultationPage />)

      // 変更ボタンをクリック
      const editButton = await screen.findByRole('button', { name: '変更' })
      await user.click(editButton)

      // ＋ボタンが無効化されている（上限に達しているため）
      const plusButton = await screen.findByRole('button', { name: '＋' })
      expect(plusButton).toBeDisabled()
    })
  })

  describe('AgentCore初回分析', () => {
    it('AgentCore利用可能時にrunners_data付きでconsultWithAgentが呼び出される', async () => {
      // AgentCoreを利用可能に設定
      vi.mocked(apiClient.isAgentCoreAvailable).mockReturnValue(true)
      vi.mocked(apiClient.consultWithAgent).mockResolvedValue({
        success: true,
        data: {
          message: 'AI分析結果です。期待値は1.5です。',
          session_id: 'test-session-id',
        },
      })

      render(<ConsultationPage />)

      // consultWithAgentがrunners_data付きで呼び出される
      await waitFor(() => {
        expect(apiClient.consultWithAgent).toHaveBeenCalledWith(
          expect.objectContaining({
            prompt: 'カートの買い目についてAI指数と照らし合わせて分析し、リスクや弱点を指摘してください。',
            cart_items: expect.arrayContaining([
              expect.objectContaining({
                raceId: 'test-race-1',
                betType: 'win',
                horseNumbers: [1],
              }),
            ]),
            runners_data: expect.arrayContaining([
              expect.objectContaining({
                horse_number: 1,
                horse_name: 'テスト馬1',
                odds: 5.0,
                popularity: 2,
              }),
            ]),
          })
        )
      })

      // AIの分析結果が表示される
      expect(await screen.findByText(/AI分析結果です/)).toBeInTheDocument()
    })

    it('AgentCore利用不可時にフォールバックメッセージが表示される', async () => {
      // AgentCoreを利用不可に設定
      vi.mocked(apiClient.isAgentCoreAvailable).mockReturnValue(false)

      render(<ConsultationPage />)

      // フォールバックメッセージが表示される
      expect(await screen.findByText(/AI分析機能は現在利用できません/)).toBeInTheDocument()
      // consultWithAgentは呼び出されない
      expect(apiClient.consultWithAgent).not.toHaveBeenCalled()
    })

    it('API失敗時にエラーメッセージが表示される', async () => {
      // AgentCoreを利用可能に設定
      vi.mocked(apiClient.isAgentCoreAvailable).mockReturnValue(true)
      vi.mocked(apiClient.consultWithAgent).mockResolvedValue({
        success: false,
        data: undefined,
      })

      render(<ConsultationPage />)

      // エラーメッセージが表示される
      expect(await screen.findByText(/分析中に問題が発生しました/)).toBeInTheDocument()
    })

    it('通信エラー時にエラーメッセージが表示される', async () => {
      // AgentCoreを利用可能に設定
      vi.mocked(apiClient.isAgentCoreAvailable).mockReturnValue(true)
      vi.mocked(apiClient.consultWithAgent).mockRejectedValue(new Error('Network error'))

      render(<ConsultationPage />)

      // エラーメッセージが表示される
      expect(await screen.findByText(/通信エラーが発生しました/)).toBeInTheDocument()
    })

    it('カート変更時にAPI再呼び出しが発生しない', async () => {
      // AgentCoreを利用可能に設定
      vi.mocked(apiClient.isAgentCoreAvailable).mockReturnValue(true)
      vi.mocked(apiClient.consultWithAgent).mockResolvedValue({
        success: true,
        data: {
          message: '初回分析結果です。',
          session_id: 'test-session-id',
        },
      })

      const { user } = render(<ConsultationPage />)

      // 初回分析が完了するのを待つ
      expect(await screen.findByText(/初回分析結果です/)).toBeInTheDocument()
      expect(apiClient.consultWithAgent).toHaveBeenCalledTimes(1)

      // カートの買い目を削除してもAPIが再呼び出しされない
      const deleteButton = screen.getByRole('button', { name: '買い目を削除' })
      await user.click(deleteButton)
      // 削除確認モーダルで「削除する」を押す
      const confirmButton = await screen.findByRole('button', { name: '削除する' })
      await user.click(confirmButton)

      // APIが再呼び出しされていないことを確認（1回のまま）
      expect(apiClient.consultWithAgent).toHaveBeenCalledTimes(1)
    })
  })
})
