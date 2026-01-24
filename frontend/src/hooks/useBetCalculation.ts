import { useMemo } from 'react';
import type { BetType, BetMethod, ColumnSelections } from '../types';
import { BetTypeRequiredHorses, BetTypeOrdered } from '../types';

function combination(n: number, r: number): number {
  if (r > n) return 0;
  let result = 1;
  for (let i = 0; i < r; i++) {
    result = result * (n - i) / (i + 1);
  }
  return Math.round(result);
}

function getAxisCount(method: BetMethod, betType: BetType): number {
  const required = BetTypeRequiredHorses[betType];
  if (['nagashi_12', 'nagashi_13', 'nagashi_23', 'nagashi_2_multi'].includes(method)) {
    return 2;
  }
  // 三連複の軸2頭流し
  if (method === 'nagashi_2' && required === 3 && !BetTypeOrdered[betType]) {
    return 2;
  }
  return 1;
}

export function calculateBetCount(
  betType: BetType,
  method: BetMethod,
  selections: ColumnSelections
): number {
  const required = BetTypeRequiredHorses[betType];
  const ordered = BetTypeOrdered[betType];
  const isNagashi = method.startsWith('nagashi');
  const axisCount = getAxisCount(method, betType);

  if (method === 'normal') {
    return selections.col1.length === required ? 1 : 0;
  }

  if (method === 'box') {
    const n = selections.col1.length;
    if (n < required) return 0;
    if (required === 2) {
      return ordered ? n * (n - 1) : combination(n, 2);
    } else if (required === 3) {
      return ordered ? n * (n - 1) * (n - 2) : combination(n, 3);
    }
  }

  if (isNagashi) {
    // 軸2頭流し（3列: col1とcol3が軸、col2が相手）
    const isNagashi2Axis3Col = ['nagashi_12', 'nagashi_13', 'nagashi_23'].includes(method);

    if (isNagashi2Axis3Col) {
      // 軸2頭流し: col1とcol3に各1頭、col2に相手
      if (selections.col1.length !== 1 || selections.col3.length !== 1 || selections.col2.length === 0) {
        return 0;
      }
      return selections.col2.length;
    }

    // 通常の流し（2列）
    const axisHorses = selections.col1;
    const partnerHorses = selections.col2;
    if (axisHorses.length !== axisCount || partnerHorses.length === 0) return 0;

    const partners = partnerHorses.length;
    let baseCount = 0;

    if (required === 2) {
      baseCount = partners;
      if (method === 'nagashi_multi') return baseCount * 2;
    } else if (required === 3) {
      if (axisCount === 1) {
        // 三連複（順不同）は組み合わせ、三連単（順番あり）は順列
        baseCount = ordered ? partners * (partners - 1) : combination(partners, 2);
        if (method === 'nagashi_1_multi') return baseCount * 3;
      } else {
        baseCount = partners;
        if (method === 'nagashi_2_multi') return baseCount * 6;
      }
    }
    return baseCount;
  }

  if (method === 'formation') {
    const col1 = selections.col1.length;
    const col2 = selections.col2.length;
    const col3 = selections.col3.length;

    if (required === 2) {
      if (col1 === 0 || col2 === 0) return 0;
      if (ordered) {
        // 馬単フォーメーション（順序あり）
        let count = 0;
        selections.col1.forEach(h1 => {
          selections.col2.forEach(h2 => {
            if (h1 !== h2) count++;
          });
        });
        return count;
      } else {
        // 馬連・ワイドフォーメーション（順不同）
        // 各列から1頭ずつ選び、重複除外したユニークな組み合わせ数
        const pairSet = new Set<string>();
        selections.col1.forEach(h1 => {
          selections.col2.forEach(h2 => {
            if (h1 === h2) return;
            const sorted = [h1, h2].sort((a, b) => a - b);
            pairSet.add(`${sorted[0]}-${sorted[1]}`);
          });
        });
        return pairSet.size;
      }
    } else if (required === 3) {
      if (col1 === 0 || col2 === 0 || col3 === 0) return 0;
      if (ordered) {
        // 三連単フォーメーション（順序あり）
        let count = 0;
        selections.col1.forEach(h1 => {
          selections.col2.forEach(h2 => {
            if (h1 === h2) return;
            selections.col3.forEach(h3 => {
              if (h1 !== h3 && h2 !== h3) count++;
            });
          });
        });
        return count;
      } else {
        // 三連複フォーメーション（順不同）
        // 各列から1頭ずつ選び、重複除外したユニークな組み合わせ数
        const tripleSet = new Set<string>();
        selections.col1.forEach(h1 => {
          selections.col2.forEach(h2 => {
            if (h1 === h2) return;
            selections.col3.forEach(h3 => {
              if (h1 === h3 || h2 === h3) return;
              const sorted = [h1, h2, h3].sort((a, b) => a - b);
              tripleSet.add(`${sorted[0]}-${sorted[1]}-${sorted[2]}`);
            });
          });
        });
        return tripleSet.size;
      }
    }
  }

  return 0;
}

interface BetBreakdown {
  formula: string;
  detail: string;
}

export function getBetBreakdown(
  betType: BetType,
  method: BetMethod,
  selections: ColumnSelections,
  betCount: number
): BetBreakdown | null {
  if (betCount === 0) return null;

  const required = BetTypeRequiredHorses[betType];
  const ordered = BetTypeOrdered[betType];
  const isNagashi = method.startsWith('nagashi');
  const axisCount = getAxisCount(method, betType);

  if (method === 'normal') {
    return {
      formula: '1点',
      detail: `${selections.col1.join('→')} の1通り`
    };
  }

  if (method === 'box') {
    const n = selections.col1.length;
    if (required === 2) {
      if (ordered) {
        return {
          formula: `${n} × ${n-1} = ${betCount}点`,
          detail: `${n}頭から2頭を順番に選ぶ組み合わせ`
        };
      } else {
        return {
          formula: `${n}C2 = ${betCount}点`,
          detail: `${n}頭から2頭を選ぶ組み合わせ`
        };
      }
    } else if (required === 3) {
      if (ordered) {
        return {
          formula: `${n} × ${n-1} × ${n-2} = ${betCount}点`,
          detail: `${n}頭から3頭を順番に選ぶ組み合わせ`
        };
      } else {
        return {
          formula: `${n}C3 = ${betCount}点`,
          detail: `${n}頭から3頭を選ぶ組み合わせ`
        };
      }
    }
  }

  if (isNagashi) {
    // 軸2頭流し（3列）
    const isNagashi2Axis3Col = ['nagashi_12', 'nagashi_13', 'nagashi_23'].includes(method);
    if (isNagashi2Axis3Col) {
      const partners = selections.col2.length;
      return {
        formula: `${partners}点`,
        detail: `軸2頭固定 → 相手${partners}頭`
      };
    }

    const partners = selections.col2.length;
    const multiplier = method.includes('multi') ? (required === 2 ? 2 : (axisCount === 1 ? 3 : 6)) : 1;

    if (required === 2) {
      if (multiplier > 1) {
        return {
          formula: `${partners} × ${multiplier} = ${betCount}点`,
          detail: `相手${partners}頭 × マルチ${multiplier}倍`
        };
      }
      return {
        formula: `${partners}点`,
        detail: `軸1頭 → 相手${partners}頭`
      };
    } else if (required === 3) {
      if (axisCount === 1) {
        if (multiplier > 1) {
          return {
            formula: `${partners} × ${partners-1} × ${multiplier} = ${betCount}点`,
            detail: `相手${partners}頭の順列 × マルチ${multiplier}倍`
          };
        }
        return {
          formula: `${partners} × ${partners-1} = ${betCount}点`,
          detail: `軸1頭固定、相手${partners}頭の順列`
        };
      } else {
        if (multiplier > 1) {
          return {
            formula: `${partners} × ${multiplier} = ${betCount}点`,
            detail: `相手${partners}頭 × マルチ${multiplier}倍`
          };
        }
        return {
          formula: `${partners}点`,
          detail: `軸2頭固定 → 相手${partners}頭`
        };
      }
    }
  }

  if (method === 'formation') {
    const col1 = selections.col1.length;
    const col2 = selections.col2.length;
    const col3 = selections.col3.length;

    if (required === 2) {
      return {
        formula: `${col1} × ${col2} → ${betCount}点`,
        detail: `重複除外後の実組み合わせ数`
      };
    } else if (required === 3) {
      return {
        formula: `${col1} × ${col2} × ${col3} → ${betCount}点`,
        detail: `重複除外後の実組み合わせ数`
      };
    }
  }

  return { formula: `${betCount}点`, detail: '' };
}

export function useBetCalculation(
  betType: BetType,
  method: BetMethod,
  selections: ColumnSelections
) {
  const betCount = useMemo(
    () => calculateBetCount(betType, method, selections),
    [betType, method, selections]
  );

  const breakdown = useMemo(
    () => getBetBreakdown(betType, method, selections, betCount),
    [betType, method, selections, betCount]
  );

  return { betCount, breakdown };
}
