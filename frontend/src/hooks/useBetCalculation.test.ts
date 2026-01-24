import { describe, it, expect } from 'vitest';
import { calculateBetCount } from './useBetCalculation';
import type { ColumnSelections } from '../types';

const emptySelections: ColumnSelections = { col1: [], col2: [], col3: [] };

describe('calculateBetCount', () => {
  describe('通常モード', () => {
    it('単勝: 1頭選択で1点', () => {
      const selections: ColumnSelections = { col1: [1], col2: [], col3: [] };
      expect(calculateBetCount('win', 'normal', selections)).toBe(1);
    });

    it('単勝: 0頭選択で0点', () => {
      expect(calculateBetCount('win', 'normal', emptySelections)).toBe(0);
    });

    it('馬連: 2頭選択で1点', () => {
      const selections: ColumnSelections = { col1: [1, 2], col2: [], col3: [] };
      expect(calculateBetCount('quinella', 'normal', selections)).toBe(1);
    });

    it('三連単: 3頭選択で1点', () => {
      const selections: ColumnSelections = { col1: [1, 2, 3], col2: [], col3: [] };
      expect(calculateBetCount('trifecta', 'normal', selections)).toBe(1);
    });
  });

  describe('ボックス', () => {
    it('馬連ボックス: 3頭で3点', () => {
      const selections: ColumnSelections = { col1: [1, 2, 3], col2: [], col3: [] };
      expect(calculateBetCount('quinella', 'box', selections)).toBe(3); // 3C2 = 3
    });

    it('馬単ボックス: 3頭で6点', () => {
      const selections: ColumnSelections = { col1: [1, 2, 3], col2: [], col3: [] };
      expect(calculateBetCount('exacta', 'box', selections)).toBe(6); // 3 * 2 = 6
    });

    it('三連複ボックス: 4頭で4点', () => {
      const selections: ColumnSelections = { col1: [1, 2, 3, 4], col2: [], col3: [] };
      expect(calculateBetCount('trio', 'box', selections)).toBe(4); // 4C3 = 4
    });

    it('三連単ボックス: 4頭で24点', () => {
      const selections: ColumnSelections = { col1: [1, 2, 3, 4], col2: [], col3: [] };
      expect(calculateBetCount('trifecta', 'box', selections)).toBe(24); // 4 * 3 * 2 = 24
    });
  });

  describe('流し（2列）', () => {
    it('馬連軸1頭流し: 軸1頭、相手3頭で3点', () => {
      const selections: ColumnSelections = { col1: [1], col2: [2, 3, 4], col3: [] };
      expect(calculateBetCount('quinella', 'nagashi', selections)).toBe(3);
    });

    it('馬単1着流し: 軸1頭、相手3頭で3点', () => {
      const selections: ColumnSelections = { col1: [1], col2: [2, 3, 4], col3: [] };
      expect(calculateBetCount('exacta', 'nagashi_1', selections)).toBe(3);
    });

    it('馬単マルチ: 軸1頭、相手3頭で6点', () => {
      const selections: ColumnSelections = { col1: [1], col2: [2, 3, 4], col3: [] };
      expect(calculateBetCount('exacta', 'nagashi_multi', selections)).toBe(6); // 3 * 2
    });

    it('三連単1着流し: 軸1頭、相手3頭で6点', () => {
      const selections: ColumnSelections = { col1: [1], col2: [2, 3, 4], col3: [] };
      expect(calculateBetCount('trifecta', 'nagashi_1', selections)).toBe(6); // 3 * 2 = 6
    });

    it('三連単1着流しマルチ: 軸1頭、相手3頭で18点', () => {
      const selections: ColumnSelections = { col1: [1], col2: [2, 3, 4], col3: [] };
      expect(calculateBetCount('trifecta', 'nagashi_1_multi', selections)).toBe(18); // 6 * 3
    });

    it('流し: 軸がないと0点', () => {
      const selections: ColumnSelections = { col1: [], col2: [2, 3, 4], col3: [] };
      expect(calculateBetCount('quinella', 'nagashi', selections)).toBe(0);
    });

    it('流し: 相手がないと0点', () => {
      const selections: ColumnSelections = { col1: [1], col2: [], col3: [] };
      expect(calculateBetCount('quinella', 'nagashi', selections)).toBe(0);
    });
  });

  describe('軸2頭流し（3列）', () => {
    it('三連単1-2着流し: 1着軸1頭、2着軸1頭、3着3頭で3点', () => {
      const selections: ColumnSelections = { col1: [1], col2: [3, 4, 5], col3: [2] };
      expect(calculateBetCount('trifecta', 'nagashi_12', selections)).toBe(3);
    });

    it('三連単1-3着流し: 1着軸1頭、2着3頭、3着軸1頭で3点', () => {
      const selections: ColumnSelections = { col1: [1], col2: [3, 4, 5], col3: [2] };
      expect(calculateBetCount('trifecta', 'nagashi_13', selections)).toBe(3);
    });

    it('三連単2-3着流し: 1着3頭、2着軸1頭、3着軸1頭で3点', () => {
      const selections: ColumnSelections = { col1: [2], col2: [3, 4, 5], col3: [6] };
      expect(calculateBetCount('trifecta', 'nagashi_23', selections)).toBe(3);
    });

    it('軸2頭流し: col1が空だと0点', () => {
      const selections: ColumnSelections = { col1: [], col2: [3, 4, 5], col3: [2] };
      expect(calculateBetCount('trifecta', 'nagashi_12', selections)).toBe(0);
    });

    it('軸2頭流し: col3が空だと0点', () => {
      const selections: ColumnSelections = { col1: [1], col2: [3, 4, 5], col3: [] };
      expect(calculateBetCount('trifecta', 'nagashi_12', selections)).toBe(0);
    });

    it('軸2頭流し: 相手（col2）が空だと0点', () => {
      const selections: ColumnSelections = { col1: [1], col2: [], col3: [2] };
      expect(calculateBetCount('trifecta', 'nagashi_12', selections)).toBe(0);
    });
  });

  describe('フォーメーション', () => {
    it('馬連フォーメーション: 2×2で重複除外', () => {
      // 1,2 × 2,3 → (1-2), (1-3), (2-3) = 3点
      const selections: ColumnSelections = { col1: [1, 2], col2: [2, 3], col3: [] };
      expect(calculateBetCount('quinella', 'formation', selections)).toBe(3);
    });

    it('馬単フォーメーション: 2×2で重複除外', () => {
      // 1,2 → 2,3 → (1→2), (1→3), (2→3) = 3点
      const selections: ColumnSelections = { col1: [1, 2], col2: [2, 3], col3: [] };
      expect(calculateBetCount('exacta', 'formation', selections)).toBe(3);
    });

    it('三連単フォーメーション: 2×2×2で重複除外', () => {
      // 1,2 → 2,3 → 3,4 → 重複除外後の点数
      const selections: ColumnSelections = { col1: [1, 2], col2: [2, 3], col3: [3, 4] };
      // 1→2→3, 1→2→4, 1→3→4, 2→3→4 = 4点
      expect(calculateBetCount('trifecta', 'formation', selections)).toBe(4);
    });

    it('フォーメーション: 列が空だと0点', () => {
      const selections: ColumnSelections = { col1: [1, 2], col2: [], col3: [] };
      expect(calculateBetCount('quinella', 'formation', selections)).toBe(0);
    });
  });
});
