/**
 * document.body.style.overflow の競合を防ぐためのスクロールロック管理.
 *
 * 複数のモーダル/BottomSheetが同時にオープンしている場合でも、
 * すべてが閉じるまで overflow: hidden を維持する。
 */
let lockCount = 0;

export function acquireScrollLock(): void {
  lockCount++;
  if (lockCount === 1) {
    document.body.style.overflow = 'hidden';
  }
}

export function releaseScrollLock(): void {
  lockCount = Math.max(0, lockCount - 1);
  if (lockCount === 0) {
    document.body.style.overflow = '';
  }
}
