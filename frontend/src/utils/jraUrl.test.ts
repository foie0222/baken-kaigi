import { describe, it, expect } from 'vitest';
import { buildJraShutsubaUrl } from './jraUrl';

describe('buildJraShutsubaUrl', () => {
  describe('正常ケース', () => {
    it('全てのフィールドが揃っている場合、正しいURLを生成する', () => {
      const race = {
        id: '20260124_06_01',
        kaisaiKai: '01',
        kaisaiNichime: '08',
        jraChecksum: 243, // 0xF3
        number: '1R',
        venue: '06',
      };

      const url = buildJraShutsubaUrl(race);

      expect(url).toBe(
        'https://www.jra.go.jp/JRADB/accessD.html?CNAME=pw01dde0106202601080120260124/F3'
      );
    });

    it('レース番号が2桁の場合も正しく処理する', () => {
      const race = {
        id: '20260124_06_11',
        kaisaiKai: '02',
        kaisaiNichime: '05',
        jraChecksum: 15, // 0x0F
        number: '11R',
        venue: '06',
      };

      const url = buildJraShutsubaUrl(race);

      expect(url).toBe(
        'https://www.jra.go.jp/JRADB/accessD.html?CNAME=pw01dde0106202602051120260124/0F'
      );
    });

    it('チェックサムが0の場合も正しく処理する', () => {
      const race = {
        id: '20260124_05_03',
        kaisaiKai: '01',
        kaisaiNichime: '01',
        jraChecksum: 0,
        number: '3R',
        venue: '05',
      };

      const url = buildJraShutsubaUrl(race);

      expect(url).toBe(
        'https://www.jra.go.jp/JRADB/accessD.html?CNAME=pw01dde0105202601010320260124/00'
      );
    });

    it('venueコードが1桁の場合、2桁にパディングされる', () => {
      const race = {
        id: '20260124_05_01',
        kaisaiKai: '3',
        kaisaiNichime: '2',
        jraChecksum: 255, // 0xFF
        number: '1R',
        venue: '5',
      };

      const url = buildJraShutsubaUrl(race);

      expect(url).toBe(
        'https://www.jra.go.jp/JRADB/accessD.html?CNAME=pw01dde0105202603020120260124/FF'
      );
    });
  });

  describe('nullを返すケース', () => {
    it('kaisaiKaiがundefinedの場合、nullを返す', () => {
      const race = {
        id: '20260124_06_01',
        kaisaiKai: undefined,
        kaisaiNichime: '08',
        jraChecksum: 243,
        number: '1R',
        venue: '06',
      };

      expect(buildJraShutsubaUrl(race)).toBeNull();
    });

    it('kaisaiKaiが空文字の場合、nullを返す', () => {
      const race = {
        id: '20260124_06_01',
        kaisaiKai: '',
        kaisaiNichime: '08',
        jraChecksum: 243,
        number: '1R',
        venue: '06',
      };

      expect(buildJraShutsubaUrl(race)).toBeNull();
    });

    it('kaisaiNichimeがundefinedの場合、nullを返す', () => {
      const race = {
        id: '20260124_06_01',
        kaisaiKai: '01',
        kaisaiNichime: undefined,
        jraChecksum: 243,
        number: '1R',
        venue: '06',
      };

      expect(buildJraShutsubaUrl(race)).toBeNull();
    });

    it('kaisaiNichimeが空文字の場合、nullを返す', () => {
      const race = {
        id: '20260124_06_01',
        kaisaiKai: '01',
        kaisaiNichime: '',
        jraChecksum: 243,
        number: '1R',
        venue: '06',
      };

      expect(buildJraShutsubaUrl(race)).toBeNull();
    });

    it('jraChecksumがnullの場合、nullを返す', () => {
      const race = {
        id: '20260124_06_01',
        kaisaiKai: '01',
        kaisaiNichime: '08',
        jraChecksum: null,
        number: '1R',
        venue: '06',
      };

      expect(buildJraShutsubaUrl(race)).toBeNull();
    });

    it('jraChecksumがundefinedの場合、nullを返す', () => {
      const race = {
        id: '20260124_06_01',
        kaisaiKai: '01',
        kaisaiNichime: '08',
        jraChecksum: undefined,
        number: '1R',
        venue: '06',
      };

      expect(buildJraShutsubaUrl(race)).toBeNull();
    });

    it('race.idが不正なフォーマットの場合、nullを返す', () => {
      const race = {
        id: 'invalid_id',
        kaisaiKai: '01',
        kaisaiNichime: '08',
        jraChecksum: 243,
        number: '1R',
        venue: '06',
      };

      expect(buildJraShutsubaUrl(race)).toBeNull();
    });

    it('race.idが空文字の場合、nullを返す', () => {
      const race = {
        id: '',
        kaisaiKai: '01',
        kaisaiNichime: '08',
        jraChecksum: 243,
        number: '1R',
        venue: '06',
      };

      expect(buildJraShutsubaUrl(race)).toBeNull();
    });

    it('race.idに日付が含まれないフォーマットの場合、nullを返す', () => {
      const race = {
        id: 'race_06_01',
        kaisaiKai: '01',
        kaisaiNichime: '08',
        jraChecksum: 243,
        number: '1R',
        venue: '06',
      };

      expect(buildJraShutsubaUrl(race)).toBeNull();
    });
  });
});
