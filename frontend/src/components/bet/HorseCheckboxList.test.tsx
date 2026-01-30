import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HorseCheckboxList } from './HorseCheckboxList';
import type { Horse, ColumnSelections } from '../../types';

// テスト用の馬データを作成
function createHorse(overrides: Partial<Horse> = {}): Horse {
  return {
    number: 1,
    wakuBan: 1,
    name: 'テスト馬',
    jockey: 'テスト騎手',
    odds: 3.5,
    popularity: 1,
    color: '#FFFFFF',
    textColor: '#000000',
    ...overrides,
  };
}

describe('HorseCheckboxList', () => {
  const defaultProps = {
    betType: 'win' as const,
    method: 'normal' as const,
    selections: { col1: [], col2: [], col3: [] } as ColumnSelections,
    onSelectionChange: vi.fn(),
  };

  describe('オッズ表示', () => {
    it('オッズが正常な値の場合、オッズを表示する', () => {
      const horses = [createHorse({ number: 1, odds: 3.5 })];
      render(<HorseCheckboxList {...defaultProps} horses={horses} />);

      expect(screen.getByText('3.5')).toBeInTheDocument();
    });

    it('オッズが0の場合、「-」を表示する', () => {
      const horses = [createHorse({ number: 1, odds: 0 })];
      render(<HorseCheckboxList {...defaultProps} horses={horses} />);

      // オッズ列に「-」が表示されることを確認
      const oddsElements = screen.getAllByText('-');
      expect(oddsElements.length).toBeGreaterThan(0);
    });

    it('オッズがNaNの場合、「-」を表示する', () => {
      const horses = [createHorse({ number: 1, odds: NaN })];
      render(<HorseCheckboxList {...defaultProps} horses={horses} />);

      const oddsElements = screen.getAllByText('-');
      expect(oddsElements.length).toBeGreaterThan(0);
    });

    it('オッズがnull/undefinedに近い値の場合、「-」を表示する', () => {
      // TypeScript的にはnumberだが、APIから返ってくる可能性を考慮
      const horses = [createHorse({ number: 1, odds: undefined as unknown as number })];
      render(<HorseCheckboxList {...defaultProps} horses={horses} />);

      const oddsElements = screen.getAllByText('-');
      expect(oddsElements.length).toBeGreaterThan(0);
    });
  });
});
