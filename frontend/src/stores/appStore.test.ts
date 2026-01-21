import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { useAppStore } from './appStore'
import type { Race } from '../types'

// テスト用のモックレース
const mockRace: Race = {
  id: 'race_001',
  number: '1R',
  name: 'テストレース',
  time: '10:00',
  course: '芝1600m',
  condition: '良',
  venue: '東京',
  date: '2024-01-01',
}

describe('appStore', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    // ストアをリセット
    useAppStore.setState({
      currentPage: 'races',
      selectedRace: null,
      selectedHorses: [],
      betType: 'quinella',
      betAmount: 1000,
      consultationSessionId: null,
      toastMessage: null,
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('ナビゲーション', () => {
    it('デフォルトでracesページ', () => {
      const state = useAppStore.getState()
      expect(state.currentPage).toBe('races')
    })

    it('ページを変更できる', () => {
      useAppStore.getState().setCurrentPage('cart')
      expect(useAppStore.getState().currentPage).toBe('cart')

      useAppStore.getState().setCurrentPage('dashboard')
      expect(useAppStore.getState().currentPage).toBe('dashboard')
    })
  })

  describe('レース選択', () => {
    it('デフォルトでnull', () => {
      const state = useAppStore.getState()
      expect(state.selectedRace).toBeNull()
    })

    it('レースを選択できる', () => {
      useAppStore.getState().setSelectedRace(mockRace)

      const state = useAppStore.getState()
      expect(state.selectedRace).toEqual(mockRace)
    })

    it('レース選択時に馬選択がリセットされる', () => {
      // 先に馬を選択
      useAppStore.getState().toggleHorse(1)
      useAppStore.getState().toggleHorse(2)
      expect(useAppStore.getState().selectedHorses).toHaveLength(2)

      // レースを選択すると馬選択がリセット
      useAppStore.getState().setSelectedRace(mockRace)
      expect(useAppStore.getState().selectedHorses).toHaveLength(0)
    })

    it('レース選択をクリアできる', () => {
      useAppStore.getState().setSelectedRace(mockRace)
      useAppStore.getState().setSelectedRace(null)

      expect(useAppStore.getState().selectedRace).toBeNull()
    })
  })

  describe('馬選択', () => {
    it('デフォルトで空', () => {
      const state = useAppStore.getState()
      expect(state.selectedHorses).toHaveLength(0)
    })

    it('馬を選択できる', () => {
      useAppStore.getState().toggleHorse(1)
      useAppStore.getState().toggleHorse(3)

      const state = useAppStore.getState()
      expect(state.selectedHorses).toContain(1)
      expect(state.selectedHorses).toContain(3)
    })

    it('同じ馬を再度選択すると解除される', () => {
      useAppStore.getState().toggleHorse(1)
      expect(useAppStore.getState().selectedHorses).toContain(1)

      useAppStore.getState().toggleHorse(1)
      expect(useAppStore.getState().selectedHorses).not.toContain(1)
    })

    it('馬選択をクリアできる', () => {
      useAppStore.getState().toggleHorse(1)
      useAppStore.getState().toggleHorse(2)
      useAppStore.getState().toggleHorse(3)

      useAppStore.getState().clearSelectedHorses()

      expect(useAppStore.getState().selectedHorses).toHaveLength(0)
    })
  })

  describe('賭け設定', () => {
    it('デフォルトでquinella', () => {
      const state = useAppStore.getState()
      expect(state.betType).toBe('quinella')
    })

    it('デフォルト金額は1000円', () => {
      const state = useAppStore.getState()
      expect(state.betAmount).toBe(1000)
    })

    it('券種を変更できる', () => {
      useAppStore.getState().setBetType('trifecta')
      expect(useAppStore.getState().betType).toBe('trifecta')

      useAppStore.getState().setBetType('win')
      expect(useAppStore.getState().betType).toBe('win')
    })

    it('金額を変更できる', () => {
      useAppStore.getState().setBetAmount(5000)
      expect(useAppStore.getState().betAmount).toBe(5000)
    })
  })

  describe('相談セッション', () => {
    it('デフォルトでnull', () => {
      const state = useAppStore.getState()
      expect(state.consultationSessionId).toBeNull()
    })

    it('セッションIDを設定できる', () => {
      useAppStore.getState().setConsultationSessionId('session_123')
      expect(useAppStore.getState().consultationSessionId).toBe('session_123')
    })

    it('セッションIDをクリアできる', () => {
      useAppStore.getState().setConsultationSessionId('session_123')
      useAppStore.getState().setConsultationSessionId(null)
      expect(useAppStore.getState().consultationSessionId).toBeNull()
    })
  })

  describe('トースト', () => {
    it('デフォルトでnull', () => {
      const state = useAppStore.getState()
      expect(state.toastMessage).toBeNull()
    })

    it('トーストを表示できる', () => {
      useAppStore.getState().showToast('テストメッセージ')
      expect(useAppStore.getState().toastMessage).toBe('テストメッセージ')
    })

    it('トーストは2秒後に自動的に消える', () => {
      useAppStore.getState().showToast('テストメッセージ')
      expect(useAppStore.getState().toastMessage).toBe('テストメッセージ')

      // 2秒進める
      vi.advanceTimersByTime(2000)

      expect(useAppStore.getState().toastMessage).toBeNull()
    })

    it('手動でトーストを非表示にできる', () => {
      useAppStore.getState().showToast('テストメッセージ')
      useAppStore.getState().hideToast()
      expect(useAppStore.getState().toastMessage).toBeNull()
    })
  })
})
