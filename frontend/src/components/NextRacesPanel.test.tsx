import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen } from '../test/utils'
import { NextRacesPanel } from './NextRacesPanel'
import type { Race } from '../types'

// モックデータ作成ヘルパー
function createMockRace(overrides: Partial<Race> = {}): Race {
  return {
    id: 'test-race-1',
    number: '1R',
    name: 'テストレース',
    time: '10:00',
    course: '',
    condition: '良',
    venue: '05',
    date: '2026-01-31',
    startTime: '2026-01-31T10:00:00+09:00',
    bettingDeadline: '2026-01-31T09:58:00+09:00',
    trackType: '芝',
    distance: 1600,
    horseCount: 16,
    ...overrides,
  }
}

describe('NextRacesPanel', () => {
  beforeEach(() => {
    // 現在時刻を固定（2026-01-31 09:00 JST）
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-01-31T09:00:00+09:00'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('今日でない場合は何も表示しない', () => {
    const races = [createMockRace()]
    const { container } = render(<NextRacesPanel races={races} isToday={false} />)
    expect(container.firstChild).toBeNull()
  })

  it('レースがない場合は何も表示しない', () => {
    const { container } = render(<NextRacesPanel races={[]} isToday={true} />)
    expect(container.firstChild).toBeNull()
  })

  it('startTimeがないレースは表示しない', () => {
    const races = [createMockRace({ startTime: undefined })]
    const { container } = render(<NextRacesPanel races={races} isToday={true} />)
    expect(container.firstChild).toBeNull()
  })

  it('発走済みのレースは表示しない', () => {
    // 現在時刻より前のレース
    const races = [
      createMockRace({
        id: 'past-race',
        startTime: '2026-01-31T08:00:00+09:00', // 現在より1時間前
      }),
    ]
    const { container } = render(<NextRacesPanel races={races} isToday={true} />)
    expect(container.firstChild).toBeNull()
  })

  it('次のレースを表示する', () => {
    const races = [
      createMockRace({
        id: 'race-1',
        number: '1R',
        name: '第1レース',
        startTime: '2026-01-31T10:00:00+09:00',
      }),
    ]

    render(<NextRacesPanel races={races} isToday={true} />)

    expect(screen.getByText('次のレース')).toBeInTheDocument()
    expect(screen.getByText('第1レース')).toBeInTheDocument()
    expect(screen.getByText('1R')).toBeInTheDocument()
    expect(screen.getByText('東京')).toBeInTheDocument() // venue '05' → 東京
  })

  it('発走時刻順で最大2レースを表示する', () => {
    const races = [
      createMockRace({
        id: 'race-3',
        number: '3R',
        name: '第3レース',
        startTime: '2026-01-31T12:00:00+09:00',
      }),
      createMockRace({
        id: 'race-1',
        number: '1R',
        name: '第1レース',
        startTime: '2026-01-31T10:00:00+09:00',
      }),
      createMockRace({
        id: 'race-2',
        number: '2R',
        name: '第2レース',
        startTime: '2026-01-31T11:00:00+09:00',
      }),
    ]

    render(<NextRacesPanel races={races} isToday={true} />)

    // 発走時刻順で1R, 2Rが表示される（3Rは表示されない）
    expect(screen.getByText('第1レース')).toBeInTheDocument()
    expect(screen.getByText('第2レース')).toBeInTheDocument()
    expect(screen.queryByText('第3レース')).not.toBeInTheDocument()
  })

  it('カウントダウンを表示する', () => {
    const races = [
      createMockRace({
        id: 'race-1',
        startTime: '2026-01-31T10:00:00+09:00', // 1時間後
      }),
    ]

    render(<NextRacesPanel races={races} isToday={true} />)

    // 残り1時間 = 1:00:00
    expect(screen.getByText('1:00:00')).toBeInTheDocument()
    expect(screen.getByText('残り')).toBeInTheDocument()
  })

  it('グレードバッジを表示する（G1）', () => {
    const races = [
      createMockRace({
        id: 'race-g1',
        name: 'G1レース',
        startTime: '2026-01-31T10:00:00+09:00',
        gradeClass: 'G1',
      }),
    ]

    render(<NextRacesPanel races={races} isToday={true} />)

    expect(screen.getByText('GI')).toBeInTheDocument()
  })

  it('トラック情報を表示する', () => {
    const races = [
      createMockRace({
        id: 'race-1',
        startTime: '2026-01-31T10:00:00+09:00',
        trackType: 'ダート',
        distance: 1200,
        horseCount: 14,
      }),
    ]

    render(<NextRacesPanel races={races} isToday={true} />)

    expect(screen.getByText('ダート')).toBeInTheDocument()
    expect(screen.getByText('1,200m')).toBeInTheDocument()
    expect(screen.getByText('14頭')).toBeInTheDocument()
  })

  it('発走時刻と投票締切を表示する', () => {
    const races = [
      createMockRace({
        id: 'race-1',
        time: '10:00',
        startTime: '2026-01-31T10:00:00+09:00',
        bettingDeadline: '2026-01-31T09:58:00+09:00',
      }),
    ]

    render(<NextRacesPanel races={races} isToday={true} />)

    expect(screen.getByText('発走')).toBeInTheDocument()
    expect(screen.getByText('10:00')).toBeInTheDocument()
    expect(screen.getByText('締切')).toBeInTheDocument()
    expect(screen.getByText('09:58')).toBeInTheDocument()
  })
})
