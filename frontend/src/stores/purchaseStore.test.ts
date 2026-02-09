import { describe, it, expect } from 'vitest'
import { toJapaneseError } from './purchaseStore'

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
