import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '../../test/utils'
import { BetProposalSheet } from './BetProposalSheet'
import type { RaceDetail, Agent } from '../../types'

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

// authStoreモック
vi.mock('../../stores/authStore', () => ({
  useAuthStore: (selector: (s: { isAuthenticated: boolean }) => unknown) =>
    selector({ isAuthenticated: false }),
}))

// agentStoreモック（テスト毎にmockAgentで切り替え可能）
let mockAgent: Agent | null = null
const mockFetchAgent = vi.fn()
vi.mock('../../stores/agentStore', () => ({
  useAgentStore: (selector: (s: { agent: Agent | null; hasFetched: boolean; fetchAgent: typeof mockFetchAgent }) => unknown) =>
    selector({ agent: mockAgent, hasFetched: true, fetchAgent: mockFetchAgent }),
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

const mockAgentObj: Agent = {
  agent_id: 'agent_001',
  user_id: 'user_001',
  name: 'うまもん',
  betting_preference: { bet_type_preference: 'auto' },
  created_at: '2024-01-01T00:00:00',
  updated_at: '2024-01-01T00:00:00',
}


describe('BetProposalSheet', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAgent = null
  })

  it('エージェント未設定時はエージェント設定を促すメッセージが表示される', () => {
    render(
      <BetProposalSheet isOpen={true} onClose={vi.fn()} race={mockRace} />
    )

    expect(screen.getByText('エージェントを設定すると買い目提案を利用できます')).toBeInTheDocument()
  })

  describe('エージェント設定済みの場合', () => {
    beforeEach(() => {
      mockAgent = mockAgentObj
    })

    it('ボタンテキストにエージェント名が表示される', () => {
      render(
        <BetProposalSheet isOpen={true} onClose={vi.fn()} race={mockRace} />
      )

      expect(screen.getByText('うまもんに提案してもらう')).toBeInTheDocument()
    })

    it('予算・券種・買い目上限・注目馬の入力フィールドが非表示', () => {
      render(
        <BetProposalSheet isOpen={true} onClose={vi.fn()} race={mockRace} />
      )

      expect(screen.queryByText('1,000円')).not.toBeInTheDocument()
      expect(screen.queryByText('希望券種')).not.toBeInTheDocument()
      expect(screen.queryByText('買い目上限')).not.toBeInTheDocument()
      expect(screen.queryByPlaceholderText('例: 3, 7')).not.toBeInTheDocument()
    })

    it('生成ボタンクリックでAPIがraceIdのみで呼ばれる', async () => {
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
          proposed_bets: [],
          total_amount: 0,
          budget_remaining: 3000,
          analysis_comment: '',
          proposal_reasoning: '',
          disclaimer: '',
        },
      })

      const { user } = render(
        <BetProposalSheet isOpen={true} onClose={vi.fn()} race={mockRace} />
      )

      await user.click(screen.getByText('うまもんに提案してもらう'))

      expect(mockRequest).toHaveBeenCalledWith('race_001')
    })
  })
})
