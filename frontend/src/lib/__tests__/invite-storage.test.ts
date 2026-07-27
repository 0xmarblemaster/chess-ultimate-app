/**
 * Tests for the invite-storage read helpers, focused on `readStoredInviteJwt`:
 * sessionStorage wins over localStorage, falls back to localStorage, and any
 * storage access throwing yields null.
 */
import { describe, it, expect, afterEach, vi } from 'vitest';
import { CE_INVITE_JWT_STORAGE_KEY, readStoredInviteJwt } from '../invite-storage';

function fakeStorage(initial: Record<string, string> = {}): Storage {
  const map = new Map(Object.entries(initial));
  return {
    getItem: (k: string) => (map.has(k) ? map.get(k)! : null),
    setItem: (k: string, v: string) => void map.set(k, v),
    removeItem: (k: string) => void map.delete(k),
    clear: () => map.clear(),
    key: (i: number) => Array.from(map.keys())[i] ?? null,
    get length() {
      return map.size;
    },
  } as Storage;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('readStoredInviteJwt', () => {
  it('prefers sessionStorage over localStorage', () => {
    vi.stubGlobal(
      'sessionStorage',
      fakeStorage({ [CE_INVITE_JWT_STORAGE_KEY]: 'session-jwt' }),
    );
    vi.stubGlobal(
      'localStorage',
      fakeStorage({ [CE_INVITE_JWT_STORAGE_KEY]: 'local-jwt' }),
    );
    expect(readStoredInviteJwt()).toBe('session-jwt');
  });

  it('falls back to localStorage when sessionStorage is empty', () => {
    vi.stubGlobal('sessionStorage', fakeStorage());
    vi.stubGlobal(
      'localStorage',
      fakeStorage({ [CE_INVITE_JWT_STORAGE_KEY]: 'local-jwt' }),
    );
    expect(readStoredInviteJwt()).toBe('local-jwt');
  });

  it('returns null when neither storage has the key', () => {
    vi.stubGlobal('sessionStorage', fakeStorage());
    vi.stubGlobal('localStorage', fakeStorage());
    expect(readStoredInviteJwt()).toBeNull();
  });

  it('returns null when storage access throws (private mode / blocked)', () => {
    vi.stubGlobal('sessionStorage', {
      getItem: () => {
        throw new Error('blocked');
      },
    } as unknown as Storage);
    vi.stubGlobal('localStorage', fakeStorage());
    expect(readStoredInviteJwt()).toBeNull();
  });
});
