import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '../test/utils'
import { RaceDetailPage } from './RaceDetailPage'
import { useCartStore } from '../stores/cartStore'

// react-router-domのuseParamsをモック
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useParams: () => ({ raceId: 'test-race-id' }),
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
  })

  describe('カートに追加ボタン', () => {
    it('btn-add-cart-subtleクラスが適用されている', async () => {
      render(<RaceDetailPage />)

      const addButton = await screen.findByRole('button', { name: /カートに追加/i })
      expect(addButton).toBeInTheDocument()
      expect(addButton).toHaveClass('btn-add-cart-subtle')
    })
  })

  describe('AI案内テキスト', () => {
    it('AI案内テキストが表示される', async () => {
      render(<RaceDetailPage />)

      expect(await screen.findByText(/カートに追加後、AIと一緒に買い目を確認できます/i)).toBeInTheDocument()
    })

    it('AI案内テキストにai-guide-textクラスが適用されている', async () => {
      render(<RaceDetailPage />)

      const guideText = await screen.findByText(/カートに追加後、AIと一緒に買い目を確認できます/i)
      expect(guideText).toHaveClass('ai-guide-text')
    })
  })

  describe('runnersDataマッピング', () => {
    it('カート追加時にrunnersDataが正しくマッピングされてcurrentRunnersDataに保存される', async () => {
      const { user } = render(<RaceDetailPage />)

      // レース詳細がロードされるのを待つ
      await screen.findByText('テストレース')

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
