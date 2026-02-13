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

  describe('モード選択', () => {
    it('初期表示でモード選択カードが表示される', async () => {
      render(<RaceDetailPage />)

      expect(await screen.findByText('AIにおまかせ')).toBeInTheDocument()
      expect(screen.getByText('自分で選ぶ')).toBeInTheDocument()
    })

    it('「AIにおまかせ」クリックでAI提案フォームが表示される', async () => {
      const { user } = render(<RaceDetailPage />)

      const aiCard = await screen.findByText('AIにおまかせ')
      await user.click(aiCard)

      // AI提案フォームの要素が表示される
      expect(await screen.findByText('予算')).toBeInTheDocument()
      expect(screen.getByText('提案を生成')).toBeInTheDocument()
      // 「選び直す」ボタンが表示される
      expect(screen.getByText('← 選び直す')).toBeInTheDocument()
    })

    it('「自分で選ぶ」クリックで手動入力UIが表示される', async () => {
      const { user } = render(<RaceDetailPage />)

      const manualCard = await screen.findByText('自分で選ぶ')
      await user.click(manualCard)

      // 手動入力UIの要素が表示される
      expect(await screen.findByText('カートに追加')).toBeInTheDocument()
      // 「選び直す」ボタンが表示される
      expect(screen.getByText('← 選び直す')).toBeInTheDocument()
    })

    it('「選び直す」ボタンでモード選択に戻る', async () => {
      const { user } = render(<RaceDetailPage />)

      // AIモードに遷移
      const aiCard = await screen.findByText('AIにおまかせ')
      await user.click(aiCard)

      // 選び直すボタンでモード選択に戻る
      const backBtn = screen.getByText('← 選び直す')
      await user.click(backBtn)

      expect(await screen.findByText('AIにおまかせ')).toBeInTheDocument()
      expect(screen.getByText('自分で選ぶ')).toBeInTheDocument()
    })
  })

  describe('手動モード - カートに追加ボタン', () => {
    it('btn-add-cart-subtleクラスが適用されている', async () => {
      const { user } = render(<RaceDetailPage />)

      // 手動モードに切り替え
      const manualCard = await screen.findByText('自分で選ぶ')
      await user.click(manualCard)

      const addButton = await screen.findByRole('button', { name: /カートに追加/i })
      expect(addButton).toBeInTheDocument()
      expect(addButton).toHaveClass('btn-add-cart-subtle')
    })
  })

  describe('手動モード - AI案内テキスト', () => {
    it('AI案内テキストが表示される', async () => {
      const { user } = render(<RaceDetailPage />)

      const manualCard = await screen.findByText('自分で選ぶ')
      await user.click(manualCard)

      expect(await screen.findByText(/カートに追加後、AI買い目レビューで確認できます/i)).toBeInTheDocument()
    })

    it('AI案内テキストにai-guide-textクラスが適用されている', async () => {
      const { user } = render(<RaceDetailPage />)

      const manualCard = await screen.findByText('自分で選ぶ')
      await user.click(manualCard)

      const guideText = await screen.findByText(/カートに追加後、AI買い目レビューで確認できます/i)
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
      const manualCard = screen.getByText('自分で選ぶ')
      await user.click(manualCard)

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
