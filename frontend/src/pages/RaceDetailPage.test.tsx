import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '../test/utils'
import { RaceDetailPage } from './RaceDetailPage'
import { useCartStore } from '../stores/cartStore'
import { apiClient } from '../api/client'

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
        ],
      },
    }),
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

      // AI提案フォームの要素が表示される
      expect(await screen.findByText('予算')).toBeInTheDocument()
      expect(screen.getByText('提案を生成')).toBeInTheDocument()
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

      expect(await screen.findByText('予算')).toBeInTheDocument()
      expect(screen.getByText('提案を生成')).toBeInTheDocument()
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

  describe('runnersDataマッピング', () => {
    it('カート追加時にrunnersDataが正しくマッピングされてcurrentRunnersDataに保存される', async () => {
      const { user } = render(<RaceDetailPage />)

      // レース詳細がロードされるのを待つ
      await screen.findByText('テストレース')

      // 手動モードに切り替え
      const manualLink = screen.getByText('手動で買い目を選ぶ')
      await user.click(manualLink)

      // 馬1を選択
      const checkboxes = await screen.findAllByRole('checkbox')
      await user.click(checkboxes[0])

      // カートに追加
      const addButton = await screen.findByRole('button', { name: /カートに追加/i })
      await user.click(addButton)

      // cartStoreのcurrentRunnersDataにマッピングされたデータが入っている
      const state = useCartStore.getState()
      expect(state.currentRunnersData).toHaveLength(2)
      expect(state.currentRunnersData[0]).toEqual(
        expect.objectContaining({
          horse_number: 1,
          horse_name: 'テスト馬1',
          odds: 5.0,
          popularity: 2,
          frame_number: 1,
        })
      )
      expect(state.currentRunnersData[1]).toEqual(
        expect.objectContaining({
          horse_number: 2,
          horse_name: 'テスト馬2',
          odds: 3.0,
          popularity: 1,
          frame_number: 1,
        })
      )
    })
  })
})
