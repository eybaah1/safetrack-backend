"""
WebSocket authentication middleware.
Extracts JWT token from query string and authenticates the user.
"""

from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from accounts.models import User


@database_sync_to_async
def get_user_from_token(token_string):
    """Validate JWT token and return the user."""
    try:
        token = AccessToken(token_string)
        user_id = token["user_id"]
        return User.objects.get(id=user_id)
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    WebSocket connection authentication.

    Client connects with:
      ws://localhost:8000/ws/chat/<chat_id>/?token=<jwt_access_token>
    """

    async def __call__(self, scope, receive, send):
        # Parse query string for token
        query_string = scope.get("query_string", b"").decode("utf-8")
        params = parse_qs(query_string)
        token_list = params.get("token", [])

        if token_list:
            scope["user"] = await get_user_from_token(token_list[0])
        else:
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)