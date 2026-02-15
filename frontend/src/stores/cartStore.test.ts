import { describe, it, expect, beforeEach } from 'vitest'
import { useCartStore } from './cartStore'

// テスト用のモックアイテム
const createMockCartItem = (overrides = {}) => ({
  raceId: 'race_001',
  raceName: 'テストレース',
  raceVenue: '東京',
  raceNumber: '1R',
  betType: 'quinella' as const,
  horseNumbers: [1, 2],
  amount: 1000,
  ...overrides,
})

describe('cartStore', () => {
  beforeEach(() => {
    // 各テスト前にストアをリセット
    useCartStore.getState().clearCart()
  })

  describe('初期状態', () => {
    it('空のカートを持つ', () => {
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(0)
    })

    it('カートIDが生成されている', () => {
      const state = useCartStore.getState()
      expect(state.cartId).toBeDefined()
      expect(state.cartId).toMatch(/^cart_/)
    })
  })

  describe('addItem', () => {
    it('アイテムをカートに追加できる', () => {
      const item = createMockCartItem()
      const result = useCartStore.getState().addItem(item)

      expect(result).toBe('ok')
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(1)
      expect(state.items[0].raceName).toBe('テストレース')
      expect(state.items[0].betType).toBe('quinella')
    })

    it('追加されたアイテムにIDが付与される', () => {
      const item = createMockCartItem()
      useCartStore.getState().addItem(item)

      const state = useCartStore.getState()
      expect(state.items[0].id).toBeDefined()
      expect(state.items[0].id).toMatch(/^item_/)
    })

    it('同一レースの買い目を複数追加できる', () => {
      const raceId = 'race_001'
      useCartStore.getState().addItem(createMockCartItem({ raceId, raceName: 'レース1', horseNumbers: [1, 2] }))
      useCartStore.getState().addItem(createMockCartItem({ raceId, raceName: 'レース1', horseNumbers: [3, 4] }))
      useCartStore.getState().addItem(createMockCartItem({ raceId, raceName: 'レース1', horseNumbers: [5, 6] }))

      const state = useCartStore.getState()
      expect(state.items).toHaveLength(3)
    })

    it('異なるレースの買い目は追加できない', () => {
      useCartStore.getState().addItem(createMockCartItem({ raceId: 'race_001' }))
      const result = useCartStore.getState().addItem(createMockCartItem({ raceId: 'race_002' }))

      expect(result).toBe('different_race')
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(1)
      expect(state.items[0].raceId).toBe('race_001')
    })

    it('カートが空の場合は任意のレースを追加できる', () => {
      const result = useCartStore.getState().addItem(createMockCartItem({ raceId: 'any_race' }))

      expect(result).toBe('ok')
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(1)
      expect(state.items[0].raceId).toBe('any_race')
    })

    it('カートクリア後は別のレースを追加できる', () => {
      useCartStore.getState().addItem(createMockCartItem({ raceId: 'race_001' }))
      useCartStore.getState().clearCart()
      const result = useCartStore.getState().addItem(createMockCartItem({ raceId: 'race_002' }))

      expect(result).toBe('ok')
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(1)
      expect(state.items[0].raceId).toBe('race_002')
    })
  })

  describe('removeItem', () => {
    it('アイテムをカートから削除できる', () => {
      useCartStore.getState().addItem(createMockCartItem())
      const itemId = useCartStore.getState().items[0].id

      useCartStore.getState().removeItem(itemId)

      const state = useCartStore.getState()
      expect(state.items).toHaveLength(0)
    })

    it('存在しないIDで削除しても他のアイテムに影響しない', () => {
      useCartStore.getState().addItem(createMockCartItem())
      useCartStore.getState().removeItem('non_existent_id')

      const state = useCartStore.getState()
      expect(state.items).toHaveLength(1)
    })

    it('特定のアイテムのみ削除される', () => {
      useCartStore.getState().addItem(createMockCartItem({ raceName: 'レース1', horseNumbers: [1, 2] }))
      useCartStore.getState().addItem(createMockCartItem({ raceName: 'レース2', horseNumbers: [3, 4] }))
      const itemToRemove = useCartStore.getState().items[0].id

      useCartStore.getState().removeItem(itemToRemove)

      const state = useCartStore.getState()
      expect(state.items).toHaveLength(1)
      expect(state.items[0].raceName).toBe('レース2')
    })
  })

  describe('clearCart', () => {
    it('カートを空にできる', () => {
      useCartStore.getState().addItem(createMockCartItem())
      useCartStore.getState().addItem(createMockCartItem())

      useCartStore.getState().clearCart()

      const state = useCartStore.getState()
      expect(state.items).toHaveLength(0)
    })

    it('クリア時に新しいカートIDが生成される', () => {
      const oldCartId = useCartStore.getState().cartId
      useCartStore.getState().clearCart()

      const newCartId = useCartStore.getState().cartId
      expect(newCartId).not.toBe(oldCartId)
    })
  })

  describe('getTotalAmount', () => {
    it('空のカートで0を返す', () => {
      const total = useCartStore.getState().getTotalAmount()
      expect(total).toBe(0)
    })

    it('単一アイテムの合計を計算できる', () => {
      useCartStore.getState().addItem(createMockCartItem({ amount: 1500 }))

      const total = useCartStore.getState().getTotalAmount()
      expect(total).toBe(1500)
    })

    it('複数アイテムの合計を計算できる', () => {
      useCartStore.getState().addItem(createMockCartItem({ amount: 1000 }))
      useCartStore.getState().addItem(createMockCartItem({ amount: 2000 }))
      useCartStore.getState().addItem(createMockCartItem({ amount: 500 }))

      const total = useCartStore.getState().getTotalAmount()
      expect(total).toBe(3500)
    })
  })

  describe('getItemCount', () => {
    it('空のカートで0を返す', () => {
      const count = useCartStore.getState().getItemCount()
      expect(count).toBe(0)
    })

    it('アイテム数を正しく返す', () => {
      useCartStore.getState().addItem(createMockCartItem({ horseNumbers: [1, 2] }))
      useCartStore.getState().addItem(createMockCartItem({ horseNumbers: [3, 4] }))
      useCartStore.getState().addItem(createMockCartItem({ horseNumbers: [5, 6] }))

      const count = useCartStore.getState().getItemCount()
      expect(count).toBe(3)
    })
  })

  describe('updateItemAmount', () => {
    it('アイテムの金額を更新できる', () => {
      useCartStore.getState().addItem(createMockCartItem({ amount: 1000 }))
      const itemId = useCartStore.getState().items[0].id

      useCartStore.getState().updateItemAmount(itemId, 2000)

      const state = useCartStore.getState()
      expect(state.items[0].amount).toBe(2000)
    })

    it('存在しないIDでは何も変更しない', () => {
      useCartStore.getState().addItem(createMockCartItem({ amount: 1000 }))

      useCartStore.getState().updateItemAmount('non_existent_id', 2000)

      const state = useCartStore.getState()
      expect(state.items[0].amount).toBe(1000)
    })

    it('特定のアイテムのみ金額が更新される', () => {
      useCartStore.getState().addItem(createMockCartItem({ horseNumbers: [1, 2], amount: 1000 }))
      useCartStore.getState().addItem(createMockCartItem({ horseNumbers: [3, 4], amount: 1500 }))
      const itemId = useCartStore.getState().items[0].id

      useCartStore.getState().updateItemAmount(itemId, 3000)

      const state = useCartStore.getState()
      expect(state.items[0].amount).toBe(3000)
      expect(state.items[1].amount).toBe(1500)
    })

    it('合計金額も正しく再計算される', () => {
      useCartStore.getState().addItem(createMockCartItem({ horseNumbers: [1, 2], amount: 1000 }))
      useCartStore.getState().addItem(createMockCartItem({ horseNumbers: [3, 4], amount: 2000 }))
      const itemId = useCartStore.getState().items[0].id

      useCartStore.getState().updateItemAmount(itemId, 5000)

      const total = useCartStore.getState().getTotalAmount()
      expect(total).toBe(7000) // 5000 + 2000
    })

    it('最低金額（100円）未満の値は無視される', () => {
      useCartStore.getState().addItem(createMockCartItem({ amount: 1000 }))
      const itemId = useCartStore.getState().items[0].id

      useCartStore.getState().updateItemAmount(itemId, 50)

      const state = useCartStore.getState()
      expect(state.items[0].amount).toBe(1000) // 変更されない
    })

    it('0円は無視される', () => {
      useCartStore.getState().addItem(createMockCartItem({ amount: 1000 }))
      const itemId = useCartStore.getState().items[0].id

      useCartStore.getState().updateItemAmount(itemId, 0)

      const state = useCartStore.getState()
      expect(state.items[0].amount).toBe(1000) // 変更されない
    })

    it('負の値は無視される', () => {
      useCartStore.getState().addItem(createMockCartItem({ amount: 1000 }))
      const itemId = useCartStore.getState().items[0].id

      useCartStore.getState().updateItemAmount(itemId, -500)

      const state = useCartStore.getState()
      expect(state.items[0].amount).toBe(1000) // 変更されない
    })

    it('最大金額（100,000円）を超える値は無視される', () => {
      useCartStore.getState().addItem(createMockCartItem({ amount: 1000 }))
      const itemId = useCartStore.getState().items[0].id

      useCartStore.getState().updateItemAmount(itemId, 150000)

      const state = useCartStore.getState()
      expect(state.items[0].amount).toBe(1000) // 変更されない
    })

    it('最大金額（100,000円）ちょうどは更新される', () => {
      useCartStore.getState().addItem(createMockCartItem({ amount: 1000 }))
      const itemId = useCartStore.getState().items[0].id

      useCartStore.getState().updateItemAmount(itemId, 100000)

      const state = useCartStore.getState()
      expect(state.items[0].amount).toBe(100000)
    })
  })

  describe('getCurrentRaceId', () => {
    it('カートが空の場合はnullを返す', () => {
      const raceId = useCartStore.getState().getCurrentRaceId()
      expect(raceId).toBeNull()
    })

    it('カートにアイテムがある場合は最初のアイテムのraceIdを返す', () => {
      useCartStore.getState().addItem(createMockCartItem({ raceId: 'race_123' }))

      const raceId = useCartStore.getState().getCurrentRaceId()
      expect(raceId).toBe('race_123')
    })

    it('複数のアイテムがある場合も最初のアイテムのraceIdを返す', () => {
      useCartStore.getState().addItem(createMockCartItem({ raceId: 'race_abc' }))
      useCartStore.getState().addItem(createMockCartItem({ raceId: 'race_abc' }))

      const raceId = useCartStore.getState().getCurrentRaceId()
      expect(raceId).toBe('race_abc')
    })
  })

  describe('addItem金額バリデーション', () => {
    it('MAX_BET_AMOUNTを超える金額のアイテムは追加できない', () => {
      const result = useCartStore.getState().addItem(
        createMockCartItem({ amount: 150000 })
      )

      expect(result).toBe('invalid_amount')
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(0)
    })

    it('MAX_BET_AMOUNTちょうどの金額は追加できる', () => {
      const result = useCartStore.getState().addItem(
        createMockCartItem({ amount: 100000 })
      )

      expect(result).toBe('ok')
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(1)
    })

    it('MIN_BET_AMOUNT未満の金額は追加できない', () => {
      const result = useCartStore.getState().addItem(
        createMockCartItem({ amount: 50 })
      )

      expect(result).toBe('invalid_amount')
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(0)
    })

    it('0円のアイテムは追加できない', () => {
      const result = useCartStore.getState().addItem(
        createMockCartItem({ amount: 0 })
      )

      expect(result).toBe('invalid_amount')
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(0)
    })

    it('負の金額のアイテムは追加できない', () => {
      const result = useCartStore.getState().addItem(
        createMockCartItem({ amount: -1000 })
      )

      expect(result).toBe('invalid_amount')
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(0)
    })
  })

  describe('重複検出と金額合算', () => {
    it('同一券種・同一馬番の買い目を追加すると金額が合算される', () => {
      useCartStore.getState().addItem(
        createMockCartItem({ betType: 'quinella', horseNumbers: [2, 6], betDisplay: '2-6', amount: 300 })
      )
      const result = useCartStore.getState().addItem(
        createMockCartItem({ betType: 'quinella', horseNumbers: [2, 6], betDisplay: '2-6', amount: 600 })
      )

      expect(result).toBe('merged')
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(1)
      expect(state.items[0].amount).toBe(900) // 300 + 600
    })

    it('合算後にMAX_BET_AMOUNTを超える場合は上限でクランプされる', () => {
      useCartStore.getState().addItem(
        createMockCartItem({ betType: 'win', horseNumbers: [1], betDisplay: '1', amount: 80000 })
      )
      const result = useCartStore.getState().addItem(
        createMockCartItem({ betType: 'win', horseNumbers: [1], betDisplay: '1', amount: 50000 })
      )

      expect(result).toBe('merged')
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(1)
      expect(state.items[0].amount).toBe(100000) // MAX_BET_AMOUNT
    })

    it('券種が異なれば重複とみなさない', () => {
      useCartStore.getState().addItem(
        createMockCartItem({ betType: 'quinella', horseNumbers: [2, 6], betDisplay: '2-6', amount: 300 })
      )
      const result = useCartStore.getState().addItem(
        createMockCartItem({ betType: 'exacta', horseNumbers: [2, 6], betDisplay: '2-6', amount: 600 })
      )

      expect(result).toBe('ok')
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(2)
    })

    it('馬番が異なれば重複とみなさない', () => {
      useCartStore.getState().addItem(
        createMockCartItem({ betType: 'quinella', horseNumbers: [2, 6], betDisplay: '2-6', amount: 300 })
      )
      const result = useCartStore.getState().addItem(
        createMockCartItem({ betType: 'quinella', horseNumbers: [2, 8], betDisplay: '2-8', amount: 600 })
      )

      expect(result).toBe('ok')
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(2)
    })

    it('順序依存券種（馬単）は逆順の馬番を重複とみなさない', () => {
      useCartStore.getState().addItem(
        createMockCartItem({ betType: 'exacta', horseNumbers: [2, 6], amount: 300 })
      )
      const result = useCartStore.getState().addItem(
        createMockCartItem({ betType: 'exacta', horseNumbers: [6, 2], amount: 600 })
      )

      expect(result).toBe('ok')
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(2)
    })

    it('順序依存券種（三連単）は同順の馬番を重複とみなす', () => {
      useCartStore.getState().addItem(
        createMockCartItem({ betType: 'trifecta', horseNumbers: [1, 2, 3], amount: 300 })
      )
      const result = useCartStore.getState().addItem(
        createMockCartItem({ betType: 'trifecta', horseNumbers: [1, 2, 3], amount: 600 })
      )

      expect(result).toBe('merged')
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(1)
      expect(state.items[0].amount).toBe(900)
    })

    it('betDisplayがない場合はhorseNumbersのソート比較で重複判定する', () => {
      useCartStore.getState().addItem(
        createMockCartItem({ betType: 'quinella', horseNumbers: [6, 2], amount: 300 })
      )
      const result = useCartStore.getState().addItem(
        createMockCartItem({ betType: 'quinella', horseNumbers: [2, 6], amount: 600 })
      )

      expect(result).toBe('merged')
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(1)
      expect(state.items[0].amount).toBe(900)
    })
  })

  describe('様々な券種', () => {
    it('単勝を追加できる', () => {
      useCartStore.getState().addItem(
        createMockCartItem({ betType: 'win', horseNumbers: [1] })
      )

      const state = useCartStore.getState()
      expect(state.items[0].betType).toBe('win')
      expect(state.items[0].horseNumbers).toEqual([1])
    })

    it('三連単を追加できる', () => {
      useCartStore.getState().addItem(
        createMockCartItem({ betType: 'trifecta', horseNumbers: [1, 2, 3] })
      )

      const state = useCartStore.getState()
      expect(state.items[0].betType).toBe('trifecta')
      expect(state.items[0].horseNumbers).toEqual([1, 2, 3])
    })
  })
})
