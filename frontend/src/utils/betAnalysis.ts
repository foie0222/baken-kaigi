export type TrigaramiRisk = 'low' | 'medium' | 'high';

/**
 * トリガミリスクを計算する
 * @param odds オッズ
 * @param betCount 買い目の点数
 * @returns リスクレベル
 */
export function calculateTrigaramiRisk(odds: number, betCount: number): TrigaramiRisk {
  if (odds > betCount * 1.5) {
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
      return { label: '安全', color: '#4caf50' };
    case 'medium':
      return { label: '注意', color: '#ff9800' };
    case 'high':
      return { label: 'トリガミ危険', color: '#f44336' };
  }
}
