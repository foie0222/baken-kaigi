import { describe, it, expect, vi, beforeEach } from 'vitest'
import { toJapaneseError, syncCartToDynamo } from './purchaseStore'
import type { CartItem } from '../types'

describe('toJapaneseError', () => {
  const fallback = 'デフォルトエラー'

  it('errorがundefinedの場合はfallbackを返す', () => {
    expect(toJapaneseError(undefined, fallback)).toBe(fallback)
  })

  it('"Failed to fetch"を通信エラーに変換する', () => {
    expect(toJapaneseError('Failed to fetch', fallback)).toBe('通信エラーが発生しました')
  })

  it('"IPAT credentials not configured"をIPAT設定エラーに変換する', () => {
    expect(toJapaneseError('IPAT credentials not configured', fallback)).toBe(
      'IPAT設定が完了していません。設定画面からIPAT情報を登録してください。'
    )
  })

  it('IPATを含むメッセージをIPAT通信エラーに変換する', () => {
    expect(toJapaneseError('IPAT session expired', fallback)).toBe('IPAT通信エラーが発生しました')
  })

  it('ASCII文字のみのメッセージはfallbackに変換する', () => {
    expect(toJapaneseError('Internal Server Error', fallback)).toBe(fallback)
    expect(toJapaneseError('TypeError: x is not a function', fallback)).toBe(fallback)
    expect(toJapaneseError('404 Not Found', fallback)).toBe(fallback)
  })

  it('日本語を含むメッセージはそのまま返す', () => {
    expect(toJapaneseError('残高が不足しています', fallback)).toBe('残高が不足しています')
    expect(toJapaneseError('購入上限を超えています', fallback)).toBe('購入上限を超えています')
  })
})

// apiClient をモック
vi.mock('../api/client', () => ({
  apiClient: {
    addToCart: vi.fn(),
    clearCart: vi.fn(() => Promise.resolve({ success: true })),
  },
}))

import { apiClient } from '../api/client'
const mockAddToCart = vi.mocked(apiClient.addToCart)
const mockClearCart = vi.mocked(apiClient.clearCart)

function makeItem(overrides: Partial<CartItem> = {}): CartItem {
  return {
    id: 'item_1',
    raceId: '2026021105',
    raceName: 'テストレース',
    raceVenue: '05',
    raceNumber: '11R',
    betType: 'win',
    horseNumbers: [1],
    amount: 100,
    ...overrides,
  }
}

describe('syncCartToDynamo', () => {
  beforeEach(() => {
    mockAddToCart.mockReset()
    mockClearCart.mockReset()
    mockClearCart.mockResolvedValue({ success: true })
  })

  it('空配列の場合はエラーを返す', async () => {
    const result = await syncCartToDynamo([])
    expect(result).toEqual({ success: false, error: 'カートに商品がありません。' })
    expect(mockAddToCart).not.toHaveBeenCalled()
  })

  it('単一アイテムの場合、cart_id空で送信してサーバーcartIdを返す', async () => {
    mockAddToCart.mockResolvedValueOnce({
      success: true,
      data: { cart_id: 'server-cart-1', item_id: 'i1', item_count: 1, total_amount: 100 },
    })

    const result = await syncCartToDynamo([makeItem()])

    expect(result).toEqual({ success: true, cartId: 'server-cart-1' })
    expect(mockAddToCart).toHaveBeenCalledTimes(1)
    expect(mockAddToCart).toHaveBeenCalledWith('', {
      raceId: '2026021105',
      raceName: 'テストレース',
      betType: 'win',
      horseNumbers: [1],
      amount: 100,
    })
  })

  it('複数アイテムの場合、2つ目以降はサーバーcartIdを使って送信する', async () => {
    mockAddToCart
      .mockResolvedValueOnce({
        success: true,
        data: { cart_id: 'server-cart-1', item_id: 'i1', item_count: 1, total_amount: 100 },
      })
      .mockResolvedValueOnce({
        success: true,
        data: { cart_id: 'server-cart-1', item_id: 'i2', item_count: 2, total_amount: 300 },
      })

    const items = [makeItem(), makeItem({ id: 'item_2', horseNumbers: [3], amount: 200 })]
    const result = await syncCartToDynamo(items)

    expect(result).toEqual({ success: true, cartId: 'server-cart-1' })
    expect(mockAddToCart).toHaveBeenCalledTimes(2)
    // 1つ目: cart_id空
    expect(mockAddToCart.mock.calls[0][0]).toBe('')
    // 2つ目: サーバーcartId
    expect(mockAddToCart.mock.calls[1][0]).toBe('server-cart-1')
  })

  it('API失敗時はエラーを返す', async () => {
    mockAddToCart.mockResolvedValueOnce({
      success: false,
      error: 'Internal Server Error',
    })

    const result = await syncCartToDynamo([makeItem()])

    expect(result).toEqual({ success: false, error: 'Internal Server Error' })
  })

  it('2つ目のアイテムで失敗した場合はエラーを返しサーバーカートをクリーンアップする', async () => {
    mockAddToCart
      .mockResolvedValueOnce({
        success: true,
        data: { cart_id: 'server-cart-1', item_id: 'i1', item_count: 1, total_amount: 100 },
      })
      .mockResolvedValueOnce({
        success: false,
        error: 'Cart item limit exceeded',
      })

    const items = [makeItem(), makeItem({ id: 'item_2' })]
    const result = await syncCartToDynamo(items)

    expect(result).toEqual({ success: false, error: 'Cart item limit exceeded' })
    // 作成済みサーバーカートのクリーンアップが呼ばれる
    expect(mockClearCart).toHaveBeenCalledWith('server-cart-1')
  })

  it('1つ目のアイテムで失敗した場合はクリーンアップしない', async () => {
    mockAddToCart.mockResolvedValueOnce({
      success: false,
      error: 'Internal Server Error',
    })

    await syncCartToDynamo([makeItem()])

    // serverCartIdがまだ空なのでクリーンアップは呼ばれない
    expect(mockClearCart).not.toHaveBeenCalled()
  })
})
