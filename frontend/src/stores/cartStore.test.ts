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

      expect(result).toBe(true)
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

      expect(result).toBe(false)
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(1)
      expect(state.items[0].raceId).toBe('race_001')
    })

    it('カートが空の場合は任意のレースを追加できる', () => {
      const result = useCartStore.getState().addItem(createMockCartItem({ raceId: 'any_race' }))

      expect(result).toBe(true)
      const state = useCartStore.getState()
      expect(state.items).toHaveLength(1)
      expect(state.items[0].raceId).toBe('any_race')
    })

    it('カートクリア後は別のレースを追加できる', () => {
      useCartStore.getState().addItem(createMockCartItem({ raceId: 'race_001' }))
      useCartStore.getState().clearCart()
      const result = useCartStore.getState().addItem(createMockCartItem({ raceId: 'race_002' }))

      expect(result).toBe(true)
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
      useCartStore.getState().addItem(createMockCartItem({ raceName: 'レース1' }))
      useCartStore.getState().addItem(createMockCartItem({ raceName: 'レース2' }))
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
      useCartStore.getState().addItem(createMockCartItem())
      useCartStore.getState().addItem(createMockCartItem())
      useCartStore.getState().addItem(createMockCartItem())

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
      useCartStore.getState().addItem(createMockCartItem({ amount: 1000 }))
      useCartStore.getState().addItem(createMockCartItem({ amount: 1500 }))
      const itemId = useCartStore.getState().items[0].id

      useCartStore.getState().updateItemAmount(itemId, 3000)

      const state = useCartStore.getState()
      expect(state.items[0].amount).toBe(3000)
      expect(state.items[1].amount).toBe(1500)
    })

    it('合計金額も正しく再計算される', () => {
      useCartStore.getState().addItem(createMockCartItem({ amount: 1000 }))
      useCartStore.getState().addItem(createMockCartItem({ amount: 2000 }))
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

  describe('currentRunnersData', () => {
    it('runnersData付きでaddItemするとcurrentRunnersDataに保存される', () => {
      const runnersData = [
        { horse_number: 1, horse_name: '馬A', odds: 5.0, popularity: 2, frame_number: 1 },
        { horse_number: 2, horse_name: '馬B', odds: 3.0, popularity: 1, frame_number: 1 },
      ]
      useCartStore.getState().addItem(createMockCartItem({ runnersData }))

      const state = useCartStore.getState()
      expect(state.currentRunnersData).toHaveLength(2)
      expect(state.currentRunnersData[0].horse_name).toBe('馬A')
    })

    it('runnersDataなしでaddItemしてもcurrentRunnersDataは変更されない', () => {
      useCartStore.getState().addItem(createMockCartItem())

      const state = useCartStore.getState()
      expect(state.currentRunnersData).toHaveLength(0)
    })

    it('同一レースで複数回addItemしてもrunnersDataは1セットだけ保持', () => {
      const runnersData = [
        { horse_number: 1, horse_name: '馬A', odds: 5.0, popularity: 2, frame_number: 1 },
      ]
      useCartStore.getState().addItem(createMockCartItem({ runnersData }))
      useCartStore.getState().addItem(createMockCartItem({ runnersData }))

      const state = useCartStore.getState()
      expect(state.items).toHaveLength(2)
      expect(state.currentRunnersData).toHaveLength(1) // 重複保持しない
    })

    it('clearCartでcurrentRunnersDataもクリアされる', () => {
      const runnersData = [
        { horse_number: 1, horse_name: '馬A', odds: 5.0, popularity: 2, frame_number: 1 },
      ]
      useCartStore.getState().addItem(createMockCartItem({ runnersData }))
      useCartStore.getState().clearCart()

      const state = useCartStore.getState()
      expect(state.currentRunnersData).toHaveLength(0)
    })

    it('CartItemにrunnersDataが含まれない', () => {
      const runnersData = [
        { horse_number: 1, horse_name: '馬A', odds: 5.0, popularity: 2, frame_number: 1 },
      ]
      useCartStore.getState().addItem(createMockCartItem({ runnersData }))

      const state = useCartStore.getState()
      // CartItemにはrunnersDataプロパティがない
      expect('runnersData' in state.items[0]).toBe(false)
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
