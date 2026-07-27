/**
 * Sign-up onboarding guard (pure decision logic).
 *
 * On a white-label org domain (e.g. chess-empire.chesster.io) a user MUST reach
 * the sign-up page through the find-yourself → confirm welcome flow, which mints
 * a short-lived invite JWT. A bare sign-up (no valid, unexpired invite JWT) would
 * register an unlinked account — the Shokan failure mode — so it is bounced back
 * to onboarding.
 *
 * The main chesster.io domain is not white-label, so it always proceeds
 * unchanged. Kept as a pure function so the redirect decision is unit-testable
 * without a Clerk/Next runtime.
 */
export interface SignupGuardInput {
  /** True when the request is on a white-label org domain. */
  isWhiteLabel: boolean;
  /** True when a valid, unexpired invite JWT is present. */
  hasValidInvite: boolean;
  /** The welcome URL stored when onboarding started, or null. */
  storedWelcomeUrl: string | null;
  /** Fallback landing when no welcome URL was stored (org welcome landing). */
  fallbackUrl?: string;
  /**
   * True when the page is on a Clerk internal sub-step (OTP verify, SSO
   * callback, continue, …). Clerk drops the `?invite=` query param on these
   * navigations, so the guard must NEVER fire there or it kills the flow.
   */
  isClerkSubStep?: boolean;
}

export type SignupGuardDecision =
  | { action: 'proceed' }
  | { action: 'redirect'; target: string };

export function computeSignupGuard({
  isWhiteLabel,
  hasValidInvite,
  storedWelcomeUrl,
  fallbackUrl = '/',
  isClerkSubStep = false,
}: SignupGuardInput): SignupGuardDecision {
  // Clerk sub-step (e.g. verify-email-address): the invite query param is
  // dropped by Clerk's own navigation, so the flow is already in progress —
  // never bounce it.
  if (isClerkSubStep) {
    return { action: 'proceed' };
  }
  // Main domain, or a valid invite in hand — nothing to block.
  if (!isWhiteLabel || hasValidInvite) {
    return { action: 'proceed' };
  }
  const target = storedWelcomeUrl?.trim() || fallbackUrl;
  return { action: 'redirect', target };
}
