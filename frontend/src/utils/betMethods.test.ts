import { describe, it, expect } from 'vitest';
import { getAvailableBetMethods, getBetMethodLabel } from './betMethods';

describe('getAvailableBetMethods', () => {
  describe('単勝・複勝（1頭）', () => {
    it('単勝は通常のみ', () => {
      const methods = getAvailableBetMethods('win');
      expect(methods).toHaveLength(1);
      expect(methods[0].id).toBe('normal');
    });

    it('複勝は通常のみ', () => {
      const methods = getAvailableBetMethods('place');
      expect(methods).toHaveLength(1);
      expect(methods[0].id).toBe('normal');
    });
  });

  describe('馬連・ワイド（2頭・順不同）', () => {
    it('馬連の買い方一覧', () => {
      const methods = getAvailableBetMethods('quinella');
      const ids = methods.map(m => m.id);
      expect(ids).toContain('normal');
      expect(ids).toContain('box');
      expect(ids).toContain('nagashi');
      expect(ids).toContain('formation');
      // 順番ありの流しは含まない
      expect(ids).not.toContain('nagashi_1');
      expect(ids).not.toContain('nagashi_2');
    });

    it('ワイドの買い方一覧', () => {
      const methods = getAvailableBetMethods('quinella_place');
      const ids = methods.map(m => m.id);
      expect(ids).toContain('normal');
      expect(ids).toContain('box');
      expect(ids).toContain('nagashi');
      expect(ids).toContain('formation');
    });
  });

  describe('馬単（2頭・順番あり）', () => {
    it('馬単の買い方一覧', () => {
      const methods = getAvailableBetMethods('exacta');
      const ids = methods.map(m => m.id);
      expect(ids).toContain('normal');
      expect(ids).toContain('box');
      expect(ids).toContain('nagashi_1');  // 1着流し
      expect(ids).toContain('nagashi_2');  // 2着流し
      expect(ids).toContain('nagashi_multi');  // マルチ
      expect(ids).toContain('formation');
      // 順不同の流しは含まない
      expect(ids).not.toContain('nagashi');
    });

    it('馬単のマルチは×2バッジ', () => {
      const methods = getAvailableBetMethods('exacta');
      const multi = methods.find(m => m.id === 'nagashi_multi');
      expect(multi?.badge).toBe('×2');
    });
  });

  describe('三連複（3頭・順不同）', () => {
    it('三連複の買い方一覧', () => {
      const methods = getAvailableBetMethods('trio');
      const ids = methods.map(m => m.id);
      expect(ids).toContain('normal');
      expect(ids).toContain('box');
      expect(ids).toContain('nagashi');    // 軸1頭流し
      expect(ids).toContain('nagashi_2');  // 軸2頭流し
      expect(ids).toContain('formation');
      // 順番ありの流しは含まない
      expect(ids).not.toContain('nagashi_1');
      expect(ids).not.toContain('nagashi_12');
    });
  });

  describe('三連単（3頭・順番あり）', () => {
    it('三連単の買い方一覧', () => {
      const methods = getAvailableBetMethods('trifecta');
      const ids = methods.map(m => m.id);
      expect(ids).toContain('normal');
      expect(ids).toContain('box');
      expect(ids).toContain('nagashi_1');     // 軸1頭 1着流し
      expect(ids).toContain('nagashi_2');     // 軸1頭 2着流し
      expect(ids).toContain('nagashi_3');     // 軸1頭 3着流し
      expect(ids).toContain('nagashi_1_multi'); // 軸1頭 マルチ
      expect(ids).toContain('nagashi_12');    // 軸2頭 1-2着流し
      expect(ids).toContain('nagashi_13');    // 軸2頭 1-3着流し
      expect(ids).toContain('nagashi_23');    // 軸2頭 2-3着流し
      expect(ids).toContain('nagashi_2_multi'); // 軸2頭 マルチ
      expect(ids).toContain('formation');
    });

    it('三連単の軸1頭マルチは×3バッジ', () => {
      const methods = getAvailableBetMethods('trifecta');
      const multi = methods.find(m => m.id === 'nagashi_1_multi');
      expect(multi?.badge).toBe('×3');
    });

    it('三連単の軸2頭マルチは×6バッジ', () => {
      const methods = getAvailableBetMethods('trifecta');
      const multi = methods.find(m => m.id === 'nagashi_2_multi');
      expect(multi?.badge).toBe('×6');
    });
  });
});

describe('getBetMethodLabel', () => {
  it('通常のラベルを取得', () => {
    expect(getBetMethodLabel('normal', 'win')).toBe('通常');
  });

  it('ボックスのラベルを取得', () => {
    expect(getBetMethodLabel('box', 'quinella')).toBe('ボックス');
  });

  it('馬単1着流しのラベルを取得', () => {
    expect(getBetMethodLabel('nagashi_1', 'exacta')).toBe('1着流し');
  });

  it('三連単軸2頭1-3着流しのラベルを取得', () => {
    expect(getBetMethodLabel('nagashi_13', 'trifecta')).toBe('軸2頭 1-3着流し');
  });

  it('存在しない買い方は通常を返す', () => {
    expect(getBetMethodLabel('nagashi_1', 'win')).toBe('通常');
  });
});
