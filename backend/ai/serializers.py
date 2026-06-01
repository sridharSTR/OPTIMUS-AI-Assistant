from rest_framework import serializers

from .models import Conversation, Memory, Message, NLPEvent, ResponseCache, ResumeAnalysis


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ("id", "role", "content", "intent", "sentiment", "sentiment_score", "entities", "created_at")


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ("id", "title", "created_at", "updated_at", "messages")


class ChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField()
    conversation_id = serializers.IntegerField(required=False, allow_null=True)


class MemorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Memory
        fields = ("id", "key", "value", "importance", "created_at", "last_accessed_at")
        read_only_fields = ("id", "created_at", "last_accessed_at")


class NLPEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = NLPEvent
        fields = (
            "id",
            "intent",
            "sentiment",
            "sentiment_score",
            "entities",
            "search_triggered",
            "handled_locally",
            "cache_hit",
            "ai_called",
            "route",
            "created_at",
        )


class ResponseCacheSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResponseCache
        fields = ("id", "normalized_question", "response", "intent", "ttl_seconds", "is_web_result", "hits", "created_at", "updated_at")


class ResumeAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeAnalysis
        fields = (
            "id",
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


class ResumeUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if not value.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("Upload a PDF resume.")
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("Resume PDF must be 5 MB or smaller.")
        return value
