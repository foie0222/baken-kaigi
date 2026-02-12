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

// JRA会場コードかどうかを判定
export function isJraVenue(code: string): boolean {
  return code in VenueNames;
}

// JRA公式の枠色（帽色）
export const WakuColors: Record<number, { background: string; text: string }> = {
  1: { background: '#FFFFFF', text: '#000000' }, // 白枠 → 文字は黒
  2: { background: '#000000', text: '#FFFFFF' }, // 黒枠 → 文字は白
  3: { background: '#E8384F', text: '#FFFFFF' }, // 赤枠
  4: { background: '#1E90FF', text: '#FFFFFF' }, // 青枠
  5: { background: '#FFD700', text: '#000000' }, // 黄枠 → 文字は黒
  6: { background: '#2E8B57', text: '#FFFFFF' }, // 緑枠
  7: { background: '#FF8C00', text: '#FFFFFF' }, // 橙枠
  8: { background: '#FF69B4', text: '#FFFFFF' }, // 桃枠
};

export function getWakuColor(wakuBan: number): { background: string; text: string } {
  return WakuColors[wakuBan] || { background: '#CCCCCC', text: '#000000' };
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
  track_type?: string;
  distance?: number;
  horse_count?: number;
  // 条件フィールド
  grade_class?: string;
  age_condition?: string;
  is_obstacle?: boolean;
  // JRA出馬表URL生成用
  kaisai_kai?: string;
  kaisai_nichime?: string;
  jra_checksum?: number | null;
}

export interface ApiRunner {
  horse_number: number;
  waku_ban: number;
  horse_name: string;
  jockey_name: string;
  odds: string;
  popularity: number;
  weight?: number;       // 馬体重(kg)
  weight_diff?: number;  // 前走比増減
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

// レースクラス
export type RaceGrade = '新馬' | '未出走' | '未勝利' | '1勝' | '2勝' | '3勝' | 'OP' | 'L' | 'G3' | 'G2' | 'G1';

// RaceGrade の許容値セット（バリデーション用）
const VALID_RACE_GRADES: ReadonlySet<string> = new Set([
  '新馬', '未出走', '未勝利', '1勝', '2勝', '3勝', 'OP', 'L', 'G3', 'G2', 'G1'
]);

// 文字列を RaceGrade に安全に変換（不正値は undefined）
export function toRaceGrade(value: string | undefined): RaceGrade | undefined {
  if (!value || !VALID_RACE_GRADES.has(value)) {
    return undefined;
  }
  return value as RaceGrade;
}

// 斤量条件
export type WeightType = '定量' | '別定' | 'ハンデ' | '馬齢';

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
  // 発走時刻・投票期限（ISO形式）
  startTime?: string;
  bettingDeadline?: string;
  // 追加フィールド（モック用）
  trackType?: string;   // 芝/ダート
  distance?: number;    // 距離（メートル）
  horseCount?: number;  // 頭数
  // 条件フィールド
  gradeClass?: RaceGrade;     // クラス（新馬、未勝利、1勝、2勝、オープン、G3など）
  ageCondition?: string;      // 年齢条件（3歳、4歳以上、3歳以上など）
  sexCondition?: string;      // 性別条件（牝、牡牝など）
  weightType?: WeightType;    // 斤量条件（定量、別定、ハンデ）
  isSpecialEntry?: boolean;   // 指定レース
  isObstacle?: boolean;       // 障害レース
  purse?: number;             // 本賞金（万円）
  // JRA出馬表URL生成用
  kaisaiKai?: string;         // 回次（01, 02など）
  kaisaiNichime?: string;     // 日目（01, 02など）
  jraChecksum?: number | null; // JRA URL用チェックサム
}

export interface Horse {
  number: number;
  wakuBan: number;
  name: string;
  jockey: string;
  odds: number;
  popularity: number;
  color: string;
  textColor: string;
  weight?: number;      // 馬体重(kg)
  weightDiff?: number;  // 前走比増減
}

export interface RaceDetail extends Race {
  horses: Horse[];
}

// API → フロントエンド 変換関数
export function mapApiRaceToRace(apiRace: ApiRace): Race {
  const startTime = new Date(apiRace.start_time);
  const hours = startTime.getHours().toString().padStart(2, '0');
  const minutes = startTime.getMinutes().toString().padStart(2, '0');

  // 障害レースの場合は trackType を undefined にして表示用に正規化
  // （フロントエンドでは芝/ダートのバッジ表示がされるため、障害は別扱い）
  const trackType = apiRace.is_obstacle ? undefined : apiRace.track_type;

  return {
    id: apiRace.race_id,
    number: `${apiRace.race_number}R`,
    name: apiRace.race_name,
    time: `${hours}:${minutes}`,
    course: '',
    condition: apiRace.track_condition,
    venue: apiRace.venue,
    date: apiRace.start_time.split('T')[0],
    // 発走時刻・投票期限（ISO形式をそのまま保持）
    startTime: apiRace.start_time,
    bettingDeadline: apiRace.betting_deadline,
    trackType,
    distance: apiRace.distance,
    horseCount: apiRace.horse_count,
    // 条件フィールド（バリデーション付き）
    gradeClass: toRaceGrade(apiRace.grade_class),
    ageCondition: apiRace.age_condition,
    isObstacle: apiRace.is_obstacle,
    // JRA出馬表URL生成用
    kaisaiKai: apiRace.kaisai_kai,
    kaisaiNichime: apiRace.kaisai_nichime,
    jraChecksum: apiRace.jra_checksum,
  };
}

export function mapApiRaceDetailToRaceDetail(
  apiRace: ApiRace,
  runners: ApiRunner[]
): RaceDetail {
  const race = mapApiRaceToRace(apiRace);

  return {
    ...race,
    horses: runners.map((runner) => {
      const wakuColor = getWakuColor(runner.waku_ban);
      return {
        number: runner.horse_number,
        wakuBan: runner.waku_ban,
        name: runner.horse_name,
        jockey: runner.jockey_name,
        odds: parseFloat(runner.odds),
        popularity: runner.popularity,
        color: wakuColor.background,
        textColor: wakuColor.text,
        weight: runner.weight,
        weightDiff: runner.weight_diff,
      };
    }),
  };
}

// 券種
export type BetType = 'win' | 'place' | 'quinella' | 'quinella_place' | 'exacta' | 'trio' | 'trifecta';

export const BetTypeLabels: Record<BetType, string> = {
  win: '単勝',
  place: '複勝',
  quinella: '馬連',
  quinella_place: 'ワイド',
  exacta: '馬単',
  trio: '三連複',
  trifecta: '三連単',
};

export const BetTypeRequiredHorses: Record<BetType, number> = {
  win: 1,
  place: 1,
  quinella: 2,
  quinella_place: 2,
  exacta: 2,
  trio: 3,
  trifecta: 3,
};

// 券種が着順を考慮するかどうか
export const BetTypeOrdered: Record<BetType, boolean> = {
  win: false,
  place: false,
  quinella: false,
  quinella_place: false,
  exacta: true,
  trio: false,
  trifecta: true,
};

// 買い方
export type BetMethod =
  | 'normal'           // 通常
  | 'box'              // ボックス
  | 'nagashi'          // 軸1頭流し（順不同券種）
  | 'nagashi_1'        // 1着流し / 軸1頭1着流し
  | 'nagashi_2'        // 2着流し / 軸1頭2着流し
  | 'nagashi_3'        // 軸1頭3着流し（三連単）
  | 'nagashi_multi'    // マルチ（馬単）
  | 'nagashi_1_multi'  // 軸1頭マルチ（三連単）
  | 'nagashi_12'       // 軸2頭1-2着流し（三連単）
  | 'nagashi_13'       // 軸2頭1-3着流し（三連単）
  | 'nagashi_23'       // 軸2頭2-3着流し（三連単）
  | 'nagashi_2_multi'  // 軸2頭マルチ（三連単）
  | 'formation';       // フォーメーション

// 買い方ラベル（表示用）
export const BetMethodLabels: Record<BetMethod, string> = {
  normal: '',
  box: 'BOX',
  nagashi: '流し',
  nagashi_1: '1着流',
  nagashi_2: '2着流',
  nagashi_3: '3着流',
  nagashi_multi: 'マルチ',
  nagashi_1_multi: '1着流マルチ',
  nagashi_12: '軸2頭1-2着',
  nagashi_13: '軸2頭1-3着',
  nagashi_23: '軸2頭2-3着',
  nagashi_2_multi: '軸2頭マルチ',
  formation: 'フォメ',
};

export interface BetMethodConfig {
  id: BetMethod;
  label: string;
  description: string;
  badge?: string;       // 倍率バッジ（×2など）
}

// 複数列選択の状態
export interface ColumnSelections {
  col1: number[];  // 1着/軸/1頭目
  col2: number[];  // 2着/相手/2頭目
  col3: number[];  // 3着/3頭目
}

// チェックボックス列の設定
export interface ColumnConfig {
  id: keyof ColumnSelections;
  label: string;
  colorClass: string;
}

// 出走馬データ（AgentCore分析用）
export interface RunnerData {
  horse_number: number;
  horse_name: string;
  odds?: number;
  popularity?: number;
  running_style?: string;
  frame_number?: number;
}

// カート
export interface CartItem {
  id: string;
  raceId: string;
  raceName: string;
  raceVenue: string;
  raceNumber: string;
  betType: BetType;
  betMethod?: BetMethod;
  horseNumbers: number[];
  betDisplay?: string;  // 買い目の表示文字列（例: "1着軸:3 → 2着:1,5"）
  betCount?: number;    // 点数
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

// IPAT残高
export interface IpatBalance {
  betDedicatedBalance: number;
  settlePossibleBalance: number;
  betBalance: number;
  limitVoteAmount: number;
}

// 購入結果
export interface PurchaseResult {
  purchaseId: string;
  status: 'PENDING' | 'SUBMITTED' | 'COMPLETED' | 'FAILED';
  totalAmount: number;
  createdAt: string;
}

// 購入注文（履歴用）
export interface PurchaseOrder {
  purchaseId: string;
  cartId: string;
  status: 'PENDING' | 'SUBMITTED' | 'COMPLETED' | 'FAILED';
  totalAmount: number;
  betLineCount: number;
  errorMessage?: string;
  createdAt: string;
  updatedAt: string;
}

// IPAT設定状態
export interface IpatStatus {
  configured: boolean;
}

// IPAT認証情報入力
export interface IpatCredentialsInput {
  inetId: string;
  subscriberNumber: string;
  pin: string;
  parsNumber: string;
}

// AI分析提案
export interface ProposedBet {
  bet_type: BetType;
  horse_numbers: number[];
  amount?: number;
  bet_count: number;
  bet_display: string;
  confidence: 'high' | 'medium' | 'low';
  expected_value: number;
  composite_odds: number;
  reasoning: string;
}

export interface RaceSummary {
  race_name: string;
  difficulty_stars: number;
  predicted_pace: string;
  ai_consensus_level: string;
  skip_score: number;
  skip_recommendation: string;
}

export interface BetProposalResponse {
  race_id: string;
  race_summary: RaceSummary;
  proposed_bets: ProposedBet[];
  total_amount: number;
  budget_remaining: number;
  analysis_comment: string;
  disclaimer: string;
}

// 賭け記録
export interface BettingRecord {
  recordId: string;
  userId: string;
  raceId: string;
  raceName: string;
  raceDate: string;
  venue: string;
  betType: BetType;
  horseNumbers: number[];
  amount: number;
  payout: number;
  profit: number;
  status: 'PENDING' | 'SETTLED' | 'CANCELLED';
  createdAt: string;
  settledAt: string | null;
}

// 損益サマリー
export interface BettingSummary {
  totalInvestment: number;
  totalPayout: number;
  netProfit: number;
  winRate: number;
  recordCount: number;
  roi: number;
}

// フィルタ
export interface BettingRecordFilter {
  dateFrom?: string;
  dateTo?: string;
  venue?: string;
  betType?: BetType;
}

// 負け額限度額
export interface LossLimit {
  lossLimit: number | null;
  totalLossThisMonth: number;
  remainingLossLimit: number | null;
  pendingChange: PendingLossLimitChange | null;
}

export interface PendingLossLimitChange {
  changeId: string;
  changeType: 'increase' | 'decrease';
  status: 'pending' | 'approved' | 'rejected';
  effectiveAt: string;
  requestedAt: string;
  currentLimit: number;
  requestedLimit: number;
}

export interface LossLimitCheckResult {
  canPurchase: boolean;
  remainingAmount: number | null;
  warningLevel: 'none' | 'caution' | 'warning';
  message: string;
}

// エージェント育成
export type AgentStyleId = 'solid' | 'longshot' | 'data' | 'pace';

export interface AgentStats {
  data_analysis: number;
  pace_reading: number;
  risk_management: number;
  intuition: number;
}

export interface AgentPerformance {
  total_bets: number;
  wins: number;
  total_invested: number;
  total_return: number;
}

export interface Agent {
  agent_id: string;
  user_id: string;
  name: string;
  base_style: AgentStyleId;
  stats: AgentStats;
  performance: AgentPerformance;
  level: number;
  win_rate: number;
  roi: number;
  profit: number;
  created_at: string;
  updated_at: string;
}

export interface AgentData {
  name: string;
  base_style: AgentStyleId;
  stats: AgentStats;
  performance: AgentPerformance;
  level: number;
}

export interface AgentReview {
  review_id: string;
  race_id: string;
  race_date: string;
  race_name: string;
  total_invested: number;
  total_return: number;
  profit: number;
  has_win: boolean;
  review_text: string;
  learnings: string[];
  stats_change: Record<string, number>;
  created_at: string;
}

// アプリ状態
export type PageType = 'races' | 'dashboard' | 'history' | 'settings' | 'cart';
