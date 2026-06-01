from django.conf import settings


def set_auth_cookies(response, access_token, refresh_token=None):
    response.set_cookie(
        settings.JWT_AUTH_COOKIE,
        str(access_token),
        max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=settings.JWT_COOKIE_SAMESITE,
        path="/",
    )
    if refresh_token is not None:
        response.set_cookie(
            settings.JWT_REFRESH_COOKIE,
            str(refresh_token),
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            httponly=True,
            secure=settings.JWT_COOKIE_SECURE,
            samesite=settings.JWT_COOKIE_SAMESITE,
            path="/",
        )
    return response


def clear_auth_cookies(response):
    response.delete_cookie(
        settings.JWT_AUTH_COOKIE,
        path="/",
        samesite=settings.JWT_COOKIE_SAMESITE,
    )
    response.delete_cookie(
        settings.JWT_REFRESH_COOKIE,
        path="/",
        samesite=settings.JWT_COOKIE_SAMESITE,
    )
    return response
