/**
 * Shared test helper: render a review component under a real
 * NextIntlClientProvider seeded with the English catalog, so components that
 * call `useTranslations('gameReview')` resolve keys instead of throwing.
 */
import React from 'react';
import { render, type RenderOptions } from '@testing-library/react';
import { NextIntlClientProvider } from 'next-intl';

import en from '../../../../messages/en.json';

export function renderIntl(ui: React.ReactElement, options?: RenderOptions) {
  return render(
    <NextIntlClientProvider locale="en" messages={en as Record<string, unknown>}>
      {ui}
    </NextIntlClientProvider>,
    options,
  );
}

/** The English `gameReview` catalog, for asserting rendered values by key. */
export const gameReview = en.gameReview;
