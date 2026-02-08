import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '../../test/utils'
import { BetProposalSheet } from './BetProposalSheet'
import type { RaceDetail } from '../../types'

// apiClientモック
vi.mock('../../api/client', () => ({
  apiClient: {
    requestBetProposal: vi.fn(),
  },
}))

// cartStoreモック
const mockAddItem = vi.fn().mockReturnValue('ok')
vi.mock('../../stores/cartStore', () => ({
  useCartStore: (selector: (s: { addItem: typeof mockAddItem }) => unknown) =>
    selector({ addItem: mockAddItem }),
}))

// appStoreモック
const mockShowToast = vi.fn()
vi.mock('../../stores/appStore', () => ({
  useAppStore: (selector: (s: { showToast: typeof mockShowToast }) => unknown) =>
    selector({ showToast: mockShowToast }),
}))

const mockRace: RaceDetail = {
  id: 'race_001',
  name: 'テストレース',
  number: '11R',
  venue: '東京',
  time: '15:30',
  course: '',
  condition: '良',
  date: '2024-01-01',
  startTime: '2024-01-01T15:30:00',
  bettingDeadline: '2024-01-01T15:25:00',
  horses: [
    {
      number: 1, name: 'テスト馬1', odds: 3.5, popularity: 1,
      jockey: 'テスト騎手1', wakuBan: 1, weight: 480, weightDiff: 0,
      color: '#1a73e8', textColor: '#ffffff',
    },
    {
      number: 2, name: 'テスト馬2', odds: 5.0, popularity: 2,
      jockey: 'テスト騎手2', wakuBan: 2, weight: 460, weightDiff: -2,
      color: '#000000', textColor: '#ffffff',
    },
  ],
}

describe('BetProposalSheet', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('予算プリセットと生成ボタンが表示される', () => {
    render(
      <BetProposalSheet isOpen={true} onClose={vi.fn()} race={mockRace} />
    )

    expect(screen.getByText('1,000円')).toBeInTheDocument()
    expect(screen.getByText('3,000円')).toBeInTheDocument()
    expect(screen.getByText('提案を生成')).toBeInTheDocument()
  })

  it('注目馬入力のラベルがinputに関連付いている', () => {
    render(
      <BetProposalSheet isOpen={true} onClose={vi.fn()} race={mockRace} />
    )

    const input = screen.getByLabelText(/注目馬/)
    expect(input).toBeInTheDocument()
    expect(input.id).toBe('axis-horses-input')
  })

  it('生成ボタンクリックでAPIが呼ばれる', async () => {
    const { apiClient } = await import('../../api/client')
    const mockRequest = vi.mocked(apiClient.requestBetProposal)
    mockRequest.mockResolvedValueOnce({
      success: true,
      data: {
        race_id: 'race_001',
        race_summary: {
          race_name: 'テストレース',
          difficulty_stars: 3,
          predicted_pace: 'ミドル',
          ai_consensus_level: '概ね合意',
          skip_score: 3,
          skip_recommendation: '通常判断',
        },
        proposed_bets: [{
          bet_type: 'quinella' as const,
          horse_numbers: [1, 2],
          bet_display: '1-2',
          amount: 1000,
          bet_count: 1,
          confidence: 'high' as const,
          expected_value: 1.2,
          composite_odds: 5.0,
          reasoning: 'テスト根拠',
        }],
        total_amount: 1000,
        budget_remaining: 2000,
        analysis_comment: 'テスト分析',
        disclaimer: '免責事項',
      },
    })

    const { user } = render(
      <BetProposalSheet isOpen={true} onClose={vi.fn()} race={mockRace} />
    )

    await user.click(screen.getByText('提案を生成'))

    expect(mockRequest).toHaveBeenCalledWith(
      'race_001',
      3000,
      expect.any(Array),
      undefined
    )
  })
})
