/**
 * Access-expired screen for time-boxed online-student members.
 *
 * Rendered when `getMembershipState` returns `expired` — a verified member
 * whose `access_expires_at` window has elapsed. Checked live on every access
 * (no cron), so a returning online student sees this instead of the app once
 * their 72h window is up. Copy points them back to their coach for a new link.
 */
export default function EmpireAccessExpired() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-50 px-4 text-center">
      <div className="w-full max-w-md rounded-3xl bg-white p-8 shadow-xl">
        <h1 className="text-2xl font-bold text-gray-800">
          Your access has expired
        </h1>
        <p className="mt-3 text-sm text-gray-500">
          Your Chesster access from this invite has ended. Contact your coach for
          a fresh link to keep playing and learning.
        </p>
      </div>
    </div>
  );
}
