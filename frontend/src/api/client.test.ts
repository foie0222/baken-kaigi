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
  async function getApiClient(baseUrl = 'http://localhost:3000', agentCoreEndpoint = '') {
    vi.stubEnv('VITE_API_BASE_URL', baseUrl)
    vi.stubEnv('VITE_AGENTCORE_ENDPOINT', agentCoreEndpoint)

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
})
