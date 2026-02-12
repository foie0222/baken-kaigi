import { describe, it, expect } from 'vitest'
import {
  getVenueName,
  isJraVenue,
  VenueNames,
  mapApiRaceToRace,
  mapApiRaceDetailToRaceDetail,
  BetTypeLabels,
  BetTypeRequiredHorses,
  toRaceGrade,
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

describe('isJraVenue', () => {
  it('JRA会場コード（01〜10）はtrueを返す', () => {
    expect(isJraVenue('01')).toBe(true)
    expect(isJraVenue('05')).toBe(true)
    expect(isJraVenue('10')).toBe(true)
  })

  it('NAR地方競馬の会場コードはfalseを返す', () => {
    expect(isJraVenue('43')).toBe(false) // 笠松
    expect(isJraVenue('54')).toBe(false) // 佐賀
  })

  it('未知のコードはfalseを返す', () => {
    expect(isJraVenue('99')).toBe(false)
    expect(isJraVenue('')).toBe(false)
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

  it('条件フィールドが正しくマッピングされる', () => {
    const raceWithConditions: ApiRace = {
      ...mockApiRace,
      grade_class: '未勝利',
      age_condition: '3歳',
      is_obstacle: false,
    }

    const race = mapApiRaceToRace(raceWithConditions)

    expect(race.gradeClass).toBe('未勝利')
    expect(race.ageCondition).toBe('3歳')
    expect(race.isObstacle).toBe(false)
  })

  it('G1レースの条件フィールドが正しくマッピングされる', () => {
    const g1Race: ApiRace = {
      ...mockApiRace,
      race_name: '日本ダービー',
      grade_class: 'G1',
      age_condition: '3歳',
      is_obstacle: false,
    }

    const race = mapApiRaceToRace(g1Race)

    expect(race.gradeClass).toBe('G1')
    expect(race.ageCondition).toBe('3歳')
    expect(race.isObstacle).toBe(false)
  })

  it('障害レースの場合 trackType は undefined になる', () => {
    const obstacleRace: ApiRace = {
      ...mockApiRace,
      race_name: '障害オープン',
      track_type: '障害',
      grade_class: 'OP',
      age_condition: '4歳以上',
      is_obstacle: true,
    }

    const race = mapApiRaceToRace(obstacleRace)

    expect(race.trackType).toBeUndefined()
    expect(race.gradeClass).toBe('OP')
    expect(race.ageCondition).toBe('4歳以上')
    expect(race.isObstacle).toBe(true)
  })

  it('通常レースの場合 trackType はそのまま返される', () => {
    const normalRace: ApiRace = {
      ...mockApiRace,
      track_type: '芝',
      is_obstacle: false,
    }

    const race = mapApiRaceToRace(normalRace)

    expect(race.trackType).toBe('芝')
    expect(race.isObstacle).toBe(false)
  })

  it('不正な grade_class は undefined になる', () => {
    const invalidGradeRace: ApiRace = {
      ...mockApiRace,
      grade_class: 'invalid_grade',
    }

    const race = mapApiRaceToRace(invalidGradeRace)

    expect(race.gradeClass).toBeUndefined()
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

  it('馬体重データが存在する場合、正しく変換される', () => {
    const runnersWithWeight: ApiRunner[] = [
      {
        horse_number: 1,
        waku_ban: 1,
        horse_name: 'テストホース1',
        jockey_name: 'テストジョッキー1',
        odds: '3.5',
        popularity: 1,
        weight: 480,
        weight_diff: 4,
      },
      {
        horse_number: 2,
        waku_ban: 2,
        horse_name: 'テストホース2',
        jockey_name: 'テストジョッキー2',
        odds: '8.0',
        popularity: 3,
        weight: 456,
        weight_diff: -2,
      },
    ]

    const detail = mapApiRaceDetailToRaceDetail(mockApiRace, runnersWithWeight)

    expect(detail.horses[0].weight).toBe(480)
    expect(detail.horses[0].weightDiff).toBe(4)
    expect(detail.horses[1].weight).toBe(456)
    expect(detail.horses[1].weightDiff).toBe(-2)
  })

  it('馬体重データが存在しない場合、undefined として扱われる', () => {
    const runnersWithoutWeight: ApiRunner[] = [
      {
        horse_number: 1,
        waku_ban: 1,
        horse_name: 'テストホース1',
        jockey_name: 'テストジョッキー1',
        odds: '3.5',
        popularity: 1,
      },
    ]

    const detail = mapApiRaceDetailToRaceDetail(mockApiRace, runnersWithoutWeight)

    expect(detail.horses[0].weight).toBeUndefined()
    expect(detail.horses[0].weightDiff).toBeUndefined()
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

describe('toRaceGrade', () => {
  it('有効な RaceGrade 値を返す', () => {
    expect(toRaceGrade('新馬')).toBe('新馬')
    expect(toRaceGrade('未出走')).toBe('未出走')
    expect(toRaceGrade('未勝利')).toBe('未勝利')
    expect(toRaceGrade('1勝')).toBe('1勝')
    expect(toRaceGrade('2勝')).toBe('2勝')
    expect(toRaceGrade('3勝')).toBe('3勝')
    expect(toRaceGrade('OP')).toBe('OP')
    expect(toRaceGrade('L')).toBe('L')
    expect(toRaceGrade('G3')).toBe('G3')
    expect(toRaceGrade('G2')).toBe('G2')
    expect(toRaceGrade('G1')).toBe('G1')
  })

  it('空文字は undefined を返す', () => {
    expect(toRaceGrade('')).toBeUndefined()
  })

  it('不正な値は undefined を返す', () => {
    expect(toRaceGrade('invalid')).toBeUndefined()
    expect(toRaceGrade('オープン')).toBeUndefined() // OP以外は無効
    expect(toRaceGrade('1勝クラス')).toBeUndefined() // 1勝以外は無効
  })

  it('undefined は undefined を返す', () => {
    expect(toRaceGrade(undefined)).toBeUndefined()
  })
})
