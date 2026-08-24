#!/usr/bin/env bash
#
# restart-backend.sh — safe restart guard for the Chesster Flask backend.
#
# WHY THIS EXISTS:
#   gunicorn does NOT hot-reload. When new backend code lands, the running
#   workers keep serving the OLD fork until the service is restarted. This bit
#   us twice (2026-08-18 gamification, 2026-08-24 game-review): routes 404'd in
#   production for hours because the process predated the code.
#
#   This script makes it mechanically impossible to "deploy" and walk away on a
#   stale process: it restarts the service, waits for it to come up, and then
#   PROVES every critical route is actually registered. If any critical route
#   still 404s, it exits NON-ZERO and screams — never reports success on a 404.
#
# USAGE:
#   sudo bash /root/chess-app/backend/restart-backend.sh
#
# EXIT CODES:
#   0  service restarted AND all critical routes serve (not 404)
#   1  service failed to come up / health check failed
#   2  service is up but one or more critical routes 404 (STALE / MISSING route)

set -uo pipefail

SERVICE="chess-backend"
BASE="http://127.0.0.1:5001"
HEALTH_PATH="/"                 # returns 200 when the app is up
HEALTH_TIMEOUT=30               # seconds to wait for the app to answer

# Critical routes that MUST exist after a restart.
# Format: "METHOD PATH [json-body]".  A 404 on any of these fails the guard.
CRITICAL_ROUTES=(
  "POST /api/review {\"pgn\":\"1. e4 e5 *\"}"
)

red()   { printf '\033[31m%s\033[0m\n' "$*"; }
green() { printf '\033[32m%s\033[0m\n' "$*"; }
bold()  { printf '\033[1m%s\033[0m\n'  "$*"; }

bold "==> Restarting ${SERVICE} ..."
if ! systemctl restart "${SERVICE}"; then
  red "FAILED: systemctl restart ${SERVICE} returned non-zero."
  exit 1
fi

# ---- wait for the app to answer health ----
bold "==> Waiting for ${SERVICE} to answer ${HEALTH_PATH} (max ${HEALTH_TIMEOUT}s) ..."
up=0
for ((i=1; i<=HEALTH_TIMEOUT; i++)); do
  code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "${BASE}${HEALTH_PATH}" || true)
  if [[ "${code}" == "200" ]]; then
    up=1
    green "    app is up (${HEALTH_PATH} -> 200 after ${i}s)"
    break
  fi
  sleep 1
done

if [[ "${up}" != "1" ]]; then
  red "FAILED: ${SERVICE} did not return 200 on ${HEALTH_PATH} within ${HEALTH_TIMEOUT}s."
  red "        Check: journalctl -u ${SERVICE} -n 50 --no-pager"
  exit 1
fi

# ---- verify every critical route is registered (not 404) ----
bold "==> Verifying critical routes are registered ..."
fail=0
for spec in "${CRITICAL_ROUTES[@]}"; do
  method="${spec%% *}"
  rest="${spec#* }"
  path="${rest%% *}"
  body=""
  if [[ "${rest}" == *" "* ]]; then
    body="${rest#* }"
  fi

  if [[ -n "${body}" ]]; then
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 \
      -X "${method}" -H 'Content-Type: application/json' -d "${body}" \
      "${BASE}${path}" || true)
  else
    code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 \
      -X "${method}" "${BASE}${path}" || true)
  fi

  if [[ "${code}" == "404" ]]; then
    red   "    ✗ ${method} ${path} -> 404  (ROUTE MISSING / STALE PROCESS)"
    fail=1
  else
    green "    ✓ ${method} ${path} -> ${code}  (route registered)"
  fi
done

echo
if [[ "${fail}" == "1" ]]; then
  red "======================================================================"
  red " DEPLOY GUARD FAILED: a critical route returned 404 after restart."
  red " The live process is missing routes that exist in the code on disk."
  red " Do NOT report this as deployed. Investigate before proceeding:"
  red "   journalctl -u ${SERVICE} -n 80 --no-pager | grep -i -E 'import|error|register'"
  red "======================================================================"
  exit 2
fi

green "======================================================================"
green " OK: ${SERVICE} restarted and all critical routes serve. Safe to deploy."
green "======================================================================"
exit 0
