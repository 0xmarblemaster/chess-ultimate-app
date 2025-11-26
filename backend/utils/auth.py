"""
Clerk Authentication - JWT Verification Middleware
Protects API routes and extracts user_id from Clerk tokens
"""

from functools import wraps
from flask import request, jsonify
import jwt
import os
import requests

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")

# Clerk JWKS URL for RSA public key verification
# Note: This is a simplified version. Production should cache JWKS.
CLERK_JWKS_URL = "https://stunning-arachnid-84.clerk.accounts.dev/.well-known/jwks.json"


def verify_clerk_token(f):
    """
    Decorator to verify Clerk JWT tokens.
    Extracts user_id from token and adds to request.user_id

    Usage:
        @app.route('/api/protected')
        @verify_clerk_token
        def protected_route():
            user_id = request.user_id
            return jsonify({"user_id": user_id})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')

        if not auth_header.startswith('Bearer '):
            return jsonify({"error": "No token provided"}), 401

        token = auth_header.replace('Bearer ', '')

        if not token:
            return jsonify({"error": "No token provided"}), 401

        try:
            # Decode JWT without verification (for development)
            # TODO: In production, verify signature using Clerk's JWKS
            decoded = jwt.decode(
                token,
                options={"verify_signature": False}  # DEVELOPMENT ONLY
            )

            # Extract user ID from Clerk token
            user_id = decoded.get('sub')

            if not user_id:
                return jsonify({"error": "Invalid token: no user ID"}), 401

            # Add user_id to request context
            request.user_id = user_id

            return f(*args, **kwargs)

        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"error": f"Invalid token: {str(e)}"}), 401
        except Exception as e:
            return jsonify({"error": f"Authentication error: {str(e)}"}), 500

    return decorated


def get_current_user_id() -> str:
    """
    Get current authenticated user ID from request context.
    Must be called within a route protected by @verify_clerk_token
    """
    return getattr(request, 'user_id', None)
