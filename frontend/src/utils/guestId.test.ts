import { describe, it, expect, vi, beforeEach } from 'vitest';
import { getOrCreateGuestId } from './guestId';

describe('getOrCreateGuestId', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('新規IDを生成してlocalStorageに保存する', () => {
    const id = getOrCreateGuestId();

    expect(id).toBeTruthy();
    expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);
    expect(localStorage.getItem('baken-kaigi-guest-id')).toBe(id);
  });

  it('既存のゲストIDがある場合はそれを返す', () => {
    localStorage.setItem('baken-kaigi-guest-id', 'existing-guest-id');

    const id = getOrCreateGuestId();

    expect(id).toBe('existing-guest-id');
  });

  it('2回呼んでも同じIDが返る', () => {
    const id1 = getOrCreateGuestId();
    const id2 = getOrCreateGuestId();

    expect(id1).toBe(id2);
  });

  it('localStorageが使えない場合は一時IDを返す', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('localStorage disabled');
    });

    const id = getOrCreateGuestId();

    expect(id).toBeTruthy();
    // UUID形式であること
    expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i);

    vi.restoreAllMocks();
  });
});
