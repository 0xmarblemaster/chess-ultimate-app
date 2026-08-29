import { ruRU, kkKZ } from '@clerk/localizations';

// Clerk localization templates per locale. `${appName}` is interpolated
// at request time from the tenant's brand name (apex falls back to
// "Chesster"), so chess-empire.chesster.io renders "Sign in to Chess Empire"
// instead of leaking the Chesster name into the auth modal.
//
// Each template is layered on top of Clerk's official translation for that
// locale (en has no base — English is Clerk's default), so buttons, links,
// error messages, and verification screens are translated too. kk-KZ is
// community-contributed with gaps; missing keys fall back to English.

const clerkBaseLocales: Record<string, Record<string, unknown> | undefined> = {
  en: undefined,
  ru: ruRU as unknown as Record<string, unknown>,
  kz: kkKZ as unknown as Record<string, unknown>,
};

const clerkLocalizationTemplates: Record<string, Record<string, unknown>> = {
  en: {
    signIn: {
      start: {
        title: 'Sign in to ${appName}',
        subtitle: 'Welcome back! Please sign in to continue',
      },
    },
    signUp: {
      start: {
        title: 'Create your ${appName} account',
        subtitle: 'Start your chess journey today',
      },
    },
    formFieldInputPlaceholder__firstName: 'Name (optional)',
    formFieldInputPlaceholder__emailAddress: 'Email',
    formFieldInputPlaceholder__password: 'Password',
    formFieldLabel__firstName: 'Name',
    formFieldLabel__emailAddress: 'Email',
    formFieldLabel__password: 'Password',
  },
  ru: {
    signIn: {
      start: {
        title: 'Войти в ${appName}',
        subtitle: 'С возвращением! Войдите, чтобы продолжить',
      },
    },
    signUp: {
      start: {
        title: 'Создайте аккаунт ${appName}',
        subtitle: 'Начните своё шахматное путешествие сегодня',
      },
    },
    formFieldInputPlaceholder__firstName: 'Имя (необязательно)',
    formFieldInputPlaceholder__emailAddress: 'Электронная почта',
    formFieldInputPlaceholder__password: 'Пароль',
    formFieldLabel__firstName: 'Имя',
    formFieldLabel__emailAddress: 'Электронная почта',
    formFieldLabel__password: 'Пароль',
  },
  kz: {
    signIn: {
      start: {
        title: '${appName}-ге кіру',
        subtitle: 'Қайта қош келдіңіз! Жалғастыру үшін кіріңіз',
      },
    },
    signUp: {
      start: {
        title: '${appName} аккаунтын жасау',
        subtitle: 'Шахмат саяхатыңызды бүгін бастаңыз',
      },
    },
    formFieldInputPlaceholder__firstName: 'Аты (міндетті емес)',
    formFieldInputPlaceholder__emailAddress: 'Электрондық пошта',
    formFieldInputPlaceholder__password: 'Құпия сөз',
    formFieldLabel__firstName: 'Аты',
    formFieldLabel__emailAddress: 'Электрондық пошта',
    formFieldLabel__password: 'Құпия сөз',
  },
};

function interpolateAppName<T>(value: T, appName: string): T {
  const token = '${appName}';
  if (typeof value === 'string') {
    return value.split(token).join(appName) as unknown as T;
  }
  if (Array.isArray(value)) {
    return value.map(v => interpolateAppName(v, appName)) as unknown as T;
  }
  if (value !== null && typeof value === 'object') {
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      out[k] = interpolateAppName(v, appName);
    }
    return out as unknown as T;
  }
  return value;
}

function deepMerge(
  base: Record<string, unknown>,
  override: Record<string, unknown>,
): Record<string, unknown> {
  const out: Record<string, unknown> = { ...base };
  for (const [k, v] of Object.entries(override)) {
    const existing = out[k];
    if (
      v !== null &&
      typeof v === 'object' &&
      !Array.isArray(v) &&
      existing !== null &&
      typeof existing === 'object' &&
      !Array.isArray(existing)
    ) {
      out[k] = deepMerge(
        existing as Record<string, unknown>,
        v as Record<string, unknown>,
      );
    } else {
      out[k] = v;
    }
  }
  return out;
}

export function buildClerkLocalization(
  locale: string,
  appName: string,
): Record<string, unknown> {
  const template =
    clerkLocalizationTemplates[locale] || clerkLocalizationTemplates.en;
  const base = clerkBaseLocales[locale];
  const merged = base ? deepMerge(base, template) : template;
  return interpolateAppName(merged, appName);
}
