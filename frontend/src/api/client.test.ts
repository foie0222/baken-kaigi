import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'

// テスト用のモックデータ
const mockApiRace = {
  race_id: 'race_001',
  race_name: 'テストレース',
  race_number: 1,
  venue: '東京',
  start_time: '2024-01-01T10:00:00',
  betting_deadline: '2024-01-01T09:55:00',
  track_condition: '良',
}

const mockApiRunner = {
  horse_number: 1,
  horse_name: 'テストホース',
  jockey_name: 'テストジョッキー',
  odds: '5.0',
  popularity: 1,
}

describe('ApiClient', () => {
  // 各テストでfetchをモック
  const mockFetch = vi.fn()

  beforeEach(() => {
    vi.resetModules()
    mockFetch.mockReset()
    globalThis.fetch = mockFetch
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  // モジュールを動的にインポートしてApiClientを取得
  async function getApiClient(baseUrl = 'http://localhost:3000', agentCoreEndpoint = '', apiKey = '') {
    vi.stubEnv('VITE_API_BASE_URL', baseUrl)
    vi.stubEnv('VITE_AGENTCORE_ENDPOINT', agentCoreEndpoint)
    vi.stubEnv('VITE_API_KEY', apiKey)

    // モジュールキャッシュをクリアして再インポート
    const { apiClient } = await import('./client')
    return apiClient
  }

  describe('getRaces', () => {
    it('レース一覧を取得できる', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          races: [mockApiRace],
          venues: ['東京', '中山'],
          target_date: '2024-01-01',
        }),
      })

      const client = await getApiClient()
      const result = await client.getRaces()

      expect(result.success).toBe(true)
      expect(result.data?.races).toHaveLength(1)
      expect(result.data?.races[0].name).toBe('テストレース')
      expect(result.data?.venues).toContain('東京')
    })

    it('日付を指定してレースを取得できる', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          races: [mockApiRace],
          venues: ['東京'],
          target_date: '2024-06-15',
        }),
      })

      const client = await getApiClient()
      await client.getRaces('2024-06-15')

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/races?date=2024-06-15',
        expect.any(Object)
      )
    })

    it('APIエラー時にエラーを返す', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ error: 'Internal Server Error' }),
      })

      const client = await getApiClient()
      const result = await client.getRaces()

      expect(result.success).toBe(false)
      expect(result.error).toBe('Internal Server Error')
    })

    it('ネットワークエラー時にエラーを返す', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network Error'))

      const client = await getApiClient()
      const result = await client.getRaces()

      expect(result.success).toBe(false)
      expect(result.error).toBe('Network Error')
    })
  })

  describe('getRaceDetail', () => {
    it('レース詳細を取得できる', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          race: mockApiRace,
          runners: [mockApiRunner],
        }),
      })

      const client = await getApiClient()
      const result = await client.getRaceDetail('race_001')

      expect(result.success).toBe(true)
      expect(result.data?.name).toBe('テストレース')
      expect(result.data?.horses).toHaveLength(1)
      expect(result.data?.horses[0].name).toBe('テストホース')
    })

    it('レースIDがエンコードされる', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          race: mockApiRace,
          runners: [],
        }),
      })

      const client = await getApiClient()
      await client.getRaceDetail('race/special')

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/races/race%2Fspecial',
        expect.any(Object)
      )
    })
  })

  describe('カート操作', () => {
    it('カートにアイテムを追加できる', async () => {
      const mockCartItem = {
        id: 'item_001',
        raceId: 'race_001',
        betType: 'quinella',
        horseNumbers: [1, 2],
        amount: 1000,
      }

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockCartItem,
      })

      const client = await getApiClient()
      const result = await client.addToCart('cart_001', {
        raceId: 'race_001',
        betType: 'quinella',
        horseNumbers: [1, 2],
        amount: 1000,
      })

      expect(result.success).toBe(true)
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/cart/items',
        expect.objectContaining({
          method: 'POST',
        })
      )
    })

    it('カートからアイテムを削除できる', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({}),
      })

      const client = await getApiClient()
      const result = await client.removeFromCart('cart_001', 'item_001')

      expect(result.success).toBe(true)
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/cart/cart_001/items/item_001',
        expect.objectContaining({
          method: 'DELETE',
        })
      )
    })
  })

  describe('AgentCore 相談', () => {
    it('AgentCoreエンドポイントが未設定の場合エラーを返す', async () => {
      const client = await getApiClient('http://localhost:3000', '')

      const result = await client.consultWithAgent({
        prompt: 'テスト',
        cart_items: [],
      })

      expect(result.success).toBe(false)
      expect(result.error).toBe('AgentCore endpoint is not configured')
    })

    it('AgentCoreに相談を送信できる', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          message: 'AIからの応答',
          session_id: 'session_123',
        }),
      })

      const client = await getApiClient('http://localhost:3000', '/api/consultation')
      const result = await client.consultWithAgent({
        prompt: 'カートの買い目を分析してください',
        cart_items: [{
          raceId: 'race_001',
          raceName: 'テストレース',
          betType: 'quinella',
          horseNumbers: [1, 2],
          amount: 1000,
        }],
      })

      expect(result.success).toBe(true)
      expect(result.data?.message).toBe('AIからの応答')
      expect(result.data?.session_id).toBe('session_123')
    })

    it('isAgentCoreAvailableが正しく動作する', async () => {
      const clientWithoutEndpoint = await getApiClient('http://localhost:3000', '')
      expect(clientWithoutEndpoint.isAgentCoreAvailable()).toBe(false)

      // 新しいインスタンスを取得するために再インポート
      vi.resetModules()
      const clientWithEndpoint = await getApiClient('http://localhost:3000', '/api/consultation')
      expect(clientWithEndpoint.isAgentCoreAvailable()).toBe(true)
    })
  })

  describe('エラーメッセージ抽出', () => {
    it('ネストされたエラーオブジェクトからmessageを抽出できる', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ error: { message: '認証情報が無効です', code: 'INVALID_CREDENTIALS' } }),
      })

      const client = await getApiClient()
      const result = await client.getRaces()

      expect(result.success).toBe(false)
      expect(result.error).toBe('認証情報が無効です')
    })

    it('文字列エラーをそのまま返す', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ error: 'Internal Server Error' }),
      })

      const client = await getApiClient()
      const result = await client.getRaces()

      expect(result.success).toBe(false)
      expect(result.error).toBe('Internal Server Error')
    })

    it('errorフィールドがない場合HTTPステータスを返す', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 403,
        json: async () => ({}),
      })

      const client = await getApiClient()
      const result = await client.getRaces()

      expect(result.success).toBe(false)
      expect(result.error).toBe('HTTP 403')
    })

    it('AgentCoreでもネストされたエラーオブジェクトからmessageを抽出できる', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => ({ error: { message: 'リクエストが不正です', code: 'BAD_REQUEST' } }),
      })

      const client = await getApiClient('http://localhost:3000', '/api/consultation')
      const result = await client.consultWithAgent({
        prompt: 'テスト',
        cart_items: [],
      })

      expect(result.success).toBe(false)
      expect(result.error).toBe('リクエストが不正です')
    })
  })

  describe('データ変換', () => {
    it('APIレースをフロントエンド形式に変換する', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          races: [{
            race_id: 'race_001',
            race_name: '第1レース',
            race_number: 1,
            venue: '東京',
            start_time: '2024-01-01T15:30:00',
            betting_deadline: '2024-01-01T15:25:00',
            track_condition: '稍重',
          }],
          venues: ['東京'],
          target_date: '2024-01-01',
        }),
      })

      const client = await getApiClient()
      const result = await client.getRaces()

      expect(result.success).toBe(true)
      const race = result.data?.races[0]
      expect(race?.id).toBe('race_001')
      expect(race?.number).toBe('1R')
      expect(race?.name).toBe('第1レース')
      expect(race?.time).toBe('15:30')
      expect(race?.condition).toBe('稍重')
    })
  })

  describe('API Key認証', () => {
    it('API Keyが設定されている場合、x-api-keyヘッダーが送信される', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          races: [mockApiRace],
          venues: ['東京'],
          target_date: '2024-01-01',
        }),
      })

      const client = await getApiClient('http://localhost:3000', '', 'test-api-key')
      await client.getRaces()

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'x-api-key': 'test-api-key',
          }),
        })
      )
    })

    it('API Keyが空文字列の場合、x-api-keyヘッダーが送信されない', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          races: [mockApiRace],
          venues: ['東京'],
          target_date: '2024-01-01',
        }),
      })

      const client = await getApiClient('http://localhost:3000', '', '')
      await client.getRaces()

      const callArgs = mockFetch.mock.calls[0][1]
      expect(callArgs.headers['x-api-key']).toBeUndefined()
    })

    it('consultWithAgentでもAPI Keyヘッダーが送信される', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          message: 'AIからの応答',
          session_id: 'session_123',
        }),
      })

      const client = await getApiClient('http://localhost:3000', '/api/consultation', 'test-api-key')
      await client.consultWithAgent({
        prompt: 'テスト',
        cart_items: [],
      })

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            'x-api-key': 'test-api-key',
          }),
        })
      )
    })
  })

  describe('getRaceDates', () => {
    it('開催日一覧を取得できる', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          dates: ['2024-06-01', '2024-06-02'],
        }),
      })

      const client = await getApiClient()
      const result = await client.getRaceDates()

      expect(result.success).toBe(true)
      expect(result.data).toHaveLength(2)
      expect(result.data).toContain('2024-06-01')
      expect(result.data).toContain('2024-06-02')
    })

    it('期間を指定して開催日一覧を取得できる', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          dates: ['2024-06-01', '2024-06-02'],
        }),
      })

      const client = await getApiClient()
      await client.getRaceDates('2024-06-01', '2024-06-30')

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:3000/race-dates?from=2024-06-01&to=2024-06-30',
        expect.any(Object)
      )
    })

    it('APIエラー時にエラーを返す', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ error: 'Internal Server Error' }),
      })

      const client = await getApiClient()
      const result = await client.getRaceDates()

      expect(result.success).toBe(false)
      expect(result.error).toBe('Internal Server Error')
    })
  })

  describe('購入レスポンスの安全な変換', () => {
    it('undefined/nullフィールドでも例外が発生しない', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          purchase_id: null,
          status: undefined,
          total_amount: undefined,
          created_at: null,
        }),
      })

      const client = await getApiClient()
      const result = await client.submitPurchase('cart-1', '20260207', '05', 11)

      expect(result.success).toBe(true)
      expect(result.data?.purchaseId).toBe('')
      expect(result.data?.status).toBe('PENDING')
      expect(result.data?.totalAmount).toBe(0)
    })

    it('正常なstatusが正しく変換される', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          purchase_id: 'p-001',
          status: 'completed',
          total_amount: 1000,
          created_at: '2026-02-07T10:00:00',
        }),
      })

      const client = await getApiClient()
      const result = await client.submitPurchase('cart-1', '20260207', '05', 11)

      expect(result.success).toBe(true)
      expect(result.data?.status).toBe('COMPLETED')
    })

    it('不正なstatusはPENDINGにフォールバックする', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          purchase_id: 'p-001',
          status: 'unknown_status',
          total_amount: 1000,
          created_at: '2026-02-07T10:00:00',
        }),
      })

      const client = await getApiClient()
      const result = await client.submitPurchase('cart-1', '20260207', '05', 11)

      expect(result.success).toBe(true)
      expect(result.data?.status).toBe('PENDING')
    })

    it('updatedAtが空文字のときcreatedAtにフォールバックする', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ([{
          purchase_id: 'p-001',
          cart_id: 'cart-1',
          status: 'completed',
          total_amount: 1000,
          bet_line_count: 2,
          created_at: '2026-02-07T10:00:00',
          updated_at: '',
        }]),
      })

      const client = await getApiClient()
      const result = await client.getPurchaseHistory()

      expect(result.success).toBe(true)
      expect(result.data?.[0].updatedAt).toBe('2026-02-07T10:00:00')
    })
  })

  describe('AI買い目提案 (requestBetProposal)', () => {
    const mockRunners = [
      { horse_number: 1, horse_name: 'テスト馬1', odds: 3.5, popularity: 1, frame_number: 1 },
      { horse_number: 2, horse_name: 'テスト馬2', odds: 5.0, popularity: 2, frame_number: 2 },
    ]
    const mockProposal = {
      race_summary: {
        race_name: 'テストレース',
        difficulty_stars: 3,
        predicted_pace: 'ミドル',
        ai_consensus_level: '概ね合意',
        skip_score: 3,
        skip_recommendation: '通常判断',
      },
      proposed_bets: [{
        bet_type: 'quinella',
        horse_numbers: [1, 2],
        bet_display: '1-2',
        amount: 1000,
        bet_count: 1,
        confidence: 'high',
        expected_value: 1.2,
        composite_odds: 5.0,
        reasoning: 'テスト根拠',
      }],
      total_amount: 1000,
      budget_remaining: 2000,
      analysis_comment: 'テスト分析',
      disclaimer: '免責事項',
    }

    it('セパレータ+JSONで正常にパースできる', async () => {
      const message = `分析結果です。\n\n---BET_PROPOSALS_JSON---\n${JSON.stringify(mockProposal)}`
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message, session_id: 'session_1' }),
      })

      const client = await getApiClient('http://localhost:3000', '/api/consultation')
      const result = await client.requestBetProposal('race_001', 3000, mockRunners)

      expect(result.success).toBe(true)
      expect(result.data?.proposed_bets).toHaveLength(1)
      expect(result.data?.total_amount).toBe(1000)
    })

    it('コードフェンス付きJSONでもパースできる', async () => {
      const message = `分析結果です。\n\n---BET_PROPOSALS_JSON---\n\`\`\`json\n${JSON.stringify(mockProposal)}\n\`\`\``
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message, session_id: 'session_1' }),
      })

      const client = await getApiClient('http://localhost:3000', '/api/consultation')
      const result = await client.requestBetProposal('race_001', 3000, mockRunners)

      expect(result.success).toBe(true)
      expect(result.data?.proposed_bets).toHaveLength(1)
    })

    it('セパレータ欠落時にエラーを返す', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message: 'セパレータなしの応答', session_id: 'session_1' }),
      })

      const client = await getApiClient('http://localhost:3000', '/api/consultation')
      const result = await client.requestBetProposal('race_001', 3000, mockRunners)

      expect(result.success).toBe(false)
      expect(result.error).toBe('提案データが見つかりませんでした')
    })

    it('JSON不正時にエラーを返す', async () => {
      const message = '分析結果です。\n\n---BET_PROPOSALS_JSON---\n{invalid json}'
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ message, session_id: 'session_1' }),
      })

      const client = await getApiClient('http://localhost:3000', '/api/consultation')
      const result = await client.requestBetProposal('race_001', 3000, mockRunners)

      expect(result.success).toBe(false)
      expect(result.error).toBe('提案データの解析に失敗しました')
    })

    it('API呼び出し失敗時にエラーを返す', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        json: async () => ({ error: 'Internal Server Error' }),
      })

      const client = await getApiClient('http://localhost:3000', '/api/consultation')
      const result = await client.requestBetProposal('race_001', 3000, mockRunners)

      expect(result.success).toBe(false)
    })
  })
})
