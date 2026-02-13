import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { acquireScrollLock, releaseScrollLock, _resetForTest } from './scrollLock';

describe('scrollLock', () => {
  let mainEl: HTMLElement;

  beforeEach(() => {
    _resetForTest();
    document.body.style.overflow = '';
    mainEl = document.createElement('main');
    document.body.appendChild(mainEl);
  });

  afterEach(() => {
    mainEl.remove();
  });

  it('acquireScrollLock sets overflow to hidden on body and main', () => {
    acquireScrollLock();
    expect(document.body.style.overflow).toBe('hidden');
    expect(mainEl.style.overflow).toBe('hidden');
    releaseScrollLock();
  });

  it('releaseScrollLock restores overflow when count reaches 0', () => {
    acquireScrollLock();
    releaseScrollLock();
    expect(document.body.style.overflow).toBe('');
    expect(mainEl.style.overflow).toBe('');
  });

  it('multiple acquires keep overflow hidden until all released', () => {
    acquireScrollLock();
    acquireScrollLock();
    expect(document.body.style.overflow).toBe('hidden');

    releaseScrollLock();
    expect(document.body.style.overflow).toBe('hidden');

    releaseScrollLock();
    expect(document.body.style.overflow).toBe('');
  });

  it('releaseScrollLock does not go below 0', () => {
    releaseScrollLock();
    releaseScrollLock();
    expect(document.body.style.overflow).toBe('');

    acquireScrollLock();
    expect(document.body.style.overflow).toBe('hidden');
    releaseScrollLock();
  });

  it('restores original overflow value', () => {
    document.body.style.overflow = 'auto';
    acquireScrollLock();
    expect(document.body.style.overflow).toBe('hidden');

    releaseScrollLock();
    expect(document.body.style.overflow).toBe('auto');
  });
});
