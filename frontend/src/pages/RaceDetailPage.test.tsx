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
          { number: 1, name: 'テスト馬1', jockey: '騎手1', weight: '54.0', odds: 5.0 },
          { number: 2, name: 'テスト馬2', jockey: '騎手2', weight: '56.0', odds: 3.0 },
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
})
