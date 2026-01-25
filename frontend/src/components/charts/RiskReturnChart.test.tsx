import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { RiskReturnChart, type RiskReturnDataPoint } from './RiskReturnChart';

describe('RiskReturnChart', () => {
  const mockData: RiskReturnDataPoint[] = [
    {
      id: '1',
      name: '東京 11R 単勝',
      risk: 65,
      expectedReturn: 3.5,
      amount: 1000,
    },
    {
      id: '2',
      name: '中山 10R 複勝',
      risk: 25,
      expectedReturn: 1.5,
      amount: 500,
    },
    {
      id: '3',
      name: '阪神 12R 三連単',
      risk: 90,
      expectedReturn: 50.0,
      amount: 100,
    },
  ];

  it('データがある場合にチャートを表示する', () => {
    render(<RiskReturnChart data={mockData} />);
    expect(screen.getByText('リスク/リターン分析')).toBeInTheDocument();
  });

  it('凡例を表示する', () => {
    render(<RiskReturnChart data={mockData} />);
    expect(screen.getByText('低リスク')).toBeInTheDocument();
    expect(screen.getByText('中リスク')).toBeInTheDocument();
    expect(screen.getByText('高リスク')).toBeInTheDocument();
  });

  it('データが空の場合はメッセージを表示する', () => {
    render(<RiskReturnChart data={[]} />);
    expect(screen.getByText('表示するデータがありません')).toBeInTheDocument();
  });

  it('チャートコンテナがレンダリングされる', () => {
    const { container } = render(<RiskReturnChart data={mockData} />);
    const chart = container.querySelector('.risk-return-chart');
    expect(chart).toBeInTheDocument();
  });
});
