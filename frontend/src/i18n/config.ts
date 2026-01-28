export const locales = ['en', 'ru', 'kk'] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = 'en';

export const localeNames: Record<Locale, string> = {
  en: 'English',
  ru: 'Русский',
  kk: 'Қазақша'
};

export const localeFlags: Record<Locale, string> = {
  en: '🇺🇸',
  ru: '🇷🇺',
  kk: '🇰🇿'
};
