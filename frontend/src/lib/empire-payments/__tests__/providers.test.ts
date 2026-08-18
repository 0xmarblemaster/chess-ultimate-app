import { describe, it, expect } from 'vitest';
import {
  type ProviderConfig,
  availableProviders,
  buildPayment,
  buildReference,
  formatKzt,
} from '../providers';

const CTX = { studentName: 'Иван Петров', packageLabel: '500🪙', amountKzt: 2500 };

describe('formatKzt', () => {
  it('groups thousands and appends the tenge sign', () => {
    expect(formatKzt(2500)).toBe('2 500 ₸');
    expect(formatKzt(0)).toBe('0 ₸');
  });
});

describe('buildReference', () => {
  it('combines student name and package so the manager can match a transfer', () => {
    expect(buildReference(CTX)).toBe('Иван Петров · 500🪙');
  });
});

describe('kaspi provider', () => {
  it('is available and renders the configured payment link + QR', () => {
    const cfg: ProviderConfig = { kaspiPaymentUrl: 'https://kaspi.kz/pay/abc' };
    const p = buildPayment('kaspi', CTX, cfg);
    expect(p.available).toBe(true);
    expect(p.payUrl).toBe('https://kaspi.kz/pay/abc');
    expect(p.qrValue).toBe('https://kaspi.kz/pay/abc'); // QR encodes the same link
    expect(p.reference).toBe('Иван Петров · 500🪙');
    expect(p.fields).toContainEqual({ label: 'reference', value: 'Иван Петров · 500🪙' });
  });

  it('degrades to unavailable when KASPI_PAYMENT_URL is unset', () => {
    const p = buildPayment('kaspi', CTX, { kaspiPaymentUrl: null });
    expect(p.available).toBe(false);
    expect(p.payUrl).toBeNull();
  });

  it('treats a blank url as unconfigured', () => {
    const p = buildPayment('kaspi', CTX, { kaspiPaymentUrl: '   ' });
    expect(p.available).toBe(false);
  });
});

describe('bank_transfer provider (stub)', () => {
  it('is always available and has no pay url or QR', () => {
    const p = buildPayment('bank_transfer', CTX, {});
    expect(p.available).toBe(true);
    expect(p.payUrl).toBeNull();
    expect(p.qrValue).toBeNull();
    expect(p.reference).toBe('Иван Петров · 500🪙');
  });

  it('surfaces configured bank requisites as fields', () => {
    const p = buildPayment('bank_transfer', CTX, {
      bankTransfer: { recipient: 'ТОО Chess Empire', iban: 'KZ123', bank: 'Kaspi Bank' },
    });
    const labels = p.fields.map((f) => f.label);
    expect(labels).toEqual(expect.arrayContaining(['recipient', 'bank', 'iban', 'reference']));
  });
});

describe('availableProviders', () => {
  it('lists kaspi first when configured, always includes the bank stub', () => {
    expect(availableProviders({ kaspiPaymentUrl: 'https://kaspi.kz/pay/x' })).toEqual([
      'kaspi',
      'bank_transfer',
    ]);
  });

  it('drops kaspi when unconfigured', () => {
    expect(availableProviders({})).toEqual(['bank_transfer']);
  });
});

describe('buildPayment', () => {
  it('throws on an unknown provider', () => {
    // @ts-expect-error — exercising the runtime guard
    expect(() => buildPayment('whop', CTX, {})).toThrow(/Unknown payment provider/);
  });
});
