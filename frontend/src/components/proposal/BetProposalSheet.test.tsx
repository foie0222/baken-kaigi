import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '../../test/utils'
import { BetProposalSheet } from './BetProposalSheet'
import { MAX_BET_AMOUNT } from '../../constants/betting'
import type { RaceDetail, Agent, AgentData } from '../../types'

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
const mockGetAgentData = vi.fn().mockReturnValue(null)
const mockFetchAgent = vi.fn()
vi.mock('../../stores/agentStore', () => ({
  useAgentStore: (selector: (s: { agent: Agent | null; hasFetched: boolean; fetchAgent: typeof mockFetchAgent; getAgentData: typeof mockGetAgentData }) => unknown) =>
    selector({ agent: mockAgent, hasFetched: true, fetchAgent: mockFetchAgent, getAgentData: mockGetAgentData }),
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

const mockAgentDataObj: AgentData = {
  name: 'うまもん',
}

describe('BetProposalSheet', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAgent = null
    mockGetAgentData.mockReturnValue(null)
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

  it('自由入力でMAX_BET_AMOUNTを超える予算を指定するとエラーが表示される', async () => {
    const { user } = render(
      <BetProposalSheet isOpen={true} onClose={vi.fn()} race={mockRace} />
    )

    const customInput = screen.getByPlaceholderText('自由入力（円）')
    await user.clear(customInput)
    await user.type(customInput, String(MAX_BET_AMOUNT + 1))

    await user.click(screen.getByText('提案を生成'))

    expect(screen.getByText(`予算は${MAX_BET_AMOUNT.toLocaleString()}円以下を指定してください`)).toBeInTheDocument()
  })

  it('自由入力でMAX_BET_AMOUNTちょうどの予算は生成を許可する', async () => {
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
        budget_remaining: MAX_BET_AMOUNT,
        analysis_comment: '',
        proposal_reasoning: '',
        disclaimer: '',
      },
    })

    const { user } = render(
      <BetProposalSheet isOpen={true} onClose={vi.fn()} race={mockRace} />
    )

    const customInput = screen.getByPlaceholderText('自由入力（円）')
    await user.clear(customInput)
    await user.type(customInput, String(MAX_BET_AMOUNT))

    await user.click(screen.getByText('提案を生成'))

    expect(mockRequest).toHaveBeenCalledWith(
      'race_001',
      MAX_BET_AMOUNT,
      expect.any(Array),
      expect.any(Object)
    )
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
        proposal_reasoning: '【軸馬選定】1番テスト馬1を軸に選定\n\n【券種】馬連を自動選定\n\n【組み合わせ】相手は2番テスト馬2を選定\n\n【リスク】積極参戦レベル',
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
      {}
    )
  })

  describe('エージェント設定済みの場合', () => {
    beforeEach(() => {
      mockAgent = mockAgentObj
      mockGetAgentData.mockReturnValue(mockAgentDataObj)
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

    it('生成ボタンクリックでagentDataがAPIに渡される', async () => {
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

      expect(mockRequest).toHaveBeenCalledWith(
        'race_001',
        3000,
        expect.any(Array),
        expect.objectContaining({ agentData: mockAgentDataObj })
      )
    })
  })
})
