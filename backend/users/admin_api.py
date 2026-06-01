from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from ai.models import Conversation, Memory, Message, NLPEvent, ResponseCache, ResumeAnalysis


User = get_user_model()
ADMIN_ROLES = {"super_admin", "admin", "moderator"}
ROLE_ORDER = ["user", "moderator", "admin", "super_admin"]
PRIMARY_SUPER_ADMIN_EMAIL = "sivasridhar2502@gmail.com"


class IsAdminRole(BasePermission):
    message = "Admin role required."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and not getattr(user, "is_banned", False)
            and getattr(user, "role", "user") in ADMIN_ROLES
        )


class AdminUserSerializer(serializers.ModelSerializer):
    conversation_count = serializers.IntegerField(read_only=True)
    message_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "display_name",
            "role",
            "email_verified",
            "is_active",
            "is_banned",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "conversation_count",
            "message_count",
        )


class AdminMemorySerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.display_name", read_only=True)

    class Meta:
        model = Memory
        fields = ("id", "user", "user_email", "user_name", "key", "value", "importance", "created_at", "last_accessed_at")
        read_only_fields = ("id", "user", "user_email", "user_name", "created_at", "last_accessed_at")


class AdminResumeAnalysisSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.display_name", read_only=True)

    class Meta:
        model = ResumeAnalysis
        fields = (
            "id",
            "user",
            "user_email",
            "user_name",
            "filename",
            "skills",
            "found_skills",
            "education",
            "projects",
            "experience",
            "missing_skills",
            "detected_sections",
            "missing_sections",
            "skills_score",
            "sections_score",
            "score_explanation",
            "suggestions",
            "interview_questions",
            "score",
            "created_at",
        )
        read_only_fields = fields


def can_manage_users(user):
    return getattr(user, "role", "user") in {"super_admin", "admin"}


def role_rank(role):
    return ROLE_ORDER.index(role) if role in ROLE_ORDER else 0


def require_super_admin_for_role_change(request, target_role):
    if target_role == "super_admin" and request.user.role != "super_admin":
        return Response({"detail": "Only a super admin can assign the super_admin role."}, status=status.HTTP_403_FORBIDDEN)
    return None


def get_target_user(user_id):
    return get_object_or_404(User, id=user_id)


class AdminDashboardView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        total_events = NLPEvent.objects.count()
        cache_hits = NLPEvent.objects.filter(cache_hit=True).count()
        today = timezone.now() - timedelta(days=1)
        return Response(
            {
                "total_users": User.objects.count(),
                "verified_users": User.objects.filter(email_verified=True).count(),
                "banned_users": User.objects.filter(is_banned=True).count(),
                "active_conversations": Conversation.objects.count(),
                "total_messages": Message.objects.count(),
                "ai_requests_count": NLPEvent.objects.filter(ai_called=True).count(),
                "cache_hit_ratio": round((cache_hits / total_events) * 100, 1) if total_events else 0,
                "resume_analysis_count": ResumeAnalysis.objects.count(),
                "recent_activity_count": NLPEvent.objects.filter(created_at__gte=today).count(),
                "memory_count": Memory.objects.count(),
                "response_cache_entries": ResponseCache.objects.count(),
                "latest_users": AdminUserSerializer(User.objects.order_by("-date_joined")[:5], many=True).data,
            }
        )


class AdminUsersView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        role = request.query_params.get("role", "").strip()
        users = User.objects.annotate(
            conversation_count=Count("conversations", distinct=True),
            message_count=Count("conversations__messages", distinct=True),
        ).order_by("-date_joined")
        if query:
            users = users.filter(
                Q(username__icontains=query)
                | Q(email__icontains=query)
                | Q(display_name__icontains=query)
            )
        if role:
            users = users.filter(role=role)
        return Response(AdminUserSerializer(users[:200], many=True).data)

    def delete(self, request):
        if not can_manage_users(request.user):
            return Response({"detail": "Only admins can delete users."}, status=status.HTTP_403_FORBIDDEN)
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"detail": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        target = get_target_user(user_id)
        if target.email.lower() == PRIMARY_SUPER_ADMIN_EMAIL:
            return Response({"detail": "The primary super admin cannot be deleted."}, status=status.HTTP_403_FORBIDDEN)
        if target.id == request.user.id:
            return Response({"detail": "You cannot delete your own account."}, status=status.HTTP_400_BAD_REQUEST)
        if role_rank(target.role) >= role_rank(request.user.role):
            return Response({"detail": "You cannot delete a user with an equal or higher role."}, status=status.HTTP_403_FORBIDDEN)
        target.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminRoleChangeView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request):
        if not can_manage_users(request.user):
            return Response({"detail": "Only admins can change user roles."}, status=status.HTTP_403_FORBIDDEN)
        user_id = request.data.get("user_id")
        role = request.data.get("role")
        if not user_id:
            return Response({"detail": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        target = get_target_user(user_id)

        if target.email.lower() == PRIMARY_SUPER_ADMIN_EMAIL:
            target.save()
            return Response(AdminUserSerializer(target).data)
        if target.id == request.user.id:
            return Response({"detail": "You cannot change your own role."}, status=status.HTTP_400_BAD_REQUEST)

        if role is None:
            role = ROLE_ORDER[min(role_rank(target.role) + 1, len(ROLE_ORDER) - 1)]
        if role not in dict(User.Role.choices):
            return Response({"detail": "Invalid role."}, status=status.HTTP_400_BAD_REQUEST)
        denied = require_super_admin_for_role_change(request, role)
        if denied:
            return denied
        if role_rank(target.role) >= role_rank(request.user.role) or role_rank(role) >= role_rank(request.user.role):
            return Response({"detail": "You cannot assign or manage an equal or higher role."}, status=status.HTTP_403_FORBIDDEN)
        target.role = role
        target.is_staff = role in ADMIN_ROLES
        target.is_superuser = role == "super_admin"
        target.save(update_fields=["role", "is_staff", "is_superuser"])
        return Response(AdminUserSerializer(target).data)


class AdminRoleDemoteView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request):
        if not can_manage_users(request.user):
            return Response({"detail": "Only admins can change user roles."}, status=status.HTTP_403_FORBIDDEN)
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"detail": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        target = get_target_user(user_id)
        if target.email.lower() == PRIMARY_SUPER_ADMIN_EMAIL:
            return Response({"detail": "The primary super admin cannot be demoted."}, status=status.HTTP_403_FORBIDDEN)
        if target.id == request.user.id:
            return Response({"detail": "You cannot demote your own account."}, status=status.HTTP_400_BAD_REQUEST)
        if role_rank(target.role) >= role_rank(request.user.role):
            return Response({"detail": "You cannot demote a user with an equal or higher role."}, status=status.HTTP_403_FORBIDDEN)
        target.role = ROLE_ORDER[max(role_rank(target.role) - 1, 0)]
        target.is_staff = target.role in ADMIN_ROLES
        target.is_superuser = target.role == "super_admin"
        target.save(update_fields=["role", "is_staff", "is_superuser"])
        return Response(AdminUserSerializer(target).data)


class AdminBanUserView(APIView):
    permission_classes = [IsAdminRole]

    def post(self, request):
        if not can_manage_users(request.user):
            return Response({"detail": "Only admins can ban users."}, status=status.HTTP_403_FORBIDDEN)
        user_id = request.data.get("user_id")
        is_banned = bool(request.data.get("is_banned", True))
        if not user_id:
            return Response({"detail": "user_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        target = get_target_user(user_id)
        if target.email.lower() == PRIMARY_SUPER_ADMIN_EMAIL:
            return Response({"detail": "The primary super admin cannot be banned."}, status=status.HTTP_403_FORBIDDEN)
        if target.id == request.user.id:
            return Response({"detail": "You cannot ban your own account."}, status=status.HTTP_400_BAD_REQUEST)
        if role_rank(target.role) >= role_rank(request.user.role):
            return Response({"detail": "You cannot ban a user with an equal or higher role."}, status=status.HTTP_403_FORBIDDEN)
        target.is_banned = is_banned
        target.is_active = not is_banned
        target.save(update_fields=["is_banned", "is_active"])
        return Response(AdminUserSerializer(target).data)


class AdminConversationSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_name = serializers.CharField(source="user.display_name", read_only=True)
    message_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Conversation
        fields = ("id", "title", "user", "user_email", "user_name", "message_count", "created_at", "updated_at")


class AdminConversationsView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        user_id = request.query_params.get("user_id")
        conversations = Conversation.objects.select_related("user").annotate(message_count=Count("messages")).order_by("-updated_at")
        if query:
            conversations = conversations.filter(Q(title__icontains=query) | Q(messages__content__icontains=query)).distinct()
        if user_id:
            conversations = conversations.filter(user_id=user_id)
        return Response(AdminConversationSerializer(conversations[:200], many=True).data)

    def delete(self, request):
        if request.user.role == "moderator":
            return Response({"detail": "Moderators can view conversations but cannot delete them."}, status=status.HTTP_403_FORBIDDEN)
        conversation_id = request.data.get("conversation_id")
        if not conversation_id:
            return Response({"detail": "conversation_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        Conversation.objects.filter(id=conversation_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminMessageSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="conversation.user.email", read_only=True)
    conversation_title = serializers.CharField(source="conversation.title", read_only=True)

    class Meta:
        model = Message
        fields = ("id", "conversation", "conversation_title", "user_email", "role", "content", "intent", "sentiment", "sentiment_score", "created_at")


class AdminMessagesView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        conversation_id = request.query_params.get("conversation_id")
        user_id = request.query_params.get("user_id")
        messages = Message.objects.select_related("conversation", "conversation__user").order_by("-created_at")
        if query:
            messages = messages.filter(content__icontains=query)
        if conversation_id:
            messages = messages.filter(conversation_id=conversation_id)
        if user_id:
            messages = messages.filter(conversation__user_id=user_id)
        return Response(AdminMessageSerializer(messages[:300], many=True).data)


class AdminAnalyticsView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        events = NLPEvent.objects.all()
        total = events.count()
        cache_hits = events.filter(cache_hit=True).count()
        return Response(
            {
                "most_used_intents": list(events.values("intent").annotate(count=Count("id")).order_by("-count")[:10]),
                "ai_response_count": events.filter(ai_called=True).count(),
                "average_response_time": None,
                "cache_performance": {
                    "cache_hits": cache_hits,
                    "total_events": total,
                    "hit_ratio": round((cache_hits / total) * 100, 1) if total else 0,
                    "cache_entries": ResponseCache.objects.count(),
                    "average_cache_hits": round(ResponseCache.objects.aggregate(value=Avg("hits"))["value"] or 0, 2),
                },
                "route_usage": list(events.values("route").annotate(count=Count("id")).order_by("-count")[:10]),
                "sentiment": list(events.values("sentiment").annotate(count=Count("id")).order_by("-count")),
            }
        )


class AdminMemoriesView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        memories = Memory.objects.select_related("user").order_by("-created_at")
        if query:
            memories = memories.filter(Q(key__icontains=query) | Q(value__icontains=query) | Q(user__email__icontains=query))
        return Response(AdminMemorySerializer(memories[:200], many=True).data)

    def patch(self, request):
        if request.user.role == "moderator":
            return Response({"detail": "Moderators can view memories but cannot edit them."}, status=status.HTTP_403_FORBIDDEN)
        memory_id = request.data.get("memory_id")
        if not memory_id:
            return Response({"detail": "memory_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        memory = get_object_or_404(Memory, id=memory_id)
        serializer = AdminMemorySerializer(memory, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request):
        if request.user.role == "moderator":
            return Response({"detail": "Moderators can view memories but cannot delete them."}, status=status.HTTP_403_FORBIDDEN)
        memory_id = request.data.get("memory_id")
        if not memory_id:
            return Response({"detail": "memory_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        Memory.objects.filter(id=memory_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminResumeAnalysesView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        analyses = ResumeAnalysis.objects.select_related("user").order_by("-created_at")
        if query:
            analyses = analyses.filter(Q(filename__icontains=query) | Q(user__email__icontains=query))
        return Response(AdminResumeAnalysisSerializer(analyses[:200], many=True).data)

    def delete(self, request):
        if request.user.role == "moderator":
            return Response({"detail": "Moderators can view resume analyses but cannot delete them."}, status=status.HTTP_403_FORBIDDEN)
        analysis_id = request.data.get("analysis_id")
        if not analysis_id:
            return Response({"detail": "analysis_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        ResumeAnalysis.objects.filter(id=analysis_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
