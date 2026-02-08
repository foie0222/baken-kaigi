/**
 * document.body.style.overflow の競合を防ぐためのスクロールロック管理.
 *
 * 複数のモーダル/BottomSheetが同時にオープンしている場合でも、
 * すべてが閉じるまで overflow: hidden を維持する。
 */
let lockCount = 0;
let savedOverflow = '';

export function acquireScrollLock(): void {
  if (lockCount === 0) {
    savedOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
  }
  lockCount++;
}

export function releaseScrollLock(): void {
  lockCount = Math.max(0, lockCount - 1);
  if (lockCount === 0) {
    document.body.style.overflow = savedOverflow;
  }
}

/** テスト用: 内部状態をリセットする */
export function _resetForTest(): void {
  lockCount = 0;
  savedOverflow = '';
}
