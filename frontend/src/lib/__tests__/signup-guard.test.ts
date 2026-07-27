/**
 * Tests for the bare-registration sign-up guard decision.
 */
import { describe, it, expect } from 'vitest';
import { computeSignupGuard } from '../signup-guard';

describe('computeSignupGuard', () => {
  it('proceeds on the main (non-white-label) domain even without an invite', () => {
    expect(
      computeSignupGuard({
        isWhiteLabel: false,
        hasValidInvite: false,
        storedWelcomeUrl: null,
      }),
    ).toEqual({ action: 'proceed' });
  });

  it('proceeds on white-label when a valid invite is present', () => {
    expect(
      computeSignupGuard({
        isWhiteLabel: true,
        hasValidInvite: true,
        storedWelcomeUrl: '/welcome/tok-abc',
      }),
    ).toEqual({ action: 'proceed' });
  });

  it('redirects to the stored welcome URL on white-label without a valid invite', () => {
    expect(
      computeSignupGuard({
        isWhiteLabel: true,
        hasValidInvite: false,
        storedWelcomeUrl: '/welcome/tok-abc?step=confirm',
      }),
    ).toEqual({ action: 'redirect', target: '/welcome/tok-abc?step=confirm' });
  });

  it('falls back to the org welcome landing when no welcome URL is stored', () => {
    expect(
      computeSignupGuard({
        isWhiteLabel: true,
        hasValidInvite: false,
        storedWelcomeUrl: null,
      }),
    ).toEqual({ action: 'redirect', target: '/' });
  });

  it('honors an explicit fallback URL', () => {
    expect(
      computeSignupGuard({
        isWhiteLabel: true,
        hasValidInvite: false,
        storedWelcomeUrl: '   ',
        fallbackUrl: '/welcome',
      }),
    ).toEqual({ action: 'redirect', target: '/welcome' });
  });

  it('proceeds on a Clerk sub-step even when the invite query param was dropped', () => {
    // The exact bug: Clerk navigates to /sign-up/verify-email-address after the
    // CONTINUE button and drops `?invite=`, so hasValidInvite is false here.
    expect(
      computeSignupGuard({
        isWhiteLabel: true,
        hasValidInvite: false,
        storedWelcomeUrl: '/welcome/tok-abc',
        isClerkSubStep: true,
      }),
    ).toEqual({ action: 'proceed' });
  });

  it('proceeds on white-label with a stored-invite fallback (hasValidInvite true)', () => {
    // The page derives hasValidInvite from the query param OR the stored JWT;
    // once the storage fallback supplies a valid invite the guard proceeds.
    expect(
      computeSignupGuard({
        isWhiteLabel: true,
        hasValidInvite: true,
        storedWelcomeUrl: null,
      }),
    ).toEqual({ action: 'proceed' });
  });

  it('still redirects a bare cold visit on the white-label base sign-up path', () => {
    // No query invite, nothing in storage, base /sign-up (not a sub-step) —
    // the bare-registration protection stays intact.
    expect(
      computeSignupGuard({
        isWhiteLabel: true,
        hasValidInvite: false,
        storedWelcomeUrl: null,
        isClerkSubStep: false,
      }),
    ).toEqual({ action: 'redirect', target: '/' });
  });
});
