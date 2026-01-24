/**
 * 賭け金関連の定数
 */

/** 最低掛け金（円）- JRA馬券の最低購入単位 */
export const MIN_BET_AMOUNT = 100;

/** 最大掛け金（円）- 一点あたりの上限 */
export const MAX_BET_AMOUNT = 100_000;

/**
 * トリガミリスク判定関連の定数
 */

/**
 * トリガミ安全閾値
 * オッズが点数の1.5倍を超えていれば、的中時に50%以上の利益が見込める
 * 計算例: 3点買い × 1.5 = 4.5 → オッズ4.5倍以上なら安全
 */
export const TRIGARAMI_SAFE_THRESHOLD = 1.5;

/**
 * リスクレベルに対応する色
 * - low: 安全（緑）
 * - medium: 注意（オレンジ）
 * - high: トリガミ危険（赤）
 */
export const RISK_COLORS = {
  low: '#4caf50',
  medium: '#ff9800',
  high: '#f44336',
} as const;

/**
 * モックオッズ生成用の定数
 * TODO: 将来的にJRA-VAN APIからリアルオッズを取得予定
 * Issue: #XX で対応予定
 */
export const MOCK_ODDS = {
  /** オッズの範囲調整用モジュロ値 */
  MODULO: 250,
  /** オッズの範囲調整用除算値 */
  DIVISOR: 10,
  /** オッズの最低値（倍） */
  MIN_ODDS: 5,
} as const;
