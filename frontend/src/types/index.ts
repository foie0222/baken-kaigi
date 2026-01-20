// レース関連
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
