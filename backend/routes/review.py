"""
Game Review API — Phase 1 (engine pipeline, no UI).

Routes:
  POST /api/review            {pgn}  → {review_id, status}
  GET  /api/review/<id>              → {status, progress, result?}

Analysis runs on a single background worker (see services.game_review) and is
cached on disk by the normalized-PGN hash, so a reviewed game never re-analyzes.
"""

from __future__ import annotations

import logging

from flask import Blueprint, jsonify, request

from services import game_review

logger = logging.getLogger(__name__)

review_bp = Blueprint("review", __name__, url_prefix="/api")


@review_bp.route("/review", methods=["POST"])
def create_review():
    body = request.get_json(silent=True) or {}
    pgn = body.get("pgn")
    if not pgn or not isinstance(pgn, str):
        return jsonify({"error": "Missing 'pgn' in request body"}), 400

    try:
        review_id, status = game_review.submit_review(pgn)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({"review_id": review_id, "status": status})


@review_bp.route("/review/<review_id>", methods=["GET"])
def get_review(review_id: str):
    review = game_review.get_review(review_id)
    if review is None:
        return jsonify({"error": "Review not found"}), 404
    return jsonify(review)
