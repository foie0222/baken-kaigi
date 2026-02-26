import { render, screen } from '@testing-library/react';
import { FinishPositionBadge } from './FinishPositionBadge';

test('1着はfinish-1クラスを持つ', () => {
  render(<FinishPositionBadge position={1} />);
  expect(screen.getByText('1')).toHaveClass('finish-1');
});

test('2着はfinish-2クラスを持つ', () => {
  render(<FinishPositionBadge position={2} />);
  expect(screen.getByText('2')).toHaveClass('finish-2');
});

test('3着はfinish-3クラスを持つ', () => {
  render(<FinishPositionBadge position={3} />);
  expect(screen.getByText('3')).toHaveClass('finish-3');
});

test('4着はハイライトクラスを持たない', () => {
  render(<FinishPositionBadge position={4} />);
  const el = screen.getByText('4');
  expect(el).toHaveClass('finish-badge');
  expect(el.className).not.toMatch(/finish-\d/);
});

test('nullは"-"を表示する', () => {
  render(<FinishPositionBadge position={null} />);
  expect(screen.getByText('-')).toBeInTheDocument();
});

test('undefinedは"-"を表示する', () => {
  render(<FinishPositionBadge position={undefined} />);
  expect(screen.getByText('-')).toBeInTheDocument();
});
