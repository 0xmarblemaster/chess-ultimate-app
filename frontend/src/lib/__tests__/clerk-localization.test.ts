import { describe, it, expect } from 'vitest';
import { buildClerkLocalization } from '../clerk-localization';

type LocalizationTree = Record<string, unknown>;

function get(obj: LocalizationTree, path: string[]): unknown {
  return path.reduce<unknown>(
    (acc, key) =>
      acc && typeof acc === 'object'
        ? (acc as LocalizationTree)[key]
        : undefined,
    obj,
  );
}

describe('buildClerkLocalization', () => {
  it('interpolates appName into custom titles', () => {
    const en = buildClerkLocalization('en', 'Chess Empire');
    expect(get(en, ['signIn', 'start', 'title'])).toBe(
      'Sign in to Chess Empire',
    );
  });

  it('keeps custom overrides on top of the ru base locale', () => {
    const ru = buildClerkLocalization('ru', 'Chesster');
    expect(get(ru, ['signIn', 'start', 'title'])).toBe('Войти в Chesster');
    expect(ru.formFieldLabel__password).toBe('Пароль');
  });

  it('fills untouched keys from the official ru translation', () => {
    const ru = buildClerkLocalization('ru', 'Chesster');
    // Keys we never defined ourselves must come from @clerk/localizations.
    expect(typeof ru.formButtonPrimary).toBe('string');
    expect(ru.formButtonPrimary).not.toBe('');
    // A nested key outside our template, e.g. the sign-in link footer.
    const actionLink = get(ru, ['signIn', 'start', 'actionLink']);
    expect(typeof actionLink).toBe('string');
  });

  it('fills untouched keys from the official kk-KZ translation for kz', () => {
    const kz = buildClerkLocalization('kz', 'Chesster');
    expect(get(kz, ['signIn', 'start', 'title'])).toBe('Chesster-ге кіру');
    expect(typeof kz.formButtonPrimary).toBe('string');
  });

  it('falls back to the en template for unknown locales', () => {
    const xx = buildClerkLocalization('xx', 'Chesster');
    expect(get(xx, ['signIn', 'start', 'title'])).toBe('Sign in to Chesster');
  });

  it('does not leak the ${appName} token anywhere in the merged tree', () => {
    for (const locale of ['en', 'ru', 'kz']) {
      const json = JSON.stringify(buildClerkLocalization(locale, 'Chesster'));
      expect(json).not.toContain('${appName}');
    }
  });
});
