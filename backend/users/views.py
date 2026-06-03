from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .cookies import clear_auth_cookies, set_auth_cookies
from .serializers import LoginSerializer, RegisterSerializer, UserSerializer, VerifyOTPSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        if serializer.context.get("pending_admin_request"):
            return Response(
                {
                    "requires_otp": False,
                    "admin_request_pending": True,
                    "detail": serializer.context.get(
                        "admin_request_message",
                        "Admin registration request sent. An existing admin can approve it from the admin panel.",
                    ),
                    "email": user.email,
                },
                status=status.HTTP_202_ACCEPTED,
            )

        data = {
            "requires_otp": True,
            "detail": serializer.context.get("otp_message", "OTP sent to your email. Please verify to continue."),
            "email": user.email,
        }
        if settings.SHOW_DEV_OTP:
            data["dev_otp"] = serializer.context.get("otp_code")
        return Response(data, status=status.HTTP_201_CREATED)


class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if data.get("purpose") == "register":
            return Response(
                {
                    "user": data["user"],
                    "purpose": data["purpose"],
                    "registration_verified": True,
                    "detail": data["detail"],
                },
                status=status.HTTP_201_CREATED,
            )

        access = data["access"]
        refresh = data["refresh"]
        response = Response(
            {
                "user": data["user"],
                "purpose": data["purpose"],
                "detail": "Authentication successful.",
            },
            status=status.HTTP_201_CREATED,
        )
        return set_auth_cookies(response, access, refresh)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        if settings.SHOW_DEV_OTP:
            data["dev_otp"] = serializer.context.get("otp_code")
        return Response(data, status=status.HTTP_202_ACCEPTED)


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        return clear_auth_cookies(response)


class MeView(APIView):
    def get(self, request):
        if request.user.email.lower() == request.user.PRIMARY_SUPER_ADMIN_EMAIL:
            request.user.save()
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
