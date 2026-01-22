import { describe, it, expect } from 'vitest'
import {
  getVenueName,
  VenueNames,
  mapApiRaceToRace,
  mapApiRaceDetailToRaceDetail,
  BetTypeLabels,
  BetTypeRequiredHorses,
} from './index'
import type { ApiRace, ApiRunner } from './index'

describe('VenueNames', () => {
  it('全ての会場コードが定義されている', () => {
    expect(VenueNames['01']).toBe('札幌')
    expect(VenueNames['05']).toBe('東京')
    expect(VenueNames['06']).toBe('中山')
    expect(VenueNames['08']).toBe('京都')
    expect(VenueNames['09']).toBe('阪神')
  })
})

describe('getVenueName', () => {
  it('会場コードから会場名を取得できる', () => {
    expect(getVenueName('01')).toBe('札幌')
    expect(getVenueName('05')).toBe('東京')
    expect(getVenueName('10')).toBe('小倉')
  })

  it('未知のコードはそのまま返す', () => {
    expect(getVenueName('99')).toBe('99')
    expect(getVenueName('unknown')).toBe('unknown')
  })
})

describe('mapApiRaceToRace', () => {
  const mockApiRace: ApiRace = {
    race_id: 'race_001',
    race_name: 'テストレース',
    race_number: 5,
    venue: '東京',
    start_time: '2024-06-15T15:30:00',
    betting_deadline: '2024-06-15T15:25:00',
    track_condition: '良',
  }

  it('APIレースをフロントエンド形式に変換する', () => {
    const race = mapApiRaceToRace(mockApiRace)

    expect(race.id).toBe('race_001')
    expect(race.number).toBe('5R')
    expect(race.name).toBe('テストレース')
    expect(race.time).toBe('15:30')
    expect(race.condition).toBe('良')
    expect(race.venue).toBe('東京')
    expect(race.date).toBe('2024-06-15')
  })

  it('午前の時刻を正しくフォーマットする', () => {
    const morningRace: ApiRace = {
      ...mockApiRace,
      start_time: '2024-06-15T09:05:00',
    }

    const race = mapApiRaceToRace(morningRace)
    expect(race.time).toBe('09:05')
  })

  it('レース番号を正しくフォーマットする', () => {
    const firstRace: ApiRace = { ...mockApiRace, race_number: 1 }
    const lastRace: ApiRace = { ...mockApiRace, race_number: 12 }

    expect(mapApiRaceToRace(firstRace).number).toBe('1R')
    expect(mapApiRaceToRace(lastRace).number).toBe('12R')
  })
})

describe('mapApiRaceDetailToRaceDetail', () => {
  const mockApiRace: ApiRace = {
    race_id: 'race_001',
    race_name: 'テストレース',
    race_number: 1,
    venue: '東京',
    start_time: '2024-06-15T10:00:00',
    betting_deadline: '2024-06-15T09:55:00',
    track_condition: '良',
  }

  const mockRunners: ApiRunner[] = [
    {
      horse_number: 1,
      waku_ban: 1,
      horse_name: 'テストホース1',
      jockey_name: 'テストジョッキー1',
      odds: '3.5',
      popularity: 1,
    },
    {
      horse_number: 2,
      waku_ban: 2,
      horse_name: 'テストホース2',
      jockey_name: 'テストジョッキー2',
      odds: '8.0',
      popularity: 3,
    },
  ]

  it('レース詳細を変換する', () => {
    const detail = mapApiRaceDetailToRaceDetail(mockApiRace, mockRunners)

    expect(detail.id).toBe('race_001')
    expect(detail.name).toBe('テストレース')
    expect(detail.horses).toHaveLength(2)
  })

  it('馬情報を正しく変換する', () => {
    const detail = mapApiRaceDetailToRaceDetail(mockApiRace, mockRunners)

    expect(detail.horses[0].number).toBe(1)
    expect(detail.horses[0].name).toBe('テストホース1')
    expect(detail.horses[0].jockey).toBe('テストジョッキー1')
    expect(detail.horses[0].odds).toBe(3.5)
    expect(detail.horses[0].popularity).toBe(1)
  })

  it('各馬に色が割り当てられる', () => {
    const detail = mapApiRaceDetailToRaceDetail(mockApiRace, mockRunners)

    expect(detail.horses[0].color).toBeDefined()
    expect(detail.horses[1].color).toBeDefined()
    expect(detail.horses[0].color).not.toBe(detail.horses[1].color)
  })

  it('オッズが数値に変換される', () => {
    const detail = mapApiRaceDetailToRaceDetail(mockApiRace, mockRunners)

    expect(typeof detail.horses[0].odds).toBe('number')
    expect(detail.horses[0].odds).toBe(3.5)
  })
})

describe('BetTypeLabels', () => {
  it('全ての券種ラベルが定義されている', () => {
    expect(BetTypeLabels.win).toBe('単勝')
    expect(BetTypeLabels.place).toBe('複勝')
    expect(BetTypeLabels.quinella).toBe('馬連')
    expect(BetTypeLabels.quinella_place).toBe('ワイド')
    expect(BetTypeLabels.exacta).toBe('馬単')
    expect(BetTypeLabels.trio).toBe('三連複')
    expect(BetTypeLabels.trifecta).toBe('三連単')
  })
})

describe('BetTypeRequiredHorses', () => {
  it('単勝・複勝は1頭必要', () => {
    expect(BetTypeRequiredHorses.win).toBe(1)
    expect(BetTypeRequiredHorses.place).toBe(1)
  })

  it('馬連・ワイド・馬単は2頭必要', () => {
    expect(BetTypeRequiredHorses.quinella).toBe(2)
    expect(BetTypeRequiredHorses.quinella_place).toBe(2)
    expect(BetTypeRequiredHorses.exacta).toBe(2)
  })

  it('三連複・三連単は3頭必要', () => {
    expect(BetTypeRequiredHorses.trio).toBe(3)
    expect(BetTypeRequiredHorses.trifecta).toBe(3)
  })
})
