import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '../test/utils'
import { RaceDetailPage } from './RaceDetailPage'
import { useCartStore } from '../stores/cartStore'
import { apiClient } from '../api/client'
import { MAX_BET_AMOUNT } from '../constants/betting'

const mockNavigate = vi.fn()

// react-router-domのuseParams・useNavigateをモック
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useParams: () => ({ raceId: 'test-race-id' }),
    useNavigate: () => mockNavigate,
  }
})

// APIクライアントをモック
vi.mock('../api/client', () => ({
  apiClient: {
    getRaceDetail: vi.fn().mockResolvedValue({
      success: true,
      data: {
        id: 'test-race-id',
        name: 'テストレース',
        venue: '東京',
        number: '11R',
        course: '芝2000m',
        condition: '良',
        time: '15:40',
        horses: [
          { number: 1, wakuBan: 1, name: 'テスト馬1', jockey: '騎手1', weight: '54.0', odds: 5.0, popularity: 2, color: '#FFFFFF', textColor: '#000000' },
          { number: 2, wakuBan: 1, name: 'テスト馬2', jockey: '騎手2', weight: '56.0', odds: 3.0, popularity: 1, color: '#FFFFFF', textColor: '#000000' },
          { number: 3, wakuBan: 2, name: 'テスト馬3', jockey: '騎手3', weight: '55.0', odds: 8.0, popularity: 3, color: '#000000', textColor: '#FFFFFF' },
          { number: 4, wakuBan: 2, name: 'テスト馬4', jockey: '騎手4', weight: '54.0', odds: 12.0, popularity: 4, color: '#000000', textColor: '#FFFFFF' },
          { number: 5, wakuBan: 3, name: 'テスト馬5', jockey: '騎手5', weight: '56.0', odds: 15.0, popularity: 5, color: '#FF0000', textColor: '#FFFFFF' },
        ],
      },
    }),
    getAllOdds: vi.fn().mockResolvedValue({ success: false }),
  },
}))

describe('RaceDetailPage', () => {
  beforeEach(() => {
    useCartStore.getState().clearCart()
    mockNavigate.mockClear()
  })

  describe('デフォルトAIモード', () => {
    it('初期表示でAI提案フォームが表示される', async () => {
      render(<RaceDetailPage />)

      // エージェント未設定の場合、設定を促すメッセージが表示される
      expect(await screen.findByText('エージェントを設定すると買い目提案を利用できます')).toBeInTheDocument()
    })

    it('「手動で買い目を選ぶ」リンクが表示される', async () => {
      render(<RaceDetailPage />)

      expect(await screen.findByText('手動で買い目を選ぶ')).toBeInTheDocument()
    })

    it('「手動で買い目を選ぶ」クリックで手動入力UIが表示される', async () => {
      const { user } = render(<RaceDetailPage />)

      const manualLink = await screen.findByText('手動で買い目を選ぶ')
      await user.click(manualLink)

      // 手動入力UIの要素が表示される
      expect(await screen.findByText('カートに追加')).toBeInTheDocument()
      // 「AI提案に戻る」ボタンが表示される
      expect(screen.getByText('← AI提案に戻る')).toBeInTheDocument()
    })

    it('手動モードから「AI提案に戻る」ボタンでAIモードに戻る', async () => {
      const { user } = render(<RaceDetailPage />)

      // 手動モードに遷移
      const manualLink = await screen.findByText('手動で買い目を選ぶ')
      await user.click(manualLink)

      // AI提案に戻る
      const backBtn = screen.getByText('← AI提案に戻る')
      await user.click(backBtn)

      expect(await screen.findByText('エージェントを設定すると買い目提案を利用できます')).toBeInTheDocument()
    })
  })

  describe('手動モード - カートに追加ボタン', () => {
    it('btn-add-cart-subtleクラスが適用されている', async () => {
      const { user } = render(<RaceDetailPage />)

      // 手動モードに切り替え
      const manualLink = await screen.findByText('手動で買い目を選ぶ')
      await user.click(manualLink)

      const addButton = await screen.findByRole('button', { name: /カートに追加/i })
      expect(addButton).toBeInTheDocument()
      expect(addButton).toHaveClass('btn-add-cart-subtle')
    })
  })

  describe('手動モード - 金額入力の上限バリデーション', () => {
    it('MAX_BET_AMOUNTを超える金額が入力されても上限でクランプされる', async () => {
      const { user } = render(<RaceDetailPage />)

      const manualLink = await screen.findByText('手動で買い目を選ぶ')
      await user.click(manualLink)

      const amountInput = await screen.findByRole('spinbutton')
      await user.clear(amountInput)
      await user.type(amountInput, '999999')

      expect(amountInput).toHaveValue(MAX_BET_AMOUNT)
    })

    it('複数点の買い目がある場合、総額がMAX_BET_AMOUNTを超えないよう1点上限が調整される', async () => {
      const { user } = render(<RaceDetailPage />)

      const manualLink = await screen.findByText('手動で買い目を選ぶ')
      await user.click(manualLink)

      // 券種を馬連に変更（ダイアログ操作）
      const betTypeBtn = await screen.findByRole('button', { name: /単勝/ })
      await user.click(betTypeBtn)
      const umaren = await screen.findByText('馬連')
      await user.click(umaren)

      // 買い方をボックスに変更
      const betMethodBtn = await screen.findByRole('button', { name: /通常/ })
      await user.click(betMethodBtn)
      const boxBtn = await screen.findByText('ボックス')
      await user.click(boxBtn)

      // 3頭選択 → C(3,2) = 3点
      const checkboxes = await screen.findAllByRole('checkbox')
      await user.click(checkboxes[0])
      await user.click(checkboxes[1])
      await user.click(checkboxes[2])

      // 大きい金額を入力
      const amountInput = await screen.findByRole('spinbutton')
      await user.clear(amountInput)
      await user.type(amountInput, '999999')

      // betCount=3なので上限は floor(MAX_BET_AMOUNT / 3) = 33333
      expect(amountInput).toHaveValue(Math.floor(MAX_BET_AMOUNT / 3))
    })

    it('金額に0を入力してフォーカスを外すと100に補正される', async () => {
      const { user } = render(<RaceDetailPage />)

      const manualLink = await screen.findByText('手動で買い目を選ぶ')
      await user.click(manualLink)

      const amountInput = await screen.findByRole('spinbutton')
      // 全選択して0で置き換え → blur
      await user.click(amountInput)
      await user.keyboard('{Control>}a{/Control}0')
      await user.tab()

      expect(amountInput).toHaveValue(100)
    })
  })

  describe('手動モード - 案内テキスト', () => {
    it('購入確認案内テキストが表示される', async () => {
      const { user } = render(<RaceDetailPage />)

      const manualLink = await screen.findByText('手動で買い目を選ぶ')
      await user.click(manualLink)

      expect(await screen.findByText(/カートに追加後、購入確認へ進めます/i)).toBeInTheDocument()
    })

    it('案内テキストにai-guide-textクラスが適用されている', async () => {
      const { user } = render(<RaceDetailPage />)

      const manualLink = await screen.findByText('手動で買い目を選ぶ')
      await user.click(manualLink)

      const guideText = await screen.findByText(/カートに追加後、購入確認へ進めます/i)
      expect(guideText).toHaveClass('ai-guide-text')
    })
  })

  describe('手動モード - カート追加後の金額リセット', () => {
    it('カート追加後に金額入力欄が100にリセットされる', async () => {
      const { user } = render(<RaceDetailPage />)

      // 手動モードに切り替え
      const manualLink = await screen.findByText('手動で買い目を選ぶ')
      await user.click(manualLink)

      // 馬を1頭選択（単勝なので1頭でOK）
      const checkboxes = await screen.findAllByRole('checkbox')
      await user.click(checkboxes[0])

      // 金額を5000に変更（プリセットボタン使用）
      const preset5000 = await screen.findByRole('button', { name: '¥5,000' })
      await user.click(preset5000)
      const amountInput = await screen.findByRole('spinbutton')
      expect(amountInput).toHaveValue(5000)

      // カートに追加
      const addButton = await screen.findByRole('button', { name: /カートに追加/i })
      await user.click(addButton)

      // 金額入力欄が100にリセットされていること
      expect(amountInput).toHaveValue(100)
    })
  })

  describe('APIエラーメッセージの日本語化', () => {
    it('英語のAPIエラーメッセージは日本語フォールバックで表示される', async () => {
      vi.mocked(apiClient.getRaceDetail).mockResolvedValueOnce({
        success: false,
        error: 'Race not found',
      })

      render(<RaceDetailPage />)

      expect(await screen.findByText('レース詳細の取得に失敗しました')).toBeInTheDocument()
    })

    it('日本語を含むエラーメッセージはそのまま表示される', async () => {
      vi.mocked(apiClient.getRaceDetail).mockResolvedValueOnce({
        success: false,
        error: 'IPAT通信エラーが発生しました',
      })

      render(<RaceDetailPage />)

      expect(await screen.findByText('IPAT通信エラーが発生しました')).toBeInTheDocument()
    })

    it('エラーメッセージがない場合はフォールバックが表示される', async () => {
      vi.mocked(apiClient.getRaceDetail).mockResolvedValueOnce({
        success: false,
      })

      render(<RaceDetailPage />)

      expect(await screen.findByText('レース詳細の取得に失敗しました')).toBeInTheDocument()
    })
  })

  describe('エラー状態のUI表示', () => {
    it('APIエラー時にタイトル「レースが見つかりませんでした」が表示される', async () => {
      vi.mocked(apiClient.getRaceDetail).mockResolvedValueOnce({
        success: false,
        error: 'Race not found',
      })

      render(<RaceDetailPage />)

      expect(await screen.findByText('レースが見つかりませんでした')).toBeInTheDocument()
    })

    it('APIエラー時に「レース一覧に戻る」ボタンが表示される', async () => {
      vi.mocked(apiClient.getRaceDetail).mockResolvedValueOnce({
        success: false,
        error: 'Race not found',
      })

      render(<RaceDetailPage />)

      expect(await screen.findByRole('button', { name: 'レース一覧に戻る' })).toBeInTheDocument()
    })

    it('「レース一覧に戻る」ボタンクリックでホームページに遷移する', async () => {
      vi.mocked(apiClient.getRaceDetail).mockResolvedValueOnce({
        success: false,
        error: 'Race not found',
      })

      const { user } = render(<RaceDetailPage />)

      const backBtn = await screen.findByRole('button', { name: 'レース一覧に戻る' })
      await user.click(backBtn)

      expect(mockNavigate).toHaveBeenCalledWith('/')
    })

    it('レースデータがnullの場合もエラーUIが表示される', async () => {
      vi.mocked(apiClient.getRaceDetail).mockResolvedValueOnce({
        success: true,
        data: null as never,
      })

      render(<RaceDetailPage />)

      expect(await screen.findByText('レースが見つかりませんでした')).toBeInTheDocument()
      expect(screen.getByText('レース詳細の取得に失敗しました')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'レース一覧に戻る' })).toBeInTheDocument()
    })
  })

})
