/**
 * スクロールロック管理.
 *
 * 複数のモーダル/BottomSheetが同時にオープンしている場合でも、
 * すべてが閉じるまで overflow: hidden を維持する。
 * body と main 両方をロックする（main は独立スクロールコンテナ）。
 */
let lockCount = 0;
let savedOverflow = '';

export function acquireScrollLock(): void {
  if (lockCount === 0) {
    savedOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const main = document.querySelector('main');
    if (main) (main as HTMLElement).style.overflow = 'hidden';
  }
  lockCount++;
}

export function releaseScrollLock(): void {
  lockCount = Math.max(0, lockCount - 1);
  if (lockCount === 0) {
    document.body.style.overflow = savedOverflow;
    const main = document.querySelector('main');
    if (main) (main as HTMLElement).style.overflow = '';
  }
}

/** テスト用: 内部状態をリセットする */
export function _resetForTest(): void {
  lockCount = 0;
  savedOverflow = '';
}
