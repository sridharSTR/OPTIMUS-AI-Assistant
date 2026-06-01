from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenRefreshView

from .cookies import set_auth_cookies


class CookieTokenRefreshView(TokenRefreshView):
    serializer_class = TokenRefreshSerializer

    def post(self, request, *args, **kwargs):
        refresh = request.COOKIES.get(settings.JWT_REFRESH_COOKIE) or request.data.get("refresh")
        if not refresh:
            raise InvalidToken("Refresh cookie is missing.")

        serializer = self.get_serializer(data={"refresh": refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc

        data = serializer.validated_data
        response = Response(
            {
                "detail": "Token refreshed.",
                "access": data["access"],
                "refresh": data.get("refresh"),
            },
            status=status.HTTP_200_OK,
        )
        return set_auth_cookies(response, data["access"], data.get("refresh"))
