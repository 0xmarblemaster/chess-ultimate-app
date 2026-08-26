"""Supabase-backed persistence for coach sessions.

Write-through layer for :class:`~src.sessions.SessionStore`: writes go to
Supabase in the background so message appends stay off the critical path, and
reads lazy-load a session + its messages on cache miss (this is what makes a
Hermes restart survivable).

Every Supabase interaction is wrapped so a failure — missing env vars, network
error, or missing tables — degrades to pure in-memory operation and can NEVER
propagate into a chat/voice turn. Follows the httpx REST pattern used in
``user_profile.py`` and ``platform_linking.py``.
"""

import logging
import os
import threading
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

TIMEOUT = 10


class SessionPersistence:
    """Best-effort Supabase persistence for coach sessions.

    All public methods swallow every exception. Writes run in daemon threads;
    reads block (only on cache miss) but still degrade to ``None``/``[]``.
    """

    def __init__(self, url: str = None, key: str = None):
        self.url = url if url is not None else os.environ.get("SUPABASE_URL", "")
        self.key = key if key is not None else os.environ.get("SUPABASE_SERVICE_KEY", "")
        self._warned = False
        if not self.enabled:
            self._warn_once()

    @property
    def enabled(self) -> bool:
        return bool(self.url and self.key)

    def _warn_once(self) -> None:
        if not self._warned:
            logger.warning(
                "Supabase not configured (SUPABASE_URL / SUPABASE_SERVICE_KEY); "
                "coach sessions are in-memory only and will not survive restarts"
            )
            self._warned = True

    def _headers(self) -> dict:
        return {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _run_bg(fn, *args) -> None:
        """Run a write in a daemon thread, keeping latency off the hot path."""
        t = threading.Thread(target=fn, args=args, daemon=True)
        t.start()

    # ------------------------------------------------------------------ writes

    def persist_session(self, session_id: str, user_id: str, board_state: str) -> None:
        if not self.enabled:
            return
        self._run_bg(self._persist_session, session_id, user_id, board_state)

    def _persist_session(self, session_id: str, user_id: str, board_state: str) -> None:
        try:
            now = datetime.now(timezone.utc).isoformat()
            headers = self._headers()
            headers["Prefer"] = "resolution=merge-duplicates"
            httpx.post(
                f"{self.url}/rest/v1/coach_sessions",
                json={
                    "id": session_id,
                    "user_id": user_id,
                    "board_state": board_state,
                    "created_at": now,
                    "updated_at": now,
                },
                headers=headers,
                timeout=TIMEOUT,
            ).raise_for_status()
        except Exception:
            logger.debug("Failed to persist coach session %s", session_id, exc_info=True)

    def persist_message(
        self, session_id: str, role: str, content: str, source: str
    ) -> None:
        if not self.enabled:
            return
        self._run_bg(self._persist_message, session_id, role, content, source)

    def _persist_message(
        self, session_id: str, role: str, content: str, source: str
    ) -> None:
        try:
            httpx.post(
                f"{self.url}/rest/v1/coach_messages",
                json={
                    "session_id": session_id,
                    "role": role,
                    "content": content,
                    "source": source,
                },
                headers=self._headers(),
                timeout=TIMEOUT,
            ).raise_for_status()
        except Exception:
            logger.debug(
                "Failed to persist coach message for session %s", session_id, exc_info=True
            )

    def update_board_state(self, session_id: str, fen: str) -> None:
        if not self.enabled:
            return
        self._run_bg(self._update_board_state, session_id, fen)

    def _update_board_state(self, session_id: str, fen: str) -> None:
        try:
            httpx.patch(
                f"{self.url}/rest/v1/coach_sessions",
                params={"id": f"eq.{session_id}"},
                json={
                    "board_state": fen,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                headers=self._headers(),
                timeout=TIMEOUT,
            ).raise_for_status()
        except Exception:
            logger.debug(
                "Failed to update board_state for session %s", session_id, exc_info=True
            )

    def delete_session(self, session_id: str) -> None:
        if not self.enabled:
            return
        self._run_bg(self._delete_session, session_id)

    def _delete_session(self, session_id: str) -> None:
        try:
            httpx.delete(
                f"{self.url}/rest/v1/coach_sessions",
                params={"id": f"eq.{session_id}"},
                headers=self._headers(),
                timeout=TIMEOUT,
            ).raise_for_status()
        except Exception:
            logger.debug("Failed to delete coach session %s", session_id, exc_info=True)

    # ------------------------------------------------------------------- reads

    def load_session(self, session_id: str) -> dict | None:
        """Fetch a single coach_sessions row. Returns None on miss/failure."""
        if not self.enabled:
            return None
        try:
            resp = httpx.get(
                f"{self.url}/rest/v1/coach_sessions",
                params={"id": f"eq.{session_id}", "select": "*"},
                headers=self._headers(),
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            rows = resp.json()
            return rows[0] if rows else None
        except Exception:
            logger.debug("Failed to load coach session %s", session_id, exc_info=True)
            return None

    def load_user_sessions(self, user_id: str) -> list[dict]:
        """Fetch all coach_sessions rows for a user. Returns [] on failure."""
        if not self.enabled:
            return []
        try:
            resp = httpx.get(
                f"{self.url}/rest/v1/coach_sessions",
                params={"user_id": f"eq.{user_id}", "select": "*"},
                headers=self._headers(),
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json() or []
        except Exception:
            logger.debug("Failed to load coach sessions for %s", user_id, exc_info=True)
            return []

    def load_messages(self, session_id: str) -> list[dict]:
        """Fetch coach_messages for a session, ordered oldest-first."""
        if not self.enabled:
            return []
        try:
            resp = httpx.get(
                f"{self.url}/rest/v1/coach_messages",
                params={
                    "session_id": f"eq.{session_id}",
                    "select": "*",
                    "order": "id.asc",
                },
                headers=self._headers(),
                timeout=TIMEOUT,
            )
            resp.raise_for_status()
            return resp.json() or []
        except Exception:
            logger.debug(
                "Failed to load coach messages for session %s", session_id, exc_info=True
            )
            return []
