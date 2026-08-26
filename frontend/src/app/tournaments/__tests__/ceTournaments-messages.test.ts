/**
 * Locale-parity guard: every locale file must carry the identical
 * `ceTournaments` key set so no string silently falls back to another language.
 */
import { describe, it, expect } from 'vitest';

import en from '../../../../messages/en.json';
import ru from '../../../../messages/ru.json';
import kz from '../../../../messages/kz.json';

/** Flatten nested keys into dotted paths ("errors.full", …). */
function keyPaths(obj: Record<string, unknown>, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([k, v]) => {
    const path = prefix ? `${prefix}.${k}` : k;
    return v && typeof v === 'object' && !Array.isArray(v)
      ? keyPaths(v as Record<string, unknown>, path)
      : [path];
  });
}

describe('ceTournaments message parity', () => {
  const enKeys = keyPaths(en.ceTournaments).sort();

  it('en has a non-empty ceTournaments namespace', () => {
    expect(enKeys.length).toBeGreaterThan(0);
  });

  it('ru carries the identical ceTournaments key set', () => {
    expect(keyPaths(ru.ceTournaments).sort()).toEqual(enKeys);
  });

  it('kz carries the identical ceTournaments key set', () => {
    expect(keyPaths(kz.ceTournaments).sort()).toEqual(enKeys);
  });
});
