import { describe, it, expect, beforeEach } from 'vitest';

// テストごとにモジュールをリセットするため動的importを使用
describe('scrollLock', () => {
  beforeEach(() => {
    document.body.style.overflow = '';
  });

  it('acquireScrollLock sets overflow to hidden', async () => {
    // 毎回新しいモジュールインスタンスを取得
    const mod = await import('./scrollLock');
    // lockCount をリセットするため、release を十分回数呼ぶ
    for (let i = 0; i < 10; i++) mod.releaseScrollLock();
    document.body.style.overflow = '';

    mod.acquireScrollLock();
    expect(document.body.style.overflow).toBe('hidden');
    // cleanup
    mod.releaseScrollLock();
  });

  it('releaseScrollLock restores overflow when count reaches 0', async () => {
    const mod = await import('./scrollLock');
    for (let i = 0; i < 10; i++) mod.releaseScrollLock();
    document.body.style.overflow = '';

    mod.acquireScrollLock();
    mod.releaseScrollLock();
    expect(document.body.style.overflow).toBe('');
  });

  it('multiple acquires keep overflow hidden until all released', async () => {
    const mod = await import('./scrollLock');
    for (let i = 0; i < 10; i++) mod.releaseScrollLock();
    document.body.style.overflow = '';

    mod.acquireScrollLock();
    mod.acquireScrollLock();
    expect(document.body.style.overflow).toBe('hidden');

    mod.releaseScrollLock();
    expect(document.body.style.overflow).toBe('hidden');

    mod.releaseScrollLock();
    expect(document.body.style.overflow).toBe('');
  });

  it('releaseScrollLock does not go below 0', async () => {
    const mod = await import('./scrollLock');
    for (let i = 0; i < 10; i++) mod.releaseScrollLock();
    document.body.style.overflow = '';

    mod.releaseScrollLock();
    mod.releaseScrollLock();
    expect(document.body.style.overflow).toBe('');

    mod.acquireScrollLock();
    expect(document.body.style.overflow).toBe('hidden');
    mod.releaseScrollLock();
  });
});
