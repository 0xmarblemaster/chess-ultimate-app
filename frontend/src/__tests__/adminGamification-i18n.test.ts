/**
 * @vitest-environment node
 *
 * Key-parity gate for the admin gamification i18n namespaces (§14.1).
 * en / ru / kz must expose an identical set of keys so no locale silently
 * falls back to another for a missing string.
 */
import { describe, it, expect } from 'vitest';

import en from '../../messages/en.json';
import ru from '../../messages/ru.json';
import kz from '../../messages/kz.json';

type Json = Record<string, unknown>;

/** Recursively collect dotted key paths for every leaf string. */
function leafKeys(obj: Json, prefix = ''): string[] {
  return Object.entries(obj)
    .flatMap(([k, v]) =>
      v && typeof v === 'object'
        ? leafKeys(v as Json, `${prefix}${k}.`)
        : [`${prefix}${k}`],
    )
    .sort();
}

const locales: Record<string, Json> = { en, ru, kz };

describe.each(['adminGamification', 'adminNav'])('%s namespace i18n', (ns) => {
  it('exists in every locale', () => {
    for (const [locale, messages] of Object.entries(locales)) {
      expect(messages[ns], `${ns} namespace missing in ${locale}.json`).toBeDefined();
    }
  });

  it('has identical key sets across en / ru / kz', () => {
    const enKeys = leafKeys(en[ns as keyof typeof en] as Json);
    const ruKeys = leafKeys(ru[ns as keyof typeof ru] as Json);
    const kzKeys = leafKeys(kz[ns as keyof typeof kz] as Json);
    expect(ruKeys).toEqual(enKeys);
    expect(kzKeys).toEqual(enKeys);
  });

  it('has a non-empty string for every leaf in every locale', () => {
    for (const [locale, messages] of Object.entries(locales)) {
      const walk = (obj: Json, prefix = '') => {
        for (const [k, v] of Object.entries(obj)) {
          if (v && typeof v === 'object') {
            walk(v as Json, `${prefix}${k}.`);
          } else {
            expect(typeof v, `${locale}.${ns}.${prefix}${k} must be a string`).toBe('string');
            expect(
              (v as string).trim().length,
              `${locale}.${ns}.${prefix}${k} must not be empty`,
            ).toBeGreaterThan(0);
          }
        }
      };
      walk(messages[ns] as Json);
    }
  });
});

describe('adminGamification interpolation placeholders', () => {
  const ns = (m: Json) => m.adminGamification as Json;

  it('preserves ICU placeholders across every locale', () => {
    const checks: Array<[string, string]> = [
      ['rules.weeksShort', '{weeks}'],
      ['seasons.standingsMeta', '{topN}'],
      ['seasons.members', '{count}'],
      ['seasons.confirmClose', '{name}'],
      ['coins.baseRate', '{coins}'],
      ['coins.confirmConfirm', '{coins}'],
      ['ops.confirmReverse', '{ledger}'],
      ['ops.confirmReverse', '{amount}'],
    ];
    const get = (obj: Json, path: string): string =>
      path.split('.').reduce<unknown>((acc, key) => (acc as Json)?.[key], obj) as string;
    for (const [locale, messages] of Object.entries(locales)) {
      for (const [path, token] of checks) {
        expect(
          get(ns(messages), path),
          `${locale}.adminGamification.${path} must keep ${token}`,
        ).toContain(token);
      }
    }
  });
});
