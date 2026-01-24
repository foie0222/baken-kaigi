import { TRIGARAMI_SAFE_THRESHOLD, RISK_COLORS } from '../constants/betting';

export type TrigaramiRisk = 'low' | 'medium' | 'high';

/**
 * トリガミリスクを計算する
 *
 * トリガミとは、的中しても賭け金を回収できない状態のこと。
 * 例: 10点買いでオッズ8倍の場合、的中しても 8 × 100 = 800円 で 1000円の賭け金を回収できない
 *
 * @param odds オッズ（倍率）
 * @param betCount 買い目の点数
 * @returns リスクレベル
 *   - low: オッズ > 点数 × 1.5 → 的中時に50%以上の利益
 *   - medium: オッズ > 点数 → 的中時にプラスだが利益は薄い
 *   - high: オッズ ≤ 点数 → トリガミ（的中してもマイナス）
 */
export function calculateTrigaramiRisk(odds: number, betCount: number): TrigaramiRisk {
  if (odds > betCount * TRIGARAMI_SAFE_THRESHOLD) {
    return 'low';
  }
  if (odds > betCount) {
    return 'medium';
  }
  return 'high';
}

interface RiskLabel {
  label: string;
  color: string;
}

/**
 * リスクレベルに対応するラベルと色を取得する
 * @param risk リスクレベル
 * @returns ラベルと色
 */
export function getTrigaramiRiskLabel(risk: TrigaramiRisk): RiskLabel {
  switch (risk) {
    case 'low':
      return { label: '安全', color: RISK_COLORS.low };
    case 'medium':
      return { label: '注意', color: RISK_COLORS.medium };
    case 'high':
      return { label: 'トリガミ危険', color: RISK_COLORS.high };
  }
}
