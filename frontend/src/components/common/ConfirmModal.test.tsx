import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '../../test/utils';
import { ConfirmModal } from './ConfirmModal';

describe('ConfirmModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onConfirm: vi.fn(),
    title: '確認',
    children: <p>本当に実行しますか？</p>,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('isOpenがfalseの場合は何も表示しない', () => {
    const { container } = render(
      <ConfirmModal {...defaultProps} isOpen={false} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('isOpenがtrueの場合にモーダルを表示する', () => {
    render(<ConfirmModal {...defaultProps} />);
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: '確認' })).toBeInTheDocument();
    expect(screen.getByText('本当に実行しますか？')).toBeInTheDocument();
  });

  it('確認ボタンをクリックするとonConfirmが呼ばれる', () => {
    render(<ConfirmModal {...defaultProps} />);
    const confirmBtn = screen.getByRole('button', { name: '確認' });
    fireEvent.click(confirmBtn);
    expect(defaultProps.onConfirm).toHaveBeenCalledTimes(1);
  });

  it('キャンセルボタンをクリックするとonCloseが呼ばれる', () => {
    render(<ConfirmModal {...defaultProps} />);
    fireEvent.click(screen.getByText('キャンセル'));
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it('バックドロップをクリックするとonCloseが呼ばれる', () => {
    render(<ConfirmModal {...defaultProps} />);
    const backdrop = document.querySelector('.confirm-modal-backdrop');
    expect(backdrop).not.toBeNull();
    fireEvent.click(backdrop!);
    expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
  });

  it('confirmTextを指定すると確認ボタンのテキストが変わる', () => {
    render(<ConfirmModal {...defaultProps} confirmText="購入する" />);
    expect(screen.getByText('購入する')).toBeInTheDocument();
  });

  it('cancelTextを指定するとキャンセルボタンのテキストが変わる', () => {
    render(<ConfirmModal {...defaultProps} cancelText="やめる" />);
    expect(screen.getByText('やめる')).toBeInTheDocument();
  });

  it('confirmVariantがdangerの場合、確認ボタンにdangerクラスが付く', () => {
    render(<ConfirmModal {...defaultProps} confirmVariant="danger" />);
    const confirmBtn = screen.getByRole('button', { name: '確認' });
    expect(confirmBtn).toHaveClass('danger');
  });

  it('aria属性が正しく設定される', () => {
    render(<ConfirmModal {...defaultProps} />);
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby', 'confirm-modal-title');
  });
});
