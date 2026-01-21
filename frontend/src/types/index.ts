// 会場コード → 会場名
export const VenueNames: Record<string, string> = {
  '01': '札幌',
  '02': '函館',
  '03': '福島',
  '04': '新潟',
  '05': '東京',
  '06': '中山',
  '07': '中京',
  '08': '京都',
  '09': '阪神',
  '10': '小倉',
};

export function getVenueName(code: string): string {
  return VenueNames[code] || code;
}

// レース関連（API形式）
export interface ApiRace {
  race_id: string;
  race_name: string;
  race_number: number;
  venue: string;
  start_time: string;
  betting_deadline: string;
  track_condition: string;
}

export interface ApiRunner {
  horse_number: number;
  horse_name: string;
  jockey_name: string;
  odds: string;
  popularity: number;
}

export interface ApiRacesResponse {
  races: ApiRace[];
  venues: string[];
  target_date: string;
}

export interface ApiRaceDetailResponse {
  race: ApiRace;
  runners: ApiRunner[];
}

// レース関連（フロントエンド表示用）
export interface Race {
  id: string;
  number: string;
  name: string;
  time: string;
  course: string;
  condition: string;
  venue: string;
  date: string;
}

export interface Horse {
  number: number;
  name: string;
  jockey: string;
  odds: number;
  popularity: number;
  color: string;
}

export interface RaceDetail extends Race {
  horses: Horse[];
}

// API → フロントエンド 変換関数
export function mapApiRaceToRace(apiRace: ApiRace): Race {
  const startTime = new Date(apiRace.start_time);
  const hours = startTime.getHours().toString().padStart(2, '0');
  const minutes = startTime.getMinutes().toString().padStart(2, '0');

  return {
    id: apiRace.race_id,
    number: `${apiRace.race_number}R`,
    name: apiRace.race_name,
    time: `${hours}:${minutes}`,
    course: '',
    condition: apiRace.track_condition,
    venue: apiRace.venue,
    date: apiRace.start_time.split('T')[0],
  };
}

export function mapApiRaceDetailToRaceDetail(
  apiRace: ApiRace,
  runners: ApiRunner[]
): RaceDetail {
  const race = mapApiRaceToRace(apiRace);
  const colors = [
    '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
    '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9',
    '#F1948A', '#82E0AA', '#F8B500', '#5DADE2', '#AF7AC5',
    '#48C9B0', '#F9E79F', '#AED6F1',
  ];

  return {
    ...race,
    horses: runners.map((runner) => ({
      number: runner.horse_number,
      name: runner.horse_name,
      jockey: runner.jockey_name,
      odds: parseFloat(runner.odds),
      popularity: runner.popularity,
      color: colors[(runner.horse_number - 1) % colors.length],
    })),
  };
}

// 券種
export type BetType = 'win' | 'place' | 'quinella' | 'exacta' | 'trio' | 'trifecta';

export const BetTypeLabels: Record<BetType, string> = {
  win: '単勝',
  place: '複勝',
  quinella: '馬連',
  exacta: '馬単',
  trio: '三連複',
  trifecta: '三連単',
};

export const BetTypeRequiredHorses: Record<BetType, number> = {
  win: 1,
  place: 1,
  quinella: 2,
  exacta: 2,
  trio: 3,
  trifecta: 3,
};

// カート
export interface CartItem {
  id: string;
  raceId: string;
  raceName: string;
  raceVenue: string;
  raceNumber: string;
  betType: BetType;
  horseNumbers: number[];
  amount: number;
}

export interface Cart {
  id: string;
  items: CartItem[];
  totalAmount: number;
}

// 相談セッション
export type MessageType = 'user' | 'ai' | 'system';

export interface Message {
  id: string;
  type: MessageType;
  content: string;
  timestamp: string;
}

export interface ConsultationSession {
  id: string;
  status: 'active' | 'completed' | 'cancelled';
  messages: Message[];
}

// API レスポンス
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

// アプリ状態
export type PageType = 'races' | 'dashboard' | 'history' | 'settings' | 'cart';
