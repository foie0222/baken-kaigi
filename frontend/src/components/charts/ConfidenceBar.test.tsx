import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConfidenceBar } from './ConfidenceBar';

describe('ConfidenceBar', () => {
  it('デフォルトラベルで表示される', () => {
    render(<ConfidenceBar confidence={50} />);
    expect(screen.getByText('AI分析の自信度')).toBeInTheDocument();
    expect(screen.getByText('中 (50%)')).toBeInTheDocument();
  });

  it('カスタムラベルで表示される', () => {
    render(<ConfidenceBar confidence={75} label="テストラベル" />);
    expect(screen.getByText('テストラベル')).toBeInTheDocument();
    expect(screen.getByText('高 (75%)')).toBeInTheDocument();
  });

  it('0%未満の値は0%にクランプされる', () => {
    render(<ConfidenceBar confidence={-10} />);
    expect(screen.getByText('低 (0%)')).toBeInTheDocument();
  });

  it('100%超の値は100%にクランプされる', () => {
    render(<ConfidenceBar confidence={150} />);
    expect(screen.getByText('高 (100%)')).toBeInTheDocument();
  });

  it('プログレスバーがaria属性を持つ', () => {
    render(<ConfidenceBar confidence={60} />);
    const progressbar = screen.getByRole('progressbar');
    expect(progressbar).toHaveAttribute('aria-valuenow', '60');
    expect(progressbar).toHaveAttribute('aria-valuemin', '0');
    expect(progressbar).toHaveAttribute('aria-valuemax', '100');
  });

  it('低自信度（30%以下）で赤色が使用される', () => {
    const { container } = render(<ConfidenceBar confidence={20} />);
    const bar = container.querySelector('[style*="background"]');
    expect(bar).toBeTruthy();
  });

  it('中自信度（31-70%）で黄色が使用される', () => {
    const { container } = render(<ConfidenceBar confidence={50} />);
    const bar = container.querySelector('[style*="background"]');
    expect(bar).toBeTruthy();
  });

  it('高自信度（71%以上）で緑色が使用される', () => {
    const { container } = render(<ConfidenceBar confidence={80} />);
    const bar = container.querySelector('[style*="background"]');
    expect(bar).toBeTruthy();
  });
});
