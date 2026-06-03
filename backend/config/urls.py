from django.contrib import admin
from django.urls import include, path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from users.token_views import CookieTokenRefreshView


@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request):
    return Response(
        {
            "name": "OPTIMUS API",
            "status": "ok",
            "frontend": "http://localhost:5173/",
            "endpoints": {
                "admin": "/admin/",
                "register": "/api/users/register/",
                "verify_otp": "/api/users/verify-otp/",
                "login": "/api/users/login/",
                "logout": "/api/users/logout/",
                "me": "/api/users/me/",
                "conversations": "/api/ai/conversations/",
                "chat": "/api/ai/chat/",
                "rag_upload": "/api/rag/upload/",
                "rag_documents": "/api/rag/documents/",
                "rag_chat": "/api/rag/chat/",
                "token_refresh": "/api/token/refresh/",
            },
        }
    )


urlpatterns = [
    path("", api_root, name="api_root"),
    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),
    path("api/admin/", include("users.admin_urls")),
    path("api/ai/", include("ai.urls")),
    path("api/rag/", include("ai.rag_urls")),
    path("api/token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
]
