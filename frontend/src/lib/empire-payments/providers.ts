/**
 * Empire Payments — provider abstraction (EMPIRE_PAYMENTS_PRD.md, PRD-gamification §10).
 *
 * Scoped here to **coin purchases**: given a payment context (student name,
 * package, KZT amount) it produces provider-specific instructions the parent-
 * facing /coins page renders. Two providers ship, proving the abstraction:
 *
 *   • kaspi          — primary. Renders `KASPI_PAYMENT_URL` as an
 *                      «Оплатить через Kaspi» button + a client-side QR of the
 *                      same link. The `reference` (student name + package) is
 *                      surfaced so the manager can match the incoming transfer.
 *   • bank_transfer  — a stub with static instructions, to prove a second
 *                      provider slots in with zero changes to callers.
 *
 * Whop is explicitly NOT a provider here — this rail is separate from Chesster
 * billing and must never touch Whop code paths.
 *
 * The builders are pure (config injected) so they unit-test without env; only
 * `loadProviderConfig()` reads `process.env`, and it does so lazily.
 */

export type PaymentProviderId = 'kaspi' | 'bank_transfer';

export const PROVIDER_IDS: readonly PaymentProviderId[] = ['kaspi', 'bank_transfer'];

/** Everything a provider needs to render one payment. Caller localizes labels. */
export interface PaymentContext {
  /** Student display name — goes into the reference so the manager can match. */
  studentName: string;
  /** Localized package label, e.g. "500 монет" — the caller formats per locale. */
  packageLabel: string;
  amountKzt: number;
}

/** Per-org provider config, read from env server-side (all optional). */
export interface ProviderConfig {
  kaspiPaymentUrl?: string | null;
  bankTransfer?: {
    recipient?: string | null;
    iban?: string | null;
    bank?: string | null;
    instructions?: string | null;
  } | null;
}

export interface PaymentField {
  label: string;
  value: string;
}

export interface PaymentInstructions {
  provider: PaymentProviderId;
  /** false when the provider isn't configured — the UI hides it rather than erroring. */
  available: boolean;
  amountKzt: number;
  /** Student name + package — the parent shows this so the manager matches the transfer. */
  reference: string;
  /** Deep link to pay (Kaspi). null for providers without one (bank_transfer). */
  payUrl: string | null;
  /** Value to encode as a QR client-side (the Kaspi link). null when N/A. */
  qrValue: string | null;
  /** Structured details (bank requisites, notes) rendered as a list. */
  fields: PaymentField[];
}

/** Whole-tenge formatting with thin-space grouping, e.g. 2500 → "2 500 ₸". */
export function formatKzt(amount: number): string {
  const n = Number.isFinite(amount) ? Math.round(amount) : 0;
  const grouped = n.toLocaleString('ru-RU').replace(/ /g, ' ');
  return `${grouped} ₸`;
}

/** The line the manager matches an incoming transfer against. */
export function buildReference(ctx: PaymentContext): string {
  return `${ctx.studentName} · ${ctx.packageLabel}`.trim();
}

function buildKaspiPayment(ctx: PaymentContext, cfg: ProviderConfig): PaymentInstructions {
  const url = (cfg.kaspiPaymentUrl ?? '').trim() || null;
  const reference = buildReference(ctx);
  return {
    provider: 'kaspi',
    available: url !== null,
    amountKzt: ctx.amountKzt,
    reference,
    payUrl: url,
    qrValue: url,
    fields: [
      { label: 'amount', value: formatKzt(ctx.amountKzt) },
      { label: 'reference', value: reference },
    ],
  };
}

function buildBankTransferPayment(ctx: PaymentContext, cfg: ProviderConfig): PaymentInstructions {
  const bt = cfg.bankTransfer ?? {};
  const reference = buildReference(ctx);
  const fields: PaymentField[] = [{ label: 'amount', value: formatKzt(ctx.amountKzt) }];
  if (bt.recipient) fields.push({ label: 'recipient', value: bt.recipient });
  if (bt.bank) fields.push({ label: 'bank', value: bt.bank });
  if (bt.iban) fields.push({ label: 'iban', value: bt.iban });
  fields.push({ label: 'reference', value: reference });
  return {
    provider: 'bank_transfer',
    available: true, // static instructions are always available (a real stub)
    amountKzt: ctx.amountKzt,
    reference,
    payUrl: null,
    qrValue: null,
    fields,
  };
}

/** Build payment instructions for one provider. Unknown ids throw. */
export function buildPayment(
  provider: PaymentProviderId,
  ctx: PaymentContext,
  cfg: ProviderConfig,
): PaymentInstructions {
  switch (provider) {
    case 'kaspi':
      return buildKaspiPayment(ctx, cfg);
    case 'bank_transfer':
      return buildBankTransferPayment(ctx, cfg);
    default:
      throw new Error(`Unknown payment provider: ${provider as string}`);
  }
}

/** Provider ids that are configured/usable for the given config, in priority order. */
export function availableProviders(cfg: ProviderConfig): PaymentProviderId[] {
  return PROVIDER_IDS.filter((id) => buildPayment(id, { studentName: '', packageLabel: '', amountKzt: 0 }, cfg).available);
}

/** Read provider config from env (server-side). Lazy — no module-level side effects. */
export function loadProviderConfig(): ProviderConfig {
  const kaspi = process.env.KASPI_PAYMENT_URL?.trim() || null;
  const btInstructions = process.env.BANK_TRANSFER_INSTRUCTIONS?.trim() || null;
  const recipient = process.env.BANK_TRANSFER_RECIPIENT?.trim() || null;
  const iban = process.env.BANK_TRANSFER_IBAN?.trim() || null;
  const bank = process.env.BANK_TRANSFER_BANK?.trim() || null;
  return {
    kaspiPaymentUrl: kaspi,
    bankTransfer:
      btInstructions || recipient || iban || bank
        ? { instructions: btInstructions, recipient, iban, bank }
        : {},
  };
}
