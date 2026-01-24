import { describe, it, expect } from 'vitest';
import { calculateTrigaramiRisk, getTrigaramiRiskLabel } from './betAnalysis';

describe('betAnalysis', () => {
  describe('calculateTrigaramiRisk', () => {
    it('オッズ > 点数 × 1.5 のとき low を返す', () => {
      // 3点買いでオッズ10倍 → 10 > 3 × 1.5 (= 4.5) → low
      expect(calculateTrigaramiRisk(10, 3)).toBe('low');
    });

    it('オッズ > 点数 かつ オッズ ≤ 点数 × 1.5 のとき medium を返す', () => {
      // 5点買いでオッズ6倍 → 6 > 5 かつ 6 ≤ 7.5 → medium
      expect(calculateTrigaramiRisk(6, 5)).toBe('medium');
    });

    it('オッズ ≤ 点数 のとき high を返す', () => {
      // 10点買いでオッズ8倍 → 8 ≤ 10 → high
      expect(calculateTrigaramiRisk(8, 10)).toBe('high');
    });

    it('オッズと点数が同じとき high を返す', () => {
      expect(calculateTrigaramiRisk(5, 5)).toBe('high');
    });

    it('1点買いでオッズ1倍のとき high を返す', () => {
      expect(calculateTrigaramiRisk(1, 1)).toBe('high');
    });

    it('1点買いでオッズ1.4倍のとき medium を返す', () => {
      // 1.4 > 1 かつ 1.4 ≤ 1.5 → medium
      expect(calculateTrigaramiRisk(1.4, 1)).toBe('medium');
    });

    it('1点買いでオッズ3倍のとき low を返す', () => {
      // 3 > 1 × 1.5 (= 1.5) → low
      expect(calculateTrigaramiRisk(3, 1)).toBe('low');
    });
  });

  describe('getTrigaramiRiskLabel', () => {
    it('low のラベルを返す', () => {
      expect(getTrigaramiRiskLabel('low')).toEqual({
        label: '安全',
        color: '#4caf50',
      });
    });

    it('medium のラベルを返す', () => {
      expect(getTrigaramiRiskLabel('medium')).toEqual({
        label: '注意',
        color: '#ff9800',
      });
    });

    it('high のラベルを返す', () => {
      expect(getTrigaramiRiskLabel('high')).toEqual({
        label: 'トリガミ危険',
        color: '#f44336',
      });
    });
  });
});
